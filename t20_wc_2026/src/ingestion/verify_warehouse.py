"""Verify all data-warehouse layers are created and populated."""
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

CHECKS: dict[str, str] = {
    # Bronze
    "bronze.raw_matches":               "SELECT COUNT(*) FROM bronze.raw_matches",
    "bronze.raw_batting_stats":         "SELECT COUNT(*) FROM bronze.raw_batting_stats",
    "bronze.raw_bowling_stats":         "SELECT COUNT(*) FROM bronze.raw_bowling_stats",
    "bronze.raw_squads":                "SELECT COUNT(*) FROM bronze.raw_squads",
    "bronze.raw_venues":                "SELECT COUNT(*) FROM bronze.raw_venues",
    "bronze.raw_key_scorecards":        "SELECT COUNT(*) FROM bronze.raw_key_scorecards",
    "bronze.raw_deliveries":            "SELECT COUNT(*) FROM bronze.raw_deliveries",
    # Silver
    "silver.clean_matches":             "SELECT COUNT(*) FROM silver.clean_matches",
    "silver.clean_deliveries":          "SELECT COUNT(*) FROM silver.clean_deliveries",
    "silver.clean_players":             "SELECT COUNT(*) FROM silver.clean_players",
    "silver.clean_venues":              "SELECT COUNT(*) FROM silver.clean_venues",
    # Gold dimensions
    "gold.dim_team":                    "SELECT COUNT(*) FROM gold.dim_team",
    "gold.dim_venue":                   "SELECT COUNT(*) FROM gold.dim_venue",
    "gold.dim_player":                  "SELECT COUNT(*) FROM gold.dim_player",
    "gold.dim_date":                    "SELECT COUNT(*) FROM gold.dim_date",
    "gold.dim_match":                   "SELECT COUNT(*) FROM gold.dim_match",
    # Gold fact
    "gold.fact_match_performance":      "SELECT COUNT(*) FROM gold.fact_match_performance",
    # Live simulator
    "public.live_ball_events":          "SELECT COUNT(*) FROM live_ball_events",
}


def verify_warehouse() -> None:
    """Print a status report for every warehouse table."""
    print("\n📊  DATA WAREHOUSE — VERIFICATION REPORT")
    print("═" * 55)

    layers = {"bronze": [], "silver": [], "gold": [], "public": []}
    for name, query in CHECKS.items():
        layer = name.split(".")[0]
        try:
            with engine.connect() as conn:
                count = conn.execute(text(query)).scalar()
            status = "✅" if count and count > 0 else "⚠️ "
            layers[layer].append((status, name, count))
        except Exception as exc:
            layers[layer].append(("❌", name, f"ERROR — {exc}"))

    for layer, rows in layers.items():
        if rows:
            print(f"\n  [{layer.upper()}]")
            for status, name, val in rows:
                print(f"    {status}  {name:<40} {str(val):>8} rows")

    print("\n" + "═" * 55)


if __name__ == "__main__":
    verify_warehouse()
