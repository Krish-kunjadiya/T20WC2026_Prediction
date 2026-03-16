"""Data quality checks for Silver layer tables.

Lightweight checks similar to Great Expectations expectations for hackathon speed.
Writes JSON report to results/quality_report.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)

results: list[dict[str, object]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    """Record and print a single quality check result."""
    status = "PASS" if passed else "FAIL"
    print(f"  {status:<4}  {name:<45} {detail}")
    results.append({"check": name, "passed": bool(passed), "detail": detail})


def run_quality_checks() -> None:
    """Run all silver-layer checks and persist summary report."""
    print("\n" + "=" * 60)
    print("DATA QUALITY CHECKS - SILVER LAYER")
    print("=" * 60)

    matches = pd.read_sql("SELECT * FROM silver.clean_matches", engine)
    deliveries = pd.read_sql("SELECT * FROM silver.clean_deliveries LIMIT 10000", engine)
    players = pd.read_sql("SELECT * FROM silver.clean_players", engine)

    print("\nMATCHES:")
    check("Row count > 50", len(matches) > 50, f"({len(matches)} rows)")
    check("No duplicate match_ids", matches["match_id"].nunique() == len(matches), f"({matches['match_id'].nunique()} unique)")
    check("winner has no nulls", matches["winner"].isnull().sum() == 0, f"({matches['winner'].isnull().sum()} nulls)")
    check(
        "toss_decision values valid",
        matches["toss_decision"].astype(str).str.lower().isin(["bat", "field"]).all(),
        f"(values: {matches['toss_decision'].dropna().astype(str).unique()[:4]})",
    )
    check("match_date is not null", matches["match_date"].isnull().sum() == 0, f"({matches['match_date'].isnull().sum()} nulls)")

    print("\nDELIVERIES:")
    check("Row count > 1000", len(deliveries) > 1000, f"({len(deliveries)} rows)")
    check("runs are non-negative", (deliveries["total_runs"] >= 0).all(), f"(min={deliveries['total_runs'].min()})")
    check(
        "over_num between 0 and 20",
        deliveries["over_num"].between(0, 20).all(),
        f"(range: {deliveries['over_num'].min()}-{deliveries['over_num'].max()})",
    )
    check("batsman has no nulls", deliveries["batsman"].isnull().sum() == 0, f"({deliveries['batsman'].isnull().sum()} nulls)")

    print("\nPLAYERS:")
    check("Row count > 10", len(players) > 10, f"({len(players)} rows)")
    check("No duplicate player_ids", players["player_id"].nunique() == len(players), f"({players['player_id'].nunique()} unique)")
    check("strike_rate non-negative", (players["strike_rate"] >= 0).all(), f"(min={players['strike_rate'].min()})")
    check("batting_avg non-negative", (players["batting_avg"] >= 0).all(), f"(min={players['batting_avg'].min()})")

    passed = sum(1 for r in results if bool(r["passed"]))
    total = len(results)
    pct = round((passed / total) * 100) if total else 0
    print("\n" + "=" * 60)
    print(f"QUALITY SCORE: {passed}/{total} checks passed ({pct}%)")
    print("=" * 60)

    os.makedirs("results", exist_ok=True)
    with open("results/quality_report.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "run_at": datetime.now().isoformat(),
                "score": f"{passed}/{total}",
                "checks": results,
            },
            handle,
            indent=2,
        )
    print("Saved report -> results/quality_report.json")


if __name__ == "__main__":
    run_quality_checks()
