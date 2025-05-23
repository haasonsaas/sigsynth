"""Rule analyzer for in-depth analysis of Sigma rules and test generation.

This module provides analysis capabilities for understanding rule complexity,
coverage, and potential issues in test generation.
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path

from ..parser import SigmaRule


@dataclass
class RuleComplexity:
    """Analysis of rule complexity metrics."""
    total_fields: int
    unique_fields: int
    nested_fields: int
    regex_patterns: int
    list_values: int
    condition_complexity: int
    estimated_difficulty: str  # "simple", "medium", "complex", "very_complex"


@dataclass
class CoverageAnalysis:
    """Analysis of test coverage for a rule."""
    positive_scenarios: int
    negative_scenarios: int
    field_coverage: Dict[str, int]  # field -> number of test variants
    condition_coverage: List[str]   # conditions tested
    edge_cases_covered: List[str]   # edge cases identified
    missing_coverage: List[str]     # potential gaps


@dataclass
class RuleIssues:
    """Potential issues identified in rule processing."""
    parsing_warnings: List[str]
    validation_issues: List[str]
    performance_concerns: List[str]
    coverage_gaps: List[str]
    platform_compatibility: List[str]


class RuleAnalyzer:
    """Analyzes Sigma rules for complexity, coverage, and potential issues."""
    
    def __init__(self):
        """Initialize rule analyzer."""
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    def analyze_rule_complexity(self, rule: SigmaRule) -> RuleComplexity:
        """Analyze the complexity of a Sigma rule.
        
        Args:
            rule: Parsed Sigma rule to analyze
            
        Returns:
            RuleComplexity analysis
        """
        detection = rule.detection
        
        # Count fields and complexity metrics
        all_fields = []
        regex_count = 0
        list_count = 0
        nested_count = 0
        
        def analyze_detection_section(obj, depth=0):
            nonlocal all_fields, regex_count, list_count, nested_count
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ["condition", "timeframe"]:
                        continue
                    
                    all_fields.append(key)
                    
                    if depth > 0:
                        nested_count += 1
                    
                    if isinstance(value, dict):
                        analyze_detection_section(value, depth + 1)
                    elif isinstance(value, list):
                        list_count += 1
                        for item in value:
                            if isinstance(item, dict):
                                analyze_detection_section(item, depth + 1)
                            elif isinstance(item, str) and self._is_regex(item):
                                regex_count += 1
                    elif isinstance(value, str) and self._is_regex(value):
                        regex_count += 1
        
        analyze_detection_section(detection)
        
        # Analyze condition complexity
        condition = detection.get("condition", "")
        condition_complexity = self._analyze_condition_complexity(condition)
        
        # Determine difficulty
        total_fields = len(all_fields)
        unique_fields = len(set(all_fields))
        
        if total_fields <= 3 and regex_count == 0 and condition_complexity <= 2:
            difficulty = "simple"
        elif total_fields <= 8 and regex_count <= 2 and condition_complexity <= 5:
            difficulty = "medium"
        elif total_fields <= 15 and regex_count <= 5 and condition_complexity <= 10:
            difficulty = "complex"
        else:
            difficulty = "very_complex"
        
        return RuleComplexity(
            total_fields=total_fields,
            unique_fields=unique_fields,
            nested_fields=nested_count,
            regex_patterns=regex_count,
            list_values=list_count,
            condition_complexity=condition_complexity,
            estimated_difficulty=difficulty
        )
    
    def analyze_test_coverage(self, rule: SigmaRule, test_cases: List[Dict[str, Any]]) -> CoverageAnalysis:
        """Analyze test coverage for a rule.
        
        Args:
            rule: Sigma rule being tested
            test_cases: Generated test cases
            
        Returns:
            CoverageAnalysis with coverage metrics
        """
        positive_count = len([tc for tc in test_cases if tc.get("should_trigger", False)])
        negative_count = len(test_cases) - positive_count
        
        # Analyze field coverage
        field_coverage = {}
        all_fields = self._extract_rule_fields(rule.detection)
        
        for field in all_fields:
            coverage_count = 0
            for test_case in test_cases:
                log_data = test_case.get("log", {})
                if self._field_appears_in_log(field, log_data):
                    coverage_count += 1
            field_coverage[field] = coverage_count
        
        # Identify edge cases covered
        edge_cases = self._identify_edge_cases(rule, test_cases)
        
        # Identify missing coverage
        missing_coverage = self._identify_missing_coverage(rule, test_cases)
        
        return CoverageAnalysis(
            positive_scenarios=positive_count,
            negative_scenarios=negative_count,
            field_coverage=field_coverage,
            condition_coverage=["basic"],  # TODO: More sophisticated analysis
            edge_cases_covered=edge_cases,
            missing_coverage=missing_coverage
        )
    
    def identify_rule_issues(self, rule: SigmaRule, test_cases: List[Dict[str, Any]] = None) -> RuleIssues:
        """Identify potential issues with rule processing.
        
        Args:
            rule: Sigma rule to analyze
            test_cases: Generated test cases (optional)
            
        Returns:
            RuleIssues with identified problems
        """
        parsing_warnings = []
        validation_issues = []
        performance_concerns = []
        coverage_gaps = []
        platform_compatibility = []
        
        # Check for parsing warnings
        if not rule.description or len(rule.description) < 10:
            parsing_warnings.append("Rule description is missing or too short")
        
        if not rule.tags:
            parsing_warnings.append("Rule has no MITRE ATT&CK tags")
        
        # Check validation issues
        detection = rule.detection
        if not detection.get("condition"):
            validation_issues.append("No condition specified in detection")
        
        if len(detection) <= 1:  # Only condition, no selections
            validation_issues.append("Rule has no detection selections")
        
        # Check performance concerns
        complexity = self.analyze_rule_complexity(rule)
        if complexity.regex_patterns > 5:
            performance_concerns.append(f"High number of regex patterns ({complexity.regex_patterns})")
        
        if complexity.total_fields > 20:
            performance_concerns.append(f"Very high field count ({complexity.total_fields})")
        
        # Check coverage gaps
        if test_cases:
            coverage = self.analyze_test_coverage(rule, test_cases)
            if coverage.positive_scenarios < 3:
                coverage_gaps.append("Low positive test case coverage")
            
            if coverage.negative_scenarios < 3:
                coverage_gaps.append("Low negative test case coverage")
            
            zero_coverage_fields = [f for f, c in coverage.field_coverage.items() if c == 0]
            if zero_coverage_fields:
                coverage_gaps.append(f"Fields with no test coverage: {', '.join(zero_coverage_fields[:3])}")
        
        # Check platform compatibility
        logsource = rule.logsource
        if logsource.get("product") == "windows" and logsource.get("service") == "sysmon":
            # Common compatibility issue
            if "EventID" not in str(detection):
                platform_compatibility.append("Windows Sysmon rules should specify EventID")
        
        return RuleIssues(
            parsing_warnings=parsing_warnings,
            validation_issues=validation_issues,
            performance_concerns=performance_concerns,
            coverage_gaps=coverage_gaps,
            platform_compatibility=platform_compatibility
        )
    
    def generate_analysis_report(self, rule: SigmaRule, test_cases: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive analysis report for a rule.
        
        Args:
            rule: Sigma rule to analyze
            test_cases: Generated test cases (optional)
            
        Returns:
            Complete analysis report
        """
        complexity = self.analyze_rule_complexity(rule)
        issues = self.identify_rule_issues(rule, test_cases)
        
        report = {
            "rule_info": {
                "id": rule.id,
                "title": rule.title,
                "level": rule.level,
                "status": rule.status,
                "author": rule.author
            },
            "complexity_analysis": {
                "total_fields": complexity.total_fields,
                "unique_fields": complexity.unique_fields,
                "nested_fields": complexity.nested_fields,
                "regex_patterns": complexity.regex_patterns,
                "list_values": complexity.list_values,
                "condition_complexity": complexity.condition_complexity,
                "difficulty": complexity.estimated_difficulty
            },
            "issues": {
                "parsing_warnings": issues.parsing_warnings,
                "validation_issues": issues.validation_issues,
                "performance_concerns": issues.performance_concerns,
                "coverage_gaps": issues.coverage_gaps,
                "platform_compatibility": issues.platform_compatibility
            }
        }
        
        if test_cases:
            coverage = self.analyze_test_coverage(rule, test_cases)
            report["coverage_analysis"] = {
                "positive_scenarios": coverage.positive_scenarios,
                "negative_scenarios": coverage.negative_scenarios,
                "field_coverage": coverage.field_coverage,
                "edge_cases_covered": coverage.edge_cases_covered,
                "missing_coverage": coverage.missing_coverage
            }
        
        return report
    
    def _is_regex(self, value: str) -> bool:
        """Check if a string contains regex patterns."""
        regex_indicators = ['.*', '.+', '\\d', '\\w', '\\s', '[', ']', '{', '}', '|', '^', '$']
        return any(indicator in value for indicator in regex_indicators)
    
    def _analyze_condition_complexity(self, condition: str) -> int:
        """Analyze the complexity of a detection condition."""
        if not condition:
            return 0
        
        complexity = 0
        
        # Count logical operators
        complexity += condition.count(" and ")
        complexity += condition.count(" or ")
        complexity += condition.count(" not ")
        
        # Count parentheses (grouping)
        complexity += condition.count("(") + condition.count(")")
        
        # Count selection references
        complexity += len(re.findall(r'\b\w+\b', condition)) - complexity  # Subtract operators
        
        return complexity
    
    def _extract_rule_fields(self, detection: Dict[str, Any]) -> List[str]:
        """Extract all field names from detection criteria."""
        fields = []
        
        def extract_fields(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key not in ["condition", "timeframe"]:
                        fields.append(key)
                        if isinstance(value, dict):
                            extract_fields(value)
                        elif isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict):
                                    extract_fields(item)
        
        extract_fields(detection)
        return fields
    
    def _field_appears_in_log(self, field: str, log_data: Dict[str, Any]) -> bool:
        """Check if a field appears in log data."""
        if field in log_data:
            return True
        
        # Check nested fields
        for key, value in log_data.items():
            if isinstance(value, dict) and self._field_appears_in_log(field, value):
                return True
        
        return False
    
    def _identify_edge_cases(self, rule: SigmaRule, test_cases: List[Dict[str, Any]]) -> List[str]:
        """Identify edge cases covered by test cases."""
        edge_cases = []
        
        # Check for common edge cases
        for test_case in test_cases:
            log_data = test_case.get("log", {})
            
            # Empty/null values
            if any(v == "" or v is None for v in log_data.values()):
                edge_cases.append("empty_values")
            
            # Very long strings
            if any(isinstance(v, str) and len(v) > 100 for v in log_data.values()):
                edge_cases.append("long_strings")
            
            # Special characters
            if any(isinstance(v, str) and any(c in v for c in ['<', '>', '&', '"', "'"])
                   for v in log_data.values()):
                edge_cases.append("special_characters")
        
        return list(set(edge_cases))
    
    def _identify_missing_coverage(self, rule: SigmaRule, test_cases: List[Dict[str, Any]]) -> List[str]:
        """Identify potential coverage gaps."""
        missing = []
        
        # Check if we have both positive and negative cases
        positive_cases = [tc for tc in test_cases if tc.get("should_trigger", False)]
        negative_cases = [tc for tc in test_cases if not tc.get("should_trigger", False)]
        
        if len(positive_cases) < 2:
            missing.append("insufficient_positive_cases")
        
        if len(negative_cases) < 2:
            missing.append("insufficient_negative_cases")
        
        # Check for field variations
        detection_fields = self._extract_rule_fields(rule.detection)
        for field in detection_fields:
            field_values = set()
            for test_case in test_cases:
                log_data = test_case.get("log", {})
                if field in log_data:
                    field_values.add(str(log_data[field]))
            
            if len(field_values) < 2:
                missing.append(f"limited_variation_in_{field}")
        
        return missing