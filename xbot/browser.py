from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page, async_playwright

from .config import Config
from .state import apply_storage_state, export_storage_state


class Browser:
    def __init__(self, cfg: Config, label: Optional[str] = None):
        self.cfg = cfg
        self.label = label or "session"
        self._ctx: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._trace_path: Optional[Path] = None
        self._har_path: Optional[Path] = None

    async def __aenter__(self) -> "Browser":
        self._ctx = await self._launch_context()
        # import cookies/localStorage from storage_state if present
        if self.cfg.storage_state:
            await apply_storage_state(self._ctx, self.cfg.storage_state)
        # start tracing for both context types if enabled
        if self.cfg.trace_enabled:
            self.cfg.trace_dir.mkdir(parents=True, exist_ok=True)
            self._trace_path = self.cfg.trace_dir / f"{self.label}.zip"
            await self._ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
        self._page = await self._ctx.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.cfg.trace_enabled and self._trace_path is not None:
            try:
                await self._ctx.tracing.stop(path=str(self._trace_path))  # type: ignore[union-attr]
            except Exception:
                pass
        if self.cfg.storage_state:
            await export_storage_state(self._ctx, self.cfg.storage_state)
        await self._ctx.close()  # type: ignore[union-attr]

    @property
    def page(self) -> Page:
        assert self._page is not None
        return self._page

    @property
    def trace_path(self) -> Optional[Path]:
        return self._trace_path

    @property
    def har_path(self) -> Optional[Path]:
        return self._har_path

    async def _launch_context(self) -> BrowserContext:
        playwright = await async_playwright().start()
        proxy = {"server": self.cfg.proxy_url} if self.cfg.proxy_url else None
        viewport = {"width": self.cfg.viewport_width, "height": self.cfg.viewport_height}
        permissions = ["geolocation"] if self.cfg.grant_geolocation else None
        geolocation = None
        if self.cfg.geolocation_lat is not None and self.cfg.geolocation_lon is not None:
            geolocation = {"latitude": self.cfg.geolocation_lat, "longitude": self.cfg.geolocation_lon}

        if self.cfg.persist_session:
            self.cfg.user_data_dir.mkdir(parents=True, exist_ok=True)
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.cfg.user_data_dir),
                headless=self.cfg.headless,
                slow_mo=self.cfg.slow_mo_ms or 0,
                proxy=proxy,  # type: ignore[arg-type]
                locale=self.cfg.locale,
                timezone_id=self.cfg.timezone_id,
                user_agent=self.cfg.user_agent,
                viewport=viewport,
                permissions=permissions,
                geolocation=geolocation,
            )
            if self.cfg.storage_state.exists():
                await context.add_cookies(await context.cookies())
            return context
        else:
            browser = await playwright.chromium.launch(
                headless=self.cfg.headless, proxy=proxy, slow_mo=self.cfg.slow_mo_ms or 0
            )  # type: ignore[arg-type]
            storage_state: Optional[str | Path] = None
            if self.cfg.storage_state.exists():
                storage_state = str(self.cfg.storage_state)
            har_path = None
            if self.cfg.har_enabled:
                self.cfg.har_dir.mkdir(parents=True, exist_ok=True)
                self._har_path = self.cfg.har_dir / f"{self.label}.har"
                har_path = str(self._har_path)
            context = await browser.new_context(
                storage_state=storage_state,
                record_har_path=har_path,
                locale=self.cfg.locale,
                timezone_id=self.cfg.timezone_id,
                user_agent=self.cfg.user_agent,
                viewport=viewport,
                permissions=permissions,
                geolocation=geolocation,
            )
            return context
