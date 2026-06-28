"""PostgreSQL Repository classes.

Provides data-access layer for all structured entities. Each repository wraps
SQLAlchemy operations behind a clean interface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .connection import get_session
from .db_models import (
    DatasetImport,
    Delivery,
    Match,
    MatchCondition,
    MatchSource,
    Player,
    PlayerAlias,
    PlayerAvailability,
    PlayerSource,
    PlayerStats,
    PlayingXI,
    ScrapeLog,
    Team,
    Venue,
)


# ===========================================================================
# Team Repository
# ===========================================================================

class TeamRepository:
    """CRUD operations for teams."""

    def get_by_code(self, code: str) -> Optional[Team]:
        with get_session() as session:
            return session.execute(
                select(Team).where(Team.team_code == code)
            ).scalar_one_or_none()

    def get_all(self) -> List[Team]:
        with get_session() as session:
            return list(session.execute(select(Team)).scalars().all())

    def upsert(self, code: str, name: str, **kwargs) -> Team:
        with get_session() as session:
            team = session.execute(
                select(Team).where(Team.team_code == code)
            ).scalar_one_or_none()
            if team:
                team.team_name = name
                for k, v in kwargs.items():
                    if hasattr(team, k):
                        setattr(team, k, v)
            else:
                team = Team(team_code=code, team_name=name, **kwargs)
                session.add(team)
            session.flush()
            team_id = team.team_id
            return team


# ===========================================================================
# Venue Repository
# ===========================================================================

class VenueRepository:
    """CRUD operations for venues."""

    def get_by_name(self, name: str) -> Optional[Venue]:
        with get_session() as session:
            return session.execute(
                select(Venue).where(Venue.venue_name == name)
            ).scalar_one_or_none()

    def get_all(self) -> List[Venue]:
        with get_session() as session:
            return list(session.execute(select(Venue)).scalars().all())

    def upsert(self, venue_name: str, city: str, **kwargs) -> Venue:
        with get_session() as session:
            venue = session.execute(
                select(Venue).where(Venue.venue_name == venue_name)
            ).scalar_one_or_none()
            if venue:
                venue.city = city
                for k, v in kwargs.items():
                    if hasattr(venue, k):
                        setattr(venue, k, v)
            else:
                venue = Venue(venue_name=venue_name, city=city, **kwargs)
                session.add(venue)
            session.flush()
            return venue


# ===========================================================================
# Player Repository
# ===========================================================================

class PlayerRepository:
    """CRUD operations for players."""

    def get_by_name(self, name: str) -> Optional[Player]:
        with get_session() as session:
            # Check full name first
            player = session.execute(
                select(Player).where(Player.full_name == name)
            ).scalar_one_or_none()
            if player:
                return player
            # Check aliases
            alias = session.execute(
                select(PlayerAlias).where(PlayerAlias.alias_name == name)
            ).scalar_one_or_none()
            if alias:
                return session.get(Player, alias.player_id)
            return None

    def get_by_source_id(self, source: str, source_id: str) -> Optional[Player]:
        with get_session() as session:
            player_source = session.execute(
                select(PlayerSource).where(
                    PlayerSource.source == source,
                    PlayerSource.source_id == source_id
                )
            ).scalar_one_or_none()
            if player_source:
                return session.get(Player, player_source.player_id)
            return None

    def get_all(self) -> List[Player]:
        with get_session() as session:
            return list(session.execute(select(Player)).scalars().all())

    def upsert(self, full_name: str, sources: Optional[Dict[str, str]] = None, **kwargs) -> Player:
        with get_session() as session:
            player = None
            sources = sources or {}
            
            # Try finding by sources first
            for src, src_id in sources.items():
                ps = session.execute(
                    select(PlayerSource).where(
                        PlayerSource.source == src,
                        PlayerSource.source_id == src_id
                    )
                ).scalar_one_or_none()
                if ps:
                    player = session.get(Player, ps.player_id)
                    break
            
            # Try finding by name next
            if not player:
                player = session.execute(
                    select(Player).where(Player.full_name == full_name)
                ).scalar_one_or_none()
                
            if player:
                for k, v in kwargs.items():
                    if v is not None and hasattr(player, k):
                        setattr(player, k, v)
                player.updated_at = datetime.utcnow()
            else:
                player = Player(full_name=full_name, **kwargs)
                session.add(player)
                session.flush()

            # Upsert sources
            for src, src_id in sources.items():
                ps = session.execute(
                    select(PlayerSource).where(
                        PlayerSource.player_id == player.player_id,
                        PlayerSource.source == src
                    )
                ).scalar_one_or_none()
                if ps:
                    ps.source_id = src_id
                else:
                    session.add(PlayerSource(player_id=player.player_id, source=src, source_id=src_id))
            
            session.flush()
            return player

    def add_alias(self, player_id: UUID, alias_name: str, source: str = "scraper") -> None:
        with get_session() as session:
            existing = session.execute(
                select(PlayerAlias).where(
                    PlayerAlias.player_id == player_id,
                    PlayerAlias.alias_name == alias_name,
                )
            ).scalar_one_or_none()
            if not existing:
                session.add(PlayerAlias(
                    player_id=player_id,
                    alias_name=alias_name,
                    source=source,
                ))


# ===========================================================================
# Dataset Imports Repository
# ===========================================================================

class DatasetImportRepository:
    def record_import(self, source: str, version: str, checksum: str) -> None:
        with get_session() as session:
            record = DatasetImport(
                source=source,
                dataset_version=version,
                sha256_checksum=checksum
            )
            session.add(record)
            session.commit()


# ===========================================================================
# Match Repository
# ===========================================================================

class MatchRepository:
    """CRUD operations for matches."""

    def get_by_id(self, match_id: UUID) -> Optional[Match]:
        with get_session() as session:
            return session.execute(
                select(Match).where(Match.match_id == match_id)
            ).scalar_one_or_none()

    def get_by_season(self, season: int) -> List[Match]:
        with get_session() as session:
            return list(
                session.execute(
                    select(Match).where(Match.season == season).order_by(Match.match_number)
                ).scalars().all()
            )

    def get_completed(self, season: Optional[int] = None) -> List[Match]:
        with get_session() as session:
            q = select(Match).where(Match.match_status == "complete")
            if season:
                q = q.where(Match.season == season)
            return list(session.execute(q.order_by(Match.match_date)).scalars().all())

    def _resolve_foreign_keys(self, session: Session, data: Dict[str, Any]) -> None:
        """Resolve string names to DB UUIDs."""
        # Teams
        for field, target in [
            ("team_a", "team_a_id"), ("team_b", "team_b_id"),
            ("toss_winner", "toss_winner_id"), ("winner", "winner_id")
        ]:
            if name := data.pop(field, None):
                team = session.execute(select(Team).where(Team.team_code == name)).scalar_one_or_none()
                if not team:
                    team = Team(team_code=name, team_name=name)
                    session.add(team)
                    session.flush()
                data[target] = team.team_id

        # Venue
        if venue_name := data.pop("venue_name", None):
            venue = session.execute(select(Venue).where(Venue.venue_name == venue_name)).scalar_one_or_none()
            if not venue:
                venue = Venue(venue_name=venue_name, city="Unknown")
                session.add(venue)
                session.flush()
            data["venue_id"] = venue.venue_id
            
        # Optional: POM
        data.pop("player_of_match", None)

    def upsert(self, data: Dict[str, Any]) -> Match:
        with get_session() as session:
            data = dict(data)
            sources = data.pop("sources", {})
            self._resolve_foreign_keys(session, data)
            
            match = None
            # Find by sources
            for src, src_id in sources.items():
                ms = session.execute(
                    select(MatchSource).where(
                        MatchSource.source == src,
                        MatchSource.source_id == src_id
                    )
                ).scalar_one_or_none()
                if ms:
                    match = session.get(Match, ms.match_id)
                    break
            
            # Find by season and match number
            if not match and data.get("season") and data.get("match_number"):
                match = session.execute(
                    select(Match).where(
                        Match.season == data["season"],
                        Match.match_number == data["match_number"]
                    )
                ).scalar_one_or_none()
                
            if match:
                for k, v in data.items():
                    if v is not None and hasattr(match, k):
                        setattr(match, k, v)
                match.updated_at = datetime.utcnow()
            else:
                match = Match(**data)
                session.add(match)
                session.flush()

            # Upsert sources
            for src, src_id in sources.items():
                ms = session.execute(
                    select(MatchSource).where(
                        MatchSource.match_id == match.match_id,
                        MatchSource.source == src
                    )
                ).scalar_one_or_none()
                if ms:
                    ms.source_id = src_id
                else:
                    session.add(MatchSource(match_id=match.match_id, source=src, source_id=src_id))

            session.flush()
            return match

    def bulk_upsert(self, matches: List[Dict[str, Any]]) -> int:
        count = 0
        for m in matches:
            self.upsert(m)
            count += 1
        logger.info("Upserted {} matches", count)
        return count


# ===========================================================================
# Delivery Repository
# ===========================================================================

class DeliveryRepository:
    """CRUD operations for ball-by-ball deliveries."""

    def get_by_match(self, match_id: UUID) -> List[Delivery]:
        with get_session() as session:
            return list(
                session.execute(
                    select(Delivery)
                    .where(Delivery.match_id == match_id)
                    .order_by(Delivery.innings, Delivery.over_number, Delivery.ball_number)
                ).scalars().all()
            )

    def bulk_insert(self, deliveries: List[Dict[str, Any]]) -> int:
        if not deliveries:
            return 0
        with get_session() as session:
            stmt = pg_insert(Delivery).values(deliveries)
            # Use on_conflict_do_nothing using the unique constraint (match_id, innings, over_number, ball_number)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=['match_id', 'innings', 'over_number', 'ball_number']
            )
            result = session.execute(stmt)
            count = result.rowcount
            logger.info("Inserted {} deliveries (ignored duplicates)", count)
            return count

    def count_by_match(self, match_id: UUID) -> int:
        with get_session() as session:
            from sqlalchemy import func
            result = session.execute(
                select(func.count()).select_from(Delivery).where(Delivery.match_id == match_id)
            ).scalar()
            return result or 0


# ===========================================================================
# Player Stats Repository
# ===========================================================================

class PlayerStatsRepository:
    """CRUD operations for season-wise player statistics."""

    def get_by_player_season(self, player_id: UUID, season: int) -> Optional[PlayerStats]:
        with get_session() as session:
            return session.execute(
                select(PlayerStats).where(
                    PlayerStats.player_id == player_id,
                    PlayerStats.season == season,
                )
            ).scalar_one_or_none()

    def upsert(self, data: Dict[str, Any]) -> PlayerStats:
        with get_session() as session:
            existing = None
            if data.get("player_id") and data.get("season"):
                existing = session.execute(
                    select(PlayerStats).where(
                        PlayerStats.player_id == data["player_id"],
                        PlayerStats.season == data["season"],
                    )
                ).scalar_one_or_none()
            if existing:
                for k, v in data.items():
                    if v is not None and hasattr(existing, k):
                        setattr(existing, k, v)
                existing.updated_at = datetime.utcnow()
                return existing
            else:
                stat = PlayerStats(**data)
                session.add(stat)
                session.flush()
                return stat


# ===========================================================================
# Scrape Log Repository
# ===========================================================================

class ScrapeLogRepository:
    """Audit trail for scraping operations."""

    def start_log(self, job_name: str, source: str) -> UUID:
        with get_session() as session:
            log = ScrapeLog(
                job_name=job_name,
                source=source,
                start_time=datetime.utcnow(),
                status="running",
            )
            session.add(log)
            session.flush()
            return log.log_id

    def finish_log(
        self,
        log_id: UUID,
        status: str = "success",
        records_fetched: int = 0,
        records_inserted: int = 0,
        records_updated: int = 0,
        records_failed: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        with get_session() as session:
            log = session.get(ScrapeLog, log_id)
            if log:
                log.end_time = datetime.utcnow()
                log.status = status
                log.records_fetched = records_fetched
                log.records_inserted = records_inserted
                log.records_updated = records_updated
                log.records_failed = records_failed
                log.error_message = error_message
