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
            
        # Handle field conditions
        for field, condition in criteria.items():
            if field not in log_entry:
                return False
                
            value = log_entry[field]
            
            # Handle regex patterns
            if isinstance(condition, re.Pattern):
                if not isinstance(value, str):
                    return False
                return bool(condition.search(value))
                
            # Handle exact matches
            if isinstance(condition, (str, int, float, bool)):
                return value == condition
                
            # Handle lists
            if isinstance(condition, list):
                if isinstance(value, list):
                    return all(item in value for item in condition)
                return value in condition
                
            # Handle comparison operators
            if isinstance(condition, dict):
                for op, op_value in condition.items():
                    if op == '|re':
                        if not isinstance(value, str):
                            return False
                        return bool(re.search(op_value, value))
                    elif op == '|contains':
                        if not isinstance(value, str):
                            return False
                        return op_value in value
                    elif op == '|startswith':
                        if not isinstance(value, str):
                            return False
                        return value.startswith(op_value)
                    elif op == '|endswith':
                        if not isinstance(value, str):
                            return False
                        return value.endswith(op_value)
                    elif op == '|gt':
                        return value > op_value
                    elif op == '|gte':
                        return value >= op_value
                    elif op == '|lt':
                        return value < op_value
                    elif op == '|lte':
                        return value <= op_value
                        
        return True 