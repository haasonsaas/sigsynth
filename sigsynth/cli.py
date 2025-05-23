"""Command-line interface for SigSynth.

This module provides a CLI for generating and validating synthetic log tests for Sigma rules.
The CLI supports:
1. Generating test cases from Sigma rules
2. Validating test cases against detection criteria
3. Formatting test cases for different platforms (currently Panther)
4. Configurable test generation parameters
"""

import os
import sys
import json
import time
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress

from .parser import parse_rule, extract_detection_criteria
from .seed_generator import SeedGenerator
from .expander import LocalExpander
from .validator import RuleValidator
from .panther_formatter import PantherFormatter
from .config import load_config, SigSynthConfig
from .batch_processor import BatchProcessor
from .platforms import get_platform, list_platforms
from .debug import DebugTracer, DebugReporter, RuleAnalyzer

console = Console()

@click.group()
@click.option('--config', type=click.Path(exists=True, path_type=Path), help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """Generate and validate synthetic log tests for Sigma rules.
    
    This tool helps generate test cases for Sigma rules by:
    1. Parsing Sigma rules to extract detection criteria
    2. Generating seed log entries that match/don't match the criteria
    3. Expanding seeds into multiple test variants
    4. Validating variants against the rule
    5. Formatting test cases for the target platform
    """
    # Load configuration and store in context
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)
    pass

@cli.command()
@click.option(
    '--rule',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to Sigma rule file to generate tests for'
)
@click.option(
    '--platform',
    type=click.Choice(list_platforms()),
    default='panther',
    help='Target platform for test output'
)
@click.option(
    '--seed-samples',
    type=int,
    default=5,
    help='Number of positive/negative seed samples to generate per type'
)
@click.option(
    '--samples',
    type=int,
    default=200,
    help='Total number of test samples to generate (including variants)'
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    required=True,
    help='Output directory for test files'
)
@click.option(
    '--random-seed',
    type=int,
    help='Random seed for reproducible test generation'
)
@click.pass_context
def generate(ctx, rule: Path, platform: str, seed_samples: int, samples: int,
            output: Path, random_seed: int):
    """Generate test cases for a Sigma rule.
    
    This command:
    1. Parses the Sigma rule to extract detection criteria
    2. Generates seed log entries that match/don't match the criteria
    3. Expands seeds into multiple test variants
    4. Validates each variant against the rule
    5. Formats and writes test cases to the output directory
    
    Args:
        rule: Path to the Sigma rule file
        platform: Target platform for test output
        seed_samples: Number of seed samples to generate per type
        samples: Total number of test samples to generate
        output: Output directory for test files
        random_seed: Random seed for reproducible generation
    """
    try:
        # Parse rule and extract detection criteria
        console.print(f"[bold]Parsing rule: {rule}[/bold]")
        sigma_rule = parse_rule(rule)
        detection_criteria = extract_detection_criteria(sigma_rule)
        
        # Initialize components for test generation
        seed_gen = SeedGenerator()
        # Flatten detection criteria if 'selection' is present
        if isinstance(detection_criteria, dict) and 'selection' in detection_criteria:
            flat_criteria = detection_criteria['selection']
        else:
            flat_criteria = detection_criteria

        # Use config values if not provided via CLI
        config = ctx.obj['config']
        if seed_samples is None:
            seed_samples = config.seed_samples
        if samples is None:
            samples = config.samples
        if random_seed is None:
            random_seed = config.random_seed

        expander = LocalExpander(random_seed=random_seed, detection_criteria=flat_criteria)
        validator = RuleValidator(flat_criteria)
        platform_instance = get_platform(platform)
        
        # Generate seed log entries
        console.print("[bold]Generating seed samples...[/bold]")
        positive_seeds, negative_seeds = seed_gen.generate_seeds(
            flat_criteria,  # Use flattened criteria here
            seed_samples
        )
        
        # Expand seeds into test variants
        console.print("[bold]Expanding seeds into variants...[/bold]")
        with Progress() as progress:
            task = progress.add_task("Expanding...", total=samples)
            variants = expander.expand_seeds(
                positive_seeds,
                negative_seeds,
                samples
            )
            progress.update(task, completed=samples)
        console.print(f"[yellow]Number of variants generated: {len(variants)}[/yellow]")
        if variants:
            console.print(f"[yellow]Sample variant: {variants[0][0]}[/yellow]")
        
        # Validate variants and format test cases
        console.print("[bold]Validating variants...[/bold]")
        test_cases = []
        validation_errors = []
        
        with Progress() as progress:
            task = progress.add_task("Validating...", total=len(variants))
            
            for i, (variant, expected_trigger) in enumerate(variants):
                # Validate variant against detection criteria
                should_trigger = validator.validate_entry(variant)
                console.print(f"[cyan]Variant {i} validation: should_trigger={should_trigger}, variant={variant}[/cyan]")
                
                # Format test case for target platform
                test_case = platform_instance.format_test_case(
                    variant,
                    expected_trigger,  # Use the expected trigger value from the expander
                    i,
                    sigma_rule.id
                )
                test_cases.append(test_case)
                
                # Check for validation errors
                if should_trigger != expected_trigger:
                    validation_errors.append(
                        f"Variant {i} {'unexpectedly triggers' if should_trigger else 'fails to trigger'} the rule"
                    )
                
                progress.update(task, advance=1)
        
        # Write test suite to output directory
        console.print("[bold]Writing test suite...[/bold]")
        output_path = platform_instance.write_test_suite(test_cases, output, sigma_rule.id)
        
        # Report generation results
        console.print(f"\n[bold]Generated {len(test_cases)} test cases[/bold]")
        
        if validation_errors:
            console.print("\n[red]Validation errors:[/red]")
            for error in validation_errors:
                console.print(f"  - {error}")
            sys.exit(1)
        else:
            console.print("\n[green]All test cases validated successfully![/green]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    '--rules-dir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help='Directory containing Sigma rules'
)
@click.option(
    '--pattern',
    multiple=True,
    help='File patterns to match (e.g., "*.yml", "rules/**/*.yaml")'
)
@click.option(
    '--exclude',
    multiple=True,
    help='Patterns to exclude (e.g., "draft/**", "*.disabled.yml")'
)
@click.option(
    '--platform',
    type=click.Choice(list_platforms()),
    multiple=True,
    default=['panther'],
    help='Target platforms for test output (can specify multiple)'
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    required=True,
    help='Output directory for test files'
)
@click.option(
    '--workers',
    type=int,
    help='Number of parallel workers (default from config)'
)
@click.option(
    '--fail-fast',
    is_flag=True,
    help='Stop processing on first error'
)
@click.pass_context
def batch(ctx, rules_dir: Path, pattern: tuple, exclude: tuple, platform: tuple,
         output: Path, workers: int, fail_fast: bool):
    """Generate test cases for multiple Sigma rules.
    
    This command processes multiple Sigma rules in parallel, generating
    test cases for each rule and organizing output by platform.
    
    Examples:
        sigsynth batch --rules-dir ./rules --output ./tests
        sigsynth batch --rules-dir ./rules --platform panther --platform splunk --output ./tests
        sigsynth batch --rules-dir ./rules --pattern "**/*.yml" --exclude "draft/**" --output ./tests
    """
    try:
        config = ctx.obj['config']
        
        # Override config with CLI options
        if pattern:
            config.batch.input_patterns = list(pattern)
        if exclude:
            config.batch.exclude_patterns = list(exclude)
        if workers is not None:
            config.batch.parallel_workers = workers
        if fail_fast:
            config.batch.fail_fast = fail_fast
        
        # Initialize batch processor
        processor = BatchProcessor(config)
        
        # Find rule files
        console.print(f"[bold]Scanning for rules in: {rules_dir}[/bold]")
        rule_files = processor.find_rule_files(
            rules_dir,
            config.batch.input_patterns,
            config.batch.exclude_patterns
        )
        
        if not rule_files:
            console.print("[red]No rule files found matching criteria[/red]")
            sys.exit(1)
        
        console.print(f"Found {len(rule_files)} rule files")
        
        # Process rules
        summary = processor.process_rules(rule_files, list(platform), output)
        
        # Exit with error code if any rules failed
        if summary.failed_rules > 0:
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    '--rule',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to Sigma rule file to debug'
)
@click.option(
    '--test-case',
    type=int,
    help='Specific test case index to debug (default: debug all)'
)
@click.option(
    '--trace',
    is_flag=True,
    help='Enable detailed tracing of rule processing'
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    help='Debug report output file (default: print to console)'
)
@click.pass_context
def debug(ctx, rule: Path, test_case: int, trace: bool, output: Path):
    """Debug rule processing and test generation.
    
    This command provides detailed information about how a rule is processed,
    including parsing, seed generation, expansion, and validation steps.
    
    Examples:
        sigsynth debug --rule rule.yml --trace
        sigsynth debug --rule rule.yml --test-case 5 --output debug.json
    """
    try:
        config = ctx.obj['config']
        
        console.print(f"[bold]🔍 Debugging rule: {rule}[/bold]\n")
        
        # Initialize debug components
        tracer = DebugTracer(rule.stem, enabled=trace or config.debug.enabled)
        reporter = DebugReporter(console)
        analyzer = RuleAnalyzer()
        
        # Step 1: Parse rule and analyze complexity
        tracer.start_step("parse_rule", {"rule_path": str(rule)})
        try:
            sigma_rule = parse_rule(rule)
            detection_criteria = extract_detection_criteria(sigma_rule)
            
            # Analyze rule complexity
            complexity = analyzer.analyze_rule_complexity(sigma_rule)
            issues = analyzer.identify_rule_issues(sigma_rule)
            
            tracer.end_step({
                "rule_id": sigma_rule.id,
                "rule_title": sigma_rule.title,
                "detection_criteria_count": len(detection_criteria) if isinstance(detection_criteria, dict) else 1,
                "complexity": complexity.estimated_difficulty,
                "total_fields": complexity.total_fields
            }, True)
            
            # Display rule information
            console.print(f"[bold cyan]📋 Rule Information[/bold cyan]")
            console.print(f"  ID: {sigma_rule.id}")
            console.print(f"  Title: {sigma_rule.title}")
            console.print(f"  Level: {sigma_rule.level}")
            console.print(f"  Author: {sigma_rule.author}")
            console.print(f"  Status: {sigma_rule.status}")
            
            # Display complexity analysis
            console.print(f"\n[bold yellow]⚡ Complexity Analysis[/bold yellow]")
            console.print(f"  Difficulty: {complexity.estimated_difficulty}")
            console.print(f"  Total Fields: {complexity.total_fields}")
            console.print(f"  Unique Fields: {complexity.unique_fields}")
            console.print(f"  Regex Patterns: {complexity.regex_patterns}")
            console.print(f"  Condition Complexity: {complexity.condition_complexity}")
            
            # Display any issues found
            if any([issues.parsing_warnings, issues.validation_issues, 
                   issues.performance_concerns, issues.platform_compatibility]):
                console.print(f"\n[bold red]⚠️  Potential Issues[/bold red]")
                
                for warning in issues.parsing_warnings:
                    console.print(f"  🟡 Parse Warning: {warning}")
                for issue in issues.validation_issues:
                    console.print(f"  🔴 Validation: {issue}")
                for concern in issues.performance_concerns:
                    console.print(f"  🟠 Performance: {concern}")
                for compat in issues.platform_compatibility:
                    console.print(f"  🟣 Platform: {compat}")
            else:
                console.print(f"\n[green]✅ No issues detected[/green]")
                
        except Exception as e:
            tracer.end_step({}, False, str(e))
            console.print(f"[red]❌ Failed to parse rule: {e}[/red]")
            if output:
                reporter.save_report(tracer, output, "json")
            return
        
        # Step 2: Generate and analyze test cases (if API key available)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "test":
            console.print(f"\n[bold green]🧪 Generating Test Cases[/bold green]")
            
            try:
                # Flatten detection criteria
                if isinstance(detection_criteria, dict) and 'selection' in detection_criteria:
                    flat_criteria = detection_criteria['selection']
                else:
                    flat_criteria = detection_criteria
                
                # Initialize components
                seed_gen = SeedGenerator()
                expander = LocalExpander(
                    random_seed=config.random_seed,
                    detection_criteria=flat_criteria
                )
                validator = RuleValidator(flat_criteria)
                
                # Step 2a: Generate seeds
                tracer.start_step("generate_seeds", {
                    "seed_samples": config.seed_samples,
                    "criteria_fields": len(flat_criteria) if isinstance(flat_criteria, dict) else 1
                })
                
                positive_seeds, negative_seeds = seed_gen.generate_seeds(
                    flat_criteria,
                    config.seed_samples
                )
                
                tracer.end_step({
                    "positive_seeds": len(positive_seeds),
                    "negative_seeds": len(negative_seeds)
                }, True)
                
                console.print(f"  Generated {len(positive_seeds)} positive seeds")
                console.print(f"  Generated {len(negative_seeds)} negative seeds")
                
                # Step 2b: Expand seeds
                tracer.start_step("expand_seeds", {
                    "target_samples": min(config.samples, 50)  # Limit for debugging
                })
                
                variants = expander.expand_seeds(
                    positive_seeds,
                    negative_seeds,
                    min(config.samples, 50)  # Limit for debugging
                )
                
                tracer.end_step({
                    "total_variants": len(variants),
                    "positive_variants": len([v for v in variants if v[1]]),
                    "negative_variants": len([v for v in variants if not v[1]])
                }, True)
                
                console.print(f"  Expanded to {len(variants)} test variants")
                
                # Step 2c: Validate and analyze
                tracer.start_step("validate_tests", {"variant_count": len(variants)})
                
                validation_errors = 0
                test_cases = []
                
                for i, (variant, expected_trigger) in enumerate(variants):
                    should_trigger = validator.validate_entry(variant)
                    
                    test_case = {
                        "index": i,
                        "log": variant,
                        "should_trigger": expected_trigger,
                        "actual_trigger": should_trigger,
                        "validation_match": should_trigger == expected_trigger
                    }
                    test_cases.append(test_case)
                    
                    if should_trigger != expected_trigger:
                        validation_errors += 1
                        if trace:
                            console.print(f"    ⚠️  Validation mismatch in test {i}: expected {expected_trigger}, got {should_trigger}")
                
                tracer.end_step({
                    "validation_errors": validation_errors,
                    "success_rate": (len(variants) - validation_errors) / len(variants) if variants else 0
                }, validation_errors == 0)
                
                # Display test analysis
                console.print(f"\n[bold blue]📊 Test Analysis[/bold blue]")
                console.print(f"  Total Test Cases: {len(test_cases)}")
                console.print(f"  Validation Errors: {validation_errors}")
                console.print(f"  Success Rate: {(len(variants) - validation_errors) / len(variants) * 100:.1f}%" if variants else "  Success Rate: N/A")
                
                # Analyze specific test case if requested
                if test_case is not None and 0 <= test_case < len(test_cases):
                    console.print(f"\n[bold magenta]🔍 Test Case {test_case} Analysis[/bold magenta]")
                    tc = test_cases[test_case]
                    console.print(f"  Expected Trigger: {tc['should_trigger']}")
                    console.print(f"  Actual Trigger: {tc['actual_trigger']}")
                    console.print(f"  Validation Match: {'✅' if tc['validation_match'] else '❌'}")
                    console.print(f"  Log Data: {json.dumps(tc['log'], indent=2)}")
                
                # Coverage analysis
                coverage = analyzer.analyze_test_coverage(sigma_rule, test_cases)
                console.print(f"\n[bold purple]📈 Coverage Analysis[/bold purple]")
                console.print(f"  Positive Scenarios: {coverage.positive_scenarios}")
                console.print(f"  Negative Scenarios: {coverage.negative_scenarios}")
                console.print(f"  Edge Cases Covered: {', '.join(coverage.edge_cases_covered) if coverage.edge_cases_covered else 'None detected'}")
                
                if coverage.missing_coverage:
                    console.print(f"  Potential Gaps: {', '.join(coverage.missing_coverage[:3])}")
                
            except Exception as e:
                tracer.end_step({}, False, str(e))
                console.print(f"[red]❌ Error during test generation: {e}[/red]")
        else:
            console.print(f"\n[yellow]⚠️  OpenAI API key not available - skipping test generation[/yellow]")
            console.print(f"   Set OPENAI_API_KEY environment variable to enable test analysis")
        
        # Step 3: Platform compatibility check
        console.print(f"\n[bold cyan]🖥️  Platform Compatibility[/bold cyan]")
        
        for platform_name in list_platforms():
            platform = get_platform(platform_name)
            warnings = platform.validate_platform_compatibility(sigma_rule.to_dict())
            
            if warnings:
                console.print(f"  {platform_name}: ⚠️  {len(warnings)} warnings")
                for warning in warnings:
                    console.print(f"    - {warning}")
            else:
                console.print(f"  {platform_name}: ✅ Compatible")
        
        # Display trace summary if tracing enabled
        if trace or config.debug.enabled:
            console.print(f"\n[bold white]📝 Debug Trace Summary[/bold white]")
            reporter.print_trace_summary(tracer)
            
            if config.debug.verbose:
                console.print(f"\n[bold white]📋 Detailed Trace[/bold white]")
                reporter.print_detailed_trace(tracer, show_inputs=True, show_outputs=True)
        
        # Save debug output if requested
        if output:
            format = "json" if output.suffix.lower() == ".json" else "text"
            
            # Generate comprehensive report
            analysis_report = analyzer.generate_analysis_report(
                sigma_rule, 
                test_cases if 'test_cases' in locals() else None
            )
            
            # Combine trace and analysis
            debug_data = {
                "rule_analysis": analysis_report,
                "debug_trace": tracer.get_full_trace() if trace else None,
                "generated_at": time.time()
            }
            
            output.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "json":
                with open(output, 'w') as f:
                    json.dump(debug_data, f, indent=2, default=str)
            else:
                reporter.save_report(tracer, output, "text")
            
            console.print(f"\n[green]💾 Debug report saved to: {output}[/green]")
        
        console.print(f"\n[bold green]🎉 Debug analysis complete![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if config.debug.verbose:
            import traceback
            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli() 