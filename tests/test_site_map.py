"""Tests for site_map module."""

import json
import os
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from brightspace_planner.site_map import (
    load_site_map,
    save_site_map,
    get_example_site_map,
)
from brightspace_planner.models import SiteMap, CourseEntry


def test_example_map():
    data = get_example_site_map()
    assert data["brightspace_url"]
    assert len(data["courses"]) >= 1
    assert data["courses"][0]["course_name"] == "Example Course 101"
    print("test_example_map PASSED")


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_map.json")
        site_map = SiteMap(
            discovered_at="2026-01-01T00:00:00",
            brightspace_url="https://example.com/d2l/home",
            courses=[
                CourseEntry(
                    course_name="Test Course",
                    course_code="TEST-101",
                    homepage_url="https://example.com/d2l/le/content/1",
                ),
            ],
        )
        save_site_map(path, site_map)
        assert os.path.exists(path)

        loaded = load_site_map(path)
        assert loaded is not None
        assert loaded.brightspace_url == "https://example.com/d2l/home"
        assert len(loaded.courses) == 1
        assert loaded.courses[0].course_name == "Test Course"

    print("test_save_and_load PASSED")


def test_load_missing():
    result = load_site_map("/nonexistent/path/map.json")
    assert result is None
    print("test_load_missing PASSED")


if __name__ == "__main__":
    test_example_map()
    test_save_and_load()
    test_load_missing()
