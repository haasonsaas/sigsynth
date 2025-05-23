"""Batch processing for multiple Sigma rules.

This module provides functionality to process multiple Sigma rules in parallel,
with progress tracking and error handling for large rule sets.
"""

import asyncio
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
import fnmatch
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from .config import SigSynthConfig
from .parser import parse_rule, extract_detection_criteria
from .seed_generator import SeedGenerator
from .expander import LocalExpander
from .validator import RuleValidator
from .platforms import get_platform

console = Console()


@dataclass
class BatchResult:
    """Result of processing a single rule."""
    rule_path: Path
    rule_id: str
    success: bool
    test_count: int = 0
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    processing_time: float = 0.0

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class BatchSummary:
    """Summary of batch processing results."""
    total_rules: int
    successful_rules: int
    failed_rules: int
    total_tests: int
    total_warnings: int
    processing_time: float
    results: List[BatchResult]


class BatchProcessor:
    """Processes multiple Sigma rules in parallel."""

    def __init__(self, config: SigSynthConfig):
        """Initialize batch processor.
        
        Args:
            config: SigSynth configuration
        """
        self.config = config
        self.seed_generator = SeedGenerator()

    def find_rule_files(self, rules_dir: Path, patterns: List[str] = None,
                       exclude_patterns: List[str] = None) -> List[Path]:
        """Find Sigma rule files matching patterns.
        
        Args:
            rules_dir: Directory to search for rules
            patterns: File patterns to match (default from config)
            exclude_patterns: Patterns to exclude (default from config)
            
        Returns:
            List of rule file paths
        """
        if patterns is None:
            patterns = self.config.batch.input_patterns
        if exclude_patterns is None:
            exclude_patterns = self.config.batch.exclude_patterns

        rule_files = []
        
        for pattern in patterns:
            # Use glob to find matching files
            matches = list(rules_dir.glob(pattern))
            rule_files.extend(matches)
        
        # Remove duplicates and filter out excluded patterns
        unique_files = list(set(rule_files))
        filtered_files = []
        
        for file_path in unique_files:
            # Check if file should be excluded
            excluded = False
            relative_path = file_path.relative_to(rules_dir)
            
            for exclude_pattern in exclude_patterns:
                if fnmatch.fnmatch(str(relative_path), exclude_pattern):
                    excluded = True
                    break
            
            if not excluded and file_path.is_file():
                filtered_files.append(file_path)
        
        return sorted(filtered_files)

    async def process_rules_async(self, rule_files: List[Path], platforms: List[str],
                                output_dir: Path, progress_callback: Optional[Callable] = None) -> BatchSummary:
        """Process multiple rules asynchronously.
        
        Args:
            rule_files: List of rule files to process
            platforms: List of target platforms
            output_dir: Base output directory
            progress_callback: Optional callback for progress updates
            
        Returns:
            Batch processing summary
        """
        import time
        start_time = time.time()
        
        # Create platform instances
        platform_instances = {}
        for platform_name in platforms:
            try:
                platform_instances[platform_name] = get_platform(platform_name)
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                return BatchSummary(0, 0, len(rule_files), 0, 0, 0.0, [])

        results = []
        
        # Use ThreadPoolExecutor for CPU-bound tasks
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.batch.parallel_workers
        ) as executor:
            
            # Submit all tasks
            future_to_rule = {}
            for rule_file in rule_files:
                future = executor.submit(
                    self._process_single_rule,
                    rule_file,
                    platform_instances,
                    output_dir
                )
                future_to_rule[future] = rule_file
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_rule):
                rule_file = future_to_rule[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(result)
                    
                    # Fail fast if configured
                    if not result.success and self.config.batch.fail_fast:
                        console.print(f"[red]Failing fast due to error in {rule_file}[/red]")
                        # Cancel remaining futures
                        for remaining_future in future_to_rule:
                            if not remaining_future.done():
                                remaining_future.cancel()
                        break
                        
                except Exception as e:
                    error_result = BatchResult(
                        rule_path=rule_file,
                        rule_id=rule_file.stem,
                        success=False,
                        error_message=str(e)
                    )
                    results.append(error_result)
                    
                    if progress_callback:
                        progress_callback(error_result)

        processing_time = time.time() - start_time
        
        # Calculate summary statistics
        successful = len([r for r in results if r.success])
        failed = len([r for r in results if not r.success])
        total_tests = sum(r.test_count for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        
        return BatchSummary(
            total_rules=len(rule_files),
            successful_rules=successful,
            failed_rules=failed,
            total_tests=total_tests,
            total_warnings=total_warnings,
            processing_time=processing_time,
            results=results
        )

    def _process_single_rule(self, rule_file: Path, platform_instances: Dict[str, Any],
                           output_dir: Path) -> BatchResult:
        """Process a single rule file.
        
        Args:
            rule_file: Path to rule file
            platform_instances: Dictionary of platform instances
            output_dir: Base output directory
            
        Returns:
            Result of processing this rule
        """
        import time
        start_time = time.time()
        
        try:
            # Parse rule
            sigma_rule = parse_rule(rule_file)
            detection_criteria = extract_detection_criteria(sigma_rule)
            
            # Flatten detection criteria if needed
            if isinstance(detection_criteria, dict) and 'selection' in detection_criteria:
                flat_criteria = detection_criteria['selection']
            else:
                flat_criteria = detection_criteria

            # Initialize components
            expander = LocalExpander(
                random_seed=self.config.random_seed,
                detection_criteria=flat_criteria
            )
            validator = RuleValidator(flat_criteria)
            
            # Generate seeds
            positive_seeds, negative_seeds = self.seed_generator.generate_seeds(
                flat_criteria,
                self.config.seed_samples
            )
            
            # Expand into variants
            variants = expander.expand_seeds(
                positive_seeds,
                negative_seeds,
                self.config.samples
            )
            
            if not variants:
                return BatchResult(
                    rule_path=rule_file,
                    rule_id=sigma_rule.id,
                    success=False,
                    error_message="No test variants generated"
                )
            
            # Process for each platform
            all_warnings = []
            output_paths = []
            
            for platform_name, platform in platform_instances.items():
                # Check platform compatibility
                platform_warnings = platform.validate_platform_compatibility(sigma_rule.to_dict())
                all_warnings.extend([f"[{platform_name}] {w}" for w in platform_warnings])
                
                # Generate and validate test cases
                test_cases = []
                for i, (variant, expected_trigger) in enumerate(variants):
                    # Validate variant
                    should_trigger = validator.validate_entry(variant)
                    
                    # Format for platform
                    test_case = platform.format_test_case(
                        variant,
                        expected_trigger,
                        i,
                        sigma_rule.id
                    )
                    test_cases.append(test_case)
                
                # Write test suite
                platform_output_dir = output_dir / platform_name / sigma_rule.id
                output_path = platform.write_test_suite(test_cases, platform_output_dir, sigma_rule.id)
                output_paths.append(output_path)
            
            processing_time = time.time() - start_time
            
            return BatchResult(
                rule_path=rule_file,
                rule_id=sigma_rule.id,
                success=True,
                test_count=len(variants),
                output_path=output_paths[0] if output_paths else None,
                warnings=all_warnings,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return BatchResult(
                rule_path=rule_file,
                rule_id=rule_file.stem,
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )

    def process_rules(self, rule_files: List[Path], platforms: List[str],
                     output_dir: Path) -> BatchSummary:
        """Process multiple rules with progress tracking.
        
        Args:
            rule_files: List of rule files to process
            platforms: List of target platforms
            output_dir: Base output directory
            
        Returns:
            Batch processing summary
        """
        console.print(f"[bold]Processing {len(rule_files)} rules for platforms: {', '.join(platforms)}[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing rules...", total=len(rule_files))
            
            def update_progress(result: BatchResult):
                status = "✓" if result.success else "✗"
                progress.update(
                    task,
                    advance=1,
                    description=f"Processing rules... {status} {result.rule_id}"
                )
            
            # Run async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                summary = loop.run_until_complete(
                    self.process_rules_async(rule_files, platforms, output_dir, update_progress)
                )
            finally:
                loop.close()
        
        # Print summary
        self._print_summary(summary)
        
        return summary

    def _print_summary(self, summary: BatchSummary) -> None:
        """Print batch processing summary.
        
        Args:
            summary: Batch processing summary
        """
        console.print("\n[bold]Batch Processing Summary[/bold]")
        console.print(f"  Total rules: {summary.total_rules}")
        console.print(f"  Successful: [green]{summary.successful_rules}[/green]")
        console.print(f"  Failed: [red]{summary.failed_rules}[/red]")
        console.print(f"  Total tests generated: {summary.total_tests}")
        console.print(f"  Total warnings: {summary.total_warnings}")
        console.print(f"  Processing time: {summary.processing_time:.2f}s")
        
        if summary.failed_rules > 0:
            console.print("\n[red]Failed rules:[/red]")
            for result in summary.results:
                if not result.success:
                    console.print(f"  - {result.rule_path}: {result.error_message}")
        
        if summary.total_warnings > 0:
            console.print(f"\n[yellow]See individual rule outputs for {summary.total_warnings} warnings[/yellow]")