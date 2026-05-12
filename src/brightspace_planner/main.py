"""Main CLI entry point for brightspace-weekly-planner."""

from __future__ import annotations

import json
import logging
import sys
from datetime import date, datetime

from .config import load_config
from .models import ScanReport
from .site_map import load_site_map, get_example_site_map, save_site_map
from .report_writer import write_all_reports
from .dashboard_writer import write_dashboard
from .browser_client import BrightspaceBrowser
from .scanner import run_scan
from .auth import run_auth
from .utils import now_iso, today_iso, ensure_dir

logger = logging.getLogger("brightspace_planner")


def _setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_gui_test(cfg: AppConfig):
    """Open headed Chromium through WSLg and navigate to Brightspace."""
    from .browser_client import open_brightspace

    print("\n[GUI TEST] Starting headed Chromium...")
    print(f"  BRIGHTSPACE_URL: {cfg.brightspace.url}")
    print(f"  HEADLESS: {cfg.browser.headless}")
    print(f"  DISPLAY: {__import__('os').environ.get('DISPLAY', 'not set')}")
    print()

    bs, pg = open_brightspace(cfg)
    try:
        if pg:
            print(f"  Browser opened successfully!")
            print(f"  Current URL: {pg.url}")
            print(f"  Title: {pg.title()}")
            print("\n  You should see a Chromium window on your Windows desktop.")
            print("  The browser will close in 30 seconds...")
            import time
            time.sleep(30)
        else:
            print("ERROR: No browser page was created.")
    finally:
        bs.stop()
    print("[GUI TEST] Done.")


def cmd_auth(cfg: AppConfig):
    """Open browser for manual login/MFA."""
    success = run_auth(cfg)
    if success:
        print("\nAuth complete. You can now run scan.")
    else:
        print("\nAuth was not confirmed. You may try again.")
        sys.exit(1)


def cmd_sample_report(cfg: AppConfig):
    """Generate reports from sample data without Brightspace."""
    print("\n[SAMPLE REPORT] Generating from fake data...\n")

    today_d = date.today()
    sample_data = {
        "week_start": cfg.week_start.isoformat(),
        "week_end": cfg.week_end.isoformat(),
        "last_checked": now_iso(),
        "auth_mode_used": "sample_data",
        "courses_checked": ["SYST-3040", "COMM-3025", "MGMT-2001"],
        "items_due": [
            {
                "course": "Systems Design & Architecture",
                "course_code": "SYST-3040",
                "title": "Assignment 3: UML Diagrams",
                "type": "assignment",
                "due_date": (today_d).isoformat(),
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
                "due_date": (today_d).isoformat(),
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
                "warnings":["Discussion post required, not just a dropbox."],
                "confidence": "high",
            },
            {
                "course": "Intro to Management",
                "course_code": "MGMT-2001",
                "title": "Quiz 4: Ch 7-9",
                "type": "quiz",
                "due_date": (today_d).isoformat(),
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
        ],
        "unclear_items": [
            "Check if reading for MGMT-2001 Ch 10 is required this week.",
        ],
        "errors": [],
    }

    report = ScanReport(**sample_data)
    paths = write_all_reports(cfg, report)
    dash_path = write_dashboard(cfg, sample_data)

    print(f"  Markdown report: {paths['markdown']}")
    print(f"  JSON report:     {paths['json']}")
    print(f"  Run log:         {paths['run_log']}")
    print(f"  Dashboard:       {dash_path}")
    print("\n[SAMPLE REPORT] Done.")


def cmd_scan(cfg: AppConfig):
    """Scan Brightspace for due work this week using persistent profile."""
    print("\n[SCAN] Starting weekly scan...")
    print(f"  Week: {cfg.week_start} to {cfg.week_end}")

    # Load site map
    site_map = load_site_map(cfg.output.site_map_path)
    if site_map is None:
        print(f"\nWARNING: No site map found at {cfg.output.site_map_path}")
        print("Run discovery first, or the scan may be limited.\n")

    bs = BrightspaceBrowser(cfg)
    try:
        ctx = bs.start()
        pg = bs.get_page()
        if pg is None:
            print("ERROR: No browser page available.")
            sys.exit(1)

        # Check if we're on Brightspace
        pg.goto(cfg.brightspace.url, wait_until="domcontentloaded", timeout=30000)
        current_url = pg.url
        if "/d2l/" not in current_url:
            print(f"\nWARNING: Current URL {current_url} does not look like Brightspace.")
            print("Your session may have expired. Run: python -m brightspace_planner.main auth")
            sys.exit(1)

        print(f"  Logged in, on: {current_url}")

        report = run_scan(cfg, pg, site_map, cfg.auth.mode)

        paths = write_all_reports(cfg, report)
        dash_path = write_dashboard(cfg, report.to_dict())

        print(f"\n  Items due: {len(report.items_due)}")
        print(f"  HIGH: {sum(1 for i in report.items_due if i.get('priority') == 'HIGH')}")
        print(f"  Errors: {len(report.errors)}")
        print(f"  Markdown: {paths['markdown']}")
        print(f"  JSON:     {paths['json']}")
        print(f"  Dashboard: {dash_path}")
        print(f"  Run log:  {paths['run_log']}")
        print("\n[SCAN] Done.")

    except KeyboardInterrupt:
        print("\n\n[SCAN] Cancelled by user.")
    finally:
        bs.stop()


def cmd_deep_scan(cfg: AppConfig):
    """Deep content scan — expands all accordion trees in every course.

    Reads every content page, extracts text, file attachments, and instructions.
    Does NOT filter by week — returns ALL content found.
    """
    print("\n[DEEP SCAN] Starting deep content scan...")
    print(f"  Week range: {cfg.week_start} to {cfg.week_end}")
    print(f"  This will expand accordion trees and visit every content page.")
    print(f"  This may take several minutes.\n")

    site_map = load_site_map(cfg.output.site_map_path)
    if site_map is None:
        print(f"\nWARNING: No site map found at {cfg.output.site_map_path}")

    bs = BrightspaceBrowser(cfg)
    try:
        ctx = bs.start()
        pg = bs.get_page()
        if pg is None:
            print("ERROR: No browser page available.")
            sys.exit(1)

        pg.goto(cfg.brightspace.url, wait_until="domcontentloaded", timeout=30000)
        current_url = pg.url
        if "/d2l/" not in current_url:
            print(f"\nWARNING: Not on Brightspace ({current_url})")
            print("Your session may have expired. Run: python -m brightspace_planner.main auth")
            sys.exit(1)

        print(f"  Logged in, on: {current_url}\n")

        report = ScanReport(
            week_start=cfg.week_start.isoformat(),
            week_end=cfg.week_end.isoformat(),
            last_checked=now_iso(),
            auth_mode_used=cfg.auth.mode,
            courses_checked=[],
            items_due=[],
            unclear_items=[],
            errors=[],
        )

        today_d = date.today()
        base_url = cfg.brightspace.url

        for course in (site_map.courses if site_map else []):
            report.courses_checked.append(course.course_name or "Unknown")
            course_name = course.course_name or "Unknown"
            print(f"\n  === {course_name} ===")

            try:
                items = scan_course(page=pg, course=course, week_start=cfg.week_start, week_end=cfg.week_end, base_url=base_url)
                for item in items:
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
                print(f"  Total items: {len(items)}")

            except Exception as e:
                err = f"Error scanning {course_name}: {e}"
                print(f"  ERROR: {err}")
                report.errors.append(err)

        # Content-only deep scan pass — expand all accordions and read every page
        all_content_items: list[dict] = []
        for course in (site_map.courses if site_map else []):
            course_name = course.course_name or "Unknown"
            print(f"\n  Deep content: {course_name}")
            try:
                content_items = scan_course_content_deep(
                    pg, course, cfg.week_start, cfg.week_end, base_url
                )
                all_content_items.extend(content_items)
                print(f"  Found {len(content_items)} content items")

                for ci in content_items:
                    ci.setdefault("priority", "LOW")
                    ci.setdefault("confidence", "medium")
                    ci.setdefault("warnings", [])
                    report.items_due.append(ci)
            except Exception as e:
                print(f"  ERROR: {e}")
                report.errors.append(f"Content deep scan error for {course_name}: {e}")

        report.items_due.sort(key=lambda x: x.get("due_date", ""))

        paths = write_all_reports(cfg, report)
        dash_path = write_dashboard(cfg, report.to_dict())

        n_content = sum(1 for i in report.items_due if i.get("content_type") == "content_page")
        n_files = sum(len(i.get("attachments", [])) for i in report.items_due)
        n_high = sum(1 for i in report.items_due if i.get("priority") == "HIGH")

        print(f"\n\n[DEEP SCAN] Complete!")
        print(f"  Total items: {len(report.items_due)}")
        print(f"  Content pages: {n_content}")
        print(f"  File attachments found: {n_files}")
        print(f"  HIGH priority: {n_high}")
        print(f"  Errors: {len(report.errors)}")
        print(f"  Markdown: {paths['markdown']}")
        print(f"  JSON:     {paths['json']}")
        print(f"  Dashboard: {dash_path}")
        print(f"  Run log:  {paths['run_log']}")

    except KeyboardInterrupt:
        print("\n\n[DEEP SCAN] Cancelled by user.")
    finally:
        bs.stop()
    """Regenerate dashboard.html from latest weekly_due_report.json."""
    from .utils import read_json
    json_path = __import__('os').path.join(cfg.output.folder, "weekly_due_report.json")
    data = read_json(json_path)
    if data is None:
        print(f"No JSON report found at {json_path}")
        print("Run scan or sample-report first.")
        sys.exit(1)
    path = write_dashboard(cfg, data)
    print(f"Dashboard regenerated: {path}")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python -m brightspace_planner.main <command> [options]")
        print()
        print("Commands:")
        print("  gui-test       Open headed Chromium, verify browser appears")
        print("  auth           Open browser for manual login/MFA")
        print("  sample-report  Generate reports from fake data (no Brightspace)")
        print("  scan           Scan Brightspace for due work this week")
        print("  deep-scan      Deep content scan — expand all accordions, read every page")
        print("  dashboard      Regenerate dashboard.html from latest JSON")
        print()
        print("Options:")
        print("  --verbose / -v  Enable debug logging")
        sys.exit(0)

    command = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    _setup_logging(verbose)
    cfg = load_config()

    commands = {
        "gui-test": cmd_gui_test,
        "auth": cmd_auth,
        "sample-report": cmd_sample_report,
        "scan": cmd_scan,
        "deep-scan": cmd_deep_scan,
        "dashboard": cmd_dashboard,
    }

    handler = commands.get(command)
    if handler is None:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands)}")
        sys.exit(1)

    handler(cfg)


if __name__ == "__main__":
    main()
