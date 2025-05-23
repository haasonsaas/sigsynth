"""Debug tracer for tracking rule processing steps.

This module provides detailed tracing of all steps in the rule processing pipeline,
from parsing through test generation and validation.
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TraceStep:
    """A single step in the processing trace."""
    step_id: str
    step_name: str
    timestamp: float
    duration: Optional[float]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class DebugTracer:
    """Traces rule processing steps for debugging and analysis."""
    
    def __init__(self, rule_id: str, enabled: bool = True):
        """Initialize debug tracer.
        
        Args:
            rule_id: Identifier for the rule being traced
            enabled: Whether tracing is enabled
        """
        self.rule_id = rule_id
        self.enabled = enabled
        self.steps: List[TraceStep] = []
        self.current_step: Optional[TraceStep] = None
        self.start_time = time.time()
    
    def start_step(self, step_name: str, inputs: Dict[str, Any] = None, 
                   metadata: Dict[str, Any] = None) -> str:
        """Start tracing a processing step.
        
        Args:
            step_name: Name of the step being traced
            inputs: Input data for this step
            metadata: Additional metadata about the step
            
        Returns:
            Step ID for referencing this step
        """
        if not self.enabled:
            return ""
        
        step_id = f"{self.rule_id}_{len(self.steps):03d}_{step_name}"
        
        self.current_step = TraceStep(
            step_id=step_id,
            step_name=step_name,
            timestamp=time.time(),
            duration=None,
            inputs=inputs or {},
            outputs={},
            metadata=metadata or {},
            success=False
        )
        
        return step_id
    
    def end_step(self, outputs: Dict[str, Any] = None, success: bool = True,
                error_message: str = None):
        """End the current tracing step.
        
        Args:
            outputs: Output data from this step
            success: Whether the step completed successfully
            error_message: Error message if step failed
        """
        if not self.enabled or not self.current_step:
            return
        
        self.current_step.duration = time.time() - self.current_step.timestamp
        self.current_step.outputs = outputs or {}
        self.current_step.success = success
        self.current_step.error_message = error_message
        
        self.steps.append(self.current_step)
        self.current_step = None
    
    def add_event(self, event_name: str, data: Dict[str, Any] = None):
        """Add a single event to the trace.
        
        Args:
            event_name: Name of the event
            data: Event data
        """
        if not self.enabled:
            return
        
        step_id = self.start_step(event_name, data)
        self.end_step({}, True)
    
    def get_trace_summary(self) -> Dict[str, Any]:
        """Get a summary of the trace.
        
        Returns:
            Trace summary with timing and success information
        """
        if not self.enabled:
            return {}
        
        total_duration = time.time() - self.start_time
        successful_steps = len([s for s in self.steps if s.success])
        failed_steps = len([s for s in self.steps if not s.success])
        
        return {
            "rule_id": self.rule_id,
            "total_duration": total_duration,
            "total_steps": len(self.steps),
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "success_rate": successful_steps / len(self.steps) if self.steps else 0,
            "step_timings": {
                step.step_name: step.duration 
                for step in self.steps if step.duration
            }
        }
    
    def get_full_trace(self) -> Dict[str, Any]:
        """Get the complete trace data.
        
        Returns:
            Complete trace including all steps and metadata
        """
        if not self.enabled:
            return {}
        
        return {
            "rule_id": self.rule_id,
            "trace_summary": self.get_trace_summary(),
            "steps": [asdict(step) for step in self.steps]
        }
    
    def save_trace(self, output_path: Path):
        """Save trace to file.
        
        Args:
            output_path: Path to save trace file
        """
        if not self.enabled:
            return
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.get_full_trace(), f, indent=2, default=str)
    
    def get_step_by_name(self, step_name: str) -> Optional[TraceStep]:
        """Get the first step with the given name.
        
        Args:
            step_name: Name of step to find
            
        Returns:
            TraceStep if found, None otherwise
        """
        for step in self.steps:
            if step.step_name == step_name:
                return step
        return None
    
    def get_steps_by_name(self, step_name: str) -> List[TraceStep]:
        """Get all steps with the given name.
        
        Args:
            step_name: Name of steps to find
            
        Returns:
            List of matching TraceSteps
        """
        return [step for step in self.steps if step.step_name == step_name]
    
    def get_failed_steps(self) -> List[TraceStep]:
        """Get all failed steps.
        
        Returns:
            List of failed TraceSteps
        """
        return [step for step in self.steps if not step.success]