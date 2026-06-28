"""Player data parser.

Normalizes player profiles and statistics from different sources.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger


def normalize_player(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw player record from any source."""
    return {
        "espncricinfo_id": raw.get("espncricinfo_id"),
        "cricbuzz_id": raw.get("cricbuzz_id"),
        "iplt20_id": raw.get("iplt20_id"),
        "full_name": str(raw.get("full_name", raw.get("name", ""))).strip(),
        "short_name": raw.get("short_name"),
        "batting_hand": _normalize_hand(raw.get("batting_hand", raw.get("battingStyle"))),
        "bowling_arm": _normalize_hand(raw.get("bowling_arm", raw.get("bowlingArm"))),
        "bowling_type": _normalize_bowling_type(raw.get("bowling_type", raw.get("bowlingType"))),
        "role": _normalize_role(raw.get("role", raw.get("playingRole", ""))),
        "nationality": raw.get("nationality", raw.get("country")),
        "date_of_birth": raw.get("date_of_birth", raw.get("dateOfBirth")),
        "debut_date": raw.get("debut_date"),
    }


def normalize_player_stats(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize player statistics."""
    return {
        "player_name": raw.get("player_name"),
        "season": int(raw.get("season", 0)),
        "team": raw.get("team"),
        "matches": int(raw.get("matches", raw.get("mat", 0))),
        "innings": int(raw.get("innings", raw.get("inns", 0))),
        "not_outs": int(raw.get("not_outs", raw.get("no", 0))),
        "runs": int(raw.get("runs", 0)),
        "balls_faced": int(raw.get("balls_faced", raw.get("bf", 0))),
        "highest_score": int(raw.get("highest_score", raw.get("hs", 0))),
        "hundreds": int(raw.get("hundreds", raw.get("100s", 0))),
        "fifties": int(raw.get("fifties", raw.get("50s", 0))),
        "fours": int(raw.get("fours", raw.get("4s", 0))),
        "sixes": int(raw.get("sixes", raw.get("6s", 0))),
        "ducks": int(raw.get("ducks", 0)),
        "batting_average": _safe_float(raw.get("batting_average", raw.get("ave"))),
        "batting_strike_rate": _safe_float(raw.get("batting_strike_rate", raw.get("sr"))),
        "wickets": int(raw.get("wickets", raw.get("wkts", 0))),
        "overs_bowled": _safe_float(raw.get("overs_bowled", raw.get("overs"))),
        "runs_conceded": int(raw.get("runs_conceded", 0)),
        "bowling_average": _safe_float(raw.get("bowling_average")),
        "bowling_economy": _safe_float(raw.get("bowling_economy", raw.get("econ"))),
        "bowling_strike_rate": _safe_float(raw.get("bowling_strike_rate")),
        "catches": int(raw.get("catches", raw.get("ct", 0))),
        "stumpings": int(raw.get("stumpings", raw.get("st", 0))),
    }


def _normalize_hand(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = str(val).lower()
    if "right" in val:
        return "right"
    elif "left" in val:
        return "left"
    return None


def _normalize_bowling_type(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = str(val).lower()
    if "spin" in val or "slow" in val:
        return "spin"
    elif "pace" in val or "fast" in val or "medium" in val:
        return "pace"
    return "none"


def _normalize_role(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = str(val).lower()
    if "wicket" in val and "bat" in val:
        return "wicketkeeper_batsman"
    elif "wicket" in val:
        return "wicketkeeper"
    elif "all" in val:
        return "all_rounder"
    elif "bat" in val:
        return "batsman"
    elif "bowl" in val:
        return "bowler"
    return None


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
