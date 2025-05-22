"""Command-line interface for SigmaTestGen.

This module provides a CLI for generating and validating synthetic log tests for Sigma rules.
The CLI supports:
1. Generating test cases from Sigma rules
2. Validating test cases against detection criteria
3. Formatting test cases for different platforms (currently Panther)
4. Configurable test generation parameters
"""

import os
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress

from .parser import parse_rule, extract_detection_criteria
from .seed_generator import SeedGenerator
from .expander import LocalExpander
from .validator import RuleValidator
from .panther_formatter import PantherFormatter

console = Console()

@click.group()
def cli():
    """Generate and validate synthetic log tests for Sigma rules.
    
    This tool helps generate test cases for Sigma rules by:
    1. Parsing Sigma rules to extract detection criteria
    2. Generating seed log entries that match/don't match the criteria
    3. Expanding seeds into multiple test variants
    4. Validating variants against the rule
    5. Formatting test cases for the target platform
    """
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
    type=click.Choice(['panther']),
    default='panther',
    help='Target platform for test output (currently only Panther is supported)'
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
def generate(rule: Path, platform: str, seed_samples: int, samples: int,
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

        expander = LocalExpander(random_seed=random_seed, detection_criteria=flat_criteria)
        validator = RuleValidator(flat_criteria)
        formatter = PantherFormatter(sigma_rule.id)
        
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
                test_case = formatter.format_test_case(
                    variant,
                    expected_trigger,  # Use the expected trigger value from the expander
                    i
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
        formatter.write_test_suite(test_cases, output)
        
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

def main():
    """Entry point for the CLI."""
    cli() 