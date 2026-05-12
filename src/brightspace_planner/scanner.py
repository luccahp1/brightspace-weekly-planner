"""Scanner — reads the site map and checks due work across courses."""

from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime
from typing import Any, Optional

from playwright.sync_api import Page, TimeoutError as PWTimeout

from .config import AppConfig
from .models import ScanReport, DueItem, CourseEntry
from .site_map import load_site_map
from .safety import is_unsafe_url
from .utils import now_iso, priority_from_due_date, priority_from_type
from .content_scanner import (
    scan_course_content_deep,
    scan_course_calendar,
    scan_course_announcements,
)

logger = logging.getLogger("brightspace_planner")

# Date patterns found in Brightspace dropbox/quiz tables
_DATE_PATTERNS = [
    # "Due on May 9, 2026 11:30 PM"
    r"Due on ([A-Z][a-z]+ \d{1,2}, \d{4})",
    # "May 9, 2026 11:30 PM"
    r"([A-Z][a-z]+ \d{1,2}, \d{4})",
    # "2026-05-09"
    r"(\d{4}-\d{2}-\d{2})",
    # "Available on Jun 17, 2026 7:00 AM until Jun 17, 2026 11:00 PM"
    r"Available on ([A-Z][a-z]+ \d{1,2}, \d{4})",
]


def _parse_date(text: str) -> str:
    """Extract a date from text and return ISO format string."""
    for pat in _DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            raw = m.group(1)
            for fmt in ("%B %d, %Y", "%b %d, %Y"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
    # Try ISO directly
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    return ""


def _extract_dropbox_items(page: Page, course_name: str, course_code: str) -> list[dict]:
    """Extract assignment items from a Brightspace Submissions (Dropbox) page.

    The dropbox page has a table.d2l-table with rows. Each folder group has:
    - A header row (folder name like "Portfolio", "Labs", "Written Assignments")
    - Item rows with: title, due date, submission status, score
    """
    items: list[dict] = []

    try:
        rows = page.query_selector_all("table.d2l-table tbody tr")
    except Exception:
        return items

    current_folder = ""
    i = 0
    while i < len(rows):
        try:
            row = rows[i]
            text = row.inner_text().strip()

            # Detect folder header rows (no link, short text, often bold)
            links = row.query_selector_all("a[href]")
            is_header = len(links) == 0 and text and len(text) < 60

            if is_header and not any(d in text.lower() for d in ["due on", "not submitted", "submitted", "score", "evaluation"]):
                current_folder = text
                i += 1
                continue

            # Item rows have a link and "Due on" text
            if links and "due on" in text.lower():
                title = ""
                link = ""
                for a in links:
                    t = a.inner_text().strip()
                    h = a.get_attribute("href") or ""
                    if t and "not submitted" not in t.lower() and "submitted" not in t.lower():
                        title = t
                        link = h
                        break

                due_date = _parse_date(text)

                # Extract score if visible
                score = ""
                score_m = re.search(r"-\s*/\s*(\d+)", text)
                if score_m:
                    score = f"/{score_m.group(1)}"

                # Extract status
                status = ""
                if "not submitted" in text.lower():
                    status = "Not Submitted"
                elif "submitted" in text.lower() and "not" not in text.lower():
                    status = "Submitted"

                if title and due_date:
                    item_type = "assignment"
                    tl = title.lower()
                    if "lab" in tl:
                        item_type = "lab"
                    elif "quiz" in tl:
                        item_type = "quiz"
                    elif "case study" in tl or "project" in tl:
                        item_type = "project"
                    elif "portfolio" in tl or "part" in tl:
                        item_type = "assignment"
                    elif "discussion" in tl:
                        item_type = "discussion"

                    items.append({
                        "course": course_name,
                        "course_code": course_code,
                        "title": title,
                        "type": item_type,
                        "due_date": due_date,
                        "status": status,
                        "link": link,
                        "points": score,
                        "folder": current_folder,
                        "confidence": "high",
                    })
        except Exception:
            pass
        i += 1

    return items


def _extract_quiz_items(page: Page, course_name: str, course_code: str) -> list[dict]:
    """Extract quiz items from a Brightspace Quiz List page."""
    items: list[dict] = []

    try:
        rows = page.query_selector_all("table.d2l-table tbody tr")
    except Exception:
        return items

    for row in rows:
        try:
            text = row.inner_text().strip()
            links = row.query_selector_all("a[href]")

            if not links:
                continue

            # Quiz rows have "Available on" or "Due on" text
            if "available on" not in text.lower() and "due on" not in text.lower():
                continue

            title = ""
            link = ""
            for a in links:
                t = a.inner_text().strip()
                h = a.get_attribute("href") or ""
                if t and "unread" not in t.lower():
                    title = t
                    link = h
                    break

            due_date = _parse_date(text)

            # Extract attempts
            attempts = ""
            att_m = re.search(r"(\d+)\s*/\s*(\d+)", text)
            if att_m:
                attempts = f"{att_m.group(1)}/{att_m.group(2)}"

            if title and due_date:
                items.append({
                    "course": course_name,
                    "course_code": course_code,
                    "title": title,
                    "type": "quiz",
                    "due_date": due_date,
                    "status": attempts,
                    "link": link,
                    "confidence": "high",
                })
        except Exception:
            continue

    return items


def _extract_discussion_items(page: Page, course_name: str, course_code: str) -> list[dict]:
    """Extract discussion topics from a Discussions List page."""
    items: list[dict] = []

    try:
        topic_links = page.query_selector_all("a[href*='discussions/topics/']")
    except Exception:
        return items

    for link_el in topic_links:
        try:
            title = link_el.inner_text().strip()
            href = link_el.get_attribute("href") or ""
            if title and href:
                items.append({
                    "course": course_name,
                    "course_code": course_code,
                    "title": title,
                    "type": "discussion",
                    "due_date": "",
                    "link": href if href.startswith("http") else f"https://www.fanshaweonline.ca{href}",
                    "confidence": "medium",
                })
        except Exception:
            continue

    return items


def _items_in_week(items: list[dict], week_start: date, week_end: date) -> list[dict]:
    """Filter items to those due within the target week."""
    result = []
    for item in items:
        dd = item.get("due_date", "")
        if not dd:
            # Items without dates (e.g. discussions) — include for review
            continue
        try:
            d = date.fromisoformat(dd[:10])
            if week_start <= d <= week_end:
                result.append(item)
        except (ValueError, TypeError):
            continue
    return result


def scan_course(page: Page, course: CourseEntry, week_start: date, week_end: date, base_url: str) -> list[dict]:
    """Scan a single course for due items. Returns list of item dicts."""
    items: list[dict] = []
    course_name = course.course_name or "Unknown"
    course_code = course.course_code or ""
    logger.info("Scanning course: %s", course_name)

    # 1. Check Submissions (Dropbox)
    if course.assignments_url:
        try:
            page.goto(course.assignments_url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(1)
            dropbox_items = _extract_dropbox_items(page, course_name, course_code)
            items.extend(_items_in_week(dropbox_items, week_start, week_end))
            logger.info("  Dropbox: %d items total, %d in week", len(dropbox_items), len(_items_in_week(dropbox_items, week_start, week_end)))
        except PWTimeout:
            logger.warning("  Timeout loading dropbox for %s", course_name)
        except Exception as e:
            logger.error("  Error loading dropbox for %s: %s", course_name, e)

    # 2. Check Quizzes
    if course.quizzes_url:
        try:
            page.goto(course.quizzes_url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(1)
            quiz_items = _extract_quiz_items(page, course_name, course_code)
            items.extend(_items_in_week(quiz_items, week_start, week_end))
            logger.info("  Quizzes: %d items total, %d in week", len(quiz_items), len(_items_in_week(quiz_items, week_start, week_end)))
        except PWTimeout:
            logger.warning("  Timeout loading quizzes for %s", course_name)
        except Exception as e:
            logger.error("  Error loading quizzes for %s: %s", course_name, e)

    # 3. Check Discussions (for topic list)
    if course.discussions_url:
        try:
            page.goto(course.discussions_url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(1)
            disc_items = _extract_discussion_items(page, course_name, course_code)
            items.extend(disc_items)
            logger.info("  Discussions: %d topics found", len(disc_items))
        except PWTimeout:
            logger.warning("  Timeout loading discussions for %s", course_name)
        except Exception as e:
            logger.error("  Error loading discussions for %s: %s", course_name, e)

    # 4. Deep content scan — expand all accordion trees
    try:
        content_items = scan_course_content_deep(page, course, week_start, week_end, base_url)
        # Only include content items that have a due date in our week,
        # or that have attachments (files to download),
        # or that are classified as important types
        for ci in content_items:
            if ci.get("due_date") and ci["due_date"] in [i.get("due_date") for i in items]:
                # Already have this from dropbox/quiz, skip duplicate
                continue
            if ci.get("in_current_week"):
                items.append(ci)
            elif ci.get("attachments"):
                # Has file attachments — always include
                items.append(ci)
            elif ci.get("type") in ("reading", "lecture_notes", "instructions", "rubric", "syllabus"):
                # Important content types — include for review
                items.append(ci)
        logger.info("  Content scan: %d items extracted, %d added to report", len(content_items), len([i for i in items if i.get("content_type") == "content_page"]))
    except Exception as e:
        logger.error("  Error in content scan for %s: %s", course_name, e)

    # 5. Calendar events
    try:
        cal_items = scan_course_calendar(page, course, week_start, week_end)
        items.extend(cal_items)
        logger.info("  Calendar: %d events in week", len(cal_items))
    except Exception as e:
        logger.error("  Error in calendar scan for %s: %s", course_name, e)

    # 6. Announcements
    try:
        ann_items = scan_course_announcements(page, course)
        items.extend(ann_items)
        logger.info("  Announcements: %d found", len(ann_items))
    except Exception as e:
        logger.error("  Error in announcements scan for %s: %s", course_name, e)

    return items


def run_scan(cfg: AppConfig, page: Page, site_map: Any, auth_mode: str) -> ScanReport:
    """Run a weekly scan using the loaded site map."""
    report = ScanReport(
        week_start=cfg.week_start.isoformat(),
        week_end=cfg.week_end.isoformat(),
        last_checked=now_iso(),
        auth_mode_used=auth_mode,
        courses_checked=[],
        items_due=[],
        unclear_items=[],
        errors=[],
    )

    if not site_map or not site_map.courses:
        report.errors.append("No site map or courses found. Run discovery first.")
        return report

    base_url = cfg.brightspace.url
    today_d = date.today()

    for course in site_map.courses:
        report.courses_checked.append(course.course_name or "Unknown")
        try:
            items = scan_course(page, course, cfg.week_start, cfg.week_end, base_url)
            for item in items:
                # Compute priority
                p = priority_from_due_date(item.get("due_date", ""), today_d)
                p2 = priority_from_type(item.get("type", ""))
                item["priority"] = "HIGH" if "HIGH" in (p, p2) else (p2 if p2 != "MEDIUM" else p)
                item.setdefault("confidence", "medium")
                item.setdefault("requirements", [])
                item.setdefault("attachments", [])
                item.setdefault("warnings", [])
                item.setdefault("summary", "")
                item.setdefault("estimated_time", "")
                item.setdefault("difficulty", "")
                item.setdefault("rubric_summary", "")
                item.setdefault("submission_instructions", "")
                report.items_due.append(item)
        except Exception as e:
            report.errors.append(f"Error scanning {course.course_name}: {e}")

    # Sort by due date
    report.items_due.sort(key=lambda x: x.get("due_date", ""))

    return report
