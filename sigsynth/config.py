"""Configuration management for SigSynth.

This module provides configuration loading, validation, and default settings
for the SigSynth tool. Supports both file-based and command-line configuration.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class PlatformConfig(BaseModel):
    """Configuration for a specific platform."""
    name: str
    output_format: str
    template_path: Optional[Path] = None
    custom_options: Dict[str, Any] = Field(default_factory=dict)


class BatchConfig(BaseModel):
    """Configuration for batch processing."""
    input_patterns: List[str] = Field(default_factory=lambda: ["**/*.yml", "**/*.yaml"])
    exclude_patterns: List[str] = Field(default_factory=list)
    parallel_workers: int = 4
    fail_fast: bool = False


class DebugConfig(BaseModel):
    """Configuration for debug features."""
    enabled: bool = False
    verbose: bool = False
    trace_validation: bool = False
    output_dir: Optional[Path] = None


class SigSynthConfig(BaseModel):
    """Main configuration for SigSynth."""
    seed_samples: int = 5
    samples: int = 200
    random_seed: Optional[int] = None
    platforms: Dict[str, PlatformConfig] = Field(default_factory=dict)
    batch: BatchConfig = Field(default_factory=BatchConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)

    def __init__(self, **data):
        super().__init__(**data)
        # Ensure default platforms are available
        if not self.platforms:
            self.platforms = self._default_platforms()

    def _default_platforms(self) -> Dict[str, PlatformConfig]:
        """Get default platform configurations."""
        return {
            "panther": PlatformConfig(
                name="panther",
                output_format="json",
                custom_options={"test_prefix": "test_"}
            ),
            "splunk": PlatformConfig(
                name="splunk",
                output_format="spl",
                custom_options={"default_index": "main"}
            ),
            "elastic": PlatformConfig(
                name="elastic", 
                output_format="json",
                custom_options={"ecs_version": "8.0"}
            )
        }


def load_config(config_path: Optional[Path] = None) -> SigSynthConfig:
    """Load configuration from file or return defaults.
    
    Args:
        config_path: Path to configuration file. If None, looks for
                    sigsynth.yaml in current directory and user home.
    
    Returns:
        Loaded configuration
    """
    config_data = {}
    
    # Try to find config file if not provided
    if config_path is None:
        config_path = find_config_file()
    
    # Load config file if it exists
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Error loading config file {config_path}: {e}")
    
    # Override with environment variables
    config_data = merge_env_vars(config_data)
    
    return SigSynthConfig(**config_data)


def find_config_file() -> Optional[Path]:
    """Find configuration file in standard locations.
    
    Returns:
        Path to config file or None if not found
    """
    search_paths = [
        Path.cwd() / "sigsynth.yaml",
        Path.cwd() / "sigsynth.yml",
        Path.cwd() / ".sigsynth.yaml",
        Path.home() / ".sigsynth.yaml",
        Path.home() / ".config" / "sigsynth" / "config.yaml"
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    return None


def merge_env_vars(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge environment variables into configuration.
    
    Args:
        config_data: Base configuration data
        
    Returns:
        Configuration with environment variable overrides
    """
    # Map environment variables to config paths
    env_mappings = {
        "SIGSYNTH_SEED_SAMPLES": ["seed_samples", int],
        "SIGSYNTH_SAMPLES": ["samples", int],
        "SIGSYNTH_RANDOM_SEED": ["random_seed", int],
        "SIGSYNTH_PARALLEL_WORKERS": ["batch", "parallel_workers", int],
        "SIGSYNTH_DEBUG": ["debug", "enabled", bool],
        "SIGSYNTH_DEBUG_VERBOSE": ["debug", "verbose", bool],
    }
    
    for env_var, mapping_info in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            # Convert type (always the last element)
            type_func = mapping_info[-1]
            if type_func is bool:
                value = value.lower() in ("true", "1", "yes", "on")
            else:
                value = type_func(value)
            
            # Set nested value
            if len(mapping_info) == 3:  # [path, subpath, type]
                main_key, sub_key = mapping_info[0], mapping_info[1]
                if main_key not in config_data:
                    config_data[main_key] = {}
                config_data[main_key][sub_key] = value
            else:  # [path, type] or [path]
                config_data[mapping_info[0]] = value
    
    return config_data


def save_config(config: SigSynthConfig, config_path: Path) -> None:
    """Save configuration to file.
    
    Args:
        config: Configuration to save
        config_path: Path to save configuration
    """
    config_dict = config.model_dump(exclude_unset=True)
    
    # Convert Path objects to strings for YAML serialization
    def convert_paths(obj):
        if isinstance(obj, dict):
            return {k: convert_paths(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_paths(item) for item in obj]
        elif isinstance(obj, Path):
            return str(obj)
        return obj
    
    config_dict = convert_paths(config_dict)
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)