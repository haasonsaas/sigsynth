"""Local expander module for generating test variants from seeds."""

import random
import string
from typing import List, Dict, Any, Optional
from copy import deepcopy

class LocalExpander:
    """Generates test variants from seed log entries."""
    
    def __init__(self, random_seed: Optional[int] = None):
        """Initialize the expander.
        
        Args:
            random_seed: Optional seed for random number generation
        """
        if random_seed is not None:
            random.seed(random_seed)
    
    def expand_seeds(
        self,
        positive_seeds: List[Dict[str, Any]],
        negative_seeds: List[Dict[str, Any]],
        target_samples: int
    ) -> List[Dict[str, Any]]:
        """Expand seeds to reach target number of samples.
        
        Args:
            positive_seeds: List of positive seed log entries
            negative_seeds: List of negative seed log entries
            target_samples: Total number of samples to generate
            
        Returns:
            List of expanded test variants
        """
        variants = []
        
        # Calculate samples per seed
        samples_per_positive = target_samples // (2 * len(positive_seeds))
        samples_per_negative = target_samples // (2 * len(negative_seeds))
        
        # Expand positive seeds
        for seed in positive_seeds:
            variants.extend(self._expand_seed(seed, samples_per_positive, should_trigger=True))
            
        # Expand negative seeds
        for seed in negative_seeds:
            variants.extend(self._expand_seed(seed, samples_per_negative, should_trigger=False))
            
        # Shuffle variants
        random.shuffle(variants)
        
        return variants[:target_samples]
    
    def _expand_seed(
        self,
        seed: Dict[str, Any],
        num_variants: int,
        should_trigger: bool
    ) -> List[Dict[str, Any]]:
        """Expand a single seed into multiple variants.
        
        Args:
            seed: Original log entry
            num_variants: Number of variants to generate
            should_trigger: Whether variants should trigger the rule
            
        Returns:
            List of expanded variants
        """
        variants = []
        
        for _ in range(num_variants):
            variant = deepcopy(seed)
            
            # Apply random transformations
            if random.random() < 0.3:  # 30% chance to reorder fields
                self._reorder_fields(variant)
            
            if random.random() < 0.2:  # 20% chance to modify casing
                self._modify_casing(variant)
            
            if random.random() < 0.1:  # 10% chance to add noise
                self._add_noise(variant)
            
            if random.random() < 0.15:  # 15% chance to modify fields
                self._modify_fields(variant, should_trigger)
            
            variants.append(variant)
        
        return variants
    
    def _reorder_fields(self, log_entry: Dict[str, Any]) -> None:
        """Randomly reorder fields in the log entry."""
        fields = list(log_entry.items())
        random.shuffle(fields)
        log_entry.clear()
        log_entry.update(dict(fields))
    
    def _modify_casing(self, log_entry: Dict[str, Any]) -> None:
        """Randomly modify string field casing."""
        for key, value in log_entry.items():
            if isinstance(value, str):
                if random.random() < 0.5:
                    log_entry[key] = value.lower()
                else:
                    log_entry[key] = value.upper()
    
    def _add_noise(self, log_entry: Dict[str, Any]) -> None:
        """Add random noise to string fields."""
        for key, value in log_entry.items():
            if isinstance(value, str):
                if random.random() < 0.3:  # 30% chance to add noise
                    noise = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
                    log_entry[key] = f"{value}_{noise}"
    
    def _modify_fields(self, log_entry: Dict[str, Any], should_trigger: bool) -> None:
        """Modify field values while preserving trigger behavior."""
        for key, value in log_entry.items():
            if isinstance(value, str):
                if random.random() < 0.2:  # 20% chance to modify
                    if should_trigger:
                        # For positive cases, ensure modifications don't break trigger conditions
                        if "error" in value.lower():
                            log_entry[key] = f"ERROR_{value}"
                        elif "failed" in value.lower():
                            log_entry[key] = f"FAILED_{value}"
                    else:
                        # For negative cases, ensure modifications don't create trigger conditions
                        if "error" in value.lower():
                            log_entry[key] = value.replace("error", "info")
                        elif "failed" in value.lower():
                            log_entry[key] = value.replace("failed", "completed") 