"""Seed script — populates teams and venues with known IPL data.

Usage:
    python -m scripts.seed_teams_venues
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import load_config, setup_logging
from src.storage.connection import init_db, get_session
from src.storage.db_models import Team, Venue

# ===========================================================================
# IPL Teams Data
# ===========================================================================

TEAMS = [
    {"team_code": "CSK", "team_name": "Chennai Super Kings", "founded_year": 2008},
    {"team_code": "MI", "team_name": "Mumbai Indians", "founded_year": 2008},
    {"team_code": "RCB", "team_name": "Royal Challengers Bengaluru", "founded_year": 2008},
    {"team_code": "KKR", "team_name": "Kolkata Knight Riders", "founded_year": 2008},
    {"team_code": "SRH", "team_name": "Sunrisers Hyderabad", "founded_year": 2013},
    {"team_code": "DC", "team_name": "Delhi Capitals", "founded_year": 2008},
    {"team_code": "RR", "team_name": "Rajasthan Royals", "founded_year": 2008},
    {"team_code": "PBKS", "team_name": "Punjab Kings", "founded_year": 2008},
    {"team_code": "GT", "team_name": "Gujarat Titans", "founded_year": 2022},
    {"team_code": "LSG", "team_name": "Lucknow Super Giants", "founded_year": 2022},
    # Historical teams (defunct)
    {"team_code": "DCH", "team_name": "Deccan Chargers", "founded_year": 2008},
    {"team_code": "PWI", "team_name": "Pune Warriors India", "founded_year": 2011},
    {"team_code": "KTK", "team_name": "Kochi Tuskers Kerala", "founded_year": 2011},
    {"team_code": "GL", "team_name": "Gujarat Lions", "founded_year": 2016},
    {"team_code": "RPS", "team_name": "Rising Pune Supergiant", "founded_year": 2016},
]

# ===========================================================================
# IPL Venues Data
# ===========================================================================

VENUES = [
    {
        "venue_name": "M.A. Chidambaram Stadium",
        "city": "Chennai",
        "country": "India",
        "capacity": 38000,
        "pitch_type": "slow",
    },
    {
        "venue_name": "Wankhede Stadium",
        "city": "Mumbai",
        "country": "India",
        "capacity": 33000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "M. Chinnaswamy Stadium",
        "city": "Bengaluru",
        "country": "India",
        "capacity": 40000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "Eden Gardens",
        "city": "Kolkata",
        "country": "India",
        "capacity": 68000,
        "pitch_type": "sporting",
    },
    {
        "venue_name": "Rajiv Gandhi International Stadium",
        "city": "Hyderabad",
        "country": "India",
        "capacity": 55000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "Arun Jaitley Stadium",
        "city": "Delhi",
        "country": "India",
        "capacity": 41000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "Sawai Mansingh Stadium",
        "city": "Jaipur",
        "country": "India",
        "capacity": 30000,
        "pitch_type": "dusty",
    },
    {
        "venue_name": "IS Bindra Stadium",
        "city": "Mohali",
        "country": "India",
        "capacity": 26000,
        "pitch_type": "sporting",
    },
    {
        "venue_name": "Narendra Modi Stadium",
        "city": "Ahmedabad",
        "country": "India",
        "capacity": 132000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium",
        "city": "Lucknow",
        "country": "India",
        "capacity": 50000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "HPCA Stadium",
        "city": "Dharamsala",
        "country": "India",
        "capacity": 23000,
        "pitch_type": "green",
    },
    {
        "venue_name": "Barsapara Cricket Stadium",
        "city": "Guwahati",
        "country": "India",
        "capacity": 40000,
        "pitch_type": "sporting",
    },
    {
        "venue_name": "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium",
        "city": "Visakhapatnam",
        "country": "India",
        "capacity": 28000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "Maharashtra Cricket Association Stadium",
        "city": "Pune",
        "country": "India",
        "capacity": 37000,
        "pitch_type": "sporting",
    },
    {
        "venue_name": "JSCA International Stadium Complex",
        "city": "Ranchi",
        "country": "India",
        "capacity": 40000,
        "pitch_type": "slow",
    },
    {
        "venue_name": "Holkar Cricket Stadium",
        "city": "Indore",
        "country": "India",
        "capacity": 30000,
        "pitch_type": "flat",
    },
    {
        "venue_name": "Vidarbha Cricket Association Stadium",
        "city": "Nagpur",
        "country": "India",
        "capacity": 45000,
        "pitch_type": "slow",
    },
    # International venues used for IPL
    {
        "venue_name": "Dubai International Cricket Stadium",
        "city": "Dubai",
        "country": "UAE",
        "capacity": 25000,
        "pitch_type": "slow",
    },
    {
        "venue_name": "Sheikh Zayed Stadium",
        "city": "Abu Dhabi",
        "country": "UAE",
        "capacity": 20000,
        "pitch_type": "slow",
    },
    {
        "venue_name": "Sharjah Cricket Stadium",
        "city": "Sharjah",
        "country": "UAE",
        "capacity": 27000,
        "pitch_type": "flat",
    },
]

# Team-Venue mapping (home grounds)
TEAM_HOME_VENUES = {
    "CSK": "M.A. Chidambaram Stadium",
    "MI": "Wankhede Stadium",
    "RCB": "M. Chinnaswamy Stadium",
    "KKR": "Eden Gardens",
    "SRH": "Rajiv Gandhi International Stadium",
    "DC": "Arun Jaitley Stadium",
    "RR": "Sawai Mansingh Stadium",
    "PBKS": "IS Bindra Stadium",
    "GT": "Narendra Modi Stadium",
    "LSG": "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium",
}


def seed():
    """Seed the database with teams and venues."""
    from loguru import logger

    config = load_config()
    setup_logging(config)

    logger.info("Initializing database tables...")
    init_db()

    with get_session() as session:
        # Seed venues
        venue_map = {}
        for venue_data in VENUES:
            from sqlalchemy import select
            existing = session.execute(
                select(Venue).where(Venue.venue_name == venue_data["venue_name"])
            ).scalar_one_or_none()

            if existing:
                venue_map[venue_data["venue_name"]] = existing
                logger.debug("Venue exists: {}", venue_data["venue_name"])
            else:
                venue = Venue(**venue_data)
                session.add(venue)
                session.flush()
                venue_map[venue_data["venue_name"]] = venue
                logger.info("Created venue: {}", venue_data["venue_name"])

        # Seed teams
        for team_data in TEAMS:
            existing = session.execute(
                select(Team).where(Team.team_code == team_data["team_code"])
            ).scalar_one_or_none()

            if existing:
                logger.debug("Team exists: {}", team_data["team_code"])
                continue

            # Link home venue
            home_venue_name = TEAM_HOME_VENUES.get(team_data["team_code"])
            home_venue = venue_map.get(home_venue_name)

            team = Team(
                team_code=team_data["team_code"],
                team_name=team_data["team_name"],
                founded_year=team_data["founded_year"],
                home_venue_id=home_venue.venue_id if home_venue else None,
            )
            session.add(team)
            logger.info("Created team: {} ({})", team_data["team_code"], team_data["team_name"])

    logger.info("✅ Seed complete: {} teams, {} venues", len(TEAMS), len(VENUES))


if __name__ == "__main__":
    seed()
