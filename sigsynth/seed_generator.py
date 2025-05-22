"""AI seed generator module for creating test seeds using OpenAI."""

import os
from typing import List, Dict, Any, Tuple
from openai import OpenAI
from rich.console import Console
import json

console = Console()

class SeedGenerator:
    """Generates positive and negative test seeds using OpenAI."""
    
    def __init__(self, api_key: str = None):
        """Initialize the seed generator.
        
        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.client = OpenAI(api_key=self.api_key)

    def generate_seeds(
        self,
        rule_criteria: Dict[str, Any],
        num_seeds: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate positive and negative test seeds.
        
        Args:
            rule_criteria: Detection criteria from the Sigma rule
            num_seeds: Number of positive and negative seeds to generate
            
        Returns:
            Tuple of (positive_seeds, negative_seeds)
        """
        prompt = self._build_prompt(rule_criteria, num_seeds)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a security log expert. Generate realistic log entries that match or don't match the given detection criteria."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            console.print("[yellow]OpenAI raw response:[/yellow]")
            console.print(result)
            positive_seeds, negative_seeds = self._parse_response(result)
            
            return positive_seeds[:num_seeds], negative_seeds[:num_seeds]
            
        except Exception as e:
            console.print(f"[red]Error generating seeds: {e}[/red]")
            raise

    def _build_prompt(self, rule_criteria: Dict[str, Any], num_seeds: int) -> str:
        """Build the prompt for the OpenAI API.
        
        Args:
            rule_criteria: Detection criteria from the Sigma rule
            num_seeds: Number of seeds to generate
            
        Returns:
            Formatted prompt string
        """
        return f"""
You are a security log expert. Generate test log entries for a Sigma rule. STRICTLY FOLLOW THESE INSTRUCTIONS:

- Generate exactly {num_seeds} POSITIVE and {num_seeds} NEGATIVE log entries.
- Each entry must be a valid JSON object, using the EXACT field names and structure as in the detection criteria below.
- POSITIVE entries MUST match ALL detection criteria and would trigger the rule.
- NEGATIVE entries MUST NOT match ALL detection criteria and would NOT trigger the rule.
- Do NOT add any explanations, comments, or text outside the JSON arrays.
- Output ONLY the following format, with no extra text:

POSITIVE:
[
  {{ ... }},
  ...
]

NEGATIVE:
[
  {{ ... }},
  ...
]

Detection criteria (use these field names and structure):
{json.dumps(rule_criteria, indent=2)}

Example output:
POSITIVE:
[
  {{"eventName": "CreateTrail", "eventSource": "cloudtrail.amazonaws.com"}},
  ...
]
NEGATIVE:
[
  {{"eventName": "DescribeTrails", "eventSource": "cloudtrail.amazonaws.com"}},
  ...
]
"""

    def _parse_response(self, response: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse the OpenAI response into positive and negative seeds.
        
        Args:
            response: Raw response from OpenAI
            
        Returns:
            Tuple of (positive_seeds, negative_seeds)
        """
        try:
            # Split response into positive and negative sections
            sections = response.split("\n\n")
            positive_section = next(s for s in sections if s.startswith("POSITIVE:"))
            negative_section = next(s for s in sections if s.startswith("NEGATIVE:"))
            
            # Extract JSON arrays
            positive_json = positive_section.split("POSITIVE:")[1].strip()
            negative_json = negative_section.split("NEGATIVE:")[1].strip()
            
            positive_seeds = json.loads(positive_json)
            negative_seeds = json.loads(negative_json)
            
            return positive_seeds, negative_seeds
            
        except Exception as e:
            console.print(f"[red]Error parsing response: {e}[/red]")
            raise 