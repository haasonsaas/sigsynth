"""Tests for the Panther formatter module."""

import json
import pytest
from pathlib import Path
from sigsynth.panther_formatter import PantherFormatter

def test_format_test_case():
    """Test formatting a test case for Panther."""
    formatter = PantherFormatter("test-rule")
    
    log_entry = {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com"
    }
    
    test_case = formatter.format_test_case(log_entry, True, 0)
    
    assert test_case["id"] == "test-rule-0"
    assert test_case["type"] == "generated_test"
    assert test_case["should_trigger"] is True
    assert test_case["log"] == log_entry

def test_write_test_suite(tmp_path):
    """Test writing test cases to files."""
    formatter = PantherFormatter("test-rule")
    
    test_cases = [
        {
            "id": "test-rule-0",
            "type": "generated_test",
            "log": {"eventName": "CreateTrail"},
            "should_trigger": True
        },
        {
            "id": "test-rule-1",
            "type": "generated_test",
            "log": {"eventName": "DescribeTrails"},
            "should_trigger": False
        }
    ]
    
    output_dir = tmp_path / "tests"
    formatter.write_test_suite(test_cases, output_dir)
    
    # Check that files were created
    assert (output_dir / "test_000.json").exists()
    assert (output_dir / "test_001.json").exists()
    
    # Check file contents
    with open(output_dir / "test_000.json") as f:
        test_case = json.load(f)
        assert test_case["id"] == "test-rule-0"
        assert test_case["should_trigger"] is True
    
    with open(output_dir / "test_001.json") as f:
        test_case = json.load(f)
        assert test_case["id"] == "test-rule-1"
        assert test_case["should_trigger"] is False 