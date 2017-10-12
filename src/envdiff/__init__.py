"""Key-safe environment file comparison."""

from .api import (ComparisonError, ComparisonResult, Difference, Source,
                  TargetResult, compare_files, compare_mappings, result_document)

__version__ = "0.6.0"

__all__ = ["ComparisonError", "ComparisonResult", "Difference", "Source", "TargetResult",
           "compare_files", "compare_mappings", "result_document"]
