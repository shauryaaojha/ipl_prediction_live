-- ============================================
-- IPL 2026 Data Scraper — Database Setup
-- ============================================
-- Run this script against PostgreSQL to create all tables.
-- Usage: psql -U ipl_user -d ipl2026 -f scripts/setup_databases.sql

-- Players Master Table
CREATE TABLE IF NOT EXISTS players (
    player_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    batting_hand VARCHAR(10) CHECK (batting_hand IN ('right', 'left')),
    bowling_arm VARCHAR(10) CHECK (bowling_arm IN ('right', 'left')),
    bowling_type VARCHAR(20) CHECK (bowling_type IN ('pace', 'spin', 'none')),
    role VARCHAR(30) CHECK (role IN ('batsman', 'bowler', 'all_rounder', 'wicketkeeper', 'wicketkeeper_batsman')),
    nationality VARCHAR(50),
    date_of_birth DATE,
    debut_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Player Sources (Normalized IDs)
CREATE TABLE IF NOT EXISTS player_sources (
    player_id UUID REFERENCES players(player_id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    PRIMARY KEY (player_id, source),
    UNIQUE(source, source_id)
);

-- Player Name Aliases (for fuzzy matching)
CREATE TABLE IF NOT EXISTS player_aliases (
    alias_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID REFERENCES players(player_id) ON DELETE CASCADE,
    alias_name VARCHAR(100) NOT NULL,
    source VARCHAR(50),
    UNIQUE(player_id, alias_name)
);

-- Venues
CREATE TABLE IF NOT EXISTS venues (
    venue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(50) DEFAULT 'India',
    capacity INTEGER,
    pitch_type VARCHAR(20),
    avg_first_innings_score DECIMAL(6,2),
    avg_second_innings_score DECIMAL(6,2),
    chase_success_rate DECIMAL(5,4),
    pace_advantage_index DECIMAL(3,2),
    spin_advantage_index DECIMAL(3,2),
    dew_factor DECIMAL(3,2),
    espncricinfo_id VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dataset Imports (Versioning)
CREATE TABLE IF NOT EXISTS dataset_imports (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,
    dataset_version VARCHAR(50),
    sha256_checksum VARCHAR(64),
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teams / Franchises
CREATE TABLE IF NOT EXISTS teams (
    team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_code VARCHAR(30) UNIQUE NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    home_venue_id UUID REFERENCES venues(venue_id),
    founded_year INTEGER
);

-- Matches
CREATE TABLE IF NOT EXISTS matches (
    match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) DEFAULT 'unknown',
    season INTEGER NOT NULL,
    match_number INTEGER NOT NULL,
    match_date TIMESTAMP NOT NULL,
    venue_id UUID REFERENCES venues(venue_id),
    team_a_id UUID REFERENCES teams(team_id),
    team_b_id UUID REFERENCES teams(team_id),
    toss_winner_id UUID REFERENCES teams(team_id),
    toss_decision VARCHAR(10) CHECK (toss_decision IN ('bat', 'field')),
    winner_id UUID REFERENCES teams(team_id),
    win_margin INTEGER,
    win_type VARCHAR(20) CHECK (win_type IN ('runs', 'wickets', 'tie', 'no_result', 'super_over')),
    player_of_match_id UUID REFERENCES players(player_id),
    dl_applied BOOLEAN DEFAULT FALSE,
    match_type VARCHAR(20) CHECK (match_type IN ('league', 'qualifier_1', 'eliminator', 'qualifier_2', 'final')),
    match_status VARCHAR(20) DEFAULT 'upcoming' CHECK (match_status IN ('upcoming', 'live', 'complete', 'abandoned', 'tied')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(season, match_number)
);

-- Match Sources (Normalized IDs)
CREATE TABLE IF NOT EXISTS match_sources (
    match_id UUID REFERENCES matches(match_id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    PRIMARY KEY (match_id, source),
    UNIQUE(source, source_id)
);

-- Ball-by-Ball Deliveries
CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID REFERENCES matches(match_id) ON DELETE CASCADE,
    innings INTEGER NOT NULL CHECK (innings BETWEEN 1 AND 10),
    over_number INTEGER NOT NULL CHECK (over_number BETWEEN 0 AND 19),
    ball_number INTEGER NOT NULL CHECK (ball_number BETWEEN 1 AND 25),
    batting_team_id UUID REFERENCES teams(team_id),
    bowling_team_id UUID REFERENCES teams(team_id),
    batsman_id UUID REFERENCES players(player_id),
    non_striker_id UUID REFERENCES players(player_id),
    bowler_id UUID REFERENCES players(player_id),
    batsman_runs INTEGER DEFAULT 0,
    extra_runs INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    extras_type VARCHAR(20) CHECK (extras_type IN ('wide', 'noball', 'bye', 'legbye', 'penalty')),
    is_wicket BOOLEAN DEFAULT FALSE,
    wicket_type VARCHAR(50),
    player_dismissed_id UUID REFERENCES players(player_id),
    fielder_id UUID REFERENCES players(player_id),
    match_phase VARCHAR(20) CHECK (match_phase IN ('powerplay', 'middle', 'death')),
    source VARCHAR(50) DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_id, innings, over_number, ball_number)
);

-- Playing XI
CREATE TABLE IF NOT EXISTS playing_xi (
    xi_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID REFERENCES matches(match_id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(team_id),
    player_id UUID REFERENCES players(player_id),
    batting_position INTEGER CHECK (batting_position BETWEEN 1 AND 11),
    is_captain BOOLEAN DEFAULT FALSE,
    is_wicketkeeper BOOLEAN DEFAULT FALSE,
    is_impact_sub BOOLEAN DEFAULT FALSE,
    UNIQUE(match_id, team_id, player_id)
);

-- Player Statistics (Season-wise)
CREATE TABLE IF NOT EXISTS player_stats (
    stat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID REFERENCES players(player_id),
    season INTEGER NOT NULL,
    team_id UUID REFERENCES teams(team_id),
    matches INTEGER DEFAULT 0,
    innings INTEGER DEFAULT 0,
    not_outs INTEGER DEFAULT 0,
    runs INTEGER DEFAULT 0,
    balls_faced INTEGER DEFAULT 0,
    highest_score INTEGER DEFAULT 0,
    highest_score_not_out BOOLEAN DEFAULT FALSE,
    hundreds INTEGER DEFAULT 0,
    fifties INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    ducks INTEGER DEFAULT 0,
    batting_average DECIMAL(6,2),
    batting_strike_rate DECIMAL(6,2),
    boundary_percentage DECIMAL(5,2),
    overs_bowled DECIMAL(5,1),
    wickets INTEGER DEFAULT 0,
    runs_conceded INTEGER DEFAULT 0,
    bowling_average DECIMAL(6,2),
    bowling_economy DECIMAL(5,2),
    bowling_strike_rate DECIMAL(6,2),
    four_wickets INTEGER DEFAULT 0,
    five_wickets INTEGER DEFAULT 0,
    dot_ball_percentage DECIMAL(5,2),
    catches INTEGER DEFAULT 0,
    stumpings INTEGER DEFAULT 0,
    run_outs_direct INTEGER DEFAULT 0,
    run_outs_assisted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, season, team_id)
);

-- Player Availability
CREATE TABLE IF NOT EXISTS player_availability (
    availability_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID REFERENCES players(player_id),
    team_id UUID REFERENCES teams(team_id),
    season INTEGER NOT NULL,
    status VARCHAR(20) CHECK (status IN ('available', 'injured', 'suspended', 'withdrawn', 'unavailable', 'rested')),
    injury_type VARCHAR(100),
    injury_description TEXT,
    expected_return_date DATE,
    replacement_player_id UUID REFERENCES players(player_id),
    source_url VARCHAR(500),
    confidence_score DECIMAL(3,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Match-Day Conditions
CREATE TABLE IF NOT EXISTS match_conditions (
    condition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID REFERENCES matches(match_id) ON DELETE CASCADE,
    temperature DECIMAL(4,1),
    humidity DECIMAL(5,2),
    weather_condition VARCHAR(50),
    wind_speed DECIMAL(5,2),
    dew_probability DECIMAL(3,2),
    rest_days_team_a INTEGER DEFAULT 0,
    rest_days_team_b INTEGER DEFAULT 0,
    home_away_team_a VARCHAR(10) CHECK (home_away_team_a IN ('home', 'away', 'neutral')),
    home_away_team_b VARCHAR(10) CHECK (home_away_team_b IN ('home', 'away', 'neutral')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraping Log (Audit Trail)
CREATE TABLE IF NOT EXISTS scrape_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    records_fetched INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(20) CHECK (status IN ('running', 'success', 'partial', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Performance Indexes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(match_status);
CREATE INDEX IF NOT EXISTS idx_deliveries_match ON deliveries(match_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_batsman ON deliveries(batsman_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_bowler ON deliveries(bowler_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_season ON player_stats(season);
CREATE INDEX IF NOT EXISTS idx_playing_xi_match ON playing_xi(match_id);
CREATE INDEX IF NOT EXISTS idx_scrape_log_job ON scrape_log(job_name, start_time);

-- ============================================
-- Done
-- ============================================
-- Verify with: \dt
