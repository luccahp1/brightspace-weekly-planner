"""Sample/fake data for tests and sample-report mode."""

from datetime import date, timedelta

TODAY = date.today()
TODAY_STR = TODAY.isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
NEXT_WEEK = (TODAY + timedelta(days=5)).isoformat()

SAMPLE_ITEMS = [
    {
        "course": "Systems Design & Architecture",
        "course_code": "SYST-3040",
        "title": "Assignment 3: UML Diagrams",
        "type": "assignment",
        "due_date": TODAY_STR,
        "priority": "HIGH",
        "status": "Not submitted",
        "link": "https://www.fanshaweonline.ca/d2l/lms/assignments/view.d2l",
        "estimated_time": "3 hours",
        "difficulty": "medium",
        "summary": "Create UML class and sequence diagrams for case study.",
        "requirements": ["Class diagram", "Sequence diagram", "2-page report"],
        "submission_instructions": "Upload PDF to Assignment Dropbox.",
        "attachments": [],
        "rubric_summary": "See rubric tab in dropbox.",
        "warnings": [],
        "confidence": "high",
    },
    {
        "course": "Technical Communications",
        "course_code": "COMM-3025",
        "title": "Discussion 5: Peer Review",
        "type": "discussion",
        "due_date": TOMORROW,
        "priority": "HIGH",
        "status": "",
        "link": "https://www.fanshaweonline.ca/d2l/le/3025/discussions/",
        "estimated_time": "1 hour",
        "difficulty": "low",
        "summary": "Post your draft report and review two classmates' posts.",
        "requirements": ["Post draft", "Review 2 peers"],
        "submission_instructions": "Post in Discussion forum.",
        "attachments": [],
        "rubric_summary": "",
        "warnings": [],
        "confidence": "high",
    },
    {
        "course": "Intro to Management",
        "course_code": "MGMT-2001",
        "title": "Quiz 4: Ch 7-9",
        "type": "quiz",
        "due_date": NEXT_WEEK,
        "priority": "MEDIUM",
        "status": "",
        "link": "https://www.fanshaweonline.ca/d2l/lms/quizzing/",
        "estimated_time": "45 min",
        "difficulty": "medium",
        "summary": "Online quiz covering chapters 7-9.",
        "requirements": [],
        "submission_instructions": "Complete in Quizzes tool.",
        "attachments": [],
        "rubric_summary": "",
        "warnings": ["Multiple-choice, timed (60 min)."],
        "confidence": "medium",
    },
]

SAMPLE_REPORT_DICT = {
    "week_start": TODAY.isoformat(),
        "week_end": (TODAY + timedelta(days=6)).isoformat(),
    "last_checked": "2026-01-01T00:00:00",
    "auth_mode_used": "sample_data",
    "courses_checked": ["SYST-3040", "COMM-3025", "MGMT-2001"],
    "items_due": SAMPLE_ITEMS,
    "unclear_items": [
        "Check if reading for MGMT-2001 Ch 10 is required this week.",
    ],
    "errors": [],
}

SAMPLE_SITE_MAP = {
    "discovered_at": "2026-01-01T00:00:00",
    "brightspace_url": "https://www.fanshaweonline.ca/d2l/home",
    "courses": [
        {
            "course_name": "Systems Design & Architecture",
            "course_code": "SYST-3040",
            "homepage_url": "https://www.fanshaweonline.ca/d2l/le/content/12345",
            "assignments_url": "https://www.fanshaweonline.ca/d2l/lms/assignments/list.d2l?ou=12345",
            "discussions_url": "",
            "quizzes_url": "",
            "content_url": "",
            "calendar_url": "",
            "announcements_url": "",
            "grades_url": "",
            "selectors_worked": [],
            "unsafe_pages_skipped": [],
            "notes": "Example only — not real data.",
        },
    ],
    "global_nav": {},
    "general_warnings": [],
}
