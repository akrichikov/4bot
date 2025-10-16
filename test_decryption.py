#!/usr/bin/env python3
"""
Test decryption with detailed debugging.
"""
import sqlite3
import subprocess
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

CHROME_PATH = Path.home() / "Library/Application Support/Google/Chrome"
COOKIES_DB = CHROME_PATH / "Default/Cookies"

def get_key():
    password = b'peanuts'
    try:
        cmd = ['security', 'find-generic-password', '-wa', 'Chrome']
        keychain_password = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).strip()
        if keychain_password:
            password = keychain_password
            print(f"Keychain password: {password[:20]}...")
    except:
        print("Using default 'peanuts'")

    salt = b'saltysalt'
    iterations = 1003
    key = PBKDF2(password, salt, dkLen=16, count=iterations)
    print(f"Key (hex): {key.hex()}")
    return key

def decrypt(encrypted_value, key):
    print(f"\n--- Decrypting cookie ---")
    print(f"Length: {len(encrypted_value)} bytes")
    print(f"First 40 bytes (hex): {encrypted_value[:40].hex()}")
    print(f"Prefix: {encrypted_value[:3]}")

    try:
        if encrypted_value[:3] in [b'v10', b'v11']:
            print("Using AES-GCM (v10/v11)")
            encrypted_value = encrypted_value[3:]
            nonce = encrypted_value[:12]
            ciphertext = encrypted_value[12:-16]
            tag = encrypted_value[-16:]

            print(f"Nonce (hex): {nonce.hex()}")
            print(f"Tag (hex): {tag.hex()}")
            print(f"Ciphertext length: {len(ciphertext)}")

            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)
            result = decrypted.decode('utf-8', errors='ignore')
            print(f"Decrypted: {result}")
            return result
        else:
            print("Using AES-CBC (older format)")
            iv = b' ' * 16
            cipher = AES.new(key, AES.MODE_CBC, IV=iv)
            decrypted = cipher.decrypt(encrypted_value)
            padding_length = decrypted[-1] if decrypted else 0
            print(f"Padding length: {padding_length}")
            if 1 <= padding_length <= 16:
                decrypted = decrypted[:-padding_length]
            result = decrypted.decode('utf-8', errors='ignore')
            print(f"Decrypted: {result}")
            return result
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return ""

print("Testing Chrome cookie decryption...")
key = get_key()

conn = sqlite3.connect(f"file:{COOKIES_DB}?mode=ro", uri=True)
cursor = conn.cursor()

query = """
SELECT host_key, name, encrypted_value
FROM cookies
WHERE (host_key LIKE '%.x.com' OR host_key LIKE '%.twitter.com')
  AND name IN ('auth_token', 'ct0', 'kdt')
LIMIT 3
"""

cursor.execute(query)
cookies = cursor.fetchall()

print(f"\nTesting {len(cookies)} cookies:\n")

for host_key, name, encrypted_value in cookies:
    print(f"\n{'='*60}")
    print(f"Cookie: {name} from {host_key}")
    decrypted = decrypt(encrypted_value, key)
    if decrypted:
        print(f"✓ SUCCESS")
    else:
        print(f"✗ FAILED")

conn.close()
