"""Parser module for Sigma rules."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

class SigmaRule(BaseModel):
    """Represents a parsed Sigma rule."""
    id: str
    title: str
    description: Optional[str]
    detection: Dict[str, Any]
    logsource: Dict[str, Any]
    level: Optional[str]
    tags: Optional[list[str]]

def parse_rule(rule_path: Path) -> SigmaRule:
    """Parse a Sigma rule file and return a structured representation.
    
    Args:
        rule_path: Path to the Sigma rule file (YAML/JSON)
        
    Returns:
        SigmaRule object containing parsed rule data
        
    Raises:
        ValueError: If the rule file is invalid or missing required fields
    """
    with open(rule_path) as f:
        data = yaml.safe_load(f)
    
    try:
        return SigmaRule(**data)
    except Exception as e:
        raise ValueError(f"Invalid Sigma rule file: {e}")

def extract_detection_criteria(rule: SigmaRule) -> Dict[str, Any]:
    """Extract the detection criteria from a Sigma rule.
    
    Args:
        rule: Parsed SigmaRule object
        
    Returns:
        Dictionary containing the detection criteria
    """
    return rule.detection 