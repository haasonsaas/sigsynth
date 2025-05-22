"""Tests for the seed generator module."""

import os
import pytest
from unittest.mock import patch, MagicMock
from sigsynth.seed_generator import SeedGenerator

def test_seed_generator_init():
    """Test seed generator initialization."""
    # Test with environment variable
    os.environ["OPENAI_API_KEY"] = "test-key"
    generator = SeedGenerator()
    assert generator.api_key == "test-key"
    
    # Test with explicit key
    generator = SeedGenerator(api_key="explicit-key")
    assert generator.api_key == "explicit-key"
    
    # Test without key
    del os.environ["OPENAI_API_KEY"]
    with pytest.raises(ValueError):
        SeedGenerator()

@patch("openai.OpenAI")
def test_generate_seeds(mock_openai):
    """Test generating seed log entries."""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""POSITIVE:
[
    {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "EXAMPLE"
        }
    }
]

NEGATIVE:
[
    {
        "eventName": "DescribeTrails",
        "eventSource": "cloudtrail.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "EXAMPLE"
        }
    }
]"""
            )
        )
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    # Initialize generator with test key
    generator = SeedGenerator(api_key="test-key")
    
    # Test criteria
    criteria = {
        "selection": {
            "eventName": ["CreateTrail", "DeleteTrail"],
            "eventSource": "cloudtrail.amazonaws.com"
        }
    }
    
    # Generate seeds
    positive_seeds, negative_seeds = generator.generate_seeds(criteria, 1)
    
    # Verify results
    assert len(positive_seeds) == 1
    assert len(negative_seeds) == 1
    
    assert positive_seeds[0]["eventName"] == "CreateTrail"
    assert negative_seeds[0]["eventName"] == "DescribeTrails"
    
    # Verify OpenAI API call
    mock_client.chat.completions.create.assert_called_once()
    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-4"
    assert "Generate 1 positive and 1 negative log entries" in call_args["messages"][1]["content"]

def test_build_prompt():
    """Test building the OpenAI prompt."""
    generator = SeedGenerator(api_key="test-key")
    
    criteria = {
        "selection": {
            "eventName": ["CreateTrail"],
            "eventSource": "cloudtrail.amazonaws.com"
        }
    }
    
    prompt = generator._build_prompt(criteria, 2)
    
    assert "Generate 2 positive and 2 negative log entries" in prompt
    assert "CreateTrail" in prompt
    assert "cloudtrail.amazonaws.com" in prompt
    assert "POSITIVE:" in prompt
    assert "NEGATIVE:" in prompt

def test_parse_response():
    """Test parsing OpenAI response."""
    generator = SeedGenerator(api_key="test-key")
    
    response = """POSITIVE:
[
    {
        "eventName": "CreateTrail",
        "eventSource": "cloudtrail.amazonaws.com"
    }
]

NEGATIVE:
[
    {
        "eventName": "DescribeTrails",
        "eventSource": "cloudtrail.amazonaws.com"
    }
]"""
    
    positive_seeds, negative_seeds = generator._parse_response(response)
    
    assert len(positive_seeds) == 1
    assert len(negative_seeds) == 1
    
    assert positive_seeds[0]["eventName"] == "CreateTrail"
    assert negative_seeds[0]["eventName"] == "DescribeTrails"
    
    # Test invalid response
    with pytest.raises(Exception):
        generator._parse_response("Invalid response") 