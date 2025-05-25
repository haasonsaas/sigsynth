"""Splunk platform formatter for SigSynth.

This module provides Splunk-specific test case formatting and output generation.
It formats test cases as SPL (Search Processing Language) queries and data.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from .base import BasePlatform


class SplunkPlatform(BasePlatform):
    """Splunk platform formatter for test cases."""

    @property
    def name(self) -> str:
        """Platform name identifier."""
        return "splunk"

    @property
    def output_format(self) -> str:
        """Output format for test files."""
        return "spl"

    def format_test_case(self, log_entry: Dict[str, Any], should_trigger: bool, 
                        index: int, rule_id: str) -> Dict[str, Any]:
        """Format a log entry as a Splunk test case.
        
        Args:
            log_entry: Raw log entry data
            should_trigger: Whether this test case should trigger the rule
            index: Test case index for naming/organization
            rule_id: Sigma rule identifier
            
        Returns:
            Splunk-formatted test case
        """
        return {
            "index": index,
            "rule_id": rule_id,
            "log": log_entry,
            "should_trigger": should_trigger,
            "splunk_index": "main",  # Default index
            "sourcetype": self._determine_sourcetype(log_entry),
            "source": f"test_data_{rule_id}",
            "timestamp": log_entry.get("timestamp", "now()"),
            "raw_log": self._convert_to_raw_log(log_entry)
        }

    def write_test_suite(self, test_cases: List[Dict[str, Any]], 
                        output_dir: Path, rule_id: str) -> Path:
        """Write test cases to Splunk SPL files.
        
        Args:
            test_cases: List of formatted test cases
            output_dir: Directory to write test files
            rule_id: Sigma rule identifier for file naming
            
        Returns:
            Path to the main SPL test file created
        """
        # Create output directory structure
        rule_output_dir = output_dir / "splunk" / rule_id
        rule_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate SPL search queries
        spl_file = rule_output_dir / f"{rule_id}.spl"
        data_file = rule_output_dir / f"{rule_id}_data.json"
        manifest_file = rule_output_dir / "test_manifest.json"
        
        # Write SPL search file
        with open(spl_file, 'w') as f:
            f.write(self._generate_spl_search(test_cases, rule_id))
        
        # Write test data file
        test_data = [
            {
                "index": tc["splunk_index"],
                "sourcetype": tc["sourcetype"],
                "source": tc["source"],
                "_time": tc["timestamp"],
                "_raw": tc["raw_log"],
                "should_trigger": tc["should_trigger"]
            }
            for tc in test_cases
        ]
        
        with open(data_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        # Write manifest file
        manifest = {
            "rule_id": rule_id,
            "platform": self.name,
            "test_count": len(test_cases),
            "positive_tests": len([tc for tc in test_cases if tc["should_trigger"]]),
            "negative_tests": len([tc for tc in test_cases if not tc["should_trigger"]]),
            "files": {
                "spl_search": spl_file.name,
                "test_data": data_file.name,
                "manifest": manifest_file.name
            },
            "usage": {
                "description": "Import test_data into Splunk and run the SPL search",
                "data_import": f"| makeresults | eval _raw=\"{data_file}\" | inputlookup",
                "search_file": spl_file.name
            }
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return spl_file

    def _determine_sourcetype(self, log_entry: Dict[str, Any]) -> str:
        """Determine appropriate Splunk sourcetype for log entry.
        
        Args:
            log_entry: Log entry data
            
        Returns:
            Suggested sourcetype
        """
        # Common sourcetype mappings based on log content
        if "EventLog" in log_entry or "EventID" in log_entry:
            return "WinEventLog"
        elif "aws" in str(log_entry).lower():
            return "aws:cloudtrail"
        elif "syslog" in str(log_entry).lower():
            return "syslog"
        elif "access_log" in str(log_entry).lower() or "method" in log_entry:
            return "access_combined"
        else:
            return "json"

    def _convert_to_raw_log(self, log_entry: Dict[str, Any]) -> str:
        """Convert structured log entry to raw log format.
        
        Args:
            log_entry: Structured log entry
            
        Returns:
            Raw log string suitable for Splunk ingestion
        """
        # For JSON-like logs, return JSON string
        if isinstance(log_entry, dict):
            return json.dumps(log_entry, separators=(',', ':'))
        else:
            return str(log_entry)

    def _generate_spl_search(self, test_cases: List[Dict[str, Any]], rule_id: str) -> str:
        """Generate SPL search query for testing.
        
        Args:
            test_cases: Test cases to generate search for
            rule_id: Rule identifier
            
        Returns:
            SPL search string
        """
        # Basic SPL template for testing
        spl_template = f"""| makeresults count={len(test_cases)}
| eval test_case=mvindex(split("{'|'.join([str(i) for i in range(len(test_cases))])}", "|"), 0)
| eval should_trigger=case(
{self._generate_case_conditions(test_cases)}
)
| eval rule_id="{rule_id}"
| eval platform="splunk"
| eval test_description="Automated test case for {rule_id}"
| table test_case, should_trigger, rule_id, platform, test_description

| comment "
Usage: 
1. Import test data from {rule_id}_data.json
2. Run this search to validate rule behavior
3. Compare should_trigger with actual rule results
"
"""
        return spl_template

    def _generate_case_conditions(self, test_cases: List[Dict[str, Any]]) -> str:
        """Generate SPL case conditions for test cases.
        
        Args:
            test_cases: Test cases to generate conditions for
            
        Returns:
            SPL case statement conditions
        """
        conditions = []
        for i, tc in enumerate(test_cases):
            conditions.append(f'test_case=={i}, {str(tc["should_trigger"]).lower()}')
        
        return ",\n".join(conditions)

    def _is_logsource_supported(self, logsource: Dict[str, Any]) -> bool:
        """Check if logsource is supported by Splunk.
        
        Args:
            logsource: Logsource configuration from Sigma rule
            
        Returns:
            True if supported, False otherwise
        """
        # Splunk supports most log sources with appropriate sourcetypes
        supported_products = {
            "windows", "linux", "aws", "azure", "gcp", 
            "network", "web", "database", "antivirus"
        }
        
        product = logsource.get("product", "").lower()
        return product in supported_products or product == ""

    def _check_field_support(self, detection: Dict[str, Any]) -> List[str]:
        """Check for field names that may need mapping in Splunk.
        
        Args:
            detection: Detection section from Sigma rule
            
        Returns:
            List of potentially unsupported field names
        """
        potentially_unsupported = []
        
        # Common field mappings that might need attention in Splunk
        field_mappings = {
            "EventID": "EventCode",
            "CommandLine": "process",
            "Image": "process_name",
            "User": "user",
            "Computer": "host"
        }
        
        def check_fields(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ["condition", "timeframe"]:
                        continue
                    
                    full_path = f"{path}.{key}" if path else key
                    
                    # Check if field might need mapping
                    if key in field_mappings:
                        potentially_unsupported.append(f"{full_path} (consider mapping to {field_mappings[key]})")
                    
                    if isinstance(value, dict):
                        check_fields(value, full_path)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                check_fields(item, full_path)
        
        check_fields(detection)
        return potentially_unsupported