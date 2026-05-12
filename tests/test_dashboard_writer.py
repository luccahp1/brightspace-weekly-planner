"""Tests for dashboard_writer."""

import json
import os
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from brightspace_planner.config import AppConfig
from brightspace_planner.dashboard_writer import write_dashboard
from tests.sample_data import SAMPLE_REPORT_DICT


def test_write_dashboard():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = AppConfig()
        cfg.output.folder = tmpdir

        path = write_dashboard(cfg, SAMPLE_REPORT_DICT)
        assert os.path.exists(path)

        with open(path, encoding="utf-8") as f:
            html = f.read()

        # Check key elements
        assert "<!DOCTYPE html>" in html
        assert "Brightspace Weekly Planner" in html
        assert "courseFilter" in html
        assert "priorityFilter" in html
        assert "cardList" in html
        assert "getElementById" in html
        assert "items_due" in html or "REPORT" in html

        # Check embedded JSON has real data
        assert "SYST-3040" in html or "SAMPLE" in html.upper()

    print("test_write_dashboard PASSED")


def test_write_dashboard_no_data():
    """Dashboard with empty data should still produce valid HTML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = AppConfig()
        cfg.output.folder = tmpdir

        empty_data = {
            "week_start": "",
            "week_end": "",
            "last_checked": "",
            "auth_mode_used": "",
            "courses_checked": [],
            "items_due": [],
            "unclear_items": [],
            "errors": [],
        }

        path = write_dashboard(cfg, empty_data)
        assert os.path.exists(path)

        with open(path, encoding="utf-8") as f:
            html = f.read()
        assert "</html>" in html

    print("test_write_dashboard_no_data PASSED")


if __name__ == "__main__":
    test_write_dashboard()
    test_write_dashboard_no_data()
