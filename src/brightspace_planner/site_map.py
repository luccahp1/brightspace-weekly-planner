"""Site map loading / saving for Brightspace structure."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .models import SiteMap, CourseEntry

logger = logging.getLogger("brightspace_planner")


def load_site_map(path: str) -> Optional[SiteMap]:
    """Load a site map from JSON; return None if not found or invalid."""
    p = Path(path)
    if not p.exists():
        logger.warning("Site map not found at %s — run discovery first.", path)
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        courses = [CourseEntry(**c) for c in data.get("courses", [])]
        return SiteMap(
            discovered_at=data.get("discovered_at", ""),
            brightspace_url=data.get("brightspace_url", ""),
            courses=courses,
            global_nav=data.get("global_nav", {}),
            general_warnings=data.get("general_warnings", []),
        )
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Failed to parse site map: %s", e)
        return None


def save_site_map(path: str, site_map: SiteMap) -> None:
    """Save a site map to JSON."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(site_map.to_dict(), f, indent=2, ensure_ascii=False)
    logger.info("Site map saved to %s", path)


def get_example_site_map() -> dict:
    """Return an example/fake site map schema for documentation."""
    return {
        "discovered_at": "",
        "brightspace_url": "https://example.brightspace.com/d2l/home",
        "courses": [
            {
                "course_name": "Example Course 101",
                "course_code": "COMP-101",
                "homepage_url": "https://example.brightspace.com/d2l/le/content/12345",
                "assignments_url": "https://example.brightspace.com/d2l/lms/assignments/list.d2l?ou=12345",
                "discussions_url": "",
                "quizzes_url": "",
                "content_url": "",
                "calendar_url": "",
                "announcements_url": "",
                "grades_url": "",
                "selectors_worked": [],
                "unsafe_pages_skipped": [],
                "notes": "This is an example entry. Replace with real discovery data.",
            }
        ],
        "global_nav": {},
        "general_warnings": [],
    }
