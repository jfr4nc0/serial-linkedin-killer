"""Text diversity calculation and validation for content variant generation.

The >70% diversity requirement helps prevent LinkedIn spam detection by ensuring
that multiple posts from the same campaign are sufficiently distinct. This is
especially important when publishing multiple variants in a short timeframe.

Diversity is calculated using Python's difflib.SequenceMatcher with a simple
ratio metric: diversity = 1.0 - similarity. A diversity of 0.0 means texts are
identical, while 1.0 means they are completely different.
"""

import difflib
from itertools import combinations
from typing import List, Tuple


def calculate_text_diversity(text_a: str, text_b: str) -> float:
    """Calculate diversity score between two text strings.

    Args:
        text_a: First text string
        text_b: Second text string

    Returns:
        Float between 0.0 (identical) and 1.0 (completely different)
    """
    # Normalize texts: lowercase and strip whitespace
    normalized_a = text_a.lower().strip()
    normalized_b = text_b.lower().strip()

    # Calculate similarity ratio using difflib
    similarity = difflib.SequenceMatcher(None, normalized_a, normalized_b).ratio()

    # Convert similarity to diversity (inverse)
    diversity = 1.0 - similarity

    return diversity


def validate_diversity(texts: List[str], threshold: float = 0.7) -> dict:
    """Validate that all text pairs meet minimum diversity threshold.

    Args:
        texts: List of text strings to validate
        threshold: Minimum diversity score required (default 0.7 = 70%)

    Returns:
        Dict with:
        - passed: bool - True if ALL pairs meet threshold
        - min_diversity: float - Lowest diversity score found
        - failing_pairs: list[tuple[int, int, float]] - Pairs below threshold
        - pair_count: int - Total number of pairs checked
    """
    if len(texts) < 2:
        return {
            "passed": True,
            "min_diversity": 1.0,
            "failing_pairs": [],
            "pair_count": 0,
        }

    failing_pairs: List[Tuple[int, int, float]] = []
    min_diversity = 1.0
    pair_count = 0

    # Check all pairwise combinations
    for idx_a, idx_b in combinations(range(len(texts)), 2):
        diversity = calculate_text_diversity(texts[idx_a], texts[idx_b])
        pair_count += 1

        # Track minimum diversity
        if diversity < min_diversity:
            min_diversity = diversity

        # Record failing pairs
        if diversity < threshold:
            failing_pairs.append((idx_a, idx_b, diversity))

    passed = len(failing_pairs) == 0

    return {
        "passed": passed,
        "min_diversity": min_diversity,
        "failing_pairs": failing_pairs,
        "pair_count": pair_count,
    }
