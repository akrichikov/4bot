#!/usr/bin/env python3
"""
Extract X/Twitter cookies using browser-cookie3.
This library handles modern Chrome encryption automatically.
Specifically targets Profile 13 (4botbsc@gmail.com).
"""
import browser_cookie3
import json
from pathlib import Path

# Output directory
OUTPUT_DIR = Path("/Users/doctordre/projects/4bot/auth_data")
OUTPUT_DIR.mkdir(exist_ok=True)

# Target Profile 13 - 4botbsc@gmail.com account
CHROME_PROFILE = Path.home() / "Library/Application Support/Google/Chrome/Profile 13"
COOKIES_DB = CHROME_PROFILE / "Cookies"

print("=" * 70)
print("X/Twitter Cookie Extractor (using browser-cookie3)")
print("Target Profile: Profile 13 (4botbsc@gmail.com)")
print("=" * 70)

try:
    # Verify profile exists
    if not COOKIES_DB.exists():
        print(f"\n[ERROR] Profile 13 not found at: {CHROME_PROFILE}")
        print("Please ensure the profile exists.")
        exit(1)

    # Get cookies from Chrome Profile 13
    # NOTE: Chrome must be closed for this to work reliably
    print(f"\n[*] Loading cookies from Profile 13...")
    print(f"[*] Cookies DB: {COOKIES_DB}")
    print("[!] Note: For best results, please close Chrome before running this.")

    # Load cookies from Chrome Profile 13
    cj = browser_cookie3.chrome(domain_name='.x.com', cookie_file=str(COOKIES_DB))

    # Also get twitter.com cookies
    cj_twitter = browser_cookie3.chrome(domain_name='.twitter.com', cookie_file=str(COOKIES_DB))

    # Convert to list
    cookies = list(cj) + list(cj_twitter)

    print(f"[+] Found {len(cookies)} cookies\n")

    # Process cookies
    cookies_data = []
    tokens = {}

    for cookie in cookies:
        cookie_dict = {
            'domain': cookie.domain,
            'name': cookie.name,
            'value': cookie.value,
            'path': cookie.path,
            'expires': cookie.expires if cookie.expires else -1,
            'secure': cookie.secure,
            'httpOnly': hasattr(cookie, 'httponly') and cookie.httponly or False
        }
        cookies_data.append(cookie_dict)

        # Track important authentication cookies
        if cookie.name in ['auth_token', 'ct0', 'twid', 'kdt', 'guest_id', 'personalization_id']:
            tokens[cookie.name] = cookie.value
            print(f"[✓] {cookie.name}: {cookie.value[:60]}{'...' if len(cookie.value) > 60 else ''}")

    if not cookies_data:
        print("\n[!] No cookies found. Possible reasons:")
        print("    1. You're not logged into X/Twitter in Chrome")
        print("    2. Chrome is running (try closing it)")
        print("    3. The profile being checked doesn't have X/Twitter cookies")
        exit(1)

    # Save cookies in JSON format
    json_file = OUTPUT_DIR / "x_cookies.json"
    with open(json_file, 'w') as f:
        json.dump(cookies_data, f, indent=2, default=str)
    print(f"\n[✓] Cookies saved to: {json_file}")

    # Save cookies in Netscape format
    netscape_file = OUTPUT_DIR / "x_cookies_netscape.txt"
    with open(netscape_file, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This file can be used with wget, curl, etc.\n")
        for cookie in cookies_data:
            line = f"{cookie['domain']}\tTRUE\t{cookie['path']}\t{'TRUE' if cookie['secure'] else 'FALSE'}\t{int(cookie['expires']) if cookie['expires'] > 0 else 0}\t{cookie['name']}\t{cookie['value']}\n"
            f.write(line)
    print(f"[✓] Netscape format saved to: {netscape_file}")

    # Save tokens
    if tokens:
        tokens_file = OUTPUT_DIR / "x_tokens.json"
        with open(tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        print(f"[✓] Auth tokens saved to: {tokens_file}")

        # Environment file
        env_file = OUTPUT_DIR / "x_tokens.env"
        with open(env_file, 'w') as f:
            f.write("# X/Twitter Authentication Tokens\n")
            f.write("# Source this file: source x_tokens.env\n\n")
            for key, value in tokens.items():
                f.write(f"export X_{key.upper()}='{value}'\n")
        print(f"[✓] Environment file saved to: {env_file}")

        # Simple tokens file
        simple_tokens_file = OUTPUT_DIR / "x_tokens.txt"
        with open(simple_tokens_file, 'w') as f:
            for key, value in tokens.items():
                f.write(f"{key}={value}\n")
        print(f"[✓] Simple tokens file saved to: {simple_tokens_file}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total cookies extracted: {len(cookies_data)}")
    print(f"Important auth tokens: {len(tokens)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)

    if not tokens:
        print("\n[!] WARNING: No authentication tokens found!")
        print("    This means you might not be logged in, or the session is in a different profile.")

except Exception as e:
    print(f"\n[ERROR] Failed to extract cookies: {e}")
    import traceback
    traceback.print_exc()
    print("\n[!] Troubleshooting:")
    print("    1. Make sure Chrome is completely closed")
    print("    2. Ensure you're logged into X/Twitter in Chrome")
    print("    3. Try running with sudo (if permission denied)")
