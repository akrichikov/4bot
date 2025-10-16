#!/usr/bin/env python3
"""
Cookie Manager Tests
Tests the critical authentication cookie handling (Pareto 80/20: auth is critical path)
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base_test_fixture import BaseTestFixture
from xbot.cookies import (
    _normalize_cookie,
    load_cookie_json,
    merge_into_storage,
    _ckey,
    Cookie
)


class TestCookieManager(BaseTestFixture):
    """Test cookie management - critical for authentication"""

    def setup_custom(self):
        """Custom setup for cookie tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.cookie_file = self.temp_path / "test_cookies.json"
        self.storage_file = self.temp_path / "storage_state.json"

    def teardown_custom(self):
        """Custom teardown"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_normalize_cookie_chrome_format(self):
        """Test normalizing Chrome export format cookies"""
        # Chrome export format with expirationDate in seconds
        chrome_cookie = {
            "name": "auth_token",
            "value": "test_token_123",
            "domain": ".x.com",
            "path": "/",
            "expirationDate": 1800000000.5,  # Float seconds
            "httponly": 1,  # Numeric boolean
            "secure": 1,  # Numeric boolean
            "sameSite": "lax"  # Lowercase
        }

        normalized = _normalize_cookie(chrome_cookie)

        assert normalized["name"] == "auth_token"
        assert normalized["value"] == "test_token_123"
        assert normalized["domain"] == ".x.com"
        assert normalized["path"] == "/"
        assert normalized["expires"] == 1800000000  # Converted to int
        assert normalized["httpOnly"] == True  # Converted from numeric
        assert normalized["secure"] == True  # Converted from numeric
        assert normalized["sameSite"] == "Lax"  # Normalized case

    def test_normalize_cookie_playwright_format(self):
        """Test normalizing Playwright storageState format"""
        playwright_cookie = {
            "name": "ct0",
            "value": "csrf_token_456",
            "domain": ".x.com",
            "path": "/",
            "expires": 1800000000,  # Already int
            "httpOnly": False,  # Already boolean
            "secure": True,  # Already boolean
            "sameSite": "Strict"
        }

        normalized = _normalize_cookie(playwright_cookie)

        assert normalized["name"] == "ct0"
        assert normalized["value"] == "csrf_token_456"
        assert normalized["expires"] == 1800000000
        assert normalized["httpOnly"] == False
        assert normalized["secure"] == True
        assert normalized["sameSite"] == "Strict"

    def test_normalize_cookie_missing_fields(self):
        """Test cookie normalization with missing optional fields"""
        minimal_cookie = {
            "name": "session",
            "value": "abc123",
            "domain": ".x.com"
            # Missing: path, expires, httpOnly, secure, sameSite
        }

        normalized = _normalize_cookie(minimal_cookie)

        assert normalized["path"] == "/"  # Default path
        assert normalized["expires"] == -1  # Default for no expiry
        assert normalized["httpOnly"] == False  # Default
        assert normalized["secure"] == False  # Default
        assert normalized["sameSite"] == "Lax"  # Default

    def test_normalize_cookie_invalid(self):
        """Test invalid cookie handling"""
        # Missing required fields
        invalid_cookies = [
            {"value": "test", "domain": ".x.com"},  # Missing name
            {"name": "test", "domain": ".x.com"},  # Missing value
            {"name": "test", "value": "val"},  # Missing domain
            {}  # Empty cookie
        ]

        for invalid in invalid_cookies:
            with pytest.raises(ValueError, match="invalid cookie"):
                _normalize_cookie(invalid)

    def test_normalize_cookie_samesite_variations(self):
        """Test sameSite normalization with various inputs"""
        test_cases = [
            ("lax", "Lax"),
            ("Lax", "Lax"),
            ("LAX", "Lax"),
            ("strict", "Strict"),
            ("Strict", "Strict"),
            ("STRICT", "Strict"),
            ("none", "None"),
            ("None", "None"),
            ("invalid", "None"),  # Unknown defaults to None
            ("", "None"),  # Empty defaults to None
        ]

        for input_val, expected in test_cases:
            cookie = {
                "name": "test",
                "value": "val",
                "domain": ".x.com",
                "sameSite": input_val
            }
            normalized = _normalize_cookie(cookie)
            assert normalized["sameSite"] == expected, f"Failed for input: {input_val}"

    def test_load_cookie_json_list_format(self):
        """Test loading cookies from JSON list format"""
        cookies = [
            {
                "name": "auth",
                "value": "token1",
                "domain": ".x.com",
                "secure": 1
            },
            {
                "name": "session",
                "value": "token2",
                "domain": ".x.com",
                "httponly": 1
            }
        ]

        self.cookie_file.write_text(json.dumps(cookies))
        loaded = load_cookie_json(self.cookie_file)

        assert len(loaded) == 2
        assert loaded[0]["name"] == "auth"
        assert loaded[0]["secure"] == True
        assert loaded[1]["name"] == "session"
        assert loaded[1]["httpOnly"] == True

    def test_load_cookie_json_dict_format(self):
        """Test loading cookies from JSON dict with 'cookies' key"""
        data = {
            "cookies": [
                {
                    "name": "test1",
                    "value": "val1",
                    "domain": ".x.com"
                },
                {
                    "name": "test2",
                    "value": "val2",
                    "domain": ".x.com"
                }
            ],
            "origins": []  # Playwright format
        }

        self.cookie_file.write_text(json.dumps(data))
        loaded = load_cookie_json(self.cookie_file)

        assert len(loaded) == 2
        assert loaded[0]["name"] == "test1"
        assert loaded[1]["name"] == "test2"

    def test_load_cookie_json_skip_invalid(self):
        """Test that invalid cookies are skipped during loading"""
        cookies = [
            {"name": "valid", "value": "val", "domain": ".x.com"},
            {"value": "missing_name", "domain": ".x.com"},  # Invalid
            {"name": "valid2", "value": "val2", "domain": ".x.com"}
        ]

        self.cookie_file.write_text(json.dumps(cookies))
        loaded = load_cookie_json(self.cookie_file)

        assert len(loaded) == 2  # Only valid cookies loaded
        assert loaded[0]["name"] == "valid"
        assert loaded[1]["name"] == "valid2"

    def test_ckey_generation(self):
        """Test cookie key generation for deduplication"""
        cookie1 = {"name": "auth", "domain": ".x.com", "path": "/"}
        cookie2 = {"name": "auth", "domain": ".x.com", "path": "/api"}
        cookie3 = {"name": "auth", "domain": ".y.com", "path": "/"}

        key1 = _ckey(cookie1)
        key2 = _ckey(cookie2)
        key3 = _ckey(cookie3)

        # Same name+domain+path = same key
        assert key1 == ("auth", ".x.com", "/")

        # Different paths = different keys
        assert key1 != key2

        # Different domains = different keys
        assert key1 != key3

    def test_merge_into_storage_new_file(self):
        """Test merging cookies into non-existent storage file"""
        cookies = [
            _normalize_cookie({
                "name": "auth",
                "value": "token1",
                "domain": ".x.com"
            }),
            _normalize_cookie({
                "name": "session",
                "value": "token2",
                "domain": ".x.com"
            })
        ]

        count = merge_into_storage(self.storage_file, cookies)

        assert count == 2
        assert self.storage_file.exists()

        # Verify storage format
        storage = json.loads(self.storage_file.read_text())
        assert "cookies" in storage
        assert "origins" in storage
        assert len(storage["cookies"]) == 2

    def test_merge_into_storage_update_existing(self):
        """Test updating existing cookies in storage"""
        # Create initial storage
        initial_storage = {
            "cookies": [
                {"name": "auth", "value": "old_token", "domain": ".x.com", "path": "/"},
                {"name": "other", "value": "keep_me", "domain": ".x.com", "path": "/"}
            ],
            "origins": []
        }
        self.storage_file.write_text(json.dumps(initial_storage))

        # Merge updated cookie
        updated_cookies = [
            _normalize_cookie({
                "name": "auth",
                "value": "new_token",  # Updated value
                "domain": ".x.com"
            })
        ]

        count = merge_into_storage(self.storage_file, updated_cookies)

        assert count == 1

        # Verify merge result
        storage = json.loads(self.storage_file.read_text())
        cookies_by_name = {c["name"]: c for c in storage["cookies"]}

        assert len(cookies_by_name) == 2  # Still 2 cookies
        assert cookies_by_name["auth"]["value"] == "new_token"  # Updated
        assert cookies_by_name["other"]["value"] == "keep_me"  # Preserved

    def test_merge_into_storage_domain_filter(self):
        """Test domain filtering during merge"""
        cookies = [
            _normalize_cookie({"name": "auth", "value": "t1", "domain": ".x.com"}),
            _normalize_cookie({"name": "session", "value": "t2", "domain": ".y.com"}),
            _normalize_cookie({"name": "track", "value": "t3", "domain": ".z.com"}),
        ]

        # Only merge cookies for x.com domain
        count = merge_into_storage(
            self.storage_file,
            cookies,
            filter_domains=[".x.com"]
        )

        assert count == 1  # Only x.com cookie merged

        storage = json.loads(self.storage_file.read_text())
        assert len(storage["cookies"]) == 1
        assert storage["cookies"][0]["domain"] == ".x.com"

    def test_merge_into_storage_subdomain_matching(self):
        """Test subdomain matching in domain filter"""
        cookies = [
            _normalize_cookie({"name": "c1", "value": "v1", "domain": "api.x.com"}),
            _normalize_cookie({"name": "c2", "value": "v2", "domain": ".x.com"}),
            _normalize_cookie({"name": "c3", "value": "v3", "domain": "x.com"}),
            _normalize_cookie({"name": "c4", "value": "v4", "domain": "other.com"}),
        ]

        count = merge_into_storage(
            self.storage_file,
            cookies,
            filter_domains=["x.com"]
        )

        assert count == 3  # All x.com variants except other.com

        storage = json.loads(self.storage_file.read_text())
        domains = {c["domain"] for c in storage["cookies"]}
        assert "other.com" not in domains

    def test_cookie_expiry_handling(self):
        """Test handling of expired vs non-expired cookies"""
        future_timestamp = int((datetime.now() + timedelta(days=30)).timestamp())
        past_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())

        cookies = [
            {
                "name": "future",
                "value": "valid",
                "domain": ".x.com",
                "expires": future_timestamp
            },
            {
                "name": "past",
                "value": "expired",
                "domain": ".x.com",
                "expires": past_timestamp
            },
            {
                "name": "session",
                "value": "no_expiry",
                "domain": ".x.com"
                # No expires = session cookie
            }
        ]

        self.cookie_file.write_text(json.dumps(cookies))
        loaded = load_cookie_json(self.cookie_file)

        assert len(loaded) == 3  # All cookies loaded (expiry check is runtime)

        # Verify expiry values
        cookies_by_name = {c["name"]: c for c in loaded}
        assert cookies_by_name["future"]["expires"] == future_timestamp
        assert cookies_by_name["past"]["expires"] == past_timestamp
        assert cookies_by_name["session"]["expires"] == -1  # Session cookie

    def test_unicode_cookie_values(self):
        """Test handling of Unicode characters in cookie values"""
        unicode_cookies = [
            {
                "name": "emoji",
                "value": "🍪🔐✨",
                "domain": ".x.com"
            },
            {
                "name": "chinese",
                "value": "你好世界",
                "domain": ".x.com"
            },
            {
                "name": "arabic",
                "value": "مرحبا",
                "domain": ".x.com"
            }
        ]

        self.cookie_file.write_text(json.dumps(unicode_cookies, ensure_ascii=False))
        loaded = load_cookie_json(self.cookie_file)

        assert len(loaded) == 3
        assert loaded[0]["value"] == "🍪🔐✨"
        assert loaded[1]["value"] == "你好世界"
        assert loaded[2]["value"] == "مرحبا"

        # Test merge preserves Unicode
        merge_into_storage(self.storage_file, loaded)
        storage = json.loads(self.storage_file.read_text())

        values = {c["value"] for c in storage["cookies"]}
        assert "🍪🔐✨" in values
        assert "你好世界" in values

    def test_cookie_deduplication_same_key(self):
        """Test that cookies with same (name, domain, path) are deduplicated"""
        cookies = [
            _normalize_cookie({"name": "auth", "value": "token1", "domain": ".x.com", "path": "/"}),
            _normalize_cookie({"name": "auth", "value": "token2", "domain": ".x.com", "path": "/"}),
            _normalize_cookie({"name": "auth", "value": "token3", "domain": ".x.com", "path": "/"}),
        ]

        merge_into_storage(self.storage_file, cookies)

        storage = json.loads(self.storage_file.read_text())
        assert len(storage["cookies"]) == 1  # Only one cookie kept
        assert storage["cookies"][0]["value"] == "token3"  # Last one wins

    def test_multi_profile_isolation(self):
        """Test cookie isolation for multiple profile support"""
        profile1_file = self.temp_path / "profile1" / "cookies.json"
        profile2_file = self.temp_path / "profile2" / "cookies.json"

        profile1_cookies = [
            _normalize_cookie({"name": "user", "value": "alice", "domain": ".x.com"})
        ]

        profile2_cookies = [
            _normalize_cookie({"name": "user", "value": "bob", "domain": ".x.com"})
        ]

        # Merge to different profiles
        merge_into_storage(profile1_file, profile1_cookies)
        merge_into_storage(profile2_file, profile2_cookies)

        # Verify isolation
        profile1_storage = json.loads(profile1_file.read_text())
        profile2_storage = json.loads(profile2_file.read_text())

        assert profile1_storage["cookies"][0]["value"] == "alice"
        assert profile2_storage["cookies"][0]["value"] == "bob"

    def test_corrupt_storage_recovery(self):
        """Test recovery from corrupted storage file"""
        # Write corrupted JSON
        self.storage_file.write_text("{corrupted json[}")

        cookies = [
            _normalize_cookie({"name": "test", "value": "recovery", "domain": ".x.com"})
        ]

        # Should recover and create new storage
        count = merge_into_storage(self.storage_file, cookies)

        assert count == 1
        storage = json.loads(self.storage_file.read_text())
        assert len(storage["cookies"]) == 1
        assert storage["cookies"][0]["value"] == "recovery"

    def test_special_characters_in_cookie_values(self):
        """Test handling of special characters that could break JSON"""
        special_cookies = [
            {"name": "quotes", "value": 'test"with"quotes', "domain": ".x.com"},
            {"name": "backslash", "value": "test\\with\\backslash", "domain": ".x.com"},
            {"name": "newline", "value": "test\nwith\nnewline", "domain": ".x.com"},
            {"name": "tab", "value": "test\twith\ttab", "domain": ".x.com"},
        ]

        self.cookie_file.write_text(json.dumps(special_cookies))
        loaded = load_cookie_json(self.cookie_file)

        assert len(loaded) == 4

        # Verify special characters preserved
        values_by_name = {c["name"]: c["value"] for c in loaded}
        assert values_by_name["quotes"] == 'test"with"quotes'
        assert values_by_name["backslash"] == "test\\with\\backslash"
        assert values_by_name["newline"] == "test\nwith\nnewline"
        assert values_by_name["tab"] == "test\twith\ttab"