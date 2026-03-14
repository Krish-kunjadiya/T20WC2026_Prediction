import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from db import get_db
from models import Player, PlayerEmbedding
from ml_model import predict_outcome
from ml_live_model import predict_live_win_probability


class StrategyRequest(BaseModel):
  question: str
  current_over: int | None = None
  batting_team: str | None = None
  bowling_team: str | None = None
  runs: float | None = None
  wickets: int | None = None
  target: float | None = None
  venue: str | None = None


class StrategyResponse(BaseModel):
  answer: str


router = APIRouter()


def build_context_snippets(db: Session, batting_team: str | None, bowling_team: str | None):
  q = db.query(Player)
  if batting_team:
    q = q.filter(Player.team == batting_team)
  top_batters = q.order_by(Player.impact_score.desc().nullslast()).limit(5).all()

  q2 = db.query(Player)
  if bowling_team:
    q2 = q2.filter(Player.team == bowling_team)
  top_bowlers = q2.order_by(Player.impact_score.desc().nullslast()).limit(5).all()

  def describe(players, label):
    lines = [label]
    for p in players:
      lines.append(
        f"- {p.name} ({p.role or 'Unknown'}) | Impact: "
        f"{p.impact_score:.2f}" if p.impact_score is not None else "-"
      )
    return "\n".join(lines)

  return describe(top_batters, "Key batters:"), describe(top_bowlers, "Key bowlers:")


def retrieve_similar_players(db: Session, question: str, k: int = 5):
  if not os.getenv("OPENAI_API_KEY"):
    return []

  embeddings = OpenAIEmbeddings()
  vec = embeddings.embed_query(question)

  stmt = text(
    """
    SELECT p.name, p.team, p.role, p.impact_score
    FROM player_embeddings pe
    JOIN players p ON p.id = pe.player_id
    ORDER BY pe.embedding <-> :embedding
    LIMIT :k
    """
  )
  rows = db.execute(stmt, {"embedding": vec, "k": k}).fetchall()

  snippets = []
  for r in rows:
    impact_str = (
      f"{float(r.impact_score):.2f}" if r.impact_score is not None else "Unknown"
    )
    snippets.append(
      f"{r.name} ({r.team}, {r.role or 'Unknown'}) – impact {impact_str}"
    )
  return snippets


@router.post("/chat", response_model=StrategyResponse)
def strategy_chat(req: StrategyRequest, db: Session = Depends(get_db)):
  if not os.getenv("OPENAI_API_KEY"):
    return StrategyResponse(
      answer=(
        "Strategy Copilot requires an OPENAI_API_KEY to be set. "
        "Once configured, it will use player embeddings and win-probability models "
        "to suggest optimal tactics."
      )
    )

  llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)

  batters_ctx, bowlers_ctx = build_context_snippets(
    db, req.batting_team, req.bowling_team
  )
  similar_players = retrieve_similar_players(db, req.question, k=5)

  live_prob_text = ""
  if (
    req.runs is not None
    and req.wickets is not None
    and req.current_over is not None
    and req.target is not None
  ):
    live_prob = predict_live_win_probability(
      runs=req.runs,
      wickets=req.wickets,
      overs=req.current_over,
      target=req.target,
    )
    live_prob_text = (
      f"Estimated live win probability for batting side: {live_prob:.2%}.\n"
    )

  system_prompt = (
    "You are a T20 cricket strategy analyst. "
    "Use the provided player profiles, impact scores, and win probabilities "
    "to recommend tactical decisions such as who should bowl next, field settings, "
    "and batting strategies. Explain your reasoning clearly in 3–5 concise bullet points."
  )

  context = (
    f"{batters_ctx}\n\n{bowlers_ctx}\n\n"
    f"Players most relevant to the question:\n"
    + "\n".join(f"- {s}" for s in similar_players)
    + "\n\n"
    + live_prob_text
  )

  user_prompt = (
    f"Match situation:\n"
    f"- Batting team: {req.batting_team}\n"
    f"- Bowling team: {req.bowling_team}\n"
    f"- Venue: {req.venue}\n"
    f"- Current over: {req.current_over}\n"
    f"- Runs: {req.runs}\n"
    f"- Wickets: {req.wickets}\n"
    f"- Target: {req.target}\n\n"
    f"Coach's question: {req.question}\n\n"
    f"Context:\n{context}"
  )

  messages = [
    ("system", system_prompt),
    ("user", user_prompt),
  ]

  response = llm.invoke(messages)
  return StrategyResponse(answer=response.content)

