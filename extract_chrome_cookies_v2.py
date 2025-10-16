#!/usr/bin/env python3
"""
Extract cookies and authentication tokens from Chrome profile for X/Twitter automation.
Works even while Chrome is running by using SQLite backup API.
"""
import sqlite3
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

CHROME_PROFILE = "Default"  # Changed from Profile 2 to Default (most recent activity)
CHROME_PATH = Path.home() / "Library/Application Support/Google/Chrome"
PROFILE_PATH = CHROME_PATH / CHROME_PROFILE
COOKIES_DB = PROFILE_PATH / "Cookies"

# Output directory
OUTPUT_DIR = Path("/Users/doctordre/projects/4bot/auth_data")
OUTPUT_DIR.mkdir(exist_ok=True)

def get_chrome_encryption_key() -> bytes:
    """
    Retrieve Chrome's encryption key for macOS.
    """
    password = b'peanuts'
    try:
        cmd = ['security', 'find-generic-password', '-wa', 'Chrome']
        keychain_password = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).strip()
        if keychain_password:
            password = keychain_password
            print("[+] Using password from Keychain")
    except subprocess.CalledProcessError:
        print("[+] Using default password")

    salt = b'saltysalt'
    iterations = 1003
    key = PBKDF2(password, salt, dkLen=16, count=iterations)
    return key

def decrypt_chrome_cookie(encrypted_value: bytes, key: bytes) -> str:
    """
    Decrypt Chrome cookie value using AES.
    """
    if not encrypted_value:
        return ""

    try:
        # Chrome v10+ uses 'v10' or 'v11' prefix
        if encrypted_value[:3] in [b'v10', b'v11']:
            encrypted_value = encrypted_value[3:]
            nonce = encrypted_value[:12]
            ciphertext = encrypted_value[12:-16]
            tag = encrypted_value[-16:]

            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)
            return decrypted.decode('utf-8', errors='ignore')
        else:
            # Older Chrome versions use AES-CBC
            iv = b' ' * 16
            cipher = AES.new(key, AES.MODE_CBC, IV=iv)
            decrypted = cipher.decrypt(encrypted_value)
            padding_length = decrypted[-1] if decrypted else 0
            if 1 <= padding_length <= 16:
                decrypted = decrypted[:-padding_length]
            return decrypted.decode('utf-8', errors='ignore')
    except Exception:
        return ""

def convert_chrome_time(chrome_time: int) -> datetime:
    """
    Convert Chrome timestamp to Python datetime.
    """
    if chrome_time:
        epoch_start = datetime(1601, 1, 1)
        delta = timedelta(microseconds=chrome_time)
        return epoch_start + delta
    return None

def extract_cookies():
    """
    Extract cookies from Chrome profile for X/Twitter.
    Uses SQLite backup API to work even while Chrome is running.
    """
    print("=" * 60)
    print("Chrome Cookie Extractor for X/Twitter")
    print("=" * 60)
    print(f"[*] Profile: {CHROME_PROFILE}")
    print(f"[*] Cookies DB: {COOKIES_DB}")

    if not COOKIES_DB.exists():
        print(f"[ERROR] Cookies database not found at: {COOKIES_DB}")
        return

    # Get encryption key
    key = get_chrome_encryption_key()

    try:
        # Connect directly to the cookies database
        # SQLite allows read access even if Chrome is using it
        conn = sqlite3.connect(f"file:{COOKIES_DB}?mode=ro", uri=True)
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

        print(f"\n[+] Found {len(cookies)} cookies for X/Twitter domains")
        print()

        # Process and save cookies
        cookies_data = []
        cookies_netscape = []
        important_cookies = {}

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

                # Netscape format
                netscape_line = f"{host_key}\tTRUE\t{path}\t{'TRUE' if is_secure else 'FALSE'}\t{int(expiry.timestamp()) if expiry else 0}\t{name}\t{decrypted_value}\n"
                cookies_netscape.append(netscape_line)

                # Track important authentication cookies
                if name in ['auth_token', 'ct0', 'twid', 'kdt', 'guest_id', 'personalization_id']:
                    important_cookies[name] = decrypted_value
                    print(f"[✓] {name}: {decrypted_value[:60]}{'...' if len(decrypted_value) > 60 else ''}")

        conn.close()

        print(f"\n[+] Successfully extracted {len(cookies_data)} cookies")

        # Save cookies in JSON format
        json_file = OUTPUT_DIR / "x_cookies.json"
        with open(json_file, 'w') as f:
            json.dump(cookies_data, f, indent=2, default=str)
        print(f"[✓] Cookies saved to: {json_file}")

        # Save cookies in Netscape format
        netscape_file = OUTPUT_DIR / "x_cookies_netscape.txt"
        with open(netscape_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This file can be used with wget, curl, etc.\n")
            f.writelines(cookies_netscape)
        print(f"[✓] Netscape format saved to: {netscape_file}")

        # Save tokens separately
        tokens_file = OUTPUT_DIR / "x_tokens.json"
        with open(tokens_file, 'w') as f:
            json.dump(important_cookies, f, indent=2)
        print(f"[✓] Auth tokens saved to: {tokens_file}")

        # Save tokens as environment variables
        env_file = OUTPUT_DIR / "x_tokens.env"
        with open(env_file, 'w') as f:
            f.write("# X/Twitter Authentication Tokens\n")
            f.write("# Source this file: source x_tokens.env\n\n")
            for key, value in important_cookies.items():
                f.write(f"export X_{key.upper()}='{value}'\n")
        print(f"[✓] Environment file saved to: {env_file}")

        # Save tokens as simple key=value for easy parsing
        simple_tokens_file = OUTPUT_DIR / "x_tokens.txt"
        with open(simple_tokens_file, 'w') as f:
            for key, value in important_cookies.items():
                f.write(f"{key}={value}\n")
        print(f"[✓] Simple tokens file saved to: {simple_tokens_file}")

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total cookies extracted: {len(cookies_data)}")
        print(f"Important auth tokens: {len(important_cookies)}")
        print(f"Output directory: {OUTPUT_DIR}")
        print("=" * 60)

        return cookies_data, important_cookies

    except Exception as e:
        print(f"[ERROR] Failed to extract cookies: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    extract_cookies()
