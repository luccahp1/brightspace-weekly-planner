"""Configuration loading for brightspace-weekly-planner."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from datetime import date, timedelta

import yaml
from dotenv import load_dotenv


def _project_root() -> Path:
    """Return the project root (contains src/, output/, etc.)."""
    return Path(__file__).resolve().parent.parent.parent


def _load_dotenv():
    """Load .env from the project root if it exists."""
    env_path = _project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@dataclass
class BrightspaceConfig:
    url: str = "https://www.fanshaweonline.ca/d2l/home"
    username: str = ""
    password: str = ""


@dataclass
class WeekConfig:
    start_date: str = ""
    end_date: str = ""


@dataclass
class OutputConfig:
    folder: str = str(_project_root() / "output")
    site_map_path: str = str(_project_root() / "output" / "brightspace_site_map.json")


@dataclass
class AuthConfig:
    mode: str = "persistent_profile"
    playwright_profile_dir: str = str(_project_root() / ".local_browser_profile")
    storage_state_path: str = str(_project_root() / "secrets" / "brightspace_storage_state.json")


@dataclass
class BrowserConfig:
    headless: bool = False
    slow_mo_ms: int = 0


@dataclass
class AppConfig:
    brightspace: BrightspaceConfig = field(default_factory=BrightspaceConfig)
    week: WeekConfig = field(default_factory=WeekConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)

    @property
    def week_start(self) -> date:
        if self.week.start_date:
            return date.fromisoformat(self.week.start_date)
        today = date.today()
        return today - timedelta(days=today.weekday())

    @property
    def week_end(self) -> date:
        if self.week.end_date:
            return date.fromisoformat(self.week.end_date)
        return self.week_start + timedelta(days=6)


def load_config(env_path: str | None = None, yaml_path: str | None = None) -> AppConfig:
    """Load configuration from .env, YAML file, and environment variables."""
    _load_dotenv()

    if env_path is None:
        env_path = str(_project_root() / ".env")
    if yaml_path is None:
        yaml_path = str(_project_root() / "config.yaml")

    # Load .env
    if Path(env_path).exists():
        load_dotenv(env_path)

    # Load YAML if present
    yaml_data: dict = {}
    if Path(yaml_path).exists():
        with open(yaml_path) as f:
            yaml_data = yaml.safe_load(f) or {}

    def env(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    bs_cfg = yaml_data.get("brightspace", {})
    week_cfg = yaml_data.get("week", {})
    out_cfg = yaml_data.get("output", {})
    auth_cfg = yaml_data.get("auth", {})
    br_cfg = yaml_data.get("browser", {})

    return AppConfig(
        brightspace=BrightspaceConfig(
            url=env("BRIGHTSPACE_URL", bs_cfg.get("url", "https://www.fanshaweonline.ca/d2l/home")),
            username=env("BRIGHTSPACE_USERNAME", bs_cfg.get("username", "")),
            password=env("BRIGHTSPACE_PASSWORD", bs_cfg.get("password", "")),
        ),
        week=WeekConfig(
            start_date=env("WEEK_START_DATE", week_cfg.get("start_date", "")),
            end_date=env("WEEK_END_DATE", week_cfg.get("end_date", "")),
        ),
        output=OutputConfig(
            folder=env("OUTPUT_FOLDER", out_cfg.get("folder", str(_project_root() / "output"))),
            site_map_path=env("SITE_MAP_PATH", out_cfg.get(
                "site_map_path", str(_project_root() / "output" / "brightspace_site_map.json")
            )),
        ),
        auth=AuthConfig(
            mode=env("AUTH_MODE", auth_cfg.get("mode", "persistent_profile")),
            playwright_profile_dir=env("PLAYWRIGHT_PROFILE_DIR", auth_cfg.get(
                "playwright_profile_dir", str(_project_root() / ".local_browser_profile")
            )),
            storage_state_path=env("PLAYWRIGHT_STORAGE_STATE_PATH", auth_cfg.get(
                "storage_state_path",
                str(_project_root() / "secrets" / "brightspace_storage_state.json")
            )),
        ),
        browser=BrowserConfig(
            headless=env("HEADLESS", str(br_cfg.get("headless", False))).lower() in ("true", "1", "yes"),
            slow_mo_ms=int(env("BROWSER_SLOW_MO_MS", str(br_cfg.get("slow_mo_ms", 0)))),
        ),
    )
