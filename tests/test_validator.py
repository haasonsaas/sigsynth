"""Tests for the validator module."""

import pytest
from sigsynth.validator import RuleValidator

def test_validate_entry():
    """Test validating log entries against rule criteria."""
    criteria = {
        "selection": {
            "eventName": ["CreateTrail", "DeleteTrail"],
            "eventSource": "cloudtrail.amazonaws.com"
        }
    }
    
    validator = RuleValidator(criteria)
    
    # Test positive case
    positive_entry = {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "EXAMPLE",
            "arn": "arn:aws:iam::123456789012:user/example"
        }
    }
    assert validator.validate_entry(positive_entry)
    
    # Test negative case
    negative_entry = {
        "eventName": "DescribeTrails",
        "eventSource": "cloudtrail.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "EXAMPLE",
            "arn": "arn:aws:iam::123456789012:user/example"
        }
    }
    assert not validator.validate_entry(negative_entry)

def test_validate_with_regex():
    """Test validating entries with regex patterns."""
    criteria = {
        "selection": {
            "eventName|re": ".*Trail$",
            "eventSource": "cloudtrail.amazonaws.com"
        }
    }
    
    validator = RuleValidator(criteria)
    
    # Test regex matching
    entry = {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com"
    }
    assert validator.validate_entry(entry)
    
    # Test regex non-matching
    entry["eventName"] = "DescribeTrails"
    assert not validator.validate_entry(entry)

def test_validate_with_conditions():
    """Test validating entries with complex conditions."""
    criteria = {
        "selection": {
            "and": [
                {
                    "eventName": ["CreateTrail", "DeleteTrail"]
                },
                {
                    "or": [
                        {"eventSource": "cloudtrail.amazonaws.com"},
                        {"eventSource": "cloudtrail.amazonaws.com.cn"}
                    ]
                }
            ]
        }
    }
    
    validator = RuleValidator(criteria)
    
    # Test AND/OR conditions
    entry = {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com"
    }
    assert validator.validate_entry(entry)
    
    entry["eventSource"] = "cloudtrail.amazonaws.com.cn"
    assert validator.validate_entry(entry)
    
    entry["eventName"] = "DescribeTrails"
    assert not validator.validate_entry(entry) 