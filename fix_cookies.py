#!/usr/bin/env python3
"""Fix cookie format for Playwright compatibility."""

import json
from pathlib import Path

# Read the cookies
cookie_file = Path("auth_data/x_cookies.json")
with open(cookie_file, 'r') as f:
    cookies = json.load(f)

# Fix boolean fields
for cookie in cookies:
    # Convert secure field from 0/1 to boolean
    if 'secure' in cookie:
        cookie['secure'] = bool(cookie['secure'])

    # Convert httpOnly field from 0/1 to boolean if needed
    if 'httpOnly' in cookie and isinstance(cookie['httpOnly'], int):
        cookie['httpOnly'] = bool(cookie['httpOnly'])

    # Ensure sameSite is a string if present
    if 'sameSite' in cookie and isinstance(cookie['sameSite'], int):
        cookie['sameSite'] = 'None' if cookie['sameSite'] == 0 else 'Lax'

# Save the fixed cookies
with open(cookie_file, 'w') as f:
    json.dump(cookies, f, indent=2)

print(f"✅ Fixed {len(cookies)} cookies in {cookie_file}")
print("🔧 Converted numeric secure/httpOnly fields to booleans")