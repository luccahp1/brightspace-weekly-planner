"""Tests for report_writer."""

import json
import os
import tempfile
from datetime import date, timedelta

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from brightspace_planner.config import AppConfig
from brightspace_planner.models import ScanReport
from brightspace_planner.report_writer import write_all_reports
from tests.sample_data import SAMPLE_REPORT_DICT


def test_write_all_reports():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = AppConfig()
        cfg.output.folder = tmpdir

        report = ScanReport(**SAMPLE_REPORT_DICT)
        paths = write_all_reports(cfg, report)

        assert os.path.exists(paths["markdown"])
        assert os.path.exists(paths["json"])
        assert os.path.exists(paths["run_log"])

        with open(paths["json"]) as f:
            data = json.load(f)
        assert data["week_start"]
        assert len(data["items_due"]) == 3

        with open(paths["markdown"]) as f:
            md_content = f.read()
        assert "# Brightspace Weekly Due Report" in md_content
        assert "HIGH Priority" in md_content

        with open(paths["run_log"]) as f:
            log_content = f.read()
        assert "scan complete" in log_content

    print("test_write_all_reports PASSED")


if __name__ == "__main__":
    test_write_all_reports()
