"""Tests for the expander module."""

import pytest
from sigsynth.expander import LocalExpander

def test_expand_seeds():
    """Test expanding seed log entries."""
    expander = LocalExpander(random_seed=42)
    
    positive_seeds = [
        {
            "eventName": "CreateTrail",
            "eventSource": "cloudtrail.amazonaws.com",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": "EXAMPLE"
            }
        }
    ]
    
    negative_seeds = [
        {
            "eventName": "DescribeTrails",
            "eventSource": "cloudtrail.amazonaws.com",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": "EXAMPLE"
            }
        }
    ]
    
    variants = expander.expand_seeds(positive_seeds, negative_seeds, 10)
    
    assert len(variants) == 10
    
    # Check that variants maintain required fields
    for variant in variants:
        assert "eventName" in variant
        assert "eventSource" in variant
        assert "userIdentity" in variant

def test_expander_transformations():
    """Test various transformations applied by the expander."""
    expander = LocalExpander(random_seed=42)
    
    seed = {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com",
        "message": "Error: Failed to create trail"
    }
    
    variants = expander._expand_seed(seed, 5, should_trigger=True)
    
    # Check that variants have been transformed
    field_orders = set()
    casings = set()
    
    for variant in variants:
        # Check field reordering
        field_orders.add(tuple(variant.keys()))
        
        # Check casing modifications
        if "message" in variant:
            casings.add(variant["message"])
    
    # At least some variants should have different field orders
    assert len(field_orders) > 1
    
    # At least some variants should have different casings
    assert len(casings) > 1

def test_expander_preserves_trigger_behavior():
    """Test that expander preserves trigger/non-trigger behavior."""
    expander = LocalExpander(random_seed=42)
    
    # Test positive case
    positive_seed = {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com",
        "message": "Error: Failed to create trail"
    }
    
    positive_variants = expander._expand_seed(positive_seed, 5, should_trigger=True)
    
    for variant in positive_variants:
        assert "CreateTrail" in variant["eventName"] or "ERROR" in variant.get("message", "")
    
    # Test negative case
    negative_seed = {
        "eventName": "DescribeTrails",
        "eventSource": "cloudtrail.amazonaws.com",
        "message": "Success: Retrieved trail info"
    }
    
    negative_variants = expander._expand_seed(negative_seed, 5, should_trigger=False)
    
    for variant in negative_variants:
        assert "CreateTrail" not in variant["eventName"]
        assert "ERROR" not in variant.get("message", "") 