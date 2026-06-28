"""Fuzzy name matching utility.

Handles player name variations (e.g., "MS Dhoni" vs "M.S. Dhoni" vs
"Mahendra Singh Dhoni") using rapidfuzz for fast, accurate matching.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from loguru import logger


def _normalize_name(name: str) -> str:
    """Normalize a player name for comparison.

    - Lowercases
    - Removes dots, extra spaces
    - Strips honorifics / common prefixes
    """
    name = name.lower().strip()
    name = re.sub(r"\.", " ", name)       # M.S. -> M S
    name = re.sub(r"\s+", " ", name)      # collapse whitespace
    name = re.sub(r"\bjr\b\.?", "", name) # remove Jr.
    name = re.sub(r"\bsr\b\.?", "", name) # remove Sr.
    return name.strip()


class FuzzyMatcher:
    """Matches player names against a known roster using fuzzy matching."""

    def __init__(self, threshold: int = 80):
        """
        Args:
            threshold: Minimum similarity score (0-100) to consider a match.
        """
        self.threshold = threshold
        self._roster: Dict[str, str] = {}  # normalized_name -> canonical_name
        self._rapidfuzz_available = False

        try:
            import rapidfuzz  # noqa: F401
            self._rapidfuzz_available = True
        except ImportError:
            logger.warning(
                "rapidfuzz not installed — falling back to exact matching only. "
                "Install with: pip install rapidfuzz"
            )

    def load_roster(self, names: List[str]) -> None:
        """Load a list of canonical player names."""
        self._roster = {}
        for name in names:
            self._roster[_normalize_name(name)] = name

    def add_alias(self, canonical: str, alias: str) -> None:
        """Register an alias for a canonical name."""
        self._roster[_normalize_name(alias)] = canonical

    def match(self, query: str) -> Optional[Tuple[str, int]]:
        """Find the best matching name in the roster.

        Returns:
            Tuple of (canonical_name, score) or None if no match found.
        """
        normalized = _normalize_name(query)

        # Exact match first
        if normalized in self._roster:
            return self._roster[normalized], 100

        if not self._rapidfuzz_available or not self._roster:
            return None

        from rapidfuzz import fuzz, process

        choices = list(self._roster.keys())
        result = process.extractOne(
            normalized,
            choices,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=self.threshold,
        )

        if result:
            matched_key, score, _ = result
            canonical = self._roster[matched_key]
            logger.debug("Fuzzy matched '{}' -> '{}' (score: {})", query, canonical, score)
            return canonical, int(score)

        return None

    def match_or_original(self, query: str) -> str:
        """Return the matched canonical name, or the original if no match found."""
        result = self.match(query)
        return result[0] if result else query
