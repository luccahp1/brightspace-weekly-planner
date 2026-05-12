"""
Deep content scanner — expands all accordion trees in Brightspace content pages.

Reads every module, sub-module, and content item. Extracts text instructions,
file attachments (PDF, PPT, DOC, etc.), and embedded media links.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from datetime import date, datetime
from typing import Any

from playwright.sync_api import Page, TimeoutError as PWTimeout

from .config import AppConfig
from .models import CourseEntry
from .safety import is_unsafe_url
from .utils import now_iso

logger = logging.getLogger("brightspace_planner")

# Selectors
_ACCORDION_ITEM = ".d2l-le-TreeAccordionItem-wrapper"
_VIEW_CONTENT_LINK = "a[href*='viewContent']"
_FILE_LINK = (
    "a[href$='.pdf'], a[href$='.ppt'], a[href$='.pptx'], a[href$='.doc'], "
    "a[href$='.docx'], a[href$='.xls'], a[href$='.xlsx'], a[href$='.zip'], "
    "a[href$='.mp4'], a[href$='.mp3'], a[href$='.wav']"
)
_PDF_IFRAME = "iframe[src*='pdfjs']"
_VIDEO_IFRAME = (
    "iframe[src*='video'], iframe[src*='youtube'], iframe[src*='vimeo'], "
    "iframe[src*='kaltura'], iframe[src*='mediaspace']"
)
_LTI_IFRAME = "iframe[src*='lti'], iframe[src*='framedlaunch']"

_EXT_TYPE = {
    ".pdf": "PDF",
    ".ppt": "PowerPoint",
    ".pptx": "PowerPoint",
    ".doc": "Word Doc",
    ".docx": "Word Doc",
    ".xls": "Spreadsheet",
    ".xlsx": "Spreadsheet",
    ".zip": "Archive",
    ".mp4": "Video",
    ".mp3": "Audio",
    ".wav": "Audio",
}


def _safe_inner_text(page: Page, selector: str) -> str:
    try:
        el = page.query_selector(selector)
        if el:
            return el.inner_text().strip()
    except Exception:
        pass
    return ""


def _all_links(page: Page, selector: str) -> list:
    try:
        return page.query_selector_all(selector)
    except Exception:
        return []


def _get_base_url(page: Page) -> str:
    try:
        parsed = urllib.parse.urlparse(page.url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return "https://www.fanshaweonline.ca"


def _make_absolute(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    return base + href


def _classify_content(title: str, url: str) -> str:
    tl = title.lower()
    if any(w in tl for w in ["lab", "exercise", "practice"]):
        return "lab"
    if any(w in tl for w in ["quiz", "test", "exam", "midterm", "final"]):
        return "quiz"
    if any(w in tl for w in ["assignment", "project", "case study", "portfolio", "report"]):
        return "assignment"
    if any(w in tl for w in ["discussion", "forum", "peer review"]):
        return "discussion"
    if any(w in tl for w in ["reading", "chapter", "article", "textbook"]):
        return "reading"
    if any(w in tl for w in ["lecture", "slide", "presentation", "notes", "powerpoint", "ppt"]):
        return "lecture_notes"
    if any(w in tl for w in ["video", "recording", "webinar"]):
        return "video"
    if any(w in tl for w in ["link", "resource", "reference", "website"]):
        return "resource"
    if any(w in tl for w in ["instruction", "guide", "how to", "tutorial"]):
        return "instructions"
    if any(w in tl for w in ["rubric", "criteria", "grading"]):
        return "rubric"
    if any(w in tl for w in ["announcement", "news", "update"]):
        return "announcement"
    if any(w in tl for w in ["syllabus", "outline", "schedule", "calendar"]):
        return "syllabus"
    if any(w in tl for w in ["welcome", "introduction", "overview", "getting started"]):
        return "overview"
    return "content"


def _extract_file_attachments(page: Page, base: str) -> list:
    """Extract all file attachment links from a content page."""
    attachments: list[dict] = []

    # 1. Direct file links
    for link_el in _all_links(page, _FILE_LINK):
        try:
            text = link_el.inner_text().strip()
            href = link_el.get_attribute("href") or ""
            if not text or not href:
                continue
            href_abs = _make_absolute(href, base)
            ext = ""
            for e in _EXT_TYPE:
                if e in href.lower():
                    ext = e
                    break
            attachments.append({
                "name": text,
                "url": href_abs,
                "type": _EXT_TYPE.get(ext, "file"),
                "source": "direct_link",
            })
        except Exception:
            continue

    # 2. PDF viewer iframes (D2L converts PPTX/PDF to pdfjs viewer)
    for iframe_el in page.query_selector_all(_PDF_IFRAME):
        try:
            src = iframe_el.get_attribute("src") or ""
            if "file=" in src:
                parsed = urllib.parse.urlparse(src)
                params = urllib.parse.parse_qs(parsed.query)
                if "file" in params:
                    pdf_url = params["file"][0]
                    title = _safe_inner_text(page, "h1, .d2l-pageTitle") or "Document"
                    attachments.append({
                        "name": title,
                        "url": pdf_url,
                        "type": "PDF",
                        "source": "pdfjs_iframe",
                    })
        except Exception:
            continue

    # 3. Video embeds
    for iframe_el in page.query_selector_all(_VIDEO_IFRAME):
        try:
            src = iframe_el.get_attribute("src") or ""
            if src:
                attachments.append({
                    "name": "Embedded Video",
                    "url": _make_absolute(src, base),
                    "type": "video",
                    "source": "video_iframe",
                })
        except Exception:
            continue

    # 4. LTI tool iframes
    for iframe_el in page.query_selector_all(_LTI_IFRAME):
        try:
            src = iframe_el.get_attribute("src") or ""
            if src and "pdfjs" not in src:
                attachments.append({
                    "name": "External Tool",
                    "url": _make_absolute(src, base),
                    "type": "lti_tool",
                    "source": "lti_iframe",
                })
        except Exception:
            continue

    return attachments


def _extract_page_text(page: Page) -> str:
    """Extract readable text content from a Brightspace content page."""
    text_parts: list[str] = []
    for sel in [".d2l-pageContent", "#d2l_pageContent", ".d2l-htmlblock", ".d2l-body", "main"]:
        try:
            el = page.query_selector(sel)
            if el:
                t = el.inner_text().strip()
                if t and len(t) > 20:
                    text_parts.append(t)
                    break
        except Exception:
            continue
    if not text_parts:
        try:
            t = page.inner_text("body")
            if t:
                text_parts.append(t.strip()[:3000])
        except Exception:
            pass
    full_text = "\n\n".join(text_parts)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    return full_text[:5000]


def _get_accordion_items(page: Page) -> list:
    try:
        return page.query_selector_all(_ACCORDION_ITEM)
    except Exception:
        return []


def _is_accordion_expanded(item) -> bool:
    try:
        cls = item.get_attribute("class") or ""
        return "selected" in cls
    except Exception:
        return False


def _get_accordion_text(item) -> str:
    try:
        return item.inner_text().strip()
    except Exception:
        return ""


def _click_accordion_and_wait(page: Page, item, wait_ms: int = 2000) -> bool:
    try:
        if not _is_accordion_expanded(item):
            item.click()
            time.sleep(wait_ms / 1000)
            return True
        return False
    except Exception:
        return False


def _get_view_content_links(page: Page) -> list:
    links: list[dict] = []
    for link_el in _all_links(page, _VIEW_CONTENT_LINK):
        try:
            text = link_el.inner_text().strip()
            href = link_el.get_attribute("href") or ""
            if text and href:
                links.append({"title": text, "url": href})
        except Exception:
            continue
    return links


def scan_course_content_deep(
    page: Page,
    course: CourseEntry,
    week_start: date,
    week_end: date,
    base_url: str,
) -> list:
    """Deep-scan a course's content page by expanding every accordion item.

    Strategy:
    1. Navigate to the course content page.
    2. Collect all top-level accordion items.
    3. For each accordion item, click to expand, collect viewContent links.
    4. Do multiple passes to catch nested accordions.
    5. For each viewContent link, navigate and extract title, text, attachments.
    """
    items: list[dict] = []
    course_name = course.course_name or "Unknown"
    course_code = course.course_code or ""
    content_url = course.content_url

    if not content_url:
        logger.info("  Content: no content URL for %s, skipping", course_name)
        return items

    logger.info("  Content deep scan: %s", course_name)

    try:
        page.goto(content_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
    except PWTimeout:
        logger.warning("  Timeout loading content page for %s", course_name)
        return items
    except Exception as e:
        logger.error("  Error loading content page for %s: %s", course_name, e)
        return items

    # Phase 1: Expand all accordion items and collect viewContent links
    all_content_links: list[dict] = []
    seen_urls: set = set()
    expanded_count = 0
    max_accordion_clicks = 200

    for pass_num in range(3):
        items_before = len(all_content_links)
        accordion_items = _get_accordion_items(page)

        for i, item in enumerate(accordion_items):
            if expanded_count >= max_accordion_clicks:
                logger.info("  Content: reached max accordion clicks (%d)", max_accordion_clicks)
                break

            text = _get_accordion_text(item)
            if not text:
                continue

            if pass_num > 0 and _is_accordion_expanded(item):
                links = _get_view_content_links(page)
                for link in links:
                    if link["url"] not in seen_urls:
                        seen_urls.add(link["url"])
                        all_content_links.append(link)
                continue

            was_clicked = _click_accordion_and_wait(page, item, wait_ms=1500)
            if was_clicked:
                expanded_count += 1

            links = _get_view_content_links(page)
            for link in links:
                if link["url"] not in seen_urls:
                    seen_urls.add(link["url"])
                    all_content_links.append(link)

        items_after = len(all_content_links)
        logger.info("  Content: pass %d — %d total viewContent links", pass_num + 1, items_after)

        if items_after == items_before:
            break

    logger.info("  Content: expanded %d accordions, found %d links", expanded_count, len(all_content_links))

    # Phase 2: Visit each content page and extract details
    for idx, link_info in enumerate(all_content_links):
        title = link_info["title"]
        url = link_info["url"]
        url_abs = _make_absolute(url, base_url)

        if is_unsafe_url(url_abs):
            logger.warning("  Content: skipping unsafe URL: %s", url_abs)
            items.append({
                "course": course_name,
                "course_code": course_code,
                "title": title,
                "type": "content",
                "due_date": "",
                "link": url_abs,
                "confidence": "low",
                "warnings": ["URL flagged as potentially unsafe — needs human review"],
                "summary": "",
                "attachments": [],
                "content_type": "unsafe_skipped",
            })
            continue

        try:
            page.goto(url_abs, wait_until="domcontentloaded", timeout=20000)
            time.sleep(1.5)

            page_title = page.title()
            page_text = _extract_page_text(page)
            attachments = _extract_file_attachments(page, base_url)
            content_type = _classify_content(title, url_abs)

            summary = page_text[:300].strip() if page_text else ""
            if summary:
                summary = summary.replace("\n", " ").strip()

            # Check for due date mentions in page text
            due_date = ""
            for pat in [
                r"[Dd]ue[:\s]+([A-Z][a-z]+ \d{1,2},? \d{4})",
                r"[Dd]ue[:\s]+(\d{4}-\d{2}-\d{2})",
                r"[Dd]eadline[:\s]+([A-Z][a-z]+ \d{1,2},? \d{4})",
            ]:
                m = re.search(pat, page_text)
                if m:
                    raw = m.group(1)
                    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%Y-%m-%d"):
                        try:
                            due_date = datetime.strptime(raw, fmt).date().isoformat()
                            break
                        except ValueError:
                            continue
                    if due_date:
                        break

            item = {
                "course": course_name,
                "course_code": course_code,
                "title": title,
                "type": content_type,
                "due_date": due_date,
                "link": url_abs,
                "confidence": "high",
                "summary": summary,
                "attachments": attachments,
                "page_title": page_title,
                "content_type": "content_page",
                "requirements": [],
                "warnings": [],
            }

            if due_date:
                try:
                    d = date.fromisoformat(due_date)
                    if week_start <= d <= week_end:
                        item["in_current_week"] = True
                except ValueError:
                    pass

            items.append(item)

        except PWTimeout:
            logger.warning("  Content: timeout loading %s", url_abs)
            items.append({
                "course": course_name,
                "course_code": course_code,
                "title": title,
                "type": "content",
                "due_date": "",
                "link": url_abs,
                "confidence": "low",
                "warnings": ["Timeout loading page"],
                "summary": "",
                "attachments": [],
                "content_type": "timeout",
            })
        except Exception as e:
            logger.error("  Content: error loading %s: %s", url_abs, e)
            items.append({
                "course": course_name,
                "course_code": course_code,
                "title": title,
                "type": "content",
                "due_date": "",
                "link": url_abs,
                "confidence": "low",
                "warnings": [f"Error: {e}"],
                "summary": "",
                "attachments": [],
                "content_type": "error",
            })

    logger.info("  Content: extracted %d items from %s", len(items), course_name)
    return items


def scan_course_calendar(
    page: Page,
    course: CourseEntry,
    week_start: date,
    week_end: date,
) -> list:
    """Extract calendar events for a course within the target week."""
    items: list[dict] = []
    course_name = course.course_name or "Unknown"
    course_code = course.course_code or ""

    if not course.calendar_url:
        return items

    try:
        page.goto(course.calendar_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
    except Exception as e:
        logger.warning("  Calendar error for %s: %s", course_name, e)
        return items

    event_links = page.query_selector_all("a[href*='calendar'][href*='event']")
    for link_el in event_links:
        try:
            text = link_el.inner_text().strip()
            href = link_el.get_attribute("href") or ""
            if not text or not href:
                continue

            due_date = ""
            for pat in [r"([A-Z][a-z]+ \d{1,2}, \d{4})", r"(\d{4}-\d{2}-\d{2})"]:
                m = re.search(pat, text)
                if m:
                    raw = m.group(1)
                    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
                        try:
                            due_date = datetime.strptime(raw, fmt).date().isoformat()
                            break
                        except ValueError:
                            continue
                    if due_date:
                        break

            if due_date:
                try:
                    d = date.fromisoformat(due_date)
                    if week_start <= d <= week_end:
                        items.append({
                            "course": course_name,
                            "course_code": course_code,
                            "title": text[:100],
                            "type": "calendar_event",
                            "due_date": due_date,
                            "link": _make_absolute(href, _get_base_url(page)),
                            "confidence": "high",
                            "summary": "",
                            "attachments": [],
                            "warnings": [],
                        })
                except ValueError:
                    pass
        except Exception:
            continue

    return items


def scan_course_announcements(
    page: Page,
    course: CourseEntry,
) -> list:
    """Extract recent announcements for a course."""
    items: list[dict] = []
    course_name = course.course_name or "Unknown"
    course_code = course.course_code or ""

    if not course.announcements_url:
        return items

    try:
        page.goto(course.announcements_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
    except Exception as e:
        logger.warning("  Announcements error for %s: %s", course_name, e)
        return items

    ann_links = page.query_selector_all(".d2l-widget-content a, .d2l-news-item a, a[href*='news']")
    for link_el in ann_links[:10]:
        try:
            text = link_el.inner_text().strip()
            href = link_el.get_attribute("href") or ""
            if not text or not href or len(text) < 5:
                continue
            if "show all" in text.lower():
                continue
            items.append({
                "course": course_name,
                "course_code": course_code,
                "title": text[:100],
                "type": "announcement",
                "due_date": "",
                "link": _make_absolute(href, _get_base_url(page)),
                "confidence": "high",
                "summary": "",
                "attachments": [],
                "warnings": [],
            })
        except Exception:
            continue

    return items
