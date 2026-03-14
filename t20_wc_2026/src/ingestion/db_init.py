"""Initialize and validate PostgreSQL connectivity for the project."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def build_database_url() -> str:
    """Build a SQLAlchemy database URL from environment variables."""
    return (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )


def test_connection() -> None:
    """Test database connectivity and print PostgreSQL version."""
    engine = create_engine(build_database_url())
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"PostgreSQL connected: {version}")


if __name__ == "__main__":
    load_dotenv()
    test_connection()
