"""
SILVER LAYER — Cleaned, typed, and normalised tables.
All columns carry correct SQL data types. Nulls handled with sensible defaults.
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


def create_silver_layer() -> None:
    """Create the silver schema and all cleaned/typed tables."""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS silver;"))

        # ── clean_matches ─────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS silver.clean_matches (
                match_id            VARCHAR(50) PRIMARY KEY,
                match_date          DATE,
                venue               VARCHAR(120),
                city                VARCHAR(60),
                team1               VARCHAR(60),
                team2               VARCHAR(60),
                gender              VARCHAR(10),
                toss_winner         VARCHAR(60),
                toss_decision       VARCHAR(10),
                winner              VARCHAR(60),
                win_by_runs         INTEGER DEFAULT 0,
                win_by_wickets      INTEGER DEFAULT 0,
                player_of_match     VARCHAR(100),
                tournament_phase    VARCHAR(20),
                is_day_night        BOOLEAN DEFAULT FALSE,
                _processed_at       TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── clean_deliveries ──────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS silver.clean_deliveries (
                delivery_id         SERIAL PRIMARY KEY,
                match_id            VARCHAR(50),
                inning              INTEGER,
                over_num            INTEGER,
                ball_num            INTEGER,
                batting_team        VARCHAR(60),
                bowling_team        VARCHAR(60),
                batsman             VARCHAR(60),
                bowler              VARCHAR(60),
                batsman_runs        INTEGER DEFAULT 0,
                extra_runs          INTEGER DEFAULT 0,
                total_runs          INTEGER DEFAULT 0,
                is_wicket           BOOLEAN DEFAULT FALSE,
                dismissal_kind      VARCHAR(30),
                gender              VARCHAR(10),
                _processed_at       TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── clean_players ─────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS silver.clean_players (
                player_id           VARCHAR(100),
                player_name         VARCHAR(100),
                country             VARCHAR(60),
                gender              VARCHAR(10),
                role                VARCHAR(40),
                matches             INTEGER DEFAULT 0,
                runs                INTEGER DEFAULT 0,
                batting_avg         FLOAT DEFAULT 0.0,
                strike_rate         FLOAT DEFAULT 0.0,
                hundreds            INTEGER DEFAULT 0,
                fifties             INTEGER DEFAULT 0,
                wickets             INTEGER DEFAULT 0,
                bowling_avg         FLOAT DEFAULT 0.0,
                economy             FLOAT DEFAULT 0.0,
                _processed_at       TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (player_name, country)
            );
        """))

        # ── clean_venues ──────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS silver.clean_venues (
                venue_name          VARCHAR(120) PRIMARY KEY,
                city                VARCHAR(60),
                country             VARCHAR(60),
                capacity            INTEGER,
                stages_hosted       VARCHAR(200),
                _processed_at       TIMESTAMP DEFAULT NOW()
            );
        """))

        conn.commit()
        print("✅ SILVER layer created — 4 tables ready")
        print("   silver.clean_matches, clean_deliveries,")
        print("   clean_players, clean_venues")


if __name__ == "__main__":
    load_dotenv()
    create_silver_layer()
