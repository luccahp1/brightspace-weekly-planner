"""Playwright browser client for Brightspace access."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from .config import AppConfig
from .safety import is_unsafe_url

logger = logging.getLogger("brightspace_planner")


class BrightspaceBrowser:
    """Wraps Playwright with persistent profile support."""

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def start(self) -> BrowserContext:
        """Launch or connect to the persistent browser profile."""
        profile_dir = self.cfg.auth.playwright_profile_dir
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch_persistent_context(
            profile_dir,
            headless=self.cfg.browser.headless,
            slow_mo=self.cfg.browser.slow_mo_ms,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Toronto",
        )
        # In launch_persistent_context, the return value IS the context
        self._context = self._browser  # type: ignore[assignment]
        logger.info("Browser started with profile at %s (headless=%s)", profile_dir, self.cfg.browser.headless)
        return self._context

    def stop(self):
        """Close the browser."""
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Browser stopped.")

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context

    def get_page(self) -> Optional[Page]:
        """Get the first page or open a new one."""
        if self._context and self._context.pages:
            return self._context.pages[0]
        if self._context:
            return self._context.new_page()
        return None

    def safe_goto(self, url: str, page: Page | None = None) -> Page:
        """Navigate to a URL after safety checks."""
        if is_unsafe_url(url):
            raise RuntimeError(f"Refusing to navigate to potentially unsafe URL: {url}")
        pg = page or self.get_page()
        if pg is None:
            raise RuntimeError("No browser page available.")
        logger.info("Navigating to %s", url)
        pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        return pg

    def wait_for_home(self, timeout_s: int = 120) -> bool:
        """Wait until the Brightspace homepage loads (used in auth flow)."""
        pg = self.get_page()
        if not pg:
            return False
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            url = pg.url
            if "/d2l/home" in url or "/d2l/lp/" in url:
                logger.info("Detected Brightspace home: %s", url)
                return True
            time.sleep(2)
        logger.warning("Timed out waiting for Brightspace home.")
        return False

    def save_storage_state(self) -> None:
        """Explicitly save storage state to a separate file."""
        if not self._context:
            return
        path = self.cfg.auth.storage_state_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=path)
        logger.info("Storage state saved to %s", path)


def open_brightspace(cfg: AppConfig) -> tuple[BrightspaceBrowser, Page]:
    """Convenience: start browser and navigate to Brightspace home."""
    bs = BrightspaceBrowser(cfg)
    ctx = bs.start()
    pg = bs.get_page()
    if pg:
        pg.goto(cfg.brightspace.url, wait_until="domcontentloaded", timeout=30000)
    return bs, pg
