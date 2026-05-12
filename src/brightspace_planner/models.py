"""Data models for brightspace-weekly-planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class DueItem:
    """A single item due in Brightspace."""
    course: str = ""
    course_code: str = ""
    title: str = ""
    type: str = ""
    due_date: str = ""
    priority: str = "MEDIUM"
    status: str = ""
    link: str = ""
    estimated_time: str = ""
    difficulty: str = ""
    summary: str = ""
    requirements: list[str] = field(default_factory=list)
    submission_instructions: str = ""
    attachments: list[str] = field(default_factory=list)
    rubric_summary: str = ""
    warnings: list[str] = field(default_factory=list)
    confidence: str = "medium"


@dataclass
class CourseEntry:
    """A course entry in the site map."""
    course_name: str = ""
    course_code: str = ""
    homepage_url: str = ""
    assignments_url: str = ""
    discussions_url: str = ""
    quizzes_url: str = ""
    content_url: str = ""
    calendar_url: str = ""
    announcements_url: str = ""
    grades_url: str = ""
    selectors_worked: list[str] = field(default_factory=list)
    unsafe_pages_skipped: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class SiteMap:
    """Brightspace site map — discovered by Hermes or created from course navigation."""
    discovered_at: str = ""
    brightspace_url: str = ""
    courses: list[CourseEntry] = field(default_factory=list)
    global_nav: dict = field(default_factory=dict)
    general_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "discovered_at": self.discovered_at,
            "brightspace_url": self.brightspace_url,
            "courses": [
                {k: v for k, v in c.__dict__.items()} for c in self.courses
            ],
            "global_nav": self.global_nav,
            "general_warnings": self.general_warnings,
        }


@dataclass
class ScanReport:
    """Weekly scan output report."""
    week_start: str = ""
    week_end: str = ""
    last_checked: str = ""
    auth_mode_used: str = ""
    courses_checked: list[str] = field(default_factory=list)
    items_due: list[dict] = field(default_factory=list)
    unclear_items: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "last_checked": self.last_checked,
            "auth_mode_used": self.auth_mode_used,
            "courses_checked": self.courses_checked,
            "items_due": self.items_due,
            "unclear_items": self.unclear_items,
            "errors": self.errors,
        }
