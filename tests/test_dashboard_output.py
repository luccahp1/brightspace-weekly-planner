"""Tests that the dashboard the writer emits is actually a working page.

test_dashboard_writer.py checks that certain substrings are present, which is
not the same thing. The dashboard once shipped for months with every brace in
the template doubled - the CSS and the JS were both invalid, the page rendered
as unstyled headings with "Items Due (0)" - and every substring assertion still
passed. These tests check the output is well formed, not merely non-empty.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from brightspace_planner.config import AppConfig
from brightspace_planner.dashboard_writer import write_dashboard
from tests.sample_data import SAMPLE_REPORT_DICT


def _render(data):
    tmpdir = tempfile.mkdtemp()
    try:
        cfg = AppConfig()
        cfg.output.folder = tmpdir
        with open(write_dashboard(cfg, data), encoding="utf-8") as f:
            return f.read()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _block(html, tag):
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.S)
    assert match, f"no <{tag}> block in the dashboard"
    return match.group(1)


def test_no_doubled_braces_survive_into_the_page():
    """The template is emitted with .replace(), so braces must not be escaped."""
    html = _render(SAMPLE_REPORT_DICT)
    assert "{{" not in html
    assert "}}" not in html


def test_css_braces_balanced():
    css = _block(_render(SAMPLE_REPORT_DICT), "style")
    assert css.count("{") == css.count("}")
    assert css.count("{") > 20, "the stylesheet looks truncated"


def test_every_priority_in_the_data_has_a_badge_rule():
    """The JS builds `badge-${priority.toLowerCase()}`; the CSS must define it.

    MEDIUM shipped unstyled because the rule was named .badge-med while the JS
    asked for .badge-medium.
    """
    html = _render(SAMPLE_REPORT_DICT)
    css = _block(html, "style")

    priorities = {i["priority"] for i in SAMPLE_REPORT_DICT["items_due"]}
    assert priorities, "sample data has no items to check"

    for priority in priorities:
        selector = f".badge-{priority.lower()}"
        assert re.search(re.escape(selector) + r"\s*\{", css), (
            f"{priority} renders with class badge-{priority.lower()} "
            f"but the stylesheet has no {selector} rule"
        )


def test_embedded_report_is_valid_json_and_round_trips():
    html = _render(SAMPLE_REPORT_DICT)
    match = re.search(r"const REPORT = (.*?);\s*\n", html, re.S)
    assert match, "no `const REPORT = ...;` assignment in the page"
    assert json.loads(match.group(1))["items_due"] == SAMPLE_REPORT_DICT["items_due"]


def test_placeholder_is_fully_substituted():
    assert "__EMBEDDED_JSON__" not in _render(SAMPLE_REPORT_DICT)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_embedded_script_is_syntactically_valid_javascript():
    script = _block(_render(SAMPLE_REPORT_DICT), "script")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "dashboard.js")
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        result = subprocess.run(
            ["node", "--check", path], capture_output=True, text=True
        )
    assert result.returncode == 0, f"emitted JS does not parse:\n{result.stderr}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_empty_report_still_emits_valid_javascript():
    empty = {
        "week_start": "",
        "week_end": "",
        "last_checked": "",
        "auth_mode_used": "",
        "courses_checked": [],
        "items_due": [],
        "unclear_items": [],
        "errors": [],
    }
    script = _block(_render(empty), "script")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "dashboard.js")
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        result = subprocess.run(
            ["node", "--check", path], capture_output=True, text=True
        )
    assert result.returncode == 0, f"emitted JS does not parse:\n{result.stderr}"
