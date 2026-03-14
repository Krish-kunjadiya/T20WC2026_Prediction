import os

import pandas as pd
from sqlalchemy import text

from db import engine
from models import Base, Player, Team, Venue


DATA_DIR = os.getenv(
    "T20_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "..", "10"),
)


def load_venues():
    path = os.path.join(DATA_DIR, "venues.csv")
    df = pd.read_csv(path)
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO venues (name, city, country)
                    VALUES (:name, :city, :country)
                    ON CONFLICT (name) DO NOTHING
                    """
                ),
                {
                    "name": row["venue_name"],
                    "city": row["city"],
                    "country": row["country"],
                },
            )


def load_squads_and_players():
    path_squads = os.path.join(DATA_DIR, "squads.csv")
    path_batting = os.path.join(DATA_DIR, "batting_stats.csv")

    squads = pd.read_csv(path_squads)
    batting = pd.read_csv(path_batting)

    # Basic impact score from batting stats (normalize runs + strike rate)
    batting["impact_raw"] = batting["runs"] * 0.6 + batting["strike_rate"] * 0.4
    batting_max = batting["impact_raw"].max() or 1
    batting["impact_score"] = batting["impact_raw"] / batting_max * 100

    # Join squads with batting where available
    merged = squads.merge(
        batting[["player", "team", "impact_score"]],
        left_on=["player_name", "team"],
        right_on=["player", "team"],
        how="left",
    )

    with engine.begin() as conn:
        # Teams
        teams = squads["team"].drop_duplicates()
        for t in teams:
            conn.execute(
                text(
                    """
                    INSERT INTO teams (name, short_name)
                    VALUES (:name, :short)
                    ON CONFLICT (name) DO NOTHING
                    """
                ),
                {"name": t, "short": t},
            )

        # Players
        for _, row in merged.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO players (name, team, role, impact_score)
                    VALUES (:name, :team, :role, :impact)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "name": row["player_name"],
                    "team": row["team"],
                    "role": row["role"],
                    "impact": float(row["impact_score"]) if not pd.isna(row["impact_score"]) else None,
                },
            )


def main():
    Base.metadata.create_all(bind=engine)
    load_venues()
    load_squads_and_players()
    print("ETL completed.")


if __name__ == "__main__":
    main()

