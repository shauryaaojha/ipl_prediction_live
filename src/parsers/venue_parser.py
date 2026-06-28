"""Venue data parser.

Normalizes venue metadata and computes derived metrics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def normalize_venue(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw venue record."""
    return {
        "venue_name": str(raw.get("venue_name", raw.get("name", "Unknown"))).strip(),
        "city": str(raw.get("city", "Unknown")).strip(),
        "country": raw.get("country", "India"),
        "capacity": raw.get("capacity"),
        "pitch_type": raw.get("pitch_type"),
        "espncricinfo_id": raw.get("espncricinfo_id"),
    }


def compute_venue_stats(
    venue_name: str, matches: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compute venue statistics from historical match data.

    Args:
        venue_name: Name of the venue.
        matches: List of completed match dicts with innings totals.

    Returns:
        Dict with avg_first_innings_score, avg_second_innings_score,
        chase_success_rate, etc.
    """
    first_totals = []
    second_totals = []
    chases_won = 0
    chases_total = 0

    for m in matches:
        inn1 = m.get("innings_1_total")
        inn2 = m.get("innings_2_total")

        if inn1 is not None:
            first_totals.append(float(inn1))
        if inn2 is not None:
            second_totals.append(float(inn2))

        # Chase success
        if m.get("win_type") == "wickets":
            chases_won += 1
            chases_total += 1
        elif m.get("win_type") == "runs":
            chases_total += 1

    return {
        "avg_first_innings_score": round(sum(first_totals) / len(first_totals), 2) if first_totals else None,
        "avg_second_innings_score": round(sum(second_totals) / len(second_totals), 2) if second_totals else None,
        "chase_success_rate": round(chases_won / chases_total, 4) if chases_total > 0 else None,
    }
