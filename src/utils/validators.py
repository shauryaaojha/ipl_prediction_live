"""Custom domain validation utilities.

Provides validators for cricket-specific data quality checks beyond what
Pydantic handles natively.
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger


def validate_delivery_consistency(deliveries: List[Dict[str, Any]]) -> List[str]:
    """Validate that delivery records are internally consistent.

    Checks:
    - Over numbers are in range 0-19
    - Ball numbers are in range 1-6 (plus extras)
    - Total runs = batsman_runs + extra_runs
    - Phase classification matches over number

    Returns:
        List of warning messages for inconsistencies.
    """
    warnings = []
    for i, d in enumerate(deliveries):
        over = d.get("over_number", -1)
        ball = d.get("ball_number", -1)
        bat_runs = d.get("batsman_runs", 0)
        extra_runs = d.get("extra_runs", 0)
        total = d.get("total_runs", 0)

        if not (0 <= over <= 19):
            warnings.append(f"Delivery {i}: over_number {over} out of range [0,19]")

        if not (1 <= ball <= 10):
            warnings.append(f"Delivery {i}: ball_number {ball} out of range [1,10]")

        if bat_runs + extra_runs != total:
            warnings.append(
                f"Delivery {i}: runs mismatch: {bat_runs} + {extra_runs} != {total}"
            )

        phase = d.get("match_phase")
        if phase:
            expected = _expected_phase(over)
            if phase != expected:
                warnings.append(
                    f"Delivery {i}: phase '{phase}' doesn't match over {over} "
                    f"(expected '{expected}')"
                )

    return warnings


def validate_match_scorecard(
    match_data: Dict[str, Any],
    deliveries: List[Dict[str, Any]],
) -> List[str]:
    """Cross-validate match totals against delivery-level data.

    Checks that the sum of delivery runs matches the match score.
    """
    warnings = []

    for innings in [1, 2]:
        inn_deliveries = [d for d in deliveries if d.get("innings") == innings]
        if not inn_deliveries:
            continue

        total_from_deliveries = sum(d.get("total_runs", 0) for d in inn_deliveries)

        # If match data has innings totals, compare
        innings_key = f"innings_{innings}_total"
        if innings_key in match_data:
            match_total = match_data[innings_key]
            if total_from_deliveries != match_total:
                warnings.append(
                    f"Innings {innings}: delivery sum ({total_from_deliveries}) "
                    f"!= match total ({match_total})"
                )

    return warnings


def validate_playing_xi(players: List[Dict[str, Any]]) -> List[str]:
    """Validate a Playing XI squad.

    Checks:
    - Exactly 11 players (or 12 with impact sub)
    - Exactly 1 captain
    - At least 1 wicketkeeper
    """
    warnings = []

    regular = [p for p in players if not p.get("is_impact_sub")]
    impact = [p for p in players if p.get("is_impact_sub")]

    if len(regular) != 11:
        warnings.append(f"Expected 11 regular players, got {len(regular)}")

    captains = [p for p in players if p.get("is_captain")]
    if len(captains) != 1:
        warnings.append(f"Expected 1 captain, got {len(captains)}")

    keepers = [p for p in players if p.get("is_wicketkeeper")]
    if len(keepers) < 1:
        warnings.append("No wicketkeeper found in playing XI")

    return warnings


def validate_player_stats(stats: Dict[str, Any]) -> List[str]:
    """Validate player statistics for sanity."""
    warnings = []

    runs = stats.get("runs", 0)
    innings = stats.get("innings", 0)
    not_outs = stats.get("not_outs", 0)
    avg = stats.get("batting_average")

    # Check batting average calculation
    if innings > 0 and (innings - not_outs) > 0 and avg is not None:
        expected_avg = runs / (innings - not_outs)
        if abs(avg - expected_avg) > 0.5:
            warnings.append(
                f"Batting average mismatch: reported {avg:.2f}, "
                f"calculated {expected_avg:.2f}"
            )

    # Check strike rate sanity
    sr = stats.get("batting_strike_rate")
    if sr is not None and sr > 400:
        warnings.append(f"Unusually high strike rate: {sr}")

    balls = stats.get("balls_faced", 0)
    if sr is not None and balls > 0:
        expected_sr = (runs / balls) * 100
        if abs(sr - expected_sr) > 1:
            warnings.append(
                f"Strike rate mismatch: reported {sr:.2f}, "
                f"calculated {expected_sr:.2f}"
            )

    return warnings


def _expected_phase(over: int) -> str:
    """Return expected match phase for a given over number."""
    if over <= 5:
        return "powerplay"
    elif over <= 14:
        return "middle"
    else:
        return "death"
