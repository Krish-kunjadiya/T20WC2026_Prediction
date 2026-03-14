"""FastAPI backend for ML predictions and analytics metadata."""

from __future__ import annotations

import json
import os
import pickle
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text


load_dotenv()

app = FastAPI(
    title="T20 WC 2026 Prediction API",
    description="ML-powered cricket analytics API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
MODELS_DIR = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")


def load_model(filename: str) -> Any:
    path = os.path.join(MODELS_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "models": [f for f in os.listdir(MODELS_DIR) if f.endswith(".pkl")] if os.path.exists(MODELS_DIR) else [],
    }


class MatchRequest(BaseModel):
    team_a: str
    team_b: str
    toss_winner: str
    toss_decision: str = "bat"
    is_knockout: int = 0


@app.post("/predict/match")
def predict_match(req: MatchRequest) -> dict[str, Any]:
    artifact = load_model("match_outcome_xgb.pkl")
    if not artifact:
        raise HTTPException(status_code=500, detail="Model not found")

    matches = pd.read_sql("SELECT * FROM silver.clean_matches", engine)
    deliveries = pd.read_sql(
        "SELECT batting_team, bowling_team, batsman_runs, total_runs, is_wicket, over_num FROM silver.clean_deliveries",
        engine,
    )

    def wr(team: str) -> float:
        played = len(matches[(matches["team1"] == team) | (matches["team2"] == team)])
        won = len(matches[matches["winner"] == team])
        return float(won / max(played, 1))

    def avg_runs(team: str, col: str = "batsman_runs") -> float:
        val = deliveries[deliveries["batting_team"] == team][col].mean()
        return float(val) if pd.notna(val) else 0.0

    team_a_six_rate = (deliveries[deliveries["batting_team"] == req.team_a]["batsman_runs"] == 6).mean()
    team_b_six_rate = (deliveries[deliveries["batting_team"] == req.team_b]["batsman_runs"] == 6).mean()

    team_a_four_rate = (deliveries[deliveries["batting_team"] == req.team_a]["batsman_runs"] == 4).mean()
    team_b_four_rate = (deliveries[deliveries["batting_team"] == req.team_b]["batsman_runs"] == 4).mean()

    da1 = deliveries[(deliveries["batting_team"] == req.team_a) & (deliveries["over_num"] >= 16)]["total_runs"].mean()
    db1 = deliveries[(deliveries["batting_team"] == req.team_b) & (deliveries["over_num"] >= 16)]["total_runs"].mean()
    death_run_rate_diff = float(da1 if pd.notna(da1) else 0) - float(db1 if pd.notna(db1) else 0)

    wa1 = deliveries[(deliveries["bowling_team"] == req.team_a) & (deliveries["over_num"] >= 16)]["is_wicket"].mean()
    wb1 = deliveries[(deliveries["bowling_team"] == req.team_b) & (deliveries["over_num"] >= 16)]["is_wicket"].mean()
    death_wkt_rate_diff = float(wa1 if pd.notna(wa1) else 0) - float(wb1 if pd.notna(wb1) else 0)

    features = {
        "run_rate_diff": avg_runs(req.team_a) - avg_runs(req.team_b),
        "six_rate_diff": float(team_a_six_rate) - float(team_b_six_rate),
        "four_rate_diff": float(team_a_four_rate) - float(team_b_four_rate),
        "pp_run_rate_diff": avg_runs(req.team_a, "total_runs") - avg_runs(req.team_b, "total_runs"),
        "death_run_rate_diff": death_run_rate_diff,
        "wicket_rate_diff": float(deliveries[deliveries["bowling_team"] == req.team_a]["is_wicket"].mean())
        - float(deliveries[deliveries["bowling_team"] == req.team_b]["is_wicket"].mean()),
        "death_wkt_rate_diff": death_wkt_rate_diff,
        "economy_diff": float(deliveries[deliveries["bowling_team"] == req.team_a]["total_runs"].mean())
        - float(deliveries[deliveries["bowling_team"] == req.team_b]["total_runs"].mean()),
        "win_rate_t1": wr(req.team_a),
        "win_rate_t2": wr(req.team_b),
        "win_rate_diff": wr(req.team_a) - wr(req.team_b),
        "toss_team1": 1 if req.toss_winner == req.team_a else 0,
        "toss_bat_first": 1 if req.toss_decision == "bat" else 0,
        "toss_advantage": (1 if req.toss_winner == req.team_a else 0) * (1 if req.toss_decision == "bat" else 0),
        "is_knockout": req.is_knockout,
    }

    model = artifact["model"]
    feat_cols = artifact["features"]
    X = pd.DataFrame([features])[feat_cols].fillna(0)
    prob = model.predict_proba(X)[0]

    return {
        "team_a": req.team_a,
        "team_b": req.team_b,
        "prob_team_a": round(float(prob[1]) * 100, 1),
        "prob_team_b": round(float(prob[0]) * 100, 1),
        "predicted_winner": req.team_a if prob[1] > 0.5 else req.team_b,
    }


class ScoreRequest(BaseModel):
    total_balls: int = 120
    wickets_lost: int = 2
    sixes: int = 5
    fours: int = 10
    pp_runs: int = 50
    pp_run_rate: float = 8.3
    boundary_pct: float = 0.15


@app.post("/predict/score")
def predict_score(req: ScoreRequest) -> dict[str, Any]:
    artifact = load_model("score_predictor_lgbm.pkl")
    if not artifact:
        raise HTTPException(status_code=500, detail="Model not found")
    model = artifact["model"]
    feat_cols = artifact["features"]
    X = pd.DataFrame([req.model_dump()])[feat_cols]
    pred = int(model.predict(X)[0])
    return {"predicted_score": pred, "classification": "above_avg" if pred > 160 else "below_avg"}


@app.get("/teams")
def get_teams() -> dict[str, list[str]]:
    teams = pd.read_sql("SELECT DISTINCT team_name FROM gold.dim_team ORDER BY team_name", engine)
    return {"teams": teams["team_name"].dropna().tolist()}


@app.get("/players/{country}")
def get_players(country: str) -> dict[str, Any]:
    sql = text(
        """
        SELECT player_name, role, runs, batting_avg, strike_rate, wickets, economy
        FROM silver.clean_players
        WHERE country = :country
        ORDER BY runs DESC
        LIMIT 20
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={"country": country})
    return {"players": df.to_dict(orient="records")}


@app.get("/metrics")
def get_metrics() -> Any:
    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Metrics not found")

class QueryRequest(BaseModel):
    sql: str

@app.post("/query")
def execute_query(req: QueryRequest) -> dict[str, Any]:
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            df = pd.read_sql(text(req.sql), conn)
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class ChatRequest(BaseModel):
    prompt: str
    match_context: str | None = None

@app.post("/chat")
def chat_endpoint(req: ChatRequest) -> dict[str, str]:
    try:
        from genai.rag_engine import ask_cricai
        answer = ask_cricai(req.prompt, match_context=req.match_context)
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/kpis")
def get_dashboard_kpis(session=Depends(get_db)):
    # Total matches
    total_matches = session.execute(text("SELECT COUNT(*) FROM silver_matches")).scalar()
    
    # Teams count
    total_teams = session.execute(text("SELECT COUNT(DISTINCT team) FROM (SELECT team_type_a AS team FROM silver_matches UNION SELECT team_type_b FROM silver_matches) x")).scalar()
    
    # Average score
    avg_score = session.execute(text("SELECT AVG(total_runs) FROM (SELECT match_id, inning, sum(runs_total) as total_runs FROM bronze_deliveries GROUP BY match_id, inning) x")).scalar()
    
    return {
        "total_matches": total_matches,
        "total_teams": total_teams,
        "avg_first_innings_score": int(avg_score) if avg_score else 165
    }
@app.get("/dashboard/charts")
def get_dashboard_charts(session=Depends(get_db)):
    # 1. Evolution Data (Yearly avg score & strike rate)
    year_query = text("""
        SELECT 
            EXTRACT(YEAR FROM m.date) as year,
            AVG(d.inning_total) as avgScore,
            (SUM(d.inning_total)*1.0 / NULLIF(SUM(d.ball_count), 0)) * 100 as strikeRate
        FROM silver_matches m
        JOIN (
            SELECT match_id, inning, SUM(runs_total) as inning_total, COUNT(ball) as ball_count
            FROM bronze_deliveries
            WHERE inning = 1
            GROUP BY match_id, inning
        ) d ON m.id = d.match_id
        GROUP BY EXTRACT(YEAR FROM m.date)
        ORDER BY year
    """)
    evo_res = session.execute(year_query).fetchall()
    
    # 2. Survival Data
    surv_query = text("""
        SELECT 
            over_num as over, 
            AVG(runs_total) * 6 as expRuns, 
            AVG(CASE WHEN is_wicket = true THEN 1.0 ELSE 0.0 END) * 100 as wktProb
        FROM bronze_deliveries
        GROUP BY over_num
        ORDER BY over_num
    """)
    surv_res = session.execute(surv_query).fetchall()

    # 3. Win Distribution
    win_query = text("""
        SELECT 
            CASE 
                WHEN toss_decision = 'bat' AND toss_winner = winner THEN 'Bat First Win'
                WHEN toss_decision = 'field' AND toss_winner != winner THEN 'Bat First Win'
                WHEN toss_decision = 'field' AND toss_winner = winner THEN 'Bowl First Win'
                WHEN toss_decision = 'bat' AND toss_winner != winner THEN 'Bowl First Win'
                ELSE 'Tie/No Result' 
            END as name,
            COUNT(*) as value
        FROM silver_matches
        WHERE winner IS NOT NULL AND winner != 'NA'
        GROUP BY 1
    """)
    win_res = session.execute(win_query).fetchall()

    return {
        "evolutionData": [{"year": int(r[0]), "avgScore": int(r[1]) if r[1] else 0, "strikeRate": round(float(r[2]), 2) if r[2] else 0} for r in evo_res if r[0]],
        "survivalData": [{"over": int(r[0]), "expRuns": round(float(r[1]), 2) if r[1] else 0, "wktProb": round(float(r[2]), 2) if r[2] else 0} for r in surv_res if r[0] is not None],
        "winDistributionData": [{"name": str(r[0]), "value": int(r[1])} for r in win_res]
    }
