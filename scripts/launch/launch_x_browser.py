#!/usr/bin/env python3
"""
Launch Chrome browser with X/Twitter cookies pre-loaded.
Opens a visible browser window logged into 4botbsc@gmail.com account.
"""
import json
import os
from typing import Any as _Moved
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Paths
PROJECT_DIR = Path("/Users/doctordre/projects/4bot")
AUTH_DATA_DIR = PROJECT_DIR / "auth_data"
COOKIES_FILE = AUTH_DATA_DIR / "x_cookies.json"
TOKENS_FILE = AUTH_DATA_DIR / "x_tokens.json"

def load_cookies_from_file():
    """Load cookies from JSON file."""
    if not COOKIES_FILE.exists():
        print(f"[ERROR] Cookies file not found: {COOKIES_FILE}")
        print("Please run extract_x_cookies_simple.py first to extract cookies.")
        return None

    with open(COOKIES_FILE, 'r') as f:
        cookies = json.load(f)

    print(f"[✓] Loaded {len(cookies)} cookies from {COOKIES_FILE.name}")
    return cookies

def load_tokens_from_file():
    """Load authentication tokens from JSON file."""
    if not TOKENS_FILE.exists():
        print(f"[WARN] Tokens file not found: {TOKENS_FILE}")
        return None

    with open(TOKENS_FILE, 'r') as f:
        tokens = json.load(f)

    print(f"[✓] Loaded {len(tokens)} authentication tokens")
    return tokens

def launch_browser_with_cookies():
    """
    Launch Chrome browser with X/Twitter cookies pre-loaded.
    Opens a VISIBLE browser window.
    """
    print("=" * 70)
    print("X/Twitter Browser Launcher")
    print("Account: 4botbsc@gmail.com")
    print("=" * 70)

    # Load cookies and tokens
    cookies = load_cookies_from_file()
    if not cookies:
        return None

    tokens = load_tokens_from_file()

    # Display loaded tokens
    if tokens:
        print("\n[*] Authentication tokens:")
        for key, value in tokens.items():
            display_value = value[:40] + "..." if len(value) > 40 else value
            print(f"    {key}: {display_value}")

    # Setup Chrome options
    chrome_options = Options()

    # VISIBLE browser (not headless)
    # chrome_options.add_argument('--headless=new')  # Commented out for visible mode

    # Additional options
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # User agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')

    # Optional: Start maximized
    chrome_options.add_argument('--start-maximized')

    print("\n[*] Launching Chrome browser...")

    try:
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)

        # Navigate to X.com to set the domain
        print("[*] Navigating to x.com...")
        driver.get("https://x.com")
        time.sleep(2)

        # Add cookies
        print(f"[*] Loading {len(cookies)} cookies into browser...")
        cookies_loaded = 0
        for cookie in cookies:
            try:
                # Selenium cookie format
                cookie_dict = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie['path'],
                    'secure': bool(cookie['secure'])
                }

                # Add expiry if present
                if cookie['expires'] and cookie['expires'] > 0:
                    cookie_dict['expiry'] = int(cookie['expires'])

                driver.add_cookie(cookie_dict)
                cookies_loaded += 1
            except Exception as e:
                # Some cookies might fail to load
                pass

        print(f"[✓] Successfully loaded {cookies_loaded} cookies")

        # Navigate to home page
        print("[*] Navigating to X home page...")
        driver.get("https://x.com/home")
        time.sleep(3)

        # Verify login
        print("[*] Verifying login status...")
        try:
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            page_title = driver.title
            current_url = driver.current_url

            print(f"[✓] Page loaded: {page_title}")
            print(f"[✓] Current URL: {current_url}")

            # Check if we're on the home page (logged in)
            if "/home" in current_url.lower():
                print("\n" + "=" * 70)
                print("✅ SUCCESS! Browser is now logged in to X/Twitter")
                print(f"   Account: 4botbsc@gmail.com")
                print(f"   Status: Logged in and ready to use")
                print("=" * 70)
                print("\n[*] You can now interact with X/Twitter in the browser")
                print("[*] The browser will remain open until you close it")
                print("[*] Press Ctrl+C in the terminal to close the browser\n")
            else:
                print("\n[!] Warning: Not on home page. You may need to log in manually.")
                print(f"    Current URL: {current_url}")

        except Exception as e:
            print(f"[!] Could not fully verify login: {e}")
            print("[*] Browser is open - check if you're logged in")

        # Keep browser open
        print("[*] Browser will stay open. Press Ctrl+C to exit...")
        try:
            # Keep the script running so the browser stays open
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Closing browser...")
            driver.quit()
            print("[✓] Browser closed")

        return driver

    except Exception as e:
        print(f"\n[ERROR] Failed to launch browser: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main entry point."""
    launch_browser_with_cookies()

if __name__ == "__main__":
    main()
