"""Panther platform implementation for SigSynth.

This module provides Panther-specific test case formatting and output generation.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console

from .base import BasePlatform

console = Console()


class PantherPlatform(BasePlatform):
    """Panther platform formatter for generating Panther-compatible test output."""

    @property
    def name(self) -> str:
        return "panther"

    @property
    def output_format(self) -> str:
        return "json"

    def format_test_case(self, log_entry: Dict[str, Any], should_trigger: bool, 
                        index: int, rule_id: str) -> Dict[str, Any]:
        """Format a test case for Panther.
        
        Args:
            log_entry: Log entry to test
            should_trigger: Whether the entry should trigger the rule
            index: Test case index
            rule_id: Sigma rule identifier
            
        Returns:
            Formatted test case for Panther
        """
        return {
            "id": f"{rule_id}-{index}",
            "type": "generated_test",
            "log": log_entry,
            "should_trigger": should_trigger,
            "rule_id": rule_id,
            "generator": "sigsynth"
        }

    def write_test_suite(self, test_cases: List[Dict[str, Any]], 
                        output_dir: Path, rule_id: str) -> Path:
        """Write test cases to output directory for Panther.
        
        Args:
            test_cases: List of formatted test cases
            output_dir: Directory to write test files to
            rule_id: Sigma rule identifier
            
        Returns:
            Path to the main test file created
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write individual test files
        for i, test_case in enumerate(test_cases):
            output_file = output_dir / f"test_{i:03d}.json"
            
            try:
                with open(output_file, 'w') as f:
                    json.dump(test_case, f, indent=2)
            except Exception as e:
                console.print(f"[red]Error writing test case {i}: {e}[/red]")
                raise
        
        # Write test suite manifest
        manifest_file = output_dir / "test_manifest.json"
        manifest = {
            "rule_id": rule_id,
            "generator": "sigsynth",
            "test_count": len(test_cases),
            "positive_tests": len([tc for tc in test_cases if tc["should_trigger"]]),
            "negative_tests": len([tc for tc in test_cases if not tc["should_trigger"]]),
            "test_files": [f"test_{i:03d}.json" for i in range(len(test_cases))]
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest_file

    def validate_platform_compatibility(self, rule_data: Dict[str, Any]) -> List[str]:
        """Check Panther-specific compatibility for a Sigma rule.
        
        Args:
            rule_data: Parsed Sigma rule data
            
        Returns:
            List of compatibility warnings/issues
        """
        warnings = super().validate_platform_compatibility(rule_data)
        
        # Check for Panther-specific field mappings
        detection = rule_data.get("detection", {})
        panther_field_mappings = self._get_panther_field_mappings()
        
        # Scan detection criteria for fields that might need mapping
        unmapped_fields = []
        for criteria in self._extract_field_names(detection):
            if criteria not in panther_field_mappings:
                unmapped_fields.append(criteria)
        
        if unmapped_fields:
            warnings.append(f"Fields may need Panther mapping: {', '.join(unmapped_fields[:5])}")
        
        # Check logsource compatibility with Panther log types
        logsource = rule_data.get("logsource", {})
        if not self._is_panther_logsource_supported(logsource):
            product = logsource.get("product", "unknown")
            service = logsource.get("service", "unknown")
            warnings.append(f"Logsource {product}/{service} may require custom Panther log schema")
        
        return warnings

    def _get_panther_field_mappings(self) -> Dict[str, str]:
        """Get common field mappings for Panther.
        
        Returns:
            Dictionary mapping common field names to Panther equivalents
        """
        return {
            # AWS CloudTrail mappings
            "eventName": "eventName",
            "sourceIPAddress": "sourceIPAddress", 
            "userIdentity.type": "userIdentity.type",
            "awsRegion": "awsRegion",
            
            # Common log fields
            "timestamp": "@timestamp",
            "source_ip": "src_ip",
            "dest_ip": "dst_ip",
            "user": "user",
            "process": "process_name",
            
            # Generic fields that usually work
            "user.name": "user",
            "process.name": "process_name",
            "network.protocol": "protocol",
        }

    def _is_panther_logsource_supported(self, logsource: Dict[str, Any]) -> bool:
        """Check if logsource is well-supported by Panther.
        
        Args:
            logsource: Logsource configuration from Sigma rule
            
        Returns:
            True if well-supported, False if may need custom schema
        """
        product = logsource.get("product", "").lower()
        service = logsource.get("service", "").lower()
        
        # Well-supported log sources in Panther
        supported_products = {
            "aws": ["cloudtrail", "vpcflow", "s3", "cloudwatch"],
            "gcp": ["audit", "vpc"],
            "azure": ["audit", "activitylog"],
            "okta": ["system"],
            "onelogin": ["events"],
            "github": ["audit"],
            "gsuite": ["admin", "drive", "login"],
            "osquery": ["result"],
            "suricata": ["eve"],
            "zeek": ["conn", "dns", "http"],
        }
        
        if product in supported_products:
            if not service or service in supported_products[product]:
                return True
        
        return False

    def _extract_field_names(self, detection: Dict[str, Any]) -> List[str]:
        """Extract field names from detection criteria.
        
        Args:
            detection: Detection section from Sigma rule
            
        Returns:
            List of field names found in detection criteria
        """
        field_names = []
        
        def extract_from_dict(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ["condition", "timeframe"]:
                        continue
                    
                    current_key = f"{prefix}.{key}" if prefix else key
                    
                    if isinstance(value, dict):
                        extract_from_dict(value, current_key)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                extract_from_dict(item, current_key)
                    else:
                        field_names.append(current_key)
            
        extract_from_dict(detection)
        return field_names