"""Debug reporter for generating human-readable debug reports.

This module converts trace data into formatted reports for debugging
and understanding rule processing behavior.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from .tracer import DebugTracer, TraceStep


class DebugReporter:
    """Generates human-readable debug reports from trace data."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize debug reporter.
        
        Args:
            console: Rich console for output (creates new if None)
        """
        self.console = console or Console()
    
    def print_trace_summary(self, tracer: DebugTracer):
        """Print a summary of the trace to console.
        
        Args:
            tracer: DebugTracer containing trace data
        """
        summary = tracer.get_trace_summary()
        
        if not summary:
            self.console.print("[yellow]No trace data available[/yellow]")
            return
        
        # Create summary panel
        summary_text = f"""[bold]Rule ID:[/bold] {summary['rule_id']}
[bold]Total Duration:[/bold] {summary['total_duration']:.2f}s
[bold]Total Steps:[/bold] {summary['total_steps']}
[bold]Successful:[/bold] [green]{summary['successful_steps']}[/green]
[bold]Failed:[/bold] [red]{summary['failed_steps']}[/red]
[bold]Success Rate:[/bold] {summary['success_rate']:.1%}"""
        
        self.console.print(Panel(summary_text, title="Trace Summary", border_style="blue"))
        
        # Show step timings
        if summary['step_timings']:
            table = Table(title="Step Timings")
            table.add_column("Step", style="cyan")
            table.add_column("Duration", style="magenta", justify="right")
            
            for step_name, duration in summary['step_timings'].items():
                table.add_row(step_name, f"{duration:.3f}s")
            
            self.console.print(table)
    
    def print_detailed_trace(self, tracer: DebugTracer, show_inputs: bool = True,
                           show_outputs: bool = True, show_metadata: bool = False):
        """Print detailed trace information to console.
        
        Args:
            tracer: DebugTracer containing trace data
            show_inputs: Whether to show step inputs
            show_outputs: Whether to show step outputs  
            show_metadata: Whether to show step metadata
        """
        if not tracer.steps:
            self.console.print("[yellow]No trace steps available[/yellow]")
            return
        
        tree = Tree(f"[bold]Trace for Rule: {tracer.rule_id}[/bold]")
        
        for i, step in enumerate(tracer.steps):
            # Step status icon
            status_icon = "✅" if step.success else "❌"
            duration_text = f" ({step.duration:.3f}s)" if step.duration else ""
            
            step_node = tree.add(
                f"{status_icon} [bold]{step.step_name}[/bold]{duration_text}"
            )
            
            # Add error message if step failed
            if not step.success and step.error_message:
                step_node.add(f"[red]Error: {step.error_message}[/red]")
            
            # Add inputs
            if show_inputs and step.inputs:
                inputs_node = step_node.add("[cyan]Inputs[/cyan]")
                self._add_dict_to_tree(inputs_node, step.inputs)
            
            # Add outputs
            if show_outputs and step.outputs:
                outputs_node = step_node.add("[green]Outputs[/green]")
                self._add_dict_to_tree(outputs_node, step.outputs)
            
            # Add metadata
            if show_metadata and step.metadata:
                metadata_node = step_node.add("[yellow]Metadata[/yellow]")
                self._add_dict_to_tree(metadata_node, step.metadata)
        
        self.console.print(tree)
    
    def print_step_analysis(self, tracer: DebugTracer, step_name: str):
        """Print analysis of specific step type.
        
        Args:
            tracer: DebugTracer containing trace data
            step_name: Name of step to analyze
        """
        steps = tracer.get_steps_by_name(step_name)
        
        if not steps:
            self.console.print(f"[yellow]No steps found with name: {step_name}[/yellow]")
            return
        
        self.console.print(f"\n[bold]Analysis of '{step_name}' steps:[/bold]\n")
        
        # Statistics
        total_duration = sum(s.duration or 0 for s in steps)
        avg_duration = total_duration / len(steps) if steps else 0
        success_count = len([s for s in steps if s.success])
        
        stats_text = f"""[bold]Count:[/bold] {len(steps)}
[bold]Success Rate:[/bold] {success_count}/{len(steps)} ({success_count/len(steps):.1%})
[bold]Total Duration:[/bold] {total_duration:.3f}s
[bold]Average Duration:[/bold] {avg_duration:.3f}s"""
        
        self.console.print(Panel(stats_text, title=f"{step_name} Statistics"))
        
        # Show each step
        for i, step in enumerate(steps):
            status = "✅" if step.success else "❌"
            duration = f" ({step.duration:.3f}s)" if step.duration else ""
            self.console.print(f"  {i+1}. {status} {step.step_id}{duration}")
            
            if not step.success and step.error_message:
                self.console.print(f"     [red]Error: {step.error_message}[/red]")
    
    def print_failed_steps(self, tracer: DebugTracer):
        """Print information about failed steps.
        
        Args:
            tracer: DebugTracer containing trace data
        """
        failed_steps = tracer.get_failed_steps()
        
        if not failed_steps:
            self.console.print("[green]No failed steps found![/green]")
            return
        
        self.console.print(f"\n[bold red]Failed Steps ({len(failed_steps)}):[/bold red]\n")
        
        for step in failed_steps:
            duration = f" ({step.duration:.3f}s)" if step.duration else ""
            
            panel_content = f"""[bold]Step:[/bold] {step.step_name}
[bold]Step ID:[/bold] {step.step_id}
[bold]Duration:[/bold] {duration.strip()}
[bold]Error:[/bold] {step.error_message or 'No error message'}"""
            
            if step.inputs:
                panel_content += f"\n[bold]Inputs:[/bold] {self._format_dict(step.inputs)}"
            
            self.console.print(Panel(panel_content, border_style="red"))
    
    def save_report(self, tracer: DebugTracer, output_path: Path,
                   format: str = "json"):
        """Save debug report to file.
        
        Args:
            tracer: DebugTracer containing trace data
            output_path: Path to save report
            format: Output format ('json', 'text', 'html')
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            self._save_json_report(tracer, output_path)
        elif format == "text":
            self._save_text_report(tracer, output_path)
        elif format == "html":
            self._save_html_report(tracer, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _add_dict_to_tree(self, node, data: Dict[str, Any], max_depth: int = 3):
        """Add dictionary data to tree node.
        
        Args:
            node: Tree node to add to
            data: Dictionary data to add
            max_depth: Maximum depth to traverse
        """
        if max_depth <= 0:
            node.add("[dim]...[/dim]")
            return
        
        for key, value in data.items():
            if isinstance(value, dict):
                sub_node = node.add(f"[bold]{key}[/bold]")
                self._add_dict_to_tree(sub_node, value, max_depth - 1)
            elif isinstance(value, list):
                if len(value) <= 5:
                    node.add(f"{key}: {value}")
                else:
                    node.add(f"{key}: [list with {len(value)} items]")
            else:
                # Truncate long strings
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                node.add(f"{key}: {value}")
    
    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary for display.
        
        Args:
            data: Dictionary to format
            
        Returns:
            Formatted string representation
        """
        try:
            return json.dumps(data, indent=2, default=str)[:200] + "..."
        except:
            return str(data)[:200] + "..."
    
    def _save_json_report(self, tracer: DebugTracer, output_path: Path):
        """Save trace as JSON report."""
        with open(output_path, 'w') as f:
            json.dump(tracer.get_full_trace(), f, indent=2, default=str)
    
    def _save_text_report(self, tracer: DebugTracer, output_path: Path):
        """Save trace as text report."""
        from io import StringIO
        
        # Capture console output to string
        string_console = Console(file=StringIO(), width=80)
        reporter = DebugReporter(string_console)
        
        reporter.print_trace_summary(tracer)
        string_console.print("\n" + "="*80 + "\n")
        reporter.print_detailed_trace(tracer)
        string_console.print("\n" + "="*80 + "\n")
        reporter.print_failed_steps(tracer)
        
        with open(output_path, 'w') as f:
            f.write(string_console.file.getvalue())
    
    def _save_html_report(self, tracer: DebugTracer, output_path: Path):
        """Save trace as HTML report."""
        from rich.console import Console
        from io import StringIO
        
        # Generate HTML using rich's HTML export
        string_file = StringIO()
        html_console = Console(file=string_file, record=True, width=120)
        reporter = DebugReporter(html_console)
        
        reporter.print_trace_summary(tracer)
        reporter.print_detailed_trace(tracer)
        reporter.print_failed_steps(tracer)
        
        html_content = html_console.export_html(inline_styles=True)
        
        with open(output_path, 'w') as f:
            f.write(html_content)