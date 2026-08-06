"""Main CLI entry point for brightspace-weekly-planner."""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from .config import load_config
from .models import ScanReport
from .site_map import load_site_map, get_example_site_map, save_site_map
from .report_writer import write_all_reports
from .dashboard_writer import write_dashboard
from .browser_client import BrightspaceBrowser
from .scanner import run_scan, scan_course
from .content_scanner import scan_course_content_deep
from .auth import run_auth
from .utils import now_iso, today_iso, ensure_dir, append_log, priority_from_due_date, priority_from_type

logger = logging.getLogger("brightspace_planner")
console = Console()


def _write_error_log(cfg, error_msg: str, tb: str = ""):
    """Write errors to a dedicated error log file for debugging."""
    ensure_dir(cfg.output.folder)
    error_path = str(Path(cfg.output.folder) / "error_log.txt")
    ts = now_iso()
    with open(error_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {error_msg}\n")
        if tb:
            f.write(f"  Traceback:\n{tb}\n")
        f.write("\n")


def _print_banner():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Brightspace Weekly Planner[/bold cyan]",
        border_style="cyan"
    ))


def _print_error(cfg, msg: str, tb: str = ""):
    console.print(f"  [red]ERROR:[/red] {msg}")
    _write_error_log(cfg, msg, tb)


def _print_success(cfg, report, paths):
    n_high = sum(1 for i in report.items_due if i.get("priority") == "HIGH")
    n_med = sum(1 for i in report.items_due if i.get("priority") == "MEDIUM")
    n_low = sum(1 for i in report.items_due if i.get("priority") == "LOW")
    n_files = sum(len(i.get("attachments", [])) for i in report.items_due)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Items found:", str(len(report.items_due)))
    table.add_row("  [red]High[/red]", str(n_high))
    table.add_row("  [yellow]Medium[/yellow]", str(n_med))
    table.add_row("  [green]Low[/green]", str(n_low))
    table.add_row("File attachments:", str(n_files))
    table.add_row("Errors:", str(len(report.errors)))

    console.print()
    console.print(Panel(
        table,
        title="[green]Scan Complete[/green]",
        border_style="green"
    ))

    console.print(f"  [dim]Reports:[/dim]")
    console.print(f"    {paths['markdown']}")
    console.print(f"    {paths['json']}")
    console.print(f"    {paths['run_log']}")

    if report.errors:
        console.print()
        console.print(f"  [yellow]⚠ {len(report.errors)} error(s) logged to error_log.txt[/yellow]")


def cmd_gui_test(cfg: AppConfig):
    """Open headed Chromium through WSLg and navigate to Brightspace."""
    from .browser_client import open_brightspace

    _print_banner()
    console.print(f"  [dim]URL:[/dim] {cfg.brightspace.url}")
    console.print(f"  [dim]Headless:[/dim] {cfg.browser.headless}")
    console.print()

    bs, pg = open_brightspace(cfg)
    try:
        if pg:
            console.print(f"  [green]✓[/green] Browser opened!")
            console.print(f"  [dim]URL:[/dim] {pg.url}")
            console.print(f"  [dim]Title:[/dim] {pg.title()}")
            console.print()
            console.print("  [yellow]You should see a Chromium window on your Windows desktop.[/yellow]")
            console.print("  [dim]Closing in 30 seconds...[/dim]")
            import time
            time.sleep(30)
        else:
            _print_error(cfg, "No browser page was created.")
    finally:
        bs.stop()
    console.print("  [dim]Done.[/dim]")


def cmd_auth(cfg: AppConfig):
    """Open headed Chromium, let user manually log in and complete MFA."""
    _print_banner()
    console.print()
    console.print(f"  [dim]URL:[/dim] {cfg.brightspace.url}")
    console.print(f"  [dim]Profile:[/dim] {cfg.auth.playwright_profile_dir}")
    console.print()
    console.print("  [yellow]A Chromium window will appear on your Windows desktop.[/yellow]")
    console.print("  [yellow]Please log in and complete MFA if required.[/yellow]")
    console.print()

    success = run_auth(cfg)
    if success:
        console.print("\n  [green]✓[/green] Auth complete. You can now run the scan.")
    else:
        console.print("\n  [red]✗[/red] Auth was not confirmed. You may try again.")
        sys.exit(1)


def cmd_sample_report(cfg: AppConfig):
    """Generate reports from sample data without Brightspace."""
    _print_banner()
    console.print("  [dim]Generating from sample data...[/dim]\n")

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
                "due_date": today_d.isoformat(),
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
                "due_date": today_d.isoformat(),
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
                "warnings": ["Discussion post required, not just a dropbox."],
                "confidence": "high",
            },
            {
                "course": "Intro to Management",
                "course_code": "MGMT-2001",
                "title": "Quiz 4: Ch 7-9",
                "type": "quiz",
                "due_date": today_d.isoformat(),
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

    console.print(f"  [green]✓[/green] Reports generated!")
    console.print(f"    {paths['markdown']}")
    console.print(f"    {paths['json']}")
    console.print(f"    {dash_path}")
    console.print()


def cmd_scan(cfg: AppConfig):
    """Scan Brightspace for due work this week using persistent profile."""
    _print_banner()
    console.print(f"  [dim]Week:[/dim] {cfg.week_start} to {cfg.week_end}")
    console.print()

    site_map = load_site_map(cfg.output.site_map_path)
    if site_map is None:
        console.print(f"  [yellow]⚠[/yellow] No site map found. Limited scanning.")

    bs = BrightspaceBrowser(cfg)
    try:
        ctx = bs.start()
        pg = bs.get_page()
        if pg is None:
            _print_error(cfg, "No browser page available.")
            sys.exit(1)

        pg.goto(cfg.brightspace.url, wait_until="domcontentloaded", timeout=30000)
        current_url = pg.url
        if "/d2l/" not in current_url:
            _print_error(cfg, f"Not on Brightspace ({current_url}). Session may have expired.")
            console.print("  [yellow]Run Login.bat to re-authenticate.[/yellow]")
            sys.exit(1)

        console.print(f"  [green]✓[/green] Logged in: {current_url}")
        console.print()
        console.print("  [dim]Scanning courses...[/dim]")

        report = run_scan(cfg, pg, site_map, cfg.auth.mode)

        paths = write_all_reports(cfg, report)
        dash_path = write_dashboard(cfg, report.to_dict())

        _print_success(cfg, report, paths)

    except KeyboardInterrupt:
        console.print("\n  [yellow]Cancelled by user.[/yellow]")
    except Exception as e:
        tb = traceback.format_exc()
        _print_error(cfg, str(e), tb)
        console.print("  [dim]Check output/error_log.txt for details.[/dim]")
    finally:
        bs.stop()


def cmd_deep_scan(cfg: AppConfig):
    """Deep content scan — expands all accordion trees in every course."""
    _print_banner()
    console.print(f"  [dim]Week:[/dim] {cfg.week_start} to {cfg.week_end}")
    console.print()

    site_map = load_site_map(cfg.output.site_map_path)
    if site_map is None:
        console.print(f"  [yellow]⚠[/yellow] No site map found. Limited scanning.")

    bs = BrightspaceBrowser(cfg)
    try:
        ctx = bs.start()
        pg = bs.get_page()
        if pg is None:
            _print_error(cfg, "No browser page available.")
            sys.exit(1)

        pg.goto(cfg.brightspace.url, wait_until="domcontentloaded", timeout=30000)
        current_url = pg.url
        if "/d2l/" not in current_url:
            _print_error(cfg, f"Not on Brightspace ({current_url}). Session may have expired.")
            console.print("  [yellow]Run Login.bat to re-authenticate.[/yellow]")
            sys.exit(1)

        console.print(f"  [green]✓[/green] Logged in: {current_url}")
        console.print()

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

        # Phase 1: Standard scan
        console.print("[bold]Phase 1:[/bold] Standard scan")
        console.print()

        for course in (site_map.courses if site_map else []):
            course_name = course.course_name or "Unknown"
            report.courses_checked.append(course_name)
            console.print(f"  [cyan]▸[/cyan] {course_name}")

            try:
                items = scan_course(
                    page=pg, course=course,
                    week_start=cfg.week_start, week_end=cfg.week_end,
                    base_url=base_url,
                )
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
                n_high = sum(1 for i in items if i.get("priority") == "HIGH")
                console.print(f"      [dim]{len(items)} items[/dim] ({n_high} HIGH)")
            except Exception as e:
                tb = traceback.format_exc()
                _print_error(cfg, f"Error scanning {course_name}: {e}", tb)
                report.errors.append(f"Error scanning {course_name}: {e}")

        # Phase 2: Deep content scan
        console.print()
        console.print("[bold]Phase 2:[/bold] Deep content scan")
        console.print()

        for course in (site_map.courses if site_map else []):
            course_name = course.course_name or "Unknown"
            console.print(f"  [cyan]▸[/cyan] {course_name}")

            try:
                content_items = scan_course_content_deep(
                    pg, course, cfg.week_start, cfg.week_end, base_url
                )
                n_added = 0
                for ci in content_items:
                    ci.setdefault("priority", "LOW")
                    ci.setdefault("confidence", "medium")
                    ci.setdefault("warnings", [])
                    report.items_due.append(ci)
                    n_added += 1
                n_files = sum(len(ci.get("attachments", [])) for ci in content_items)
                console.print(f"      [dim]{n_added} pages[/dim] ({n_files} files)")
            except Exception as e:
                tb = traceback.format_exc()
                _print_error(cfg, f"Content scan error for {course_name}: {e}", tb)
                report.errors.append(f"Content scan error for {course_name}: {e}")

        report.items_due.sort(key=lambda x: x.get("due_date", ""))

        console.print()
        console.print("[bold]Writing reports...[/bold]")

        paths = write_all_reports(cfg, report)
        dash_path = write_dashboard(cfg, report.to_dict())

        _print_success(cfg, report, paths)

    except KeyboardInterrupt:
        console.print("\n  [yellow]Cancelled by user.[/yellow]")
    except Exception as e:
        tb = traceback.format_exc()
        _print_error(cfg, str(e), tb)
        console.print("  [dim]Check output/error_log.txt for details.[/dim]")
    finally:
        bs.stop()


def cmd_dashboard(cfg: AppConfig):
    """Regenerate dashboard.html from latest weekly_due_report.json."""
    from .utils import read_json
    json_path = str(Path(cfg.output.folder) / "weekly_due_report.json")
    data = read_json(json_path)
    if data is None:
        console.print(f"  [yellow]No JSON report found.[/yellow]")
        console.print("  [dim]Run a scan first.[/dim]")
        sys.exit(1)
    path = write_dashboard(cfg, data)
    console.print(f"  [green]✓[/green] Dashboard: {path}")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Brightspace Weekly Planner[/bold cyan]",
            border_style="cyan"
        ))
        console.print()
        console.print("  [bold]Commands:[/bold]")
        console.print("    [cyan]gui-test[/cyan]       Open headed Chromium, verify browser")
        console.print("    [cyan]auth[/cyan]           Open browser for manual login/MFA")
        console.print("    [cyan]sample-report[/cyan]  Generate reports from fake data")
        console.print("    [cyan]scan[/cyan]           Scan Brightspace for due work this week")
        console.print("    [cyan]deep-scan[/cyan]      Deep content scan (all accordions)")
        console.print("    [cyan]dashboard[/cyan]      Regenerate dashboard.html")
        console.print()
        console.print("  [dim]Options: --verbose / -v[/dim]")
        console.print()
        sys.exit(0)

    command = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")

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
        console.print(f"  [red]Unknown command:[/red] {command}")
        console.print(f"  [dim]Available:[/dim] {', '.join(commands)}")
        sys.exit(1)

    handler(cfg)


if __name__ == "__main__":
    main()
