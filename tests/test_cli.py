"""Tests for the CLI module."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from sigsynth.cli import cli

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def mock_openai():
    """Mock OpenAI API."""
    with patch("openai.OpenAI") as mock:
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
        mock.return_value = mock_client
        yield mock

def test_generate_command(runner, mock_openai, tmp_path):
    """Test the generate command."""
    # Create test rule file
    rule_file = tmp_path / "test_rule.yml"
    rule_file.write_text("""title: Test Rule
id: test-rule
detection:
    selection:
        eventName:
            - CreateTrail
            - DeleteTrail
        eventSource: cloudtrail.amazonaws.com
    condition: selection""")
    
    # Set OpenAI API key
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    # Run command
    result = runner.invoke(cli, [
        "generate",
        "--rule", str(rule_file),
        "--platform", "panther",
        "--seed-samples", "1",
        "--samples", "10",
        "--output", str(tmp_path / "tests")
    ])
    
    assert result.exit_code == 0
    assert "Generated 10 test cases" in result.output
    assert "All test cases validated successfully" in result.output
    
    # Check output files
    test_files = list((tmp_path / "tests").glob("test_*.json"))
    assert len(test_files) == 10

def test_generate_command_validation_error(runner, mock_openai, tmp_path):
    """Test the generate command with validation errors."""
    # Create test rule file
    rule_file = tmp_path / "test_rule.yml"
    rule_file.write_text("""title: Test Rule
id: test-rule
detection:
    selection:
        eventName:
            - CreateTrail
            - DeleteTrail
        eventSource: cloudtrail.amazonaws.com
    condition: selection""")
    
    # Set OpenAI API key
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    # Mock validator to return validation errors
    with patch("sigsynth.validator.RuleValidator.validate_entry") as mock_validate:
        mock_validate.return_value = False
        
        # Run command
        result = runner.invoke(cli, [
            "generate",
            "--rule", str(rule_file),
            "--platform", "panther",
            "--seed-samples", "1",
            "--samples", "10",
            "--output", str(tmp_path / "tests")
        ])
        
        assert result.exit_code == 1
        assert "Validation errors" in result.output

def test_generate_command_missing_api_key(runner, tmp_path):
    """Test the generate command without API key."""
    # Create test rule file
    rule_file = tmp_path / "test_rule.yml"
    rule_file.write_text("""title: Test Rule
id: test-rule
detection:
    selection:
        eventName:
            - CreateTrail
            - DeleteTrail
        eventSource: cloudtrail.amazonaws.com
    condition: selection""")
    
    # Remove API key
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    # Run command
    result = runner.invoke(cli, [
        "generate",
        "--rule", str(rule_file),
        "--platform", "panther",
        "--seed-samples", "1",
        "--samples", "10",
        "--output", str(tmp_path / "tests")
    ])
    
    assert result.exit_code == 1
    assert "OpenAI API key not provided" in result.output 