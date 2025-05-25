"""Platform support for SigSynth.

This package provides platform-specific formatters for different SIEM/security platforms.
Each platform implements the BasePlatform interface to ensure consistent functionality.
"""

from .base import BasePlatform
from .panther import PantherPlatform
from .splunk import SplunkPlatform
from .elastic import ElasticPlatform

# Registry of available platforms
PLATFORMS = {
    "panther": PantherPlatform,
    "splunk": SplunkPlatform,
    "elastic": ElasticPlatform,
}

def get_platform(name: str) -> BasePlatform:
    """Get platform instance by name.
    
    Args:
        name: Platform name (e.g., 'panther', 'splunk')
        
    Returns:
        Platform instance
        
    Raises:
        ValueError: If platform is not supported
    """
    if name not in PLATFORMS:
        available = ", ".join(PLATFORMS.keys())
        raise ValueError(f"Platform '{name}' not supported. Available: {available}")
    
    return PLATFORMS[name]()

def list_platforms() -> list[str]:
    """Get list of supported platform names."""
    return list(PLATFORMS.keys())