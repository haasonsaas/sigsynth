"""Panther formatter module for generating Panther-compatible test output."""

import json
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console

console = Console()

class PantherFormatter:
    """Formats test cases for Panther's Rules SDK."""
    
    def __init__(self, rule_id: str):
        """Initialize the formatter.
        
        Args:
            rule_id: ID of the Sigma rule
        """
        self.rule_id = rule_id
    
    def format_test_case(
        self,
        log_entry: Dict[str, Any],
        should_trigger: bool,
        variant_index: int
    ) -> Dict[str, Any]:
        """Format a test case for Panther.
        
        Args:
            log_entry: Log entry to test
            should_trigger: Whether the entry should trigger the rule
            variant_index: Index of the variant
            
        Returns:
            Formatted test case
        """
        return {
            "id": f"{self.rule_id}-{variant_index}",
            "type": "generated_test",
            "log": log_entry,
            "should_trigger": should_trigger
        }
    
    def write_test_suite(
        self,
        test_cases: List[Dict[str, Any]],
        output_dir: Path
    ) -> None:
        """Write test cases to output directory.
        
        Args:
            test_cases: List of formatted test cases
            output_dir: Directory to write test files to
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, test_case in enumerate(test_cases):
            output_file = output_dir / f"test_{i:03d}.json"
            
            try:
                with open(output_file, 'w') as f:
                    json.dump(test_case, f, indent=2)
            except Exception as e:
                console.print(f"[red]Error writing test case {i}: {e}[/red]")
                raise 