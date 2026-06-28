"""Parser for Cricsheet JSON files.

Extracts match metadata, player registries, and ball-by-ball deliveries
from the standard Cricsheet JSON format.
"""

from typing import Any, Dict, List, Tuple, Optional
from loguru import logger
from ..models.match import MatchCreate

class CricsheetParser:
    """Parses Cricsheet JSON into standardized schemas."""

    def __init__(self, season: int):
        self.season = season

    def parse(self, data: Dict[str, Any], match_id_str: str) -> Tuple[Optional[MatchCreate], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse a full Cricsheet match JSON.

        Returns:
            Tuple containing:
            - MatchCreate object (or None if season doesn't match)
            - List of Player dictionaries to upsert
            - List of Delivery dictionaries to insert
        """
        info = data.get("info", {})
        
        # Match season by checking the actual match date
        dates = info.get("dates", [""])
        match_year = dates[0][:4] if dates and dates[0] else ""
        if str(self.season) != match_year:
            return None, [], []

        # 1. Parse Registry (Players)
        players_to_upsert = []
        registry = info.get("registry", {}).get("people", {})
        for name, pid in registry.items():
            players_to_upsert.append({
                "full_name": name,
                "sources": {"cricsheet": pid}
            })

        # 2. Parse Match
        teams = info.get("teams", [])
        outcome = info.get("outcome", {})
        winner = outcome.get("winner", None)
        by = outcome.get("by", {})
        
        match_create = MatchCreate(
            sources={"cricsheet": match_id_str},
            source="cricsheet",
            season=self.season,
            match_number=info.get("match_type_number", 0),
            match_date=dates[0],
            venue_name=info.get("venue", ""),
            team_a=teams[0] if len(teams) > 0 else "Unknown",
            team_b=teams[1] if len(teams) > 1 else "Unknown",
            toss_winner=info.get("toss", {}).get("winner"),
            toss_decision=info.get("toss", {}).get("decision"),
            winner=winner,
            win_margin=by.get("runs", by.get("wickets")),
            win_type="runs" if "runs" in by else ("wickets" if "wickets" in by else None),
            match_status="complete" if winner else ("tied" if outcome.get("result") == "tie" else "abandoned"),
            match_type="league"
        )

        # 3. Parse Deliveries
        deliveries = []
        innings_list = data.get("innings", [])
        for inn_idx, innings_data in enumerate(innings_list):
            innings_num = inn_idx + 1
            batting_team = innings_data.get("team", "")
            bowling_team = teams[1] if batting_team == teams[0] else teams[0]
            
            overs = innings_data.get("overs", [])
            for over_data in overs:
                over_num = over_data.get("over", 0)
                for ball_idx, ball_data in enumerate(over_data.get("deliveries", [])):
                    ball_num = ball_idx + 1
                    
                    batter_name = ball_data.get("batter")
                    bowler_name = ball_data.get("bowler")
                    non_striker_name = ball_data.get("non_striker")
                    
                    runs_data = ball_data.get("runs", {})
                    extras_data = ball_data.get("extras", {})
                    
                    is_wicket = "wickets" in ball_data
                    wicket_type = None
                    player_dismissed_name = None
                    fielder_name = None
                    
                    if is_wicket:
                        wicket_info = ball_data["wickets"][0]
                        wicket_type = wicket_info.get("kind")
                        player_dismissed_name = wicket_info.get("player_out")
                        if "fielders" in wicket_info:
                            fielder_name = wicket_info["fielders"][0].get("name")
                    
                    # Extras type
                    extras_type = None
                    if extras_data:
                        if "wides" in extras_data: extras_type = "wide"
                        elif "noballs" in extras_data: extras_type = "noball"
                        elif "byes" in extras_data: extras_type = "bye"
                        elif "legbyes" in extras_data: extras_type = "legbye"
                        elif "penalty" in extras_data: extras_type = "penalty"

                    delivery = {
                        "innings": innings_num,
                        "over_number": over_num,
                        "ball_number": ball_num,
                        "batting_team": batting_team,
                        "bowling_team": bowling_team,
                        "batter_name": batter_name,
                        "bowler_name": bowler_name,
                        "non_striker_name": non_striker_name,
                        "batsman_runs": runs_data.get("batter", 0),
                        "extra_runs": runs_data.get("extras", 0),
                        "total_runs": runs_data.get("total", 0),
                        "extras_type": extras_type,
                        "is_wicket": is_wicket,
                        "wicket_type": wicket_type,
                        "player_dismissed_name": player_dismissed_name,
                        "fielder_name": fielder_name,
                        "source": "cricsheet"
                    }
                    deliveries.append(delivery)

        return match_create, players_to_upsert, deliveries
