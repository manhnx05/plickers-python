"""
Math utility functions for Plickers system.
"""

from scipy import stats
from typing import List, Any
import numpy as np


class Math:
    """Mathematical utility functions."""

    @staticmethod
    def mode(arr: List[Any]) -> List[int]:
        """
        Calculate mode (most frequent value) of an array.

        Args:
            arr: Input array or list

        Returns:
            List containing the mode value as integer
        """
        mode_result = stats.mode(arr, keepdims=False)
        return [int(mode_result.mode)]
