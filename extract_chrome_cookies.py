#!/usr/bin/env python3
"""
Extract cookies and authentication tokens from Chrome profile for X/Twitter automation.
"""
import sqlite3
import json
import os
import subprocess
import base64
from pathlib import Path
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

CHROME_PROFILE = "Profile 2"
CHROME_PATH = Path.home() / "Library/Application Support/Google/Chrome"
PROFILE_PATH = CHROME_PATH / CHROME_PROFILE
COOKIES_DB = PROFILE_PATH / "Cookies"

# Output directory
OUTPUT_DIR = Path("/Users/doctordre/projects/4bot/auth_data")
OUTPUT_DIR.mkdir(exist_ok=True)

def get_chrome_encryption_key() -> bytes:
    """
    Retrieve Chrome's encryption key for macOS.
    Chrome on macOS uses PBKDF2 with keychain password or default 'peanuts'.
    """
    try:
        # Try to get password from macOS Keychain
        password = b'peanuts'
        try:
            cmd = ['security', 'find-generic-password', '-wa', 'Chrome']
            keychain_password = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).strip()
            if keychain_password:
                password = keychain_password
                print("Using password from Keychain")
        except subprocess.CalledProcessError:
            print("Using default password (keychain not available)")
            pass

        # Derive key using PBKDF2
        salt = b'saltysalt'
        iterations = 1003
        key = PBKDF2(password, salt, dkLen=16, count=iterations)

        print(f"Generated encryption key: {len(key)} bytes")
        return key
    except Exception as e:
        print(f"Error getting encryption key: {e}")
        import traceback
        traceback.print_exc()
        return None

def decrypt_chrome_cookie(encrypted_value: bytes, key: bytes) -> str:
    """
    Decrypt Chrome cookie value using AES.
    """
    try:
        # Chrome v10+ uses 'v10' or 'v11' prefix
        if encrypted_value[:3] == b'v10' or encrypted_value[:3] == b'v11':
            # Remove 'v10'/'v11' prefix
            encrypted_value = encrypted_value[3:]
            # Extract nonce (12 bytes) and ciphertext
            nonce = encrypted_value[:12]
            ciphertext = encrypted_value[12:-16]
            tag = encrypted_value[-16:]

            # Decrypt using AES-GCM
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)
            return decrypted.decode('utf-8', errors='ignore')
        elif encrypted_value[:3] == b'v20':
            # Newer Chrome versions
            print("v20 encryption detected (newer format)")
            return ""
        else:
            # Older Chrome versions use AES-CBC with PKCS7 padding
            iv = b' ' * 16
            cipher = AES.new(key, AES.MODE_CBC, IV=iv)
            decrypted = cipher.decrypt(encrypted_value)
            # Remove PKCS7 padding
            padding_length = decrypted[-1]
            if padding_length < 1 or padding_length > 16:
                return ""
            decrypted = decrypted[:-padding_length]
            return decrypted.decode('utf-8', errors='ignore')
    except Exception as e:
        # Silently fail for individual cookies
        return ""

def convert_chrome_time(chrome_time: int) -> datetime:
    """
    Convert Chrome timestamp to Python datetime.
    Chrome timestamps are in microseconds since 1601-01-01.
    """
    if chrome_time:
        epoch_start = datetime(1601, 1, 1)
        delta = timedelta(microseconds=chrome_time)
        return epoch_start + delta
    return None

def extract_cookies():
    """
    Extract cookies from Chrome profile for X/Twitter.
    """
    print(f"Extracting cookies from: {COOKIES_DB}")

    # Get encryption key
    key = get_chrome_encryption_key()
    if not key:
        print("Failed to get encryption key")
        return

    # Make a copy of the cookies database (Chrome locks it when running)
    temp_cookies = "/tmp/chrome_cookies_temp.db"
    import shutil
    try:
        shutil.copy2(COOKIES_DB, temp_cookies)
    except Exception as e:
        print(f"Error copying cookies database: {e}")
        print("Make sure Chrome is closed or the profile is not active")
        return

    try:
        # Connect to cookies database
        conn = sqlite3.connect(temp_cookies)
        cursor = conn.cursor()

        # Query cookies for X/Twitter domains
        query = """
        SELECT host_key, name, encrypted_value, path, expires_utc, is_secure, is_httponly, samesite
        FROM cookies
        WHERE host_key LIKE '%twitter.com%' OR host_key LIKE '%x.com%'
        ORDER BY host_key, name
        """

        cursor.execute(query)
        cookies = cursor.fetchall()

        print(f"Found {len(cookies)} cookies for X/Twitter")

        # Process and save cookies
        cookies_data = []
        cookies_netscape = []

        for cookie in cookies:
            host_key, name, encrypted_value, path, expires_utc, is_secure, is_httponly, samesite = cookie

            # Decrypt value
            decrypted_value = decrypt_chrome_cookie(encrypted_value, key)

            if decrypted_value:
                expiry = convert_chrome_time(expires_utc)

                cookie_dict = {
                    'domain': host_key,
                    'name': name,
                    'value': decrypted_value,
                    'path': path,
                    'expires': expiry.timestamp() if expiry else -1,
                    'secure': bool(is_secure),
                    'httpOnly': bool(is_httponly),
                    'sameSite': 'None' if samesite == 0 else ('Lax' if samesite == 1 else 'Strict')
                }
                cookies_data.append(cookie_dict)

                # Netscape format for compatibility
                netscape_line = f"{host_key}\tTRUE\t{path}\t{'TRUE' if is_secure else 'FALSE'}\t{int(expiry.timestamp()) if expiry else 0}\t{name}\t{decrypted_value}\n"
                cookies_netscape.append(netscape_line)

                print(f"  {name}: {decrypted_value[:50]}..." if len(decrypted_value) > 50 else f"  {name}: {decrypted_value}")

        conn.close()

        # Save cookies in JSON format
        json_file = OUTPUT_DIR / "x_cookies.json"
        with open(json_file, 'w') as f:
            json.dump(cookies_data, f, indent=2, default=str)
        print(f"\nCookies saved to: {json_file}")

        # Save cookies in Netscape format (for wget/curl)
        netscape_file = OUTPUT_DIR / "x_cookies_netscape.txt"
        with open(netscape_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.writelines(cookies_netscape)
        print(f"Cookies (Netscape format) saved to: {netscape_file}")

        # Extract important tokens
        tokens = {}
        for cookie in cookies_data:
            name = cookie['name']
            if name in ['auth_token', 'ct0', 'twid', 'kdt', 'guest_id', 'personalization_id']:
                tokens[name] = cookie['value']

        # Save tokens separately
        tokens_file = OUTPUT_DIR / "x_tokens.json"
        with open(tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        print(f"Tokens saved to: {tokens_file}")

        # Save tokens as environment variables format
        env_file = OUTPUT_DIR / "x_tokens.env"
        with open(env_file, 'w') as f:
            for key, value in tokens.items():
                f.write(f"X_{key.upper()}={value}\n")
        print(f"Tokens (env format) saved to: {env_file}")

        return cookies_data, tokens

    except Exception as e:
        print(f"Error extracting cookies: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temp file
        if os.path.exists(temp_cookies):
            os.remove(temp_cookies)

if __name__ == "__main__":
    print("Chrome Cookie Extractor for X/Twitter")
    print("=" * 50)
    extract_cookies()
