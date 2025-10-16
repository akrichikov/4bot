#!/usr/bin/env python3
"""
Chrome Profile Mapper for X/Twitter accounts.
Maps Chrome profiles to their associated accounts for safe testing.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import browser_cookie3
import shutil


@dataclass
class ChromeProfile:
    """Represents a Chrome profile with its associated accounts."""
    profile_name: str
    profile_path: Path
    email: Optional[str] = None
    x_handle: Optional[str] = None
    x_user_id: Optional[str] = None
    is_production: bool = False
    description: Optional[str] = None
    cookies_extracted: bool = False
    last_updated: Optional[str] = None


class ChromeProfileManager:
    """Manages Chrome profiles and their X/Twitter account mappings."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.home() / "Library/Application Support/Google/Chrome"
        self.profiles_dir = Path("chrome_profiles")
        self.profiles_dir.mkdir(exist_ok=True)
        self.mapping_file = self.profiles_dir / "profile_mapping.json"
        self.profiles: Dict[str, ChromeProfile] = {}
        self.load_mapping()

    def load_mapping(self):
        """Load existing profile mapping from file."""
        if self.mapping_file.exists():
            with open(self.mapping_file, 'r') as f:
                data = json.load(f)
                for profile_name, profile_data in data.items():
                    profile_data['profile_path'] = Path(profile_data['profile_path'])
                    self.profiles[profile_name] = ChromeProfile(**profile_data)

    def save_mapping(self):
        """Save profile mapping to file."""
        data = {}
        for profile_name, profile in self.profiles.items():
            profile_dict = asdict(profile)
            profile_dict['profile_path'] = str(profile.profile_path)
            data[profile_name] = profile_dict

        with open(self.mapping_file, 'w') as f:
            json.dump(data, f, indent=2)

    def discover_profiles(self) -> List[str]:
        """Discover all Chrome profiles on the system."""
        profiles = []

        # Check Default profile
        default_path = self.base_path / "Default"
        if default_path.exists():
            profiles.append("Default")

        # Check numbered profiles
        for i in range(1, 20):
            profile_path = self.base_path / f"Profile {i}"
            if profile_path.exists():
                profiles.append(f"Profile {i}")

        return profiles

    def analyze_profile(self, profile_name: str) -> ChromeProfile:
        """Analyze a Chrome profile to extract account information."""
        profile_path = self.base_path / profile_name

        if not profile_path.exists():
            raise ValueError(f"Profile {profile_name} does not exist")

        profile = ChromeProfile(
            profile_name=profile_name,
            profile_path=profile_path
        )

        # Check Preferences file for email
        prefs_file = profile_path / "Preferences"
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                    # Try to find email in various locations
                    if 'account_info' in prefs:
                        for account in prefs['account_info']:
                            if 'email' in account:
                                profile.email = account['email']
                                break
                    elif 'profile' in prefs and 'name' in prefs['profile']:
                        profile.email = prefs['profile']['name']
            except Exception as e:
                print(f"Could not parse preferences for {profile_name}: {e}")

        # Try to extract X/Twitter cookies to get user info
        cookies_db = profile_path / "Cookies"
        if cookies_db.exists():
            try:
                # Create a temporary copy to avoid locking issues
                temp_db = Path(f"/tmp/cookies_{profile_name}.db")
                shutil.copy2(cookies_db, temp_db)

                # Connect to the database
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()

                # Look for X/Twitter cookies
                cursor.execute("""
                    SELECT name, value, host_key
                    FROM cookies
                    WHERE host_key IN ('.x.com', '.twitter.com')
                    AND name IN ('twid', 'auth_token', 'kdt')
                """)

                cookies = cursor.fetchall()
                for name, value, host in cookies:
                    if name == 'twid' and value:
                        # Extract user ID from twid cookie
                        if 'u%3D' in value:
                            profile.x_user_id = value.split('u%3D')[1]
                        profile.cookies_extracted = True

                conn.close()
                temp_db.unlink()

            except Exception as e:
                print(f"Could not extract cookies for {profile_name}: {e}")

        return profile

    def map_all_profiles(self):
        """Discover and map all Chrome profiles."""
        profiles = self.discover_profiles()
        print(f"🔍 Found {len(profiles)} Chrome profiles")

        for profile_name in profiles:
            print(f"\n📁 Analyzing {profile_name}...")
            try:
                profile = self.analyze_profile(profile_name)
                self.profiles[profile_name] = profile

                if profile.email:
                    print(f"  📧 Email: {profile.email}")
                if profile.x_user_id:
                    print(f"  🆔 X User ID: {profile.x_user_id}")
                if profile.cookies_extracted:
                    print(f"  🍪 X/Twitter cookies found")

            except Exception as e:
                print(f"  ❌ Error: {e}")

        self.save_mapping()
        print(f"\n✅ Mapped {len(self.profiles)} profiles to {self.mapping_file}")

    def set_profile_details(self, profile_name: str, x_handle: str = None,
                           is_production: bool = False, description: str = None):
        """Manually set profile details."""
        if profile_name not in self.profiles:
            profile_path = self.base_path / profile_name
            if not profile_path.exists():
                raise ValueError(f"Profile {profile_name} does not exist")
            self.profiles[profile_name] = ChromeProfile(
                profile_name=profile_name,
                profile_path=profile_path
            )

        profile = self.profiles[profile_name]
        if x_handle:
            profile.x_handle = x_handle
        if description:
            profile.description = description
        profile.is_production = is_production

        self.save_mapping()

    def get_safe_test_profile(self) -> Optional[ChromeProfile]:
        """Get a non-production profile for testing."""
        for profile in self.profiles.values():
            if not profile.is_production and profile.cookies_extracted:
                return profile
        return None

    def extract_cookies_for_profile(self, profile_name: str, output_dir: Path = None) -> Path:
        """Extract X/Twitter cookies for a specific profile."""
        if profile_name not in self.profiles:
            raise ValueError(f"Profile {profile_name} not in mapping")

        profile = self.profiles[profile_name]
        output_dir = output_dir or self.profiles_dir / "cookies"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{profile_name.replace(' ', '_').lower()}_cookies.json"

        # Use browser_cookie3 to extract cookies
        cookies_db = profile.profile_path / "Cookies"

        # Extract cookies for X.com and Twitter.com
        all_cookies = []

        try:
            cj_x = browser_cookie3.chrome(domain_name='.x.com', cookie_file=str(cookies_db))
            for cookie in cj_x:
                all_cookies.append({
                    'domain': cookie.domain,
                    'name': cookie.name,
                    'value': cookie.value,
                    'path': cookie.path,
                    'expires': int(cookie.expires) if cookie.expires else None,
                    'secure': bool(cookie.secure),
                    'httpOnly': False  # browser_cookie3 doesn't provide this
                })
        except:
            pass

        try:
            cj_twitter = browser_cookie3.chrome(domain_name='.twitter.com', cookie_file=str(cookies_db))
            for cookie in cj_twitter:
                # Avoid duplicates
                if not any(c['name'] == cookie.name and c['domain'] == cookie.domain for c in all_cookies):
                    all_cookies.append({
                        'domain': cookie.domain,
                        'name': cookie.name,
                        'value': cookie.value,
                        'path': cookie.path,
                        'expires': int(cookie.expires) if cookie.expires else None,
                        'secure': bool(cookie.secure),
                        'httpOnly': False
                    })
        except:
            pass

        # Save cookies
        with open(output_file, 'w') as f:
            json.dump(all_cookies, f, indent=2)

        profile.cookies_extracted = True
        self.save_mapping()

        print(f"✅ Extracted {len(all_cookies)} cookies to {output_file}")
        return output_file

    def list_profiles(self):
        """List all mapped profiles with their details."""
        print("\n" + "=" * 70)
        print("Chrome Profile Mapping for X/Twitter Accounts")
        print("=" * 70)

        for profile_name, profile in self.profiles.items():
            status = "🔴 PRODUCTION" if profile.is_production else "🟢 TEST"
            cookies = "🍪" if profile.cookies_extracted else "❌"

            print(f"\n📁 {profile_name} {status}")
            print(f"   Path: {profile.profile_path}")
            if profile.email:
                print(f"   Email: {profile.email}")
            if profile.x_handle:
                print(f"   X Handle: @{profile.x_handle}")
            if profile.x_user_id:
                print(f"   X User ID: {profile.x_user_id}")
            if profile.description:
                print(f"   Description: {profile.description}")
            print(f"   Cookies Extracted: {cookies}")

        print("\n" + "=" * 70)


def main():
    """Main function to map Chrome profiles."""
    import sys

    manager = ChromeProfileManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "discover":
            manager.map_all_profiles()
            manager.list_profiles()

        elif command == "set" and len(sys.argv) >= 4:
            profile_name = sys.argv[2]
            x_handle = sys.argv[3]
            is_production = len(sys.argv) > 4 and sys.argv[4] == "production"
            description = sys.argv[5] if len(sys.argv) > 5 else None

            manager.set_profile_details(profile_name, x_handle, is_production, description)
            print(f"✅ Updated {profile_name}")

        elif command == "extract" and len(sys.argv) >= 3:
            profile_name = sys.argv[2]
            cookie_file = manager.extract_cookies_for_profile(profile_name)
            print(f"📁 Cookies saved to: {cookie_file}")

        elif command == "list":
            manager.list_profiles()

        else:
            print("Usage:")
            print("  python profile_mapper.py discover                     - Discover all profiles")
            print("  python profile_mapper.py list                         - List mapped profiles")
            print("  python profile_mapper.py set <profile> <handle> [production] [description]")
            print("  python profile_mapper.py extract <profile>            - Extract cookies")
    else:
        # Default: discover and list
        manager.map_all_profiles()
        manager.list_profiles()


if __name__ == "__main__":
    main()