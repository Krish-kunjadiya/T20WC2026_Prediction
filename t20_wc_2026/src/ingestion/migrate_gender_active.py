"""
Migration: Add gender + is_active columns to warehouse tables.

Run once after initial CricSheet-only load so the global sidebar filters
(gender toggle + active-players toggle) work across all dashboard pages.

Gender logic:
  - All current data defaults to 'male' (CricSheet t20s dataset).
  - When female data is loaded separately the column should be set accordingly.

is_active logic:
  - last_played_date = most recent start_date in bronze.raw_deliveries for that player.
  - is_active = TRUE if last_played_date is within the last 3 years.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)


def run_migration() -> None:
    with engine.connect() as conn:

        # ── 1. silver.clean_matches ──────────────────────────────────────
        print("Adding gender to silver.clean_matches ...")
        conn.execute(text(
            "ALTER TABLE silver.clean_matches "
            "ADD COLUMN IF NOT EXISTS gender VARCHAR(10) DEFAULT 'male';"
        ))
        conn.execute(text(
            "UPDATE silver.clean_matches SET gender = 'male' WHERE gender IS NULL;"
        ))

        # ── 2. silver.clean_deliveries ───────────────────────────────────
        print("Adding gender to silver.clean_deliveries ...")
        conn.execute(text(
            "ALTER TABLE silver.clean_deliveries "
            "ADD COLUMN IF NOT EXISTS gender VARCHAR(10) DEFAULT 'male';"
        ))
        conn.execute(text(
            "UPDATE silver.clean_deliveries SET gender = 'male' WHERE gender IS NULL;"
        ))

        # ── 3. silver.clean_players ──────────────────────────────────────
        print("Adding gender / last_played_date / is_active to silver.clean_players ...")
        conn.execute(text(
            "ALTER TABLE silver.clean_players "
            "ADD COLUMN IF NOT EXISTS gender VARCHAR(10) DEFAULT 'male';"
        ))
        conn.execute(text(
            "ALTER TABLE silver.clean_players "
            "ADD COLUMN IF NOT EXISTS last_played_date DATE;"
        ))
        conn.execute(text(
            "ALTER TABLE silver.clean_players "
            "ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;"
        ))

        # ── 4. Compute last_played_date from bronze.raw_deliveries ───────
        print("Computing last_played_date per player from bronze.raw_deliveries ...")
        conn.execute(text("""
            UPDATE silver.clean_players cp
            SET last_played_date = sub.last_date
            FROM (
                SELECT
                    TRIM(striker) AS pname,
                    MAX(
                        CASE
                            WHEN TRIM(start_date) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                            THEN TRIM(start_date)::date
                            ELSE NULL
                        END
                    ) AS last_date
                FROM bronze.raw_deliveries
                WHERE start_date IS NOT NULL AND TRIM(start_date) != ''
                GROUP BY TRIM(striker)
            ) sub
            WHERE cp.player_name = sub.pname;
        """))

        # ── 5. Set is_active flag (within last 3 years) ──────────────────
        print("Flagging is_active (last 3 years) ...")
        conn.execute(text("""
            UPDATE silver.clean_players
            SET is_active = (last_played_date >= NOW() - INTERVAL '3 years')
            WHERE last_played_date IS NOT NULL;
        """))
        conn.execute(text("""
            UPDATE silver.clean_players
            SET is_active = FALSE
            WHERE last_played_date IS NULL;
        """))

        conn.commit()

    # ── Summary ──────────────────────────────────────────────────────────
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM silver.clean_players")).scalar()
        active = conn.execute(text("SELECT COUNT(*) FROM silver.clean_players WHERE is_active = TRUE")).scalar()
        has_date = conn.execute(text("SELECT COUNT(*) FROM silver.clean_players WHERE last_played_date IS NOT NULL")).scalar()

    print(f"\n✅ Migration complete.")
    print(f"   silver.clean_players  total={total:,}  active={active:,}  with_date={has_date:,}")


if __name__ == "__main__":
    run_migration()
