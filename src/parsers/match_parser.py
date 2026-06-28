"""Unified match data parser.

Normalizes match data from different sources (ESPN, Cricbuzz, IPLT20)
into a consistent format matching the MatchCreate schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from ..models.match import MatchCreate

# Team name normalization map
TEAM_NAME_MAP = {
    # Full names
    "Chennai Super Kings": "CSK",
    "Mumbai Indians": "MI",
    "Royal Challengers Bengaluru": "RCB",
    "Royal Challengers Bangalore": "RCB",
    "Royal Challengers Bengaluru/Bangalore": "RCB",
    "Kolkata Knight Riders": "KKR",
    "Sunrisers Hyderabad": "SRH",
    "Delhi Capitals": "DC",
    "Delhi Daredevils": "DC",
    "Rajasthan Royals": "RR",
    "Punjab Kings": "PBKS",
    "Kings XI Punjab": "PBKS",
    "Gujarat Titans": "GT",
    "Lucknow Super Giants": "LSG",
    "Rising Pune Supergiant": "RPS",
    "Rising Pune Supergiants": "RPS",
    "Gujarat Lions": "GL",
    "Kochi Tuskers Kerala": "KTK",
    "Pune Warriors India": "PWI",
    "Pune Warriors": "PWI",
    "Deccan Chargers": "DCH",
    # Short codes map to themselves
    "CSK": "CSK", "MI": "MI", "RCB": "RCB", "KKR": "KKR",
    "SRH": "SRH", "DC": "DC", "RR": "RR", "PBKS": "PBKS",
    "GT": "GT", "LSG": "LSG",
}


def normalize_team_name(name: str) -> str:
    """Normalize team name to standard code."""
    name = name.strip()
    if name in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[name]
    # Try case-insensitive
    for key, code in TEAM_NAME_MAP.items():
        if key.lower() == name.lower():
            return code
    # Return as-is if unknown
    return name


def parse_match_date(date_str: str) -> datetime:
    """Parse various date formats into datetime."""
    if not date_str:
        return datetime(2000, 1, 1)

    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    logger.warning("Unable to parse date: {}", date_str)
    return datetime(2000, 1, 1)


def normalize_match_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw match data from any source into MatchCreate-compatible dict."""
    # Extract known IDs into sources dict if provided directly
    sources = raw.get("sources", {})
    if "cricsheet_id" in raw and raw["cricsheet_id"]: sources["cricsheet"] = raw["cricsheet_id"]
    if "espn_id" in raw and raw["espn_id"]: sources["espncricinfo"] = raw["espn_id"]
    if "espncricinfo_id" in raw and raw["espncricinfo_id"]: sources["espncricinfo"] = raw["espncricinfo_id"]
    if "cricbuzz_id" in raw and raw["cricbuzz_id"]: sources["cricbuzz"] = raw["cricbuzz_id"]
    if "iplt20_id" in raw and raw["iplt20_id"]: sources["iplt20"] = raw["iplt20_id"]

    normalized = {
        "sources": sources,
        "source": raw.get("source", "unknown"),
        "season": int(raw.get("season", 0)),
        "match_number": int(raw.get("match_number", 0)),
        "match_date": parse_match_date(str(raw.get("match_date", ""))),
        "venue_name": str(raw.get("venue_name", "Unknown")).strip(),
        "team_a": normalize_team_name(str(raw.get("team_a", ""))),
        "team_b": normalize_team_name(str(raw.get("team_b", ""))),
        "match_type": raw.get("match_type", "league"),
        "match_status": raw.get("match_status", "upcoming"),
        "dl_applied": raw.get("dl_applied", False),
    }

    # Optional fields
    if raw.get("toss_winner"):
        normalized["toss_winner"] = normalize_team_name(raw["toss_winner"])
    if raw.get("toss_decision"):
        normalized["toss_decision"] = raw["toss_decision"]
    if raw.get("winner"):
        normalized["winner"] = normalize_team_name(raw["winner"])
    if raw.get("win_margin") is not None:
        normalized["win_margin"] = int(raw["win_margin"])
    if raw.get("win_type"):
        normalized["win_type"] = raw["win_type"]
    if raw.get("player_of_match"):
        normalized["player_of_match"] = raw["player_of_match"]

    return normalized


def merge_match_sources(
    primary: List[Dict[str, Any]],
    fallback: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge match data from primary and fallback sources.

    Primary data takes precedence; fallback fills in gaps.
    """
    merged = {m.get("match_number", i): m for i, m in enumerate(primary)}

    for fb in fallback:
        key = fb.get("match_number", -1)
        if key not in merged:
            merged[key] = fb
        else:
            # Fill in missing fields from fallback
            for field, value in fb.items():
                if value and not merged[key].get(field):
                    merged[key][field] = value

    return list(merged.values())
