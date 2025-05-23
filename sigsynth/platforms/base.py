"""Base platform interface for SigSynth.

This module defines the abstract base class that all platform-specific
formatters must implement to ensure consistent functionality across platforms.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional


class BasePlatform(ABC):
    """Abstract base class for platform-specific test formatters.
    
    Each platform (Panther, Splunk, Elastic, etc.) must implement this interface
    to provide consistent test case generation and validation functionality.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name identifier."""
        pass

    @property
    @abstractmethod
    def output_format(self) -> str:
        """Output format for test files (e.g., 'json', 'yaml', 'spl')."""
        pass

    @abstractmethod
    def format_test_case(self, log_entry: Dict[str, Any], should_trigger: bool, 
                        index: int, rule_id: str) -> Dict[str, Any]:
        """Format a log entry as a test case for this platform.
        
        Args:
            log_entry: Raw log entry data
            should_trigger: Whether this test case should trigger the rule
            index: Test case index for naming/organization
            rule_id: Sigma rule identifier
            
        Returns:
            Platform-specific formatted test case
        """
        pass

    @abstractmethod
    def write_test_suite(self, test_cases: List[Dict[str, Any]], 
                        output_dir: Path, rule_id: str) -> Path:
        """Write test cases to output files for this platform.
        
        Args:
            test_cases: List of formatted test cases
            output_dir: Directory to write test files
            rule_id: Sigma rule identifier for file naming
            
        Returns:
            Path to the main test file created
        """
        pass

    def validate_platform_compatibility(self, rule_data: Dict[str, Any]) -> List[str]:
        """Check if a Sigma rule is compatible with this platform.
        
        Args:
            rule_data: Parsed Sigma rule data
            
        Returns:
            List of compatibility warnings/issues (empty if fully compatible)
        """
        warnings = []
        
        # Check logsource compatibility
        logsource = rule_data.get("logsource", {})
        if not self._is_logsource_supported(logsource):
            product = logsource.get("product", "unknown")
            service = logsource.get("service", "unknown")
            warnings.append(f"Logsource {product}/{service} may not be fully supported")
        
        # Check field mappings
        detection = rule_data.get("detection", {})
        unsupported_fields = self._check_field_support(detection)
        if unsupported_fields:
            warnings.append(f"Fields may need mapping: {', '.join(unsupported_fields)}")
        
        return warnings

    def _is_logsource_supported(self, logsource: Dict[str, Any]) -> bool:
        """Check if logsource is supported by this platform.
        
        Override in platform implementations for specific support checks.
        
        Args:
            logsource: Logsource configuration from Sigma rule
            
        Returns:
            True if supported, False otherwise
        """
        return True  # Default: assume all logsources are supported

    def _check_field_support(self, detection: Dict[str, Any]) -> List[str]:
        """Check for unsupported field names in detection criteria.
        
        Override in platform implementations for specific field mappings.
        
        Args:
            detection: Detection section from Sigma rule
            
        Returns:
            List of potentially unsupported field names
        """
        return []  # Default: assume all fields are supported

    def get_file_extension(self) -> str:
        """Get file extension for test files on this platform.
        
        Returns:
            File extension (e.g., '.json', '.yaml', '.spl')
        """
        format_extensions = {
            "json": ".json",
            "yaml": ".yaml",
            "yml": ".yml",
            "spl": ".spl",
            "txt": ".txt"
        }
        return format_extensions.get(self.output_format, ".txt")

    def get_test_filename(self, rule_id: str) -> str:
        """Generate test filename for a rule.
        
        Args:
            rule_id: Sigma rule identifier
            
        Returns:
            Test filename
        """
        safe_rule_id = rule_id.replace("-", "_").replace(".", "_")
        return f"test_{safe_rule_id}{self.get_file_extension()}"