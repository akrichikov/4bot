#!/usr/bin/env python3
"""
Load X/Twitter cookies into a headless browser session.
This script demonstrates how to use the extracted cookies for automation.
"""
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Paths
AUTH_DATA_DIR = Path("/Users/doctordre/projects/4bot/auth_data")
COOKIES_FILE = AUTH_DATA_DIR / "x_cookies.json"

def load_cookies_and_launch():
    """
    Launch a headless Chrome browser with X/Twitter cookies pre-loaded.
    """
    print("=" * 70)
    print("X/Twitter Headless Browser with Pre-loaded Cookies")
    print("=" * 70)

    # Check if cookies file exists
    if not COOKIES_FILE.exists():
        print(f"\n[ERROR] Cookies file not found: {COOKIES_FILE}")
        print("Please run extract_x_cookies_simple.py first to extract cookies.")
        return None

    # Load cookies from file
    with open(COOKIES_FILE, 'r') as f:
        cookies_data = json.load(f)

    print(f"\n[*] Loaded {len(cookies_data)} cookies from file")

    # Setup Chrome options
    chrome_options = Options()

    # Headless mode
    chrome_options.add_argument('--headless=new')  # Use new headless mode

    # Additional options for better compatibility
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # User agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')

    print("[*] Launching Chrome in headless mode...")

    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # First, navigate to X.com to set the domain
        print("[*] Navigating to x.com...")
        driver.get("https://x.com")
        time.sleep(2)

        # Add cookies
        print(f"[*] Loading {len(cookies_data)} cookies...")
        cookies_loaded = 0
        for cookie in cookies_data:
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
                # Some cookies might fail to load (e.g., expired or invalid)
                pass

        print(f"[✓] Successfully loaded {cookies_loaded} cookies")

        # Refresh to apply cookies
        print("[*] Refreshing page to apply cookies...")
        driver.refresh()
        time.sleep(3)

        # Check if logged in by looking for specific elements
        print("[*] Checking if logged in...")
        try:
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check if we're logged in by looking for common logged-in elements
            page_source = driver.page_source.lower()

            if 'data-testid="SideNav_NewTweet_Button"'.lower() in page_source or \
               'compose/tweet' in driver.current_url.lower() or \
               any(keyword in page_source for keyword in ['timeline', 'tweet', 'following']):
                print("[✓] Successfully logged in to X/Twitter!")
                print(f"[✓] Current URL: {driver.current_url}")

                # Get page title
                print(f"[✓] Page title: {driver.title}")

                # Take a screenshot
                screenshot_path = AUTH_DATA_DIR / "headless_session_screenshot.png"
                driver.save_screenshot(str(screenshot_path))
                print(f"[✓] Screenshot saved: {screenshot_path}")

            else:
                print("[!] Warning: Might not be logged in, or page structure changed")
                print(f"    Current URL: {driver.current_url}")

        except Exception as e:
            print(f"[!] Could not verify login status: {e}")

        print("\n" + "=" * 70)
        print("Browser session is ready for automation!")
        print("=" * 70)

        return driver

    except Exception as e:
        print(f"\n[ERROR] Failed to setup browser: {e}")
        import traceback
        traceback.print_exc()
        driver.quit()
        return None

def example_usage():
    """
    Example of using the authenticated browser session.
    """
    driver = load_cookies_and_launch()

    if driver:
        try:
            print("\n[*] Example: Navigating to profile...")
            driver.get("https://x.com/home")
            time.sleep(3)

            print(f"[✓] Current page: {driver.title}")

            # You can now use the driver for automation tasks
            # For example:
            # - Post tweets
            # - Read timeline
            # - Like/retweet posts
            # - Send DMs
            # etc.

            print("\n[*] Browser session ready for your automation tasks!")
            print("    Use the 'driver' object to interact with X/Twitter")

            # Keep browser open for demonstration (optional)
            # input("\nPress Enter to close the browser...")

        finally:
            print("\n[*] Closing browser...")
            driver.quit()
            print("[✓] Browser closed")

if __name__ == "__main__":
    example_usage()
