import os

from sqlalchemy import text
from sqlalchemy.orm import Session
from langchain_openai import OpenAIEmbeddings

from db import engine, SessionLocal
from models import Base, Player, PlayerEmbedding


def ensure_vector_extension():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def build_profile(player: Player) -> str:
    parts = [
        f"Name: {player.name}",
        f"Team: {player.team}",
        f"Role: {player.role or 'Unknown'}",
    ]
    if player.batting_style:
        parts.append(f"Batting: {player.batting_style}")
    if player.bowling_style:
        parts.append(f"Bowling: {player.bowling_style}")
    if player.impact_score is not None:
        parts.append(f"Impact score: {player.impact_score:.2f}")
    return " | ".join(parts)


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to generate embeddings.")

    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)

    embeddings = OpenAIEmbeddings()

    db: Session = SessionLocal()
    try:
        players = db.query(Player).all()
        for p in players:
            profile_text = build_profile(p)
            vector = embeddings.embed_query(profile_text)

            existing = (
                db.query(PlayerEmbedding)
                .filter(PlayerEmbedding.player_id == p.id)
                .one_or_none()
            )
            if existing:
                existing.embedding = vector
            else:
                db.add(
                    PlayerEmbedding(
                        player_id=p.id,
                        embedding=vector,
                    )
                )
        db.commit()
        print(f"Embedded {len(players)} players into player_embeddings.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

