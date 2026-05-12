"""Report writers — Markdown, JSON, and run log."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig
from .models import ScanReport, DueItem
from .utils import ensure_dir, write_json, append_log

logger = logging.getLogger("brightspace_planner")


def _item_to_dict(item: DueItem) -> dict:
    return {
        "course": item.course,
        "course_code": item.course_code,
        "title": item.title,
        "type": item.type,
        "due_date": item.due_date,
        "priority": item.priority,
        "status": item.status,
        "link": item.link,
        "estimated_time": item.estimated_time,
        "difficulty": item.difficulty,
        "summary": item.summary,
        "requirements": item.requirements,
        "submission_instructions": item.submission_instructions,
        "attachments": item.attachments,
        "rubric_summary": item.rubric_summary,
        "warnings": item.warnings,
        "confidence": item.confidence,
    }


def write_markdown_report(cfg: AppConfig, report: ScanReport) -> str:
    """Write weekly_due_report.md and return the file path."""
    out_dir = ensure_dir(cfg.output.folder)
    md_path = str(out_dir / "weekly_due_report.md")

    lines: list[str] = []
    lines.append(f"# Brightspace Weekly Due Report")
    lines.append(f"")
    lines.append(f"**Week:** {report.week_start} to {report.week_end}")
    lines.append(f"**Last checked:** {report.last_checked}")
    lines.append(f"**Courses checked:** {', '.join(report.courses_checked) or 'none'}")
    lines.append(f"**Items due:** {len(report.items_due)}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    high = [i for i in report.items_due if i.get("priority") == "HIGH"]
    med = [i for i in report.items_due if i.get("priority") == "MEDIUM"]
    low = [i for i in report.items_due if i.get("priority") == "LOW"]
    lines.append(f"- HIGH priority: {len(high)}")
    lines.append(f"- MEDIUM priority: {len(med)}")
    lines.append(f"- LOW priority: {len(low)}")
    lines.append("")

    # Items grouped by priority
    for priority, items in [("HIGH", high), ("MEDIUM", med), ("LOW", low)]:
        if not items:
            continue
        lines.append(f"## {priority} Priority")
        lines.append("")
        for item in items:
            course = item.get("course", "Unknown Course")
            title = item.get("title", "Untitled")
            due = item.get("due_date", "unknown")
            item_type = item.get("type", "unknown")
            lines.append(f"### {course} — {title}")
            lines.append(f"- **Type:** {item_type}")
            lines.append(f"- **Due:** {due}")
            if item.get("status"):
                lines.append(f"- **Status:** {item['status']}")
            if item.get("link"):
                lines.append(f"- **Link:** {item['link']}")
            if item.get("estimated_time"):
                lines.append(f"- **Estimated time:** {item['estimated_time']}")
            if item.get("summary"):
                lines.append(f"- **Summary:** {item['summary']}")
            if item.get("requirements"):
                lines.append(f"- **Requirements:**")
                for req in item["requirements"]:
                    lines.append(f"  - {req}")
            if item.get("submission_instructions"):
                lines.append(f"- **Submission:** {item['submission_instructions']}")
            if item.get("warnings"):
                for w in item["warnings"]:
                    lines.append(f"- **Warning:** {w}")
            lines.append("")

    # Unclear items
    if report.unclear_items:
        lines.append("## Needs Human Review")
        lines.append("")
        for item in report.unclear_items:
            lines.append(f"- {item}")
        lines.append("")

    # Errors
    if report.errors:
        lines.append("## Errors")
        lines.append("")
        for err in report.errors:
            lines.append(f"- {err}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Markdown report written to %s", md_path)
    return md_path


def write_json_report(cfg: AppConfig, report: ScanReport) -> str:
    """Write weekly_due_report.json and return the file path."""
    out_dir = ensure_dir(cfg.output.folder)
    json_path = str(out_dir / "weekly_due_report.json")
    write_json(json_path, report.to_dict())
    logger.info("JSON report written to %s", json_path)
    return json_path


def write_run_log(cfg: AppConfig, report: ScanReport) -> str:
    """Append a summary to run_log.txt."""
    out_dir = ensure_dir(cfg.output.folder)
    log_path = str(out_dir / "run_log.txt")
    n_items = len(report.items_due)
    n_high = sum(1 for i in report.items_due if i.get("priority") == "HIGH")
    n_err = len(report.errors)
    msg = (
        f"scan complete — {n_items} items due ({n_high} HIGH), "
        f"{n_err} errors, {len(report.unclear_items)} unclear"
    )
    append_log(log_path, msg)
    return log_path


def write_all_reports(cfg: AppConfig, report: ScanReport) -> dict[str, str]:
    """Write all report files. Returns {kind: path}."""
    return {
        "markdown": write_markdown_report(cfg, report),
        "json": write_json_report(cfg, report),
        "run_log": write_run_log(cfg, report),
    }
