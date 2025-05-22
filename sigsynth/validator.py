"""Validator module for testing log entries against Sigma rules."""

from typing import Dict, Any, List, Optional
import re
from rich.console import Console

console = Console()

class RuleValidator:
    """Validates log entries against Sigma rule detection criteria."""
    
    def __init__(self, detection_criteria: Dict[str, Any]):
        """Initialize the validator.
        
        Args:
            detection_criteria: Detection criteria from the Sigma rule
        """
        self.criteria = detection_criteria
        self._compile_patterns()
    
    def validate_entry(self, log_entry: Dict[str, Any]) -> bool:
        """Validate a log entry against the rule criteria.
        
        Args:
            log_entry: Log entry to validate
            
        Returns:
            True if the entry matches the criteria, False otherwise
        """
        try:
            return self._evaluate_criteria(self.criteria, log_entry)
        except Exception as e:
            console.print(f"[yellow]Warning: Error validating entry: {e}[/yellow]")
            return False
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns in the criteria."""
        def compile_patterns_in_dict(d: Dict[str, Any]) -> None:
            for key, value in d.items():
                if isinstance(value, dict):
                    compile_patterns_in_dict(value)
                elif isinstance(value, str) and key.endswith('|re'):
                    try:
                        d[key] = re.compile(value)
                    except re.error:
                        console.print(f"[yellow]Warning: Invalid regex pattern: {value}[/yellow]")
        
        compile_patterns_in_dict(self.criteria)
    
    def _evaluate_criteria(self, criteria: Dict[str, Any], log_entry: Dict[str, Any]) -> bool:
        """Recursively evaluate detection criteria against a log entry.
        
        Args:
            criteria: Current criteria to evaluate
            log_entry: Log entry to check
            
        Returns:
            True if the entry matches the criteria, False otherwise
        """
        if not criteria:
            return True
            
        # Handle AND conditions
        if 'and' in criteria:
            return all(
                self._evaluate_criteria(condition, log_entry)
                for condition in criteria['and']
            )
            
        # Handle OR conditions
        if 'or' in criteria:
            return any(
                self._evaluate_criteria(condition, log_entry)
                for condition in criteria['or']
            )
            
        # Handle NOT conditions
        if 'not' in criteria:
            return not self._evaluate_criteria(criteria['not'], log_entry)
            
        # Handle field conditions: ALL fields must match
        for field, condition in criteria.items():
            if field not in log_entry:
                return False
            value = log_entry[field]
            # Handle regex patterns
            if isinstance(condition, re.Pattern):
                if not isinstance(value, str):
                    return False
                if not condition.search(value):
                    return False
            # Handle exact matches
            elif isinstance(condition, (str, int, float, bool)):
                if value != condition:
                    return False
            # Handle lists (case-insensitive match for any value)
            elif isinstance(condition, list):
                if isinstance(value, list):
                    if not all(any(item.lower() == v.lower() for v in value) for item in condition):
                        return False
                else:
                    if not any(item.lower() == value.lower() for item in condition):
                        return False
            # Handle comparison operators
            elif isinstance(condition, dict):
                for op, op_value in condition.items():
                    if op == '|re':
                        if not isinstance(value, str):
                            return False
                        if not re.search(op_value, value):
                            return False
                    elif op == '|contains':
                        if not isinstance(value, str):
                            return False
                        if op_value.lower() not in value.lower():
                            return False
                    elif op == '|startswith':
                        if not isinstance(value, str):
                            return False
                        if not value.lower().startswith(op_value.lower()):
                            return False
                    elif op == '|endswith':
                        if not isinstance(value, str):
                            return False
                        if not value.lower().endswith(op_value.lower()):
                            return False
                    elif op == '|gt':
                        if not value > op_value:
                            return False
                    elif op == '|gte':
                        if not value >= op_value:
                            return False
                    elif op == '|lt':
                        if not value < op_value:
                            return False
                    elif op == '|lte':
                        if not value <= op_value:
                            return False
                    else:
                        if not self._evaluate_criteria(condition, log_entry):
                            return False
            else:
                # Unknown condition type
                return False
        return True 