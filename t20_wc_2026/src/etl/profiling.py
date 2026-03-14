"""Generate HTML profiling reports from Silver layer tables."""

from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from ydata_profiling import ProfileReport


load_dotenv()
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)


def run_profiles() -> None:
    """Create minimal HTML profiling reports for key Silver tables."""
    os.makedirs("results/profiles", exist_ok=True)

    tables = {
        "silver.clean_matches": "results/profiles/matches_profile.html",
        "silver.clean_players": "results/profiles/players_profile.html",
    }

    for table, output_path in tables.items():
        print(f"Profiling {table}...")
        df = pd.read_sql(f"SELECT * FROM {table}", engine)
        profile = ProfileReport(df, title=f"Profile: {table}", minimal=True)
        profile.to_file(output_path)
        print(f"  Saved -> {output_path}")

    print("\nAll profiling reports generated")


if __name__ == "__main__":
    run_profiles()
