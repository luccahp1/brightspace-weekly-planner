"""Safety helpers — enforce read-only behaviour in Brightspace."""

from __future__ import annotations
import re
from typing import Optional

# Keywords that suggest a page/action could modify state
_UNSAFE_ACTION_HINTS = [
    "submit", "start attempt", "begin attempt", "post reply", "upload",
    "save", "confirm", "final submit", "send message", "mark complete",
    "dropbox submit", "quiz attempt", "new topic", "create thread",
]

# URL patterns that strongly suggest modification endpoints
_UNSAFE_URL_PATTERNS = [
    r"/dropbox/submissions/",
    r"/quizzes/[0-9]+/attempt",
    r"/discussions.*/posts.*new",
    r"/assignments.*/submit",
]


def is_unsafe_url(url: str) -> bool:
    """Return True if the URL looks like it could trigger a modification."""
    for pat in _UNSAFE_URL_PATTERNS:
        if re.search(pat, url, re.IGNORECASE):
            return True
    return False


def check_button_safety(label: str) -> tuple[bool, Optional[str]]:
    """Check whether a button label looks like a write/submission action.

    Returns (is_safe, reason_if_unsafe).
    """
    lowered = label.strip().lower()
    for hint in _UNSAFE_ACTION_HINTS:
        if hint in lowered:
            return False, f"Button '{label}' matches unsafe hint: '{hint}'"
    return True, None


def filter_unsafe_items(item_type: str, link: str, label: str = "") -> tuple[bool, Optional[str]]:
    """Return (is_safe, reason) for a navigation/item action."""
    if is_unsafe_url(link):
        return False, f"URL pattern mismatch: {link}"
    if label:
        safe, reason = check_button_safety(label)
        if not safe:
            return safe, reason
    return True, None
