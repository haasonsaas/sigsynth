"""Tests for the parser module."""

import pytest
from pathlib import Path
from sigsynth.parser import parse_rule, extract_detection_criteria

def test_parse_rule():
    """Test parsing a valid Sigma rule."""
    rule_path = Path("examples/aws_cloudtrail_change.yml")
    rule = parse_rule(rule_path)
    
    assert rule.id == "aws-cloudtrail-config-change"
    assert rule.title == "AWS CloudTrail Configuration Change"
    assert "CreateTrail" in rule.detection["selection"]["eventName"]
    assert rule.detection["selection"]["eventSource"] == "cloudtrail.amazonaws.com"

def test_extract_detection_criteria():
    """Test extracting detection criteria."""
    rule_path = Path("examples/aws_cloudtrail_change.yml")
    rule = parse_rule(rule_path)
    criteria = extract_detection_criteria(rule)
    
    assert "selection" in criteria
    assert "eventName" in criteria["selection"]
    assert "eventSource" in criteria["selection"] 