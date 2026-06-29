-- ============================================
-- IPL Data Platform — Analytics Warehouse
-- ============================================
-- Creates materialized views, star schema dimensions, and fact views.
-- Run after historical data is fully loaded.
--
-- Usage:
--   psql -U ipl_user -d ipl2026 -f scripts/analytics_views.sql
--   docker compose exec postgres psql -U ipl_user -d ipl2026 -f /tmp/analytics_views.sql


-- ============================================
-- 1. BATTING CAREER STATS (Materialized View)
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS mv_batting_career_stats CASCADE;

CREATE MATERIALIZED VIEW mv_batting_career_stats AS
SELECT
    d.batsman_id,
    p.full_name,
    COUNT(DISTINCT d.match_id)                                    AS matches,
    COUNT(DISTINCT (d.match_id, d.innings))                       AS innings,
    SUM(d.batsman_runs)                                           AS total_runs,
    SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END)
                                                                  AS balls_faced,
    MAX(sub.innings_runs)                                         AS highest_score,
    SUM(CASE WHEN d.batsman_runs = 4 THEN 1 ELSE 0 END)          AS fours,
    SUM(CASE WHEN d.batsman_runs = 6 THEN 1 ELSE 0 END)          AS sixes,
    SUM(CASE WHEN d.batsman_runs = 0
              AND (d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball'))
         THEN 1 ELSE 0 END)                                      AS dot_balls,
    SUM(CASE WHEN d.is_wicket = TRUE
              AND d.player_dismissed_id = d.batsman_id
         THEN 1 ELSE 0 END)                                      AS dismissals,
    -- Derived metrics computed in query for accuracy
    CASE
        WHEN SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            SUM(d.batsman_runs)::NUMERIC * 100.0 /
            NULLIF(SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END), 0),
            2
        )
        ELSE 0
    END                                                           AS strike_rate,
    CASE
        WHEN (COUNT(DISTINCT (d.match_id, d.innings)) -
              SUM(CASE WHEN d.is_wicket = TRUE AND d.player_dismissed_id = d.batsman_id THEN 1 ELSE 0 END)) > 0
        THEN ROUND(
            SUM(d.batsman_runs)::NUMERIC /
            NULLIF(
                COUNT(DISTINCT (d.match_id, d.innings)) -
                SUM(CASE WHEN d.is_wicket = TRUE AND d.player_dismissed_id = d.batsman_id THEN 1 ELSE 0 END),
                0
            ),
            2
        )
        ELSE NULL
    END                                                           AS batting_average,
    ROUND(
        SUM(CASE WHEN d.batsman_runs IN (4, 6) THEN 1 ELSE 0 END)::NUMERIC * 100.0 /
        NULLIF(SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END), 0),
        2
    )                                                             AS boundary_percentage
FROM deliveries d
JOIN players p ON d.batsman_id = p.player_id
LEFT JOIN LATERAL (
    SELECT SUM(d2.batsman_runs) AS innings_runs
    FROM deliveries d2
    WHERE d2.batsman_id = d.batsman_id
      AND d2.match_id = d.match_id
      AND d2.innings = d.innings
) sub ON TRUE
WHERE d.batsman_id IS NOT NULL
GROUP BY d.batsman_id, p.full_name;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_batting_career_player
    ON mv_batting_career_stats (batsman_id);


-- ============================================
-- 2. BOWLING CAREER STATS (Materialized View)
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS mv_bowling_career_stats CASCADE;

CREATE MATERIALIZED VIEW mv_bowling_career_stats AS
SELECT
    d.bowler_id,
    p.full_name,
    COUNT(DISTINCT d.match_id)                                     AS matches,
    COUNT(DISTINCT (d.match_id, d.innings))                        AS innings,
    -- Overs: count legal deliveries, divide by 6
    ROUND(
        SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END)::NUMERIC / 6,
        1
    )                                                              AS overs_bowled,
    SUM(d.total_runs)                                              AS runs_conceded,
    SUM(CASE WHEN d.is_wicket = TRUE
              AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
         THEN 1 ELSE 0 END)                                       AS wickets,
    SUM(CASE WHEN d.batsman_runs = 0
              AND d.extra_runs = 0
         THEN 1 ELSE 0 END)                                       AS dot_balls,
    SUM(CASE WHEN d.batsman_runs IN (4, 6) THEN 1 ELSE 0 END)     AS boundaries_conceded,
    -- Economy Rate
    CASE
        WHEN SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            SUM(d.total_runs)::NUMERIC * 6.0 /
            NULLIF(SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END), 0),
            2
        )
        ELSE NULL
    END                                                            AS economy_rate,
    -- Bowling Average
    CASE
        WHEN SUM(CASE WHEN d.is_wicket = TRUE
                       AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                  THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            SUM(d.total_runs)::NUMERIC /
            NULLIF(SUM(CASE WHEN d.is_wicket = TRUE
                              AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                         THEN 1 ELSE 0 END), 0),
            2
        )
        ELSE NULL
    END                                                            AS bowling_average,
    -- Bowling Strike Rate
    CASE
        WHEN SUM(CASE WHEN d.is_wicket = TRUE
                       AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                  THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END)::NUMERIC /
            NULLIF(SUM(CASE WHEN d.is_wicket = TRUE
                              AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                         THEN 1 ELSE 0 END), 0),
            2
        )
        ELSE NULL
    END                                                            AS bowling_strike_rate,
    -- Dot Ball Percentage
    ROUND(
        SUM(CASE WHEN d.batsman_runs = 0 AND d.extra_runs = 0 THEN 1 ELSE 0 END)::NUMERIC * 100.0 /
        NULLIF(SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END), 0),
        2
    )                                                              AS dot_ball_percentage
FROM deliveries d
JOIN players p ON d.bowler_id = p.player_id
WHERE d.bowler_id IS NOT NULL
GROUP BY d.bowler_id, p.full_name;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_bowling_career_player
    ON mv_bowling_career_stats (bowler_id);


-- ============================================
-- 3. BATTING SEASON STATS (Materialized View)
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS mv_batting_season_stats CASCADE;

CREATE MATERIALIZED VIEW mv_batting_season_stats AS
SELECT
    d.batsman_id,
    p.full_name,
    m.season,
    COUNT(DISTINCT d.match_id)                                     AS matches,
    COUNT(DISTINCT (d.match_id, d.innings))                        AS innings,
    SUM(d.batsman_runs)                                            AS total_runs,
    SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END)
                                                                   AS balls_faced,
    SUM(CASE WHEN d.batsman_runs = 4 THEN 1 ELSE 0 END)           AS fours,
    SUM(CASE WHEN d.batsman_runs = 6 THEN 1 ELSE 0 END)           AS sixes,
    SUM(CASE WHEN d.is_wicket = TRUE AND d.player_dismissed_id = d.batsman_id THEN 1 ELSE 0 END)
                                                                   AS dismissals,
    CASE
        WHEN SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            SUM(d.batsman_runs)::NUMERIC * 100.0 /
            NULLIF(SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END), 0),
            2
        )
        ELSE 0
    END                                                            AS strike_rate,
    CASE
        WHEN (COUNT(DISTINCT (d.match_id, d.innings)) -
              SUM(CASE WHEN d.is_wicket = TRUE AND d.player_dismissed_id = d.batsman_id THEN 1 ELSE 0 END)) > 0
        THEN ROUND(
            SUM(d.batsman_runs)::NUMERIC /
            NULLIF(
                COUNT(DISTINCT (d.match_id, d.innings)) -
                SUM(CASE WHEN d.is_wicket = TRUE AND d.player_dismissed_id = d.batsman_id THEN 1 ELSE 0 END),
                0
            ),
            2
        )
        ELSE NULL
    END                                                            AS batting_average
FROM deliveries d
JOIN players p ON d.batsman_id = p.player_id
JOIN matches m ON d.match_id = m.match_id
WHERE d.batsman_id IS NOT NULL
GROUP BY d.batsman_id, p.full_name, m.season;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_batting_season
    ON mv_batting_season_stats (batsman_id, season);


-- ============================================
-- 4. BOWLING SEASON STATS (Materialized View)
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS mv_bowling_season_stats CASCADE;

CREATE MATERIALIZED VIEW mv_bowling_season_stats AS
SELECT
    d.bowler_id,
    p.full_name,
    m.season,
    COUNT(DISTINCT d.match_id)                                     AS matches,
    COUNT(DISTINCT (d.match_id, d.innings))                        AS innings,
    ROUND(
        SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END)::NUMERIC / 6,
        1
    )                                                              AS overs_bowled,
    SUM(d.total_runs)                                              AS runs_conceded,
    SUM(CASE WHEN d.is_wicket = TRUE
              AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
         THEN 1 ELSE 0 END)                                       AS wickets,
    SUM(CASE WHEN d.batsman_runs = 0 AND d.extra_runs = 0 THEN 1 ELSE 0 END)
                                                                   AS dot_balls,
    CASE
        WHEN SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            SUM(d.total_runs)::NUMERIC * 6.0 /
            NULLIF(SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END), 0),
            2
        )
        ELSE NULL
    END                                                            AS economy_rate,
    CASE
        WHEN SUM(CASE WHEN d.is_wicket = TRUE
                       AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                  THEN 1 ELSE 0 END) > 0
        THEN ROUND(
            SUM(d.total_runs)::NUMERIC /
            NULLIF(SUM(CASE WHEN d.is_wicket = TRUE
                              AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                         THEN 1 ELSE 0 END), 0),
            2
        )
        ELSE NULL
    END                                                            AS bowling_average
FROM deliveries d
JOIN players p ON d.bowler_id = p.player_id
JOIN matches m ON d.match_id = m.match_id
WHERE d.bowler_id IS NOT NULL
GROUP BY d.bowler_id, p.full_name, m.season;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_bowling_season
    ON mv_bowling_season_stats (bowler_id, season);


-- ============================================
-- 5. VENUE STATS (Materialized View)
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS mv_venue_stats CASCADE;

CREATE MATERIALIZED VIEW mv_venue_stats AS
WITH innings_totals AS (
    SELECT
        m.venue_id,
        m.match_id,
        d.innings,
        SUM(d.total_runs) AS innings_total,
        SUM(CASE WHEN d.batsman_runs IN (4, 6) THEN 1 ELSE 0 END) AS boundaries,
        SUM(CASE WHEN d.is_wicket = TRUE THEN 1 ELSE 0 END) AS wickets
    FROM deliveries d
    JOIN matches m ON d.match_id = m.match_id
    WHERE m.venue_id IS NOT NULL
    GROUP BY m.venue_id, m.match_id, d.innings
),
first_innings AS (
    SELECT venue_id, AVG(innings_total) AS avg_score, AVG(boundaries) AS avg_boundaries, AVG(wickets) AS avg_wickets
    FROM innings_totals WHERE innings = 1
    GROUP BY venue_id
),
second_innings AS (
    SELECT venue_id, AVG(innings_total) AS avg_score, AVG(boundaries) AS avg_boundaries
    FROM innings_totals WHERE innings = 2
    GROUP BY venue_id
),
chase_results AS (
    SELECT
        m.venue_id,
        COUNT(*) AS total_chases,
        SUM(CASE WHEN m.win_type = 'wickets' THEN 1 ELSE 0 END) AS chases_won
    FROM matches m
    WHERE m.venue_id IS NOT NULL
      AND m.match_status = 'complete'
      AND m.win_type IN ('runs', 'wickets')
    GROUP BY m.venue_id
),
toss_results AS (
    SELECT
        m.venue_id,
        COUNT(*) AS total_matches,
        SUM(CASE WHEN m.toss_decision = 'bat' AND m.toss_winner_id = m.winner_id THEN 1 ELSE 0 END) AS bat_first_toss_wins,
        SUM(CASE WHEN m.toss_decision = 'field' AND m.toss_winner_id = m.winner_id THEN 1 ELSE 0 END) AS field_first_toss_wins
    FROM matches m
    WHERE m.venue_id IS NOT NULL
      AND m.match_status = 'complete'
      AND m.winner_id IS NOT NULL
    GROUP BY m.venue_id
)
SELECT
    v.venue_id,
    v.venue_name,
    v.city,
    COALESCE(tr.total_matches, 0)                                  AS total_matches,
    ROUND(COALESCE(fi.avg_score, 0), 1)                            AS avg_first_innings_score,
    ROUND(COALESCE(si.avg_score, 0), 1)                            AS avg_second_innings_score,
    ROUND(COALESCE(fi.avg_boundaries, 0), 1)                       AS avg_boundaries_first,
    ROUND(COALESCE(fi.avg_wickets, 0), 1)                          AS avg_wickets_first,
    CASE
        WHEN cr.total_chases > 0
        THEN ROUND(cr.chases_won::NUMERIC * 100.0 / cr.total_chases, 1)
        ELSE NULL
    END                                                            AS chase_success_pct,
    CASE
        WHEN tr.total_matches > 0
        THEN ROUND(tr.bat_first_toss_wins::NUMERIC * 100.0 / tr.total_matches, 1)
        ELSE NULL
    END                                                            AS bat_first_win_pct,
    CASE
        WHEN tr.total_matches > 0
        THEN ROUND(tr.field_first_toss_wins::NUMERIC * 100.0 / tr.total_matches, 1)
        ELSE NULL
    END                                                            AS field_first_win_pct
FROM venues v
LEFT JOIN first_innings fi ON v.venue_id = fi.venue_id
LEFT JOIN second_innings si ON v.venue_id = si.venue_id
LEFT JOIN chase_results cr ON v.venue_id = cr.venue_id
LEFT JOIN toss_results tr ON v.venue_id = tr.venue_id
WHERE tr.total_matches > 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_venue_stats
    ON mv_venue_stats (venue_id);


-- ============================================
-- 6. TEAM SEASON STATS (Materialized View)
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS mv_team_season_stats CASCADE;

CREATE MATERIALIZED VIEW mv_team_season_stats AS
WITH team_matches AS (
    SELECT
        t.team_id,
        t.team_code,
        t.team_name,
        m.season,
        m.match_id,
        CASE WHEN m.winner_id = t.team_id THEN 1 ELSE 0 END AS won,
        CASE WHEN m.match_status = 'complete' AND m.winner_id IS NOT NULL AND m.winner_id != t.team_id THEN 1 ELSE 0 END AS lost,
        CASE WHEN m.toss_winner_id = t.team_id THEN 1 ELSE 0 END AS toss_won,
        CASE WHEN m.toss_winner_id = t.team_id AND m.toss_decision = 'bat' AND m.winner_id = t.team_id THEN 1 ELSE 0 END AS bat_first_won,
        CASE WHEN m.toss_winner_id = t.team_id AND m.toss_decision = 'field' AND m.winner_id = t.team_id THEN 1 ELSE 0 END AS chase_won,
        CASE WHEN m.match_status IN ('tied', 'no_result') OR m.win_type IN ('tie', 'no_result') THEN 1 ELSE 0 END AS no_result
    FROM teams t
    JOIN matches m ON (m.team_a_id = t.team_id OR m.team_b_id = t.team_id)
    WHERE m.match_status IN ('complete', 'tied')
)
SELECT
    team_id,
    team_code,
    team_name,
    season,
    COUNT(*)                                                       AS matches_played,
    SUM(won)                                                       AS wins,
    SUM(lost)                                                      AS losses,
    SUM(no_result)                                                 AS no_results,
    ROUND(SUM(won)::NUMERIC * 100.0 / NULLIF(COUNT(*), 0), 1)     AS win_percentage,
    SUM(toss_won)                                                  AS tosses_won,
    ROUND(SUM(toss_won)::NUMERIC * 100.0 / NULLIF(COUNT(*), 0), 1) AS toss_win_pct,
    SUM(bat_first_won)                                             AS bat_first_wins,
    SUM(chase_won)                                                 AS chase_wins
FROM team_matches
GROUP BY team_id, team_code, team_name, season;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_team_season
    ON mv_team_season_stats (team_id, season);


-- ============================================
-- STAR SCHEMA: Dimension Views
-- ============================================

-- dim_players
CREATE OR REPLACE VIEW dim_players AS
SELECT
    p.player_id,
    p.full_name,
    p.short_name,
    p.batting_hand,
    p.bowling_arm,
    p.bowling_type,
    p.role,
    p.nationality,
    p.date_of_birth,
    p.debut_date
FROM players p;

-- dim_teams
CREATE OR REPLACE VIEW dim_teams AS
SELECT
    t.team_id,
    t.team_code,
    t.team_name,
    t.founded_year,
    v.venue_name AS home_venue,
    v.city AS home_city
FROM teams t
LEFT JOIN venues v ON t.home_venue_id = v.venue_id;

-- dim_venues
CREATE OR REPLACE VIEW dim_venues AS
SELECT
    v.venue_id,
    v.venue_name,
    v.city,
    v.country,
    v.capacity,
    v.pitch_type
FROM venues v;

-- dim_seasons
CREATE OR REPLACE VIEW dim_seasons AS
SELECT
    m.season,
    COUNT(*) AS total_matches,
    MIN(m.match_date) AS season_start,
    MAX(m.match_date) AS season_end,
    COUNT(DISTINCT m.venue_id) AS venues_used,
    COUNT(DISTINCT CASE WHEN m.team_a_id IS NOT NULL THEN m.team_a_id END) +
    COUNT(DISTINCT CASE WHEN m.team_b_id IS NOT NULL THEN m.team_b_id END) AS teams_participated
FROM matches m
GROUP BY m.season;

-- ============================================
-- STAR SCHEMA: Fact View (Enriched Deliveries)
-- ============================================

CREATE OR REPLACE VIEW fact_deliveries AS
SELECT
    d.delivery_id,
    d.match_id,
    m.season,
    m.match_date,
    m.match_type,
    m.match_number,
    d.innings,
    d.over_number,
    d.ball_number,
    -- Phase classification
    CASE
        WHEN d.over_number BETWEEN 0 AND 5 THEN 'powerplay'
        WHEN d.over_number BETWEEN 6 AND 14 THEN 'middle'
        WHEN d.over_number BETWEEN 15 AND 19 THEN 'death'
        ELSE 'super_over'
    END AS match_phase,
    -- Player keys
    d.batsman_id,
    d.bowler_id,
    d.non_striker_id,
    d.batting_team_id,
    d.bowling_team_id,
    -- Venue key
    m.venue_id,
    -- Measures
    d.batsman_runs,
    d.extra_runs,
    d.total_runs,
    d.extras_type,
    d.is_wicket,
    d.wicket_type,
    d.player_dismissed_id,
    d.fielder_id,
    -- Derived flags
    CASE WHEN d.batsman_runs = 4 THEN TRUE ELSE FALSE END AS is_four,
    CASE WHEN d.batsman_runs = 6 THEN TRUE ELSE FALSE END AS is_six,
    CASE WHEN d.batsman_runs = 0 AND d.extra_runs = 0 THEN TRUE ELSE FALSE END AS is_dot,
    CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN TRUE ELSE FALSE END AS is_legal
FROM deliveries d
JOIN matches m ON d.match_id = m.match_id;


-- ============================================
-- Done
-- ============================================
-- Refresh materialized views with:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_batting_career_stats;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_bowling_career_stats;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_batting_season_stats;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_bowling_season_stats;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_venue_stats;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_team_season_stats;
