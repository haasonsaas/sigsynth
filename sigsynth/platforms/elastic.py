"""Elastic platform formatter for SigSynth.

This module provides Elasticsearch/Elastic Security-specific test case formatting 
and output generation. It formats test cases as Elasticsearch documents and 
Elastic Detection Engine rules.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
from .base import BasePlatform


class ElasticPlatform(BasePlatform):
    """Elastic platform formatter for test cases."""

    @property
    def name(self) -> str:
        """Platform name identifier."""
        return "elastic"

    @property
    def output_format(self) -> str:
        """Output format for test files."""
        return "json"

    def format_test_case(self, log_entry: Dict[str, Any], should_trigger: bool, 
                        index: int, rule_id: str) -> Dict[str, Any]:
        """Format a log entry as an Elastic test case.
        
        Args:
            log_entry: Raw log entry data
            should_trigger: Whether this test case should trigger the rule
            index: Test case index for naming/organization
            rule_id: Sigma rule identifier
            
        Returns:
            Elastic-formatted test case
        """
        # Add Elastic Common Schema (ECS) fields
        ecs_entry = self._add_ecs_fields(log_entry)
        
        return {
            "_index": self._determine_index(log_entry),
            "_type": "_doc",
            "_id": f"{rule_id}_{index}",
            "_source": ecs_entry,
            "test_metadata": {
                "rule_id": rule_id,
                "test_case_index": index,
                "should_trigger": should_trigger,
                "test_type": "positive" if should_trigger else "negative",
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }

    def write_test_suite(self, test_cases: List[Dict[str, Any]], 
                        output_dir: Path, rule_id: str) -> Path:
        """Write test cases to Elastic JSON files.
        
        Args:
            test_cases: List of formatted test cases
            output_dir: Directory to write test files
            rule_id: Sigma rule identifier for file naming
            
        Returns:
            Path to the main test file created
        """
        # Create output directory structure
        rule_output_dir = output_dir / "elastic" / rule_id
        rule_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate files
        bulk_file = rule_output_dir / f"{rule_id}_bulk.ndjson"
        individual_docs_file = rule_output_dir / f"{rule_id}_documents.json"
        manifest_file = rule_output_dir / "test_manifest.json"
        
        # Write bulk import file (NDJSON format for Elasticsearch _bulk API)
        with open(bulk_file, 'w') as f:
            for tc in test_cases:
                # Index operation metadata
                index_meta = {
                    "index": {
                        "_index": tc["_index"],
                        "_type": tc["_type"],
                        "_id": tc["_id"]
                    }
                }
                f.write(json.dumps(index_meta) + '\n')
                f.write(json.dumps(tc["_source"]) + '\n')
        
        # Write individual documents file for easier inspection
        documents = {
            "test_documents": [
                {
                    "metadata": tc["test_metadata"],
                    "document": tc["_source"]
                }
                for tc in test_cases
            ]
        }
        
        with open(individual_docs_file, 'w') as f:
            json.dump(documents, f, indent=2)
        
        # Write manifest file
        manifest = {
            "rule_id": rule_id,
            "platform": self.name,
            "test_count": len(test_cases),
            "positive_tests": len([tc for tc in test_cases if tc["test_metadata"]["should_trigger"]]),
            "negative_tests": len([tc for tc in test_cases if not tc["test_metadata"]["should_trigger"]]),
            "files": {
                "bulk_import": bulk_file.name,
                "documents": individual_docs_file.name,
                "manifest": manifest_file.name
            },
            "usage": {
                "description": "Import test documents into Elasticsearch and test rule behavior",
                "bulk_import_command": f"curl -X POST 'localhost:9200/_bulk' -H 'Content-Type: application/x-ndjson' --data-binary @{bulk_file.name}",
                "index_pattern": self._get_common_index_pattern(test_cases)
            },
            "elastic_info": {
                "ecs_version": "8.0",
                "recommended_index_template": self._get_index_template_suggestion(test_cases)
            }
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return individual_docs_file

    def _add_ecs_fields(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add Elastic Common Schema (ECS) fields to log entry.
        
        Args:
            log_entry: Original log entry
            
        Returns:
            Log entry enhanced with ECS fields
        """
        ecs_entry = log_entry.copy()
        
        # Add timestamp if not present
        if "@timestamp" not in ecs_entry and "timestamp" not in ecs_entry:
            ecs_entry["@timestamp"] = datetime.now(timezone.utc).isoformat()
        elif "timestamp" in ecs_entry:
            ecs_entry["@timestamp"] = ecs_entry["timestamp"]
        
        # Map common fields to ECS
        field_mappings = {
            "EventID": "event.code",
            "Computer": "host.name", 
            "User": "user.name",
            "CommandLine": "process.command_line",
            "Image": "process.executable",
            "ProcessId": "process.pid",
            "ParentProcessId": "process.parent.pid",
            "SourceIp": "source.ip",
            "DestinationIp": "destination.ip",
            "SourcePort": "source.port",
            "DestinationPort": "destination.port"
        }
        
        for original_field, ecs_field in field_mappings.items():
            if original_field in log_entry:
                self._set_nested_field(ecs_entry, ecs_field, log_entry[original_field])
        
        # Add event category if determinable
        event_category = self._determine_event_category(log_entry)
        if event_category:
            ecs_entry.setdefault("event", {})["category"] = event_category
        
        # Add data stream fields for modern Elastic
        ecs_entry.setdefault("data_stream", {
            "type": "logs",
            "dataset": self._determine_dataset(log_entry),
            "namespace": "default"
        })
        
        return ecs_entry

    def _set_nested_field(self, obj: Dict[str, Any], field_path: str, value: Any) -> None:
        """Set a nested field value using dot notation.
        
        Args:
            obj: Object to modify
            field_path: Dot-separated field path (e.g., "event.code")
            value: Value to set
        """
        parts = field_path.split('.')
        current = obj
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value

    def _determine_index(self, log_entry: Dict[str, Any]) -> str:
        """Determine appropriate Elasticsearch index for log entry.
        
        Args:
            log_entry: Log entry data
            
        Returns:
            Suggested index name
        """
        # Use data stream naming convention
        if "aws" in str(log_entry).lower():
            return "logs-aws.cloudtrail-default"
        elif "EventLog" in log_entry or "EventID" in log_entry:
            return "logs-windows.sysmon-default"
        elif "syslog" in str(log_entry).lower():
            return "logs-system.syslog-default"
        else:
            return "logs-generic-default"

    def _determine_event_category(self, log_entry: Dict[str, Any]) -> List[str]:
        """Determine ECS event categories for log entry.
        
        Args:
            log_entry: Log entry data
            
        Returns:
            List of applicable event categories
        """
        categories = []
        
        # Process events
        if any(field in log_entry for field in ["CommandLine", "Image", "ProcessId"]):
            categories.append("process")
        
        # Network events
        if any(field in log_entry for field in ["SourceIp", "DestinationIp", "SourcePort"]):
            categories.append("network")
        
        # Authentication events
        if any(keyword in str(log_entry).lower() for keyword in ["login", "logon", "auth"]):
            categories.append("authentication")
        
        # File events
        if any(field in log_entry for field in ["FileName", "FilePath", "TargetFilename"]):
            categories.append("file")
        
        return categories or ["host"]

    def _determine_dataset(self, log_entry: Dict[str, Any]) -> str:
        """Determine dataset name for data stream.
        
        Args:
            log_entry: Log entry data
            
        Returns:
            Dataset name
        """
        if "aws" in str(log_entry).lower():
            return "aws.cloudtrail"
        elif "EventLog" in log_entry:
            return "windows.sysmon"
        elif "syslog" in str(log_entry).lower():
            return "system.syslog"
        else:
            return "generic"

    def _get_common_index_pattern(self, test_cases: List[Dict[str, Any]]) -> str:
        """Get common index pattern for test cases.
        
        Args:
            test_cases: List of test cases
            
        Returns:
            Index pattern string
        """
        indices = {tc["_index"] for tc in test_cases}
        if len(indices) == 1:
            return list(indices)[0]
        else:
            # Find common prefix
            common_parts = []
            for part in list(indices)[0].split('-'):
                if all(part in idx for idx in indices):
                    common_parts.append(part)
                else:
                    break
            
            if common_parts:
                return '-'.join(common_parts) + '*'
            else:
                return 'logs-*'

    def _get_index_template_suggestion(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get index template suggestion for test data.
        
        Args:
            test_cases: List of test cases
            
        Returns:
            Index template configuration
        """
        return {
            "name": "sigsynth-test-template",
            "index_patterns": [self._get_common_index_pattern(test_cases)],
            "data_stream": {},
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "event": {
                            "properties": {
                                "category": {"type": "keyword"},
                                "code": {"type": "keyword"}
                            }
                        },
                        "host": {
                            "properties": {
                                "name": {"type": "keyword"}
                            }
                        },
                        "process": {
                            "properties": {
                                "command_line": {"type": "text"},
                                "executable": {"type": "keyword"},
                                "pid": {"type": "long"}
                            }
                        }
                    }
                }
            }
        }

    def _is_logsource_supported(self, logsource: Dict[str, Any]) -> bool:
        """Check if logsource is supported by Elastic.
        
        Args:
            logsource: Logsource configuration from Sigma rule
            
        Returns:
            True if supported, False otherwise
        """
        # Elastic supports most log sources through Beats and integrations
        supported_products = {
            "windows", "linux", "aws", "azure", "gcp", "kubernetes",
            "network", "web", "database", "antivirus", "zeek", "suricata"
        }
        
        product = logsource.get("product", "").lower()
        return product in supported_products or product == ""

    def _check_field_support(self, detection: Dict[str, Any]) -> List[str]:
        """Check for field names that may need mapping in Elastic.
        
        Args:
            detection: Detection section from Sigma rule
            
        Returns:
            List of potentially unsupported field names
        """
        potentially_unsupported = []
        
        # Common ECS field mappings
        ecs_mappings = {
            "EventID": "event.code",
            "Computer": "host.name",
            "User": "user.name", 
            "CommandLine": "process.command_line",
            "Image": "process.executable",
            "ProcessId": "process.pid"
        }
        
        def check_fields(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ["condition", "timeframe"]:
                        continue
                    
                    full_path = f"{path}.{key}" if path else key
                    
                    # Check if field should use ECS mapping
                    if key in ecs_mappings:
                        potentially_unsupported.append(f"{full_path} (recommend ECS field: {ecs_mappings[key]})")
                    
                    if isinstance(value, dict):
                        check_fields(value, full_path)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                check_fields(item, full_path)
        
        check_fields(detection)
        return potentially_unsupported