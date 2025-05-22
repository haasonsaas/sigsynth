"""Local expander module for generating test variants from seeds.

This module is responsible for taking seed log entries (both positive and negative)
and expanding them into multiple variants while preserving their trigger behavior.
The expander ensures that:
1. Positive variants always match the detection criteria
2. Negative variants never match the detection criteria
3. Non-critical fields are transformed to test edge cases
4. The ratio of positive/negative variants is maintained
"""

import random
import string
from typing import List, Dict, Any, Optional, Tuple
from copy import deepcopy
from sigsynth.validator import RuleValidator

class LocalExpander:
    """Generates test variants from seed log entries.
    
    The expander takes seed log entries and generates multiple variants by:
    1. Preserving critical fields for positive variants
    2. Breaking critical fields for negative variants
    3. Transforming non-critical fields to test edge cases
    4. Validating each variant to ensure correct trigger behavior
    """
    
    def __init__(self, random_seed: Optional[int] = None, detection_criteria: Optional[Dict[str, Any]] = None):
        """Initialize the expander.
        
        Args:
            random_seed: Optional seed for random number generation to ensure reproducibility
            detection_criteria: The detection criteria dict containing critical fields and their allowed values
        """
        if random_seed is not None:
            random.seed(random_seed)
        self.detection_criteria = detection_criteria or {}
        self.critical_fields = list(self.detection_criteria.keys())
        self.validator = RuleValidator(self.detection_criteria)
    
    def expand_seeds(
        self,
        positive_seeds: List[Dict[str, Any]],
        negative_seeds: List[Dict[str, Any]],
        target_samples: int
    ) -> List[Tuple[Dict[str, Any], bool]]:
        """Expand seeds to reach target number of samples.
        
        This method:
        1. Calculates the target number of positive/negative variants based on seed ratio
        2. Expands positive seeds into variants that should trigger the rule
        3. Expands negative seeds into variants that should not trigger the rule
        4. Combines and shuffles variants while maintaining the correct ratio
        5. Ensures we generate exactly the target number of samples
        
        Args:
            positive_seeds: List of positive seed log entries that should trigger the rule
            negative_seeds: List of negative seed log entries that should not trigger the rule
            target_samples: Total number of samples to generate
            
        Returns:
            List of (variant, should_trigger) tuples, where should_trigger indicates
            whether the variant should trigger the rule
        """
        variants = []
        total_seeds = len(positive_seeds) + len(negative_seeds)
        if total_seeds == 0:
            return []
            
        # Calculate target samples for each type based on seed ratio
        positive_ratio = len(positive_seeds) / total_seeds
        target_positive = int(target_samples * positive_ratio)
        target_negative = target_samples - target_positive
        
        # Expand positive seeds into variants that should trigger
        positive_variants = []
        for seed in positive_seeds:
            variants_from_seed = self._expand_seed(seed, target_positive // len(positive_seeds), should_trigger=True)
            positive_variants.extend(variants_from_seed)
            
        # Expand negative seeds into variants that should not trigger
        negative_variants = []
        for seed in negative_seeds:
            variants_from_seed = self._expand_seed(seed, target_negative // len(negative_seeds), should_trigger=False)
            negative_variants.extend(variants_from_seed)
            
        # Combine and shuffle variants while maintaining ratio
        variants = positive_variants + negative_variants
        random.shuffle(variants)
        
        # Ensure we have exactly the target number of samples
        if len(variants) > target_samples:
            variants = variants[:target_samples]
        elif len(variants) < target_samples:
            # If we don't have enough variants, try to generate more
            remaining = target_samples - len(variants)
            if remaining > 0:
                # Try to generate more variants from random seeds
                all_seeds = positive_seeds + negative_seeds
                for _ in range(remaining):
                    seed = random.choice(all_seeds)
                    should_trigger = seed in positive_seeds
                    new_variants = self._expand_seed(seed, 1, should_trigger)
                    if new_variants:
                        variants.extend(new_variants)
                        if len(variants) >= target_samples:
                            break
        
        return variants[:target_samples]
    
    def _expand_seed(
        self,
        seed: Dict[str, Any],
        num_variants: int,
        should_trigger: bool
    ) -> List[Tuple[Dict[str, Any], bool]]:
        """Expand a single seed into multiple variants.
        
        This method:
        1. Creates multiple variants from a single seed
        2. For positive variants: only transforms non-critical fields
        3. For negative variants: breaks at least one critical field
        4. Validates each variant to ensure correct trigger behavior
        5. Retries up to 5 times if validation fails
        
        Args:
            seed: Original log entry to expand
            num_variants: Number of variants to generate
            should_trigger: Whether variants should trigger the rule
            
        Returns:
            List of (variant, should_trigger) tuples
        """
        variants = []
        attempts_per_variant = 5
        
        for _ in range(num_variants):
            for attempt in range(attempts_per_variant):
                variant = deepcopy(seed)
                
                if should_trigger:
                    # For positive variants, only transform non-critical fields
                    # to ensure they still trigger the rule
                    self._transform_non_critical_fields(variant)
                else:
                    # For negative variants, always break at least one critical field
                    # to ensure they don't trigger the rule
                    self._break_critical_field(variant)
                    self._transform_non_critical_fields(variant)
                
                # Post-validate to ensure correct trigger behavior
                is_valid = self.validator.validate_entry(variant)
                if is_valid == should_trigger:
                    variants.append((variant, should_trigger))
                    break  # Accept this variant
                # else: try again
            # If after attempts we can't get a valid variant, skip
        return variants
    
    def _transform_non_critical_fields(self, log_entry: Dict[str, Any]):
        """Transform non-critical fields while preserving trigger behavior.
        
        This method applies random transformations to non-critical fields:
        1. Random casing changes (20% chance)
        2. Random noise addition (10% chance)
        3. Random field modifications (15% chance)
        
        Args:
            log_entry: Log entry to transform
        """
        for key, value in log_entry.items():
            if key in self.critical_fields:
                continue
            if isinstance(value, str):
                if random.random() < 0.2:
                    log_entry[key] = value.lower() if random.random() < 0.5 else value.upper()
                if random.random() < 0.1:
                    noise = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
                    log_entry[key] = f"{value}_{noise}"
                if random.random() < 0.15:
                    if "error" in value.lower():
                        log_entry[key] = f"ERROR_{value}"
                    elif "failed" in value.lower():
                        log_entry[key] = f"FAILED_{value}"
    
    def _break_critical_field(self, log_entry: Dict[str, Any]):
        """Break a critical field to ensure it cannot match the rule.
        
        This method:
        1. Picks a random critical field that exists in the log entry
        2. Changes its value to something not in the allowed set
        3. For list values: adds '_notallowed' and random digits
        4. For string values: adds '_notallowed'
        
        Args:
            log_entry: Log entry to modify
        """
        if not self.critical_fields:
            return
            
        # Pick a random critical field that exists in the log entry
        available_fields = [f for f in self.critical_fields if f in log_entry]
        if not available_fields:
            return
            
        field = random.choice(available_fields)
        allowed = self.detection_criteria[field]
        
        if isinstance(allowed, list):
            # Pick a value not in the list
            new_value = allowed[0] + "_notallowed"
            while new_value.lower() in [v.lower() for v in allowed]:
                new_value += str(random.randint(0,9))
            log_entry[field] = new_value
        elif isinstance(allowed, str):
            log_entry[field] = allowed + "_notallowed"
        else:
            log_entry[field] = "notallowed" 