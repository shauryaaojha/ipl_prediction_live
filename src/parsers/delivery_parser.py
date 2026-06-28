"""Ball-by-ball delivery parser.

Normalizes delivery data and enriches with phase classification
and derived fields.
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger


def classify_phase(over: int) -> str:
    """Classify over number into match phase."""
    if over <= 5:
        return "powerplay"
    elif over <= 14:
        return "middle"
    return "death"


def normalize_delivery(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw delivery record."""
    over = int(raw.get("over_number", 0))

    return {
        "match_id": raw.get("match_id"),
        "innings": int(raw.get("innings", 1)),
        "over_number": over,
        "ball_number": int(raw.get("ball_number", 1)),
        "batting_team": raw.get("batting_team"),
        "bowling_team": raw.get("bowling_team"),
        "batsman": str(raw.get("batsman", "")).strip(),
        "non_striker": str(raw.get("non_striker", "")).strip() if raw.get("non_striker") else None,
        "bowler": str(raw.get("bowler", "")).strip(),
        "batsman_runs": int(raw.get("batsman_runs", 0)),
        "extra_runs": int(raw.get("extra_runs", 0)),
        "total_runs": int(raw.get("total_runs", 0)),
        "extras_type": raw.get("extras_type"),
        "is_wicket": bool(raw.get("is_wicket", False)),
        "wicket_type": raw.get("wicket_type"),
        "player_dismissed": raw.get("player_dismissed"),
        "fielder": raw.get("fielder"),
        "match_phase": raw.get("match_phase") or classify_phase(over),
        "source": raw.get("source", "unknown"),
    }


def normalize_deliveries(raw_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize a list of delivery records."""
    return [normalize_delivery(d) for d in raw_list]


def compute_innings_summary(deliveries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics from delivery-level data."""
    total_runs = sum(d.get("total_runs", 0) for d in deliveries)
    wickets = sum(1 for d in deliveries if d.get("is_wicket", False))
    legal_balls = sum(1 for d in deliveries if not d.get("extras_type") or d.get("extras_type") not in ("wide", "noball"))
    overs = legal_balls / 6

    boundaries = sum(1 for d in deliveries if d.get("batsman_runs", 0) == 4)
    sixes = sum(1 for d in deliveries if d.get("batsman_runs", 0) == 6)
    dots = sum(1 for d in deliveries if d.get("total_runs", 0) == 0 and not d.get("extras_type"))

    return {
        "total_runs": total_runs,
        "wickets": wickets,
        "overs": round(overs, 1),
        "legal_balls": legal_balls,
        "boundaries": boundaries,
        "sixes": sixes,
        "dot_balls": dots,
        "run_rate": round(total_runs / overs, 2) if overs > 0 else 0,
        "boundary_runs": (boundaries * 4) + (sixes * 6),
    }
