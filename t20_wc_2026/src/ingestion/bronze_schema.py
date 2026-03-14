"""
BRONZE LAYER — Raw ingested tables (exact structure from source CSVs).
No transformations. Data lands as-is with an audit timestamp.
Tables align with the actual files present in data/raw/.
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


def create_bronze_layer() -> None:
    """Create the bronze schema and all raw staging tables."""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))

        # ── raw_matches (from matches.csv / organizer data) ───────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bronze.raw_matches (
                match_no            VARCHAR(20),
                stage               VARCHAR(30),
                "group"             VARCHAR(10),
                date                VARCHAR(20),
                venue               VARCHAR(120),
                city                VARCHAR(60),
                team1               VARCHAR(60),
                team2               VARCHAR(60),
                toss_winner         VARCHAR(60),
                toss_decision       VARCHAR(10),
                winner              VARCHAR(60),
                result              VARCHAR(100),
                margin              VARCHAR(30),
                _ingested_at        TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── raw_batting_stats (from batting_stats.csv) ────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bronze.raw_batting_stats (
                player              VARCHAR(100),
                team                VARCHAR(60),
                matches             VARCHAR(10),
                innings             VARCHAR(10),
                runs                VARCHAR(10),
                average             VARCHAR(10),
                strike_rate         VARCHAR(10),
                fours               VARCHAR(10),
                sixes               VARCHAR(10),
                hundreds            VARCHAR(5),
                fifties             VARCHAR(5),
                _ingested_at        TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── raw_bowling_stats (from bowling_stats.csv) ────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bronze.raw_bowling_stats (
                player              VARCHAR(100),
                team                VARCHAR(60),
                matches             VARCHAR(10),
                overs               VARCHAR(10),
                balls               VARCHAR(10),
                wickets             VARCHAR(10),
                average             VARCHAR(10),
                runs_conceded       VARCHAR(10),
                economy             VARCHAR(10),
                four_wicket_hauls   VARCHAR(5),
                five_wicket_hauls   VARCHAR(5),
                best_figures        VARCHAR(20),
                _ingested_at        TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── raw_squads (from squads.csv) ──────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bronze.raw_squads (
                team                VARCHAR(60),
                player_name         VARCHAR(100),
                role                VARCHAR(40),
                designation         VARCHAR(40),
                _ingested_at        TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── raw_venues (from venues.csv) ──────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bronze.raw_venues (
                venue_name          VARCHAR(120),
                city                VARCHAR(60),
                country             VARCHAR(60),
                capacity            VARCHAR(20),
                stages_hosted       VARCHAR(200),
                _ingested_at        TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── raw_key_scorecards (from key_scorecards.csv) ──────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bronze.raw_key_scorecards (
                match               VARCHAR(60),
                innings             VARCHAR(10),
                team                VARCHAR(60),
                player              VARCHAR(100),
                runs                VARCHAR(10),
                balls               VARCHAR(10),
                fours               VARCHAR(10),
                sixes               VARCHAR(10),
                dismissal           VARCHAR(120),
                _ingested_at        TIMESTAMP DEFAULT NOW()
            );
        """))

        # ── raw_deliveries (from cricsheet ball-by-ball CSVs) ─────────────
        # Columns match the actual t20s_csv2 format from cricsheet.org
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bronze.raw_deliveries (
                match_id                VARCHAR(20),
                season                  VARCHAR(10),
                start_date              VARCHAR(20),
                venue                   VARCHAR(120),
                innings                 VARCHAR(5),
                ball                    VARCHAR(10),
                batting_team            VARCHAR(60),
                bowling_team            VARCHAR(60),
                striker                 VARCHAR(60),
                non_striker             VARCHAR(60),
                bowler                  VARCHAR(60),
                runs_off_bat            VARCHAR(5),
                extras                  VARCHAR(5),
                wides                   VARCHAR(5),
                noballs                 VARCHAR(5),
                byes                    VARCHAR(5),
                legbyes                 VARCHAR(5),
                penalty                 VARCHAR(5),
                wicket_type             VARCHAR(30),
                player_dismissed        VARCHAR(60),
                other_wicket_type       VARCHAR(30),
                other_player_dismissed  VARCHAR(60),
                _ingested_at            TIMESTAMP DEFAULT NOW()
            );
        """))

        conn.commit()
        print("✅ BRONZE layer created — 7 tables ready")
        print("   bronze.raw_matches, raw_batting_stats, raw_bowling_stats,")
        print("   raw_squads, raw_venues, raw_key_scorecards, raw_deliveries")


if __name__ == "__main__":
    load_dotenv()
    create_bronze_layer()
