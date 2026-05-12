"""Utility helpers for brightspace-weekly-planner."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any

logger = logging.getLogger("brightspace_planner")


def ensure_dir(path: str) -> Path:
    """Create directory if it doesn't exist, return Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def now_iso() -> str:
    return datetime.now().isoformat()


def today_iso() -> str:
    return date.today().isoformat()


def write_json(path: str, data: Any) -> None:
    """Write data as pretty-printed JSON."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def read_json(path: str) -> Any:
    """Read JSON from path; return None if missing."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def append_log(path: str, message: str) -> None:
    """Append a timestamped line to a log file."""
    ensure_dir(os.path.dirname(path))
    ts = now_iso()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


def priority_from_due_date(due_str: str, today_d: date | None = None) -> str:
    """Assign priority based on how soon something is due."""
    if not today_d:
        today_d = date.today()
    try:
        due = date.fromisoformat(due_str[:10])
        delta = (due - today_d).days
        if delta <= 2:
            return "HIGH"
        elif delta <= 7:
            return "MEDIUM"
        else:
            return "LOW"
    except (ValueError, TypeError):
        return "MEDIUM"


def priority_from_type(item_type: str, weight_hint: str = "") -> str:
    """Boost priority for major item types."""
    lowered = item_type.lower()
    major = ["exam", "test", "midterm", "final", "project", "lab report", "major"]
    if any(m in lowered for m in major):
        return "HIGH"
    if "quiz" in lowered:
        return "MEDIUM"
    if "reading" in lowered or "optional" in lowered:
        return "LOW"
    return "MEDIUM"
