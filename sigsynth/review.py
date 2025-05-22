import argparse
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax


def main():
    parser = argparse.ArgumentParser(description="Review generated Sigma test cases.")
    parser.add_argument("--input", type=str, required=True, help="Directory containing test case files")
    parser.add_argument("--show", type=int, default=0, help="Show N sample test cases from each class")
    args = parser.parse_args()

    console = Console()
    test_dir = Path(args.input)
    if not test_dir.exists() or not test_dir.is_dir():
        console.print(f"[red]Input directory does not exist: {test_dir}[/red]")
        return

    test_files = sorted(test_dir.glob("test_*.json"))
    if not test_files:
        console.print(f"[yellow]No test_*.json files found in {test_dir}[/yellow]")
        return

    trigger_cases = []
    nontrigger_cases = []
    errors = []

    for file in test_files:
        try:
            with open(file) as f:
                data = json.load(f)
            if data.get("should_trigger"):
                trigger_cases.append((file, data))
            else:
                nontrigger_cases.append((file, data))
        except Exception as e:
            errors.append((file, str(e)))

    total = len(test_files)
    n_trigger = len(trigger_cases)
    n_nontrigger = len(nontrigger_cases)

    table = Table(title="Sigma Test Case Review")
    table.add_column("Type", style="cyan", justify="right")
    table.add_column("Count", style="magenta", justify="right")
    table.add_row("Total", str(total))
    table.add_row("Should Trigger", str(n_trigger))
    table.add_row("Should NOT Trigger", str(n_nontrigger))
    if errors:
        table.add_row("[red]Errors[/red]", str(len(errors)))
    console.print(table)

    if args.show > 0:
        def show_samples(cases, label):
            console.print(f"\n[bold]{label} (showing up to {args.show}):[/bold]")
            for i, (file, data) in enumerate(cases[:args.show]):
                console.print(f"[green]{file.name}[/green]")
                syntax = Syntax(json.dumps(data, indent=2), "json", theme="monokai", word_wrap=True)
                console.print(syntax)
        show_samples(trigger_cases, "Should Trigger")
        show_samples(nontrigger_cases, "Should NOT Trigger")

    if errors:
        console.print(f"\n[red]Files with errors:[/red]")
        for file, err in errors:
            console.print(f"  {file.name}: {err}")

if __name__ == "__main__":
    main() 