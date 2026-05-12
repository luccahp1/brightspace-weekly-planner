"""Authentication helper — opens Brightspace for manual login/MFA."""

from __future__ import annotations

import logging
import sys
import time

from .config import AppConfig
from .browser_client import BrightspaceBrowser

logger = logging.getLogger("brightspace_planner")


def run_auth(cfg: AppConfig, timeout_s: int = 180) -> bool:
    """Open headed Chromium, navigate to Brightspace, wait for manual login.

    Returns True if login to Brightspace was detected.
    """
    print("\n" + "=" * 60)
    print("  Brightspace Authentication")
    print("=" * 60)
    print(f"\n  URL: {cfg.brightspace.url}")
    print(f"  Profile: {cfg.auth.playwright_profile_dir}")
    print(f"\n  A Chromium window should appear on your Windows desktop.")
    print(f"  Please log in and complete MFA if required.")
    print(f"  Waiting up to {timeout_s} seconds for you to reach the Brightspace homepage.")
    print("=" * 60 + "\n")

    bs = BrightspaceBrowser(cfg)
    try:
        ctx = bs.start()
        pg = bs.get_page()
        if pg is None:
            print("ERROR: Could not open a browser page.")
            return False

        pg.goto(cfg.brightspace.url, wait_until="domcontentloaded", timeout=30000)
        print(f"  Browser navigated to {cfg.brightspace.url}")
        print("  Waiting for Brightspace homepage...\n")

        detected = bs.wait_for_home(timeout_s=timeout_s)
        if detected:
            print("\n  SUCCESS: Brightspace homepage detected!")
            print(f"  Current URL: {pg.url}")
            # Save extra storage state copy for convenience
            try:
                bs.save_storage_state()
                print("  Storage state saved.")
            except Exception:
                pass
            return True
        else:
            print("\n  TIMEOUT: Could not confirm Brightspace homepage.")
            print(f"  Current URL: {pg.url}")
            print("  You can still close the browser. The profile may have")
            print("  partial auth state saved.")
            return False
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user.")
        return False
    finally:
        bs.stop()
