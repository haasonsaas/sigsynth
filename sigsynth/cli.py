"""Command-line interface for SigmaTestGen."""

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
    """Generate and validate synthetic log tests for Sigma rules."""
    pass

@cli.command()
@click.option(
    '--rule',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to Sigma rule file'
)
@click.option(
    '--platform',
    type=click.Choice(['panther']),
    default='panther',
    help='Target platform for test output'
)
@click.option(
    '--seed-samples',
    type=int,
    default=5,
    help='Number of positive/negative seed samples to generate'
)
@click.option(
    '--samples',
    type=int,
    default=200,
    help='Total number of test samples to generate'
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
    help='Random seed for reproducible generation'
)
def generate(rule: Path, platform: str, seed_samples: int, samples: int,
            output: Path, random_seed: int):
    """Generate test cases for a Sigma rule."""
    try:
        # Parse rule
        console.print(f"[bold]Parsing rule: {rule}[/bold]")
        sigma_rule = parse_rule(rule)
        detection_criteria = extract_detection_criteria(sigma_rule)
        
        # Initialize components
        seed_gen = SeedGenerator()
        expander = LocalExpander(random_seed=random_seed)
        
        # Flatten detection criteria if 'selection' is present
        if isinstance(detection_criteria, dict) and 'selection' in detection_criteria:
            flat_criteria = detection_criteria['selection']
        else:
            flat_criteria = detection_criteria
            
        validator = RuleValidator(flat_criteria)
        formatter = PantherFormatter(sigma_rule.id)
        
        # Generate seeds
        console.print("[bold]Generating seed samples...[/bold]")
        positive_seeds, negative_seeds = seed_gen.generate_seeds(
            flat_criteria,  # Use flattened criteria here
            seed_samples
        )
        
        # Expand seeds
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
            console.print(f"[yellow]Sample variant: {variants[0]}[/yellow]")
        
        # Validate variants
        console.print("[bold]Validating variants...[/bold]")
        test_cases = []
        validation_errors = []
        
        with Progress() as progress:
            task = progress.add_task("Validating...", total=len(variants))
            
            for i, variant in enumerate(variants):
                should_trigger = validator.validate_entry(variant)
                console.print(f"[cyan]Variant {i} validation: should_trigger={should_trigger}, variant={variant}[/cyan]")
                # Determine if this variant should trigger
                
                # Format test case
                test_case = formatter.format_test_case(
                    variant,
                    should_trigger,
                    i
                )
                test_cases.append(test_case)
                
                # Check for validation errors
                if should_trigger and i >= len(positive_seeds):
                    validation_errors.append(
                        f"Variant {i} unexpectedly triggers the rule"
                    )
                elif not should_trigger and i < len(positive_seeds):
                    validation_errors.append(
                        f"Variant {i} fails to trigger the rule"
                    )
                
                progress.update(task, advance=1)
        
        # Write test suite
        console.print("[bold]Writing test suite...[/bold]")
        formatter.write_test_suite(test_cases, output)
        
        # Report results
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