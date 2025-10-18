from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
import json


LoginMethod = Literal["cookies", "credentials", "google"]


class Config(BaseModel):
    headless: bool = Field(default=True)
    persist_session: bool = Field(default=True)
    storage_state: Path = Field(default=Path("auth/storageState.json"))
    user_data_dir: Path = Field(default=Path(".x-user"))
    proxy_url: Optional[str] = None
    base_url: str = Field(default="https://x.com")
    login_method: LoginMethod = Field(default="cookies")
    # Browser engine: 'chromium' (default), 'webkit' (Safari-like), or 'firefox'
    browser_name: Literal["chromium", "webkit", "firefox"] = Field(default="chromium")

    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    handle: Optional[str] = Field(default=None)
    twofa: Optional[str] = Field(default=None)
    totp_secret: Optional[str] = Field(default=None)

    # reliability / observability
    retry_attempts: int = Field(default=3)
    jitter_min_ms: int = Field(default=200)
    jitter_max_ms: int = Field(default=800)
    trace_enabled: bool = Field(default=False)
    trace_dir: Path = Field(default=Path("artifacts/traces"))
    slow_mo_ms: int = Field(default=0)
    # HAR capture
    har_enabled: bool = Field(default=False)
    har_dir: Path = Field(default=Path("artifacts/har"))
    # Centralized roots
    artifacts_dir: Path = Field(default=Path("artifacts"))
    logs_dir: Path = Field(default=Path("logs"))
    notification_log_dir: Path = Field(default=Path("notification_json_logs"))
    # Human-like interaction
    humanize: bool = Field(default=True)
    type_min_ms: int = Field(default=20)
    type_max_ms: int = Field(default=60)
    # Rate limiting
    rate_min_s: float = Field(default=1.0)
    rate_max_s: float = Field(default=3.0)
    rate_enabled: bool = Field(default=True)

    # Media constraints
    media_max_bytes: int = Field(default=50 * 1024 * 1024)
    media_allow_images: bool = Field(default=True)
    media_allow_video: bool = Field(default=True)
    media_allow_gif: bool = Field(default=True)
    media_preview_enforce: bool = Field(default=False)
    media_preview_warn_only: bool = Field(default=True)
    media_cap_enforce: bool = Field(default=False)
    media_cap_warn_only: bool = Field(default=True)

    # Environment / stealth
    locale: str = Field(default="en-US")
    timezone_id: str = Field(default="America/Los_Angeles")
    user_agent: Optional[str] = Field(default=None)
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=800)
    geolocation_lat: Optional[float] = Field(default=None)
    geolocation_lon: Optional[float] = Field(default=None)
    grant_geolocation: bool = Field(default=False)

    # Profiles
    profile_name: str = Field(default="default")

    # Confirmations and reporting
    confirm_content_enabled: bool = Field(default=True)
    report_html_enabled: bool = Field(default=False)
    report_html_actions: Optional[str] = Field(default=None)
    report_html_daily_enabled: bool = Field(default=False)
    report_html_limit: int = Field(default=200)
    report_html_days: int = Field(default=3)
    report_html_outdir: Path = Field(default=Path("artifacts/results"))
    confirm_post_profile_nav: bool = Field(default=False)
    confirm_post_strict: bool = Field(default=False)
    confirm_reply_strict: bool = Field(default=False)

    # VTerm integration
    vterm_mode: str = Field(default="unix")  # 'unix' or 'http'
    vterm_socket: Path = Field(default=Path(".x-vterm.sock"))
    vterm_http_base: Optional[str] = Field(default=None)  # e.g., http://127.0.0.1:9876
    vterm_token: Optional[str] = Field(default=None)

    # Browser engine: 'chromium' (default), 'webkit' (Safari engine), 'firefox'
    browser: str = Field(default="chromium")

    # Timeouts and retries (ms / counts)
    wait_timeout_ms: int = Field(default=5000)
    long_wait_timeout_ms: int = Field(default=20000)
    toast_timeout_ms: int = Field(default=4000)
    content_confirm_timeout_ms: int = Field(default=5000)
    action_retries: int = Field(default=3)
    action_retry_jitter_min_ms: int = Field(default=200)
    action_retry_jitter_max_ms: int = Field(default=600)

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        # also load ~/.env without overriding existing values
        try:
            from dotenv import load_dotenv as _ld
            _ld(Path.home() / ".env", override=False)
        except Exception:
            pass
        from os import getenv

        # Support both UPPERCASE and lowercase keys (loaded from .env)
        xu = getenv("X_USER") or getenv("USERNAME") or getenv("x_user")
        xp = getenv("X_PASSWORD") or getenv("PASSWORD") or getenv("x_passwd") or getenv("x_password")
        xe = getenv("X_EMAIL") or getenv("EMAIL") or getenv("x_email")
        cfg = cls(
            headless=_parse_bool(getenv("HEADLESS", "true")),
            persist_session=_parse_bool(getenv("PERSIST_SESSION", "true")),
            storage_state=Path(getenv("STORAGE_STATE", "auth/storageState.json")),
            user_data_dir=Path(getenv("USER_DATA_DIR", ".x-user")),
            proxy_url=getenv("PROXY_URL"),
            base_url=getenv("BASE_URL", "https://x.com"),
            login_method=(getenv("LOGIN_METHOD", "cookies").lower() or ("google" if getenv("LOGIN_WITH_GOOGLE","false").lower() in {"1","true","yes","y","on"} else "cookies")),
            browser_name=(getenv("BROWSER_NAME", getenv("BROWSER", "chromium")).lower() or "chromium"),
            username=xu,
            password=xp,
            email=xe,
            handle=(getenv("X_HANDLE") or None),
            twofa=getenv("X_2FA_CODE") or getenv("TWOFA"),
            totp_secret=getenv("X_TOTP_SECRET") or getenv("TOTP_SECRET"),
            retry_attempts=int(getenv("RETRY_ATTEMPTS", "3")),
            jitter_min_ms=int(getenv("JITTER_MIN_MS", "200")),
            jitter_max_ms=int(getenv("JITTER_MAX_MS", "800")),
            trace_enabled=_parse_bool(getenv("TRACE_ENABLED", "false")),
            trace_dir=Path(getenv("TRACE_DIR", "artifacts/traces")),
            slow_mo_ms=int(getenv("SLOW_MO_MS", "0")),
            har_enabled=_parse_bool(getenv("HAR_ENABLED", "false")),
            har_dir=Path(getenv("HAR_DIR", "artifacts/har")),
            artifacts_dir=Path(getenv("ARTIFACTS_DIR", "artifacts")),
            logs_dir=Path(getenv("LOGS_DIR", "logs")),
            notification_log_dir=Path(getenv("NOTIFICATION_LOG_DIR", "notification_json_logs")),
            humanize=_parse_bool(getenv("HUMANIZE", "true")),
            type_min_ms=int(getenv("TYPE_MIN_MS", "20")),
            type_max_ms=int(getenv("TYPE_MAX_MS", "60")),
            rate_min_s=float(getenv("RATE_MIN_S", "1.0")),
            rate_max_s=float(getenv("RATE_MAX_S", "3.0")),
            rate_enabled=_parse_bool(getenv("RATE_ENABLED", "true")),
            media_max_bytes=int(getenv("MEDIA_MAX_BYTES", str(50 * 1024 * 1024))),
            media_allow_images=_parse_bool(getenv("MEDIA_ALLOW_IMAGES", "true")),
            media_allow_video=_parse_bool(getenv("MEDIA_ALLOW_VIDEO", "true")),
            media_allow_gif=_parse_bool(getenv("MEDIA_ALLOW_GIF", "true")),
            media_preview_enforce=_parse_bool(getenv("MEDIA_PREVIEW_ENFORCE", "false")),
            media_preview_warn_only=_parse_bool(getenv("MEDIA_PREVIEW_WARN_ONLY", "true")),
            media_cap_enforce=_parse_bool(getenv("MEDIA_CAP_ENFORCE", "false")),
            media_cap_warn_only=_parse_bool(getenv("MEDIA_CAP_WARN_ONLY", "true")),
            locale=getenv("LOCALE", "en-US"),
            timezone_id=getenv("TIMEZONE_ID", "America/Los_Angeles"),
            user_agent=(getenv("USER_AGENT") or None),
            viewport_width=int(getenv("VIEWPORT_WIDTH", "1280")),
            viewport_height=int(getenv("VIEWPORT_HEIGHT", "800")),
            geolocation_lat=(float(getenv("GEO_LAT")) if getenv("GEO_LAT") else None),
            geolocation_lon=(float(getenv("GEO_LON")) if getenv("GEO_LON") else None),
            grant_geolocation=_parse_bool(getenv("GRANT_GEOLOCATION", "false")),
            profile_name=getenv("PROFILE", getenv("X_PROFILE", "default")) or "default",
            confirm_content_enabled=_parse_bool(getenv("CONFIRM_CONTENT_ENABLED", "true")),
            report_html_enabled=_parse_bool(getenv("REPORT_HTML_ENABLED", "false")),
            report_html_actions=(getenv("REPORT_HTML_ACTIONS") or None),
            report_html_daily_enabled=_parse_bool(getenv("REPORT_HTML_DAILY_ENABLED", "false")),
            report_html_limit=int(getenv("REPORT_HTML_LIMIT", "200")),
            report_html_days=int(getenv("REPORT_HTML_DAYS", "3")),
            report_html_outdir=Path(getenv("REPORT_HTML_OUTDIR", "artifacts/results")),
            confirm_post_profile_nav=_parse_bool(getenv("CONFIRM_POST_PROFILE_NAV", "false")),
            confirm_post_strict=_parse_bool(getenv("CONFIRM_POST_STRICT", "false")),
            confirm_reply_strict=_parse_bool(getenv("CONFIRM_REPLY_STRICT", "false")),
            wait_timeout_ms=int(getenv("WAIT_TIMEOUT_MS", "5000")),
            long_wait_timeout_ms=int(getenv("LONG_WAIT_TIMEOUT_MS", "20000")),
            toast_timeout_ms=int(getenv("TOAST_TIMEOUT_MS", "4000")),
            content_confirm_timeout_ms=int(getenv("CONTENT_CONFIRM_TIMEOUT_MS", "5000")),
            action_retries=int(getenv("ACTION_RETRIES", "3")),
            action_retry_jitter_min_ms=int(getenv("ACTION_RETRY_JITTER_MIN_MS", "200")),
            action_retry_jitter_max_ms=int(getenv("ACTION_RETRY_JITTER_MAX_MS", "600")),
            vterm_mode=(getenv("VTERM_MODE", "unix").lower()),
            vterm_socket=Path(getenv("VTERM_SOCKET", ".x-vterm.sock")),
            vterm_http_base=(getenv("VTERM_HTTP_BASE") or None),
            vterm_token=(getenv("VTERM_TOKEN") or None),
            browser=(getenv("BROWSER", "chromium").lower()),
        )

        # Apply per-profile overrides from config/profiles/<profile>.json if present
        overlay_path = Path("config/profiles") / f"{cfg.profile_name}.json"
        if overlay_path.exists():
            try:
                data = json.loads(overlay_path.read_text())
                for key, val in data.items():
                    if not hasattr(cfg, key):
                        continue
                    # Convert simple paths for known keys
                    if key in {"storage_state", "trace_dir", "har_dir", "user_data_dir"} and isinstance(val, str):
                        setattr(cfg, key, Path(val))
                    else:
                        setattr(cfg, key, val)
            except Exception:
                pass

        # Derive handle if not explicitly provided (after overlay application)
        if cfg.handle is None and cfg.username:
            u = cfg.username.strip()
            if u.startswith("@"):
                cfg.handle = u[1:]
            elif "@" in u and "." in u:
                # likely an email; leave handle unset
                pass
            else:
                cfg.handle = u
        return cfg


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
