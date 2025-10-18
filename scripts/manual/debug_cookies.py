#!/usr/bin/env python3
"""
Debug script to check cookie encryption format.
"""
import sqlite3
from typing import Any as _Moved
from pathlib import Path

CHROME_PROFILE = "Profile 2"
CHROME_PATH = Path.home() / "Library/Application Support/Google/Chrome"
PROFILE_PATH = CHROME_PATH / CHROME_PROFILE
COOKIES_DB = PROFILE_PATH / "Cookies"

print(f"Connecting to: {COOKIES_DB}")

conn = sqlite3.connect(f"file:{COOKIES_DB}?mode=ro", uri=True)
cursor = conn.cursor()

query = """
SELECT host_key, name, encrypted_value, length(encrypted_value) as value_len
FROM cookies
WHERE host_key LIKE '%twitter.com%' OR host_key LIKE '%x.com%'
ORDER BY host_key, name
LIMIT 10
"""

cursor.execute(query)
cookies = cursor.fetchall()

print(f"\nFound {len(cookies)} cookies:\n")

for host_key, name, encrypted_value, value_len in cookies:
    prefix = encrypted_value[:3] if len(encrypted_value) >= 3 else b''
    print(f"Host: {host_key}")
    print(f"Name: {name}")
    print(f"Length: {value_len} bytes")
    print(f"Prefix: {prefix}")
    print(f"Hex (first 20 bytes): {encrypted_value[:20].hex()}")
    print("-" * 60)

conn.close()
