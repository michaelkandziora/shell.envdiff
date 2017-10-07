"""Key-safe environment file comparison."""

from .api import ComparisonResult, Difference, Source, TargetResult, compare_mappings

__version__ = "0.6.0"

__all__ = ["ComparisonResult", "Difference", "Source", "TargetResult",
           "compare_mappings"]
