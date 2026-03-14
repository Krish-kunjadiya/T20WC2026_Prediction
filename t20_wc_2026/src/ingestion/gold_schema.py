"""
GOLD LAYER — Star Schema (analytics-ready).
One central fact table surrounded by five dimension tables.
Designed for dashboard queries and ML feature extraction.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

_u = os.getenv("POSTGRES_USER")
_p = os.getenv("POSTGRES_PASSWORD")
_h = os.getenv("POSTGRES_HOST")
_port = os.getenv("POSTGRES_PORT")
_db = os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql://{_u}:{_p}@{_h}:{_port}/{_db}"
engine = create_engine(DATABASE_URL)


def create_gold_layer() -> None:
    """Create the gold schema: 5 dimension tables + 1 fact table."""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold;"))

        # ── dim_team ──────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold.dim_team (
                team_id             SERIAL PRIMARY KEY,
                team_name           VARCHAR(60) UNIQUE NOT NULL,
                icc_ranking         INTEGER,
                icc_rating          FLOAT,
                captain             VARCHAR(100),
                coach               VARCHAR(100),
                home_country        VARCHAR(60)
            );
        """))

        # ── dim_venue ─────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold.dim_venue (
                venue_id            SERIAL PRIMARY KEY,
                stadium_name        VARCHAR(120) NOT NULL,
                city                VARCHAR(60),
                country             VARCHAR(60),
                pitch_type          VARCHAR(30),
                avg_first_innings   FLOAT DEFAULT 0.0,
                capacity            INTEGER,
                is_day_night        BOOLEAN DEFAULT TRUE
            );
        """))

        # ── dim_player ────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold.dim_player (
                player_id           VARCHAR(100) PRIMARY KEY,
                player_name         VARCHAR(100) NOT NULL,
                country             VARCHAR(60),
                role                VARCHAR(40),
                batting_style       VARCHAR(30),
                bowling_style       VARCHAR(50),
                age                 INTEGER,
                is_active           BOOLEAN DEFAULT TRUE
            );
        """))

        # ── dim_date ──────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold.dim_date (
                date_id             SERIAL PRIMARY KEY,
                match_date          DATE UNIQUE NOT NULL,
                year                INTEGER,
                month               INTEGER,
                month_name          VARCHAR(15),
                day_of_week         VARCHAR(10),
                tournament_phase    VARCHAR(20),
                is_knockout         BOOLEAN DEFAULT FALSE,
                is_final            BOOLEAN DEFAULT FALSE
            );
        """))

        # ── dim_match ─────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold.dim_match (
                match_id            VARCHAR(50) PRIMARY KEY,
                toss_winner_id      INTEGER REFERENCES gold.dim_team(team_id),
                toss_decision       VARCHAR(10),
                weather_condition   VARCHAR(30),
                is_day_night        BOOLEAN DEFAULT FALSE,
                result_type         VARCHAR(20),
                result_margin       INTEGER DEFAULT 0
            );
        """))

        # ── fact_match_performance ────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold.fact_match_performance (
                perf_id             SERIAL PRIMARY KEY,
                match_id            VARCHAR(50) REFERENCES gold.dim_match(match_id),
                player_id           VARCHAR(100) REFERENCES gold.dim_player(player_id),
                team_id             INTEGER REFERENCES gold.dim_team(team_id),
                opponent_team_id    INTEGER REFERENCES gold.dim_team(team_id),
                venue_id            INTEGER REFERENCES gold.dim_venue(venue_id),
                date_id             INTEGER REFERENCES gold.dim_date(date_id),
                runs_scored         INTEGER DEFAULT 0,
                balls_faced         INTEGER DEFAULT 0,
                strike_rate         FLOAT DEFAULT 0.0,
                fours               INTEGER DEFAULT 0,
                sixes               INTEGER DEFAULT 0,
                wickets_taken       INTEGER DEFAULT 0,
                overs_bowled        FLOAT DEFAULT 0.0,
                runs_conceded       INTEGER DEFAULT 0,
                economy_rate        FLOAT DEFAULT 0.0,
                catches             INTEGER DEFAULT 0,
                match_result        VARCHAR(5),
                is_player_of_match  BOOLEAN DEFAULT FALSE
            );
        """))

        conn.commit()
        print("✅ GOLD layer created — 5 dimension tables + 1 fact table ready")
        print("   gold.dim_team, dim_venue, dim_player, dim_date, dim_match")
        print("   gold.fact_match_performance")


if __name__ == "__main__":
    load_dotenv()
    create_gold_layer()
