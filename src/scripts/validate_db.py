import logging
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session
from loguru import logger

from src.storage.db_models import engine
from src.storage.postgres_repo import get_session

logging.basicConfig(level=logging.INFO)

# Expected matches per season (based on historical facts)
EXPECTED_MATCHES = {
    2008: 58,
    2009: 57,
    2010: 60,
    2011: 73,
    2012: 74,
    2013: 76,
    2014: 60,
    2015: 59,
    2016: 60,
    2017: 59,
    2018: 60,
    2019: 60,
    2020: 60,
    2021: 60,
    2022: 74,
    2023: 74,
    2024: 74,
}

def check_orphaned_records(session: Session) -> bool:
    """Check for orphaned records that shouldn't exist."""
    passed = True
    
    # 1. Deliveries without a valid match
    result = session.execute(text("SELECT COUNT(*) FROM deliveries WHERE match_id NOT IN (SELECT match_id FROM matches)"))
    count = result.scalar()
    if count > 0:
        logger.error(f"Found {count} orphaned deliveries without a valid match.")
        passed = False
        
    # 2. Match sources without a valid match
    result = session.execute(text("SELECT COUNT(*) FROM match_sources WHERE match_id NOT IN (SELECT match_id FROM matches)"))
    count = result.scalar()
    if count > 0:
        logger.error(f"Found {count} orphaned match sources.")
        passed = False
        
    if passed:
        logger.success("No orphaned records found.")
        
    return passed

def check_duplicates(session: Session) -> bool:
    """Check for duplicate records."""
    passed = True
    
    # 1. Duplicate deliveries in the same match, inning, over, ball
    result = session.execute(text("""
        SELECT match_id, inning, over, ball, COUNT(*) 
        FROM deliveries 
        GROUP BY match_id, inning, over, ball 
        HAVING COUNT(*) > 1
    """))
    duplicates = result.fetchall()
    if duplicates:
        logger.error(f"Found {len(duplicates)} duplicate deliveries.")
        passed = False
        
    # 2. Duplicate matches per season/match_number
    result = session.execute(text("""
        SELECT season, match_number, COUNT(*)
        FROM matches
        WHERE match_number > 0
        GROUP BY season, match_number
        HAVING COUNT(*) > 1
    """))
    duplicates = result.fetchall()
    if duplicates:
        logger.error(f"Found {len(duplicates)} duplicate matches.")
        passed = False
        
    if passed:
        logger.success("No duplicates found.")
        
    return passed

def check_season_counts(session: Session) -> bool:
    """Check if the number of matches per season matches expectations."""
    passed = True
    
    result = session.execute(text("SELECT season, COUNT(*) FROM matches GROUP BY season ORDER BY season"))
    counts = dict(result.fetchall())
    
    for season, expected in EXPECTED_MATCHES.items():
        actual = counts.get(season, 0)
        # Note: sometimes a match is abandoned/no result, so counts might vary slightly.
        # But generally, Cricsheet has complete data for IPL.
        # In 2024, Cricsheet might only have 71 matches.
        if actual < expected * 0.9: # Allow 10% variance for missing/abandoned matches
            logger.warning(f"Season {season}: Expected ~{expected}, found {actual}")
            passed = False
        else:
            logger.info(f"Season {season}: Found {actual}/{expected} matches (OK)")
            
    if passed:
        logger.success("Season counts are within acceptable ranges.")
        
    return passed

def run_validation():
    logger.info("Starting database validation...")
    
    with get_session() as session:
        orphans_ok = check_orphaned_records(session)
        duplicates_ok = check_duplicates(session)
        counts_ok = check_season_counts(session)
        
    if orphans_ok and duplicates_ok and counts_ok:
        logger.success("Database validation passed! 🎉")
        sys.exit(0)
    else:
        logger.error("Database validation failed! ❌")
        sys.exit(1)

if __name__ == "__main__":
    run_validation()
