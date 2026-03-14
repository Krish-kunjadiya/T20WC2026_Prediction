"""
Build ChromaDB vector knowledge base from:
  1. Match summaries (generated from DB)
  2. Player profiles (from silver layer)
  3. Team stats (from gold/silver layer)
  4. Venue records (from silver layer)
  5. Tournament rules & facts (hardcoded)
"""

import os
import sys
from typing import Dict, List

import chromadb
import pandas as pd
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
sys.path.append(os.path.dirname(__file__))

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chromadb")
os.makedirs(CHROMA_PATH, exist_ok=True)


def get_chroma_collection():
    """Get or create ChromaDB collection with sentence-transformer embeddings."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="cricket_knowledge",
        embedding_function=ef,
        metadata={"description": "T20 WC 2026 cricket knowledge base"},
    )
    return collection


def build_match_documents() -> List[Dict]:
    """Generate natural language match summary documents."""
    matches = pd.read_sql("SELECT * FROM silver.clean_matches", engine)
    docs: List[Dict] = []
    for _, m in matches.iterrows():
        margin = ""
        if m.get("win_by_runs", 0) > 0:
            margin = f"by {int(m['win_by_runs'])} runs"
        elif m.get("win_by_wickets", 0) > 0:
            margin = f"by {int(m['win_by_wickets'])} wickets"

        text = (
            f"Match Summary: {m.get('team1', '?')} vs {m.get('team2', '?')} "
            f"on {m.get('match_date', '?')} at {m.get('venue', '?')}. "
            f"Toss: {m.get('toss_winner', '?')} won the toss and chose to "
            f"{m.get('toss_decision', '?')}. "
            f"Result: {m.get('winner', '?')} won {margin}. "
            f"Player of the Match: {m.get('player_of_match', '?')}. "
            f"Tournament Phase: {m.get('tournament_phase', 'Group Stage')}."
        )
        docs.append(
            {
                "id": f"match_{m.get('match_id', '?')}",
                "text": text,
                "meta": {
                    "type": "match",
                    "team1": str(m.get("team1", "")),
                    "team2": str(m.get("team2", "")),
                    "winner": str(m.get("winner", "")),
                    "phase": str(m.get("tournament_phase", "")),
                },
            }
        )
    print(f"  OK {len(docs)} match documents built")
    return docs


def build_player_documents() -> List[Dict]:
    """Generate player profile documents."""
    players = pd.read_sql("SELECT * FROM silver.clean_players", engine)
    docs: List[Dict] = []
    for _, p in players.iterrows():
        text = (
            f"Player Profile: {p.get('player_name', '?')} from {p.get('country', '?')}. "
            f"Role: {p.get('role', '?')}. "
            f"Batting - Runs: {int(p.get('runs', 0))}, "
            f"Average: {float(p.get('batting_avg', 0)):.1f}, "
            f"Strike Rate: {float(p.get('strike_rate', 0)):.1f}, "
            f"Hundreds: {int(p.get('hundreds', 0))}, "
            f"Fifties: {int(p.get('fifties', 0))}. "
            f"Bowling - Wickets: {int(p.get('wickets', 0))}, "
            f"Average: {float(p.get('bowling_avg', 0)):.1f}, "
            f"Economy: {float(p.get('economy', 0)):.1f}."
        )
        docs.append(
            {
                "id": f"player_{p.get('player_id', '?')}",
                "text": text,
                "meta": {
                    "type": "player",
                    "name": str(p.get("player_name", "")),
                    "country": str(p.get("country", "")),
                    "role": str(p.get("role", "")),
                },
            }
        )
    print(f"  OK {len(docs)} player documents built")
    return docs


def build_team_documents() -> List[Dict]:
    """Generate team statistics documents."""
    matches = pd.read_sql("SELECT * FROM silver.clean_matches", engine)
    deliveries = pd.read_sql(
        "SELECT batting_team, bowling_team, batsman_runs, total_runs, is_wicket "
        "FROM silver.clean_deliveries",
        engine,
    )
    teams = pd.concat([matches["team1"], matches["team2"]]).unique()
    docs: List[Dict] = []

    for team in teams:
        played = len(matches[(matches["team1"] == team) | (matches["team2"] == team)])
        won = len(matches[matches["winner"] == team])
        bat_del = deliveries[deliveries["batting_team"] == team]
        bowl_del = deliveries[deliveries["bowling_team"] == team]

        total_runs = int(bat_del["batsman_runs"].sum())
        total_wkts = int(bowl_del["is_wicket"].sum())
        avg_sr = round(bat_del["batsman_runs"].mean() * 100, 1) if len(bat_del) else 0.0
        sixes = int((bat_del["batsman_runs"] == 6).sum())

        text = (
            f"Team Statistics: {team}. "
            f"Matches Played: {played}, Won: {won}, Lost: {played - won}. "
            f"Win Rate: {round(won / max(played, 1) * 100, 1)}%. "
            f"Total Runs Scored: {total_runs:,}. "
            f"Total Wickets Taken: {total_wkts}. "
            f"Team Strike Rate: {avg_sr}. "
            f"Total Sixes Hit: {sixes}."
        )
        docs.append(
            {
                "id": f"team_{str(team).replace(' ', '_')}",
                "text": text,
                "meta": {"type": "team", "team": str(team)},
            }
        )
    print(f"  OK {len(docs)} team documents built")
    return docs


def build_venue_documents() -> List[Dict]:
    """Generate venue record documents."""
    venues = pd.read_sql("SELECT * FROM silver.clean_venues", engine)
    matches = pd.read_sql("SELECT * FROM silver.clean_matches", engine)

    docs: List[Dict] = []
    for idx, v in venues.iterrows():
        name = v.get("stadium_name", "?")
        venue_matches = matches[matches["venue"].astype(str).str.contains(str(name), na=False)]
        match_count = len(venue_matches)

        pitch = str(v.get("pitch_type", "Balanced"))
        favors = "batsmen" if pitch in ["Flat", "Batting"] else "bowlers"

        text = (
            f"Venue Profile: {name} in {v.get('city', '?')}, {v.get('country', '?')}. "
            f"Pitch Type: {pitch}. "
            f"Matches Hosted: {match_count}. "
            f"Typically favors: {favors}."
        )
        venue_suffix = str(v.get("venue_id", idx))
        docs.append(
            {
                "id": f"venue_{str(name).replace(' ', '_')[:30]}_{venue_suffix}",
                "text": text,
                "meta": {
                    "type": "venue",
                    "stadium": str(name),
                    "city": str(v.get("city", "")),
                },
            }
        )
    print(f"  OK {len(docs)} venue documents built")
    return docs


def build_tournament_facts() -> List[Dict]:
    """Add hardcoded ICC T20 WC tournament knowledge."""
    facts = [
        "The ICC Men's T20 World Cup 2026 is hosted across multiple venues. "
        "The tournament features 20 teams divided into 4 groups of 5. "
        "Top 2 from each group advance to the Super 8 stage.",
        "ICC T20 World Cup records: Most runs all-time by Virat Kohli (India). "
        "Most wickets all-time by Shakib Al Hasan (Bangladesh). "
        "Highest team total is 260/6 by Sri Lanka vs Kenya in 2007.",
        "T20 cricket rules: Each team bats for 20 overs. "
        "Powerplay is overs 1-6 where only 2 fielders are allowed outside the ring. "
        "Death overs are 16-20, typically highest scoring phase.",
        "Key T20 World Cup 2024 results: India won the 2024 T20 World Cup "
        "defeating South Africa in the final. Rohit Sharma led India "
        "to an unbeaten campaign. Jasprit Bumrah was the top bowler.",
        "T20 batting strategies: Strike rotation in middle overs, "
        "aggressive hitting in powerplay and death overs. "
        "Average T20 score is around 155-165 runs.",
        "Top T20 teams by ICC ranking 2024-2025: India, England, Australia, "
        "South Africa, New Zealand, Pakistan, West Indies, Sri Lanka, "
        "Afghanistan, Bangladesh.",
        "T20 World Cup 2026 format: Group Stage -> Super 8 -> Semi Finals -> Final. "
        "Net Run Rate (NRR) is used as tiebreaker in group stages. "
        "DLS method applied for rain-affected matches.",
    ]
    docs: List[Dict] = []
    for i, fact in enumerate(facts):
        docs.append({"id": f"fact_{i:03d}", "text": fact, "meta": {"type": "tournament_fact"}})
    print(f"  OK {len(docs)} tournament fact documents built")
    return docs


def index_all_documents() -> None:
    """Index all document types into ChromaDB."""
    print("\n" + "=" * 55)
    print("BUILDING CRICKET KNOWLEDGE BASE -> ChromaDB")
    print("=" * 55)

    collection = get_chroma_collection()

    existing = collection.count()
    if existing > 0:
        print(f"  Collection already has {existing} docs. Recreating collection...")
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        try:
            client.delete_collection("cricket_knowledge")
        except Exception:
            pass
        collection = get_chroma_collection()

    all_docs = (
        build_match_documents()
        + build_player_documents()
        + build_team_documents()
        + build_venue_documents()
        + build_tournament_facts()
    )

    batch_size = 100
    for i in range(0, len(all_docs), batch_size):
        batch = all_docs[i : i + batch_size]
        collection.upsert(
            ids=[d["id"] for d in batch],
            documents=[d["text"] for d in batch],
            metadatas=[d["meta"] for d in batch],
        )
        print(f"  Indexed {min(i + batch_size, len(all_docs))}/{len(all_docs)} docs")

    print(f"\n  Total documents in ChromaDB: {collection.count()}")
    print("=" * 55)


if __name__ == "__main__":
    index_all_documents()
