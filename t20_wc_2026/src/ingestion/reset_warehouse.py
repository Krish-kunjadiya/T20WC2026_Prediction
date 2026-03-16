"""Reset warehouse tables in bronze/silver/gold schemas."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)


def reset_warehouse() -> None:
    """Truncate all tables in bronze, silver, and gold schemas."""
    sql = text(
        """
        DO $$
        DECLARE r RECORD;
        BEGIN
            FOR r IN
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname IN ('bronze', 'silver', 'gold')
            LOOP
                EXECUTE format(
                    'TRUNCATE TABLE %I.%I RESTART IDENTITY CASCADE',
                    r.schemaname,
                    r.tablename
                );
            END LOOP;
        END $$;
        """
    )

    with engine.begin() as conn:
        conn.execute(sql)

    print("Reset complete: truncated bronze/silver/gold")


if __name__ == "__main__":
    reset_warehouse()
