"""Simulate live ball-by-ball events and stream them into PostgreSQL."""

import os
import random
import time
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

TEAMS = ["India", "Australia", "England", "Pakistan", "South Africa", "New Zealand"]
PLAYERS = ["Rohit", "Virat", "Bumrah", "Warner", "Stokes", "Babar", "Rabada", "Conway"]


def build_database_url() -> str:
    """Build a SQLAlchemy database URL from environment variables."""
    return (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )


def ensure_live_table(engine) -> None:
    """Create the live ball events table if it does not already exist."""
    with engine.connect() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS live_ball_events (
                    event_id SERIAL PRIMARY KEY,
                    match_id VARCHAR(20),
                    over_num FLOAT,
                    ball_num INT,
                    batting_team VARCHAR(50),
                    bowling_team VARCHAR(50),
                    batsman VARCHAR(50),
                    bowler VARCHAR(50),
                    runs_scored INT,
                    is_wicket BOOLEAN,
                    extras INT,
                    timestamp TIMESTAMP
                );
                """
            )
        )
        connection.commit()


def generate_ball_event(match_id: str, over: int, ball: int) -> dict:
    """Generate one synthetic delivery event row."""
    return {
        "match_id": match_id,
        "over_num": over,
        "ball_num": ball,
        "batting_team": random.choice(TEAMS),
        "bowling_team": random.choice(TEAMS),
        "batsman": random.choice(PLAYERS),
        "bowler": random.choice(PLAYERS),
        "runs_scored": random.choices([0, 1, 2, 3, 4, 6], weights=[30, 25, 15, 5, 15, 10])[0],
        "is_wicket": random.random() < 0.05,
        "extras": random.choices([0, 1, 2], weights=[85, 10, 5])[0],
        "timestamp": datetime.now(),
    }


def simulate_match(engine, match_id: str = "MATCH_001", interval: float = 0.2) -> None:
    """Simulate 20 overs and append each ball event to PostgreSQL."""
    print(f"Simulating match: {match_id}")
    for over in range(1, 21):
        for ball in range(1, 7):
            event = generate_ball_event(match_id=match_id, over=over, ball=ball)
            pd.DataFrame([event]).to_sql("live_ball_events", engine, if_exists="append", index=False)
            print(f"Over {over}.{ball} | Runs: {event['runs_scored']} | Wicket: {event['is_wicket']}")
            time.sleep(interval)


if __name__ == "__main__":
    load_dotenv()
    db_engine = create_engine(build_database_url())
    ensure_live_table(db_engine)
    simulate_match(engine=db_engine, interval=0.2)
