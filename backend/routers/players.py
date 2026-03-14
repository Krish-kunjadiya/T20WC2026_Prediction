from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models import Player


class PlayerOut(BaseModel):
    id: int
    name: str
    team: str
    role: str
    batting_style: str | None = None
    bowling_style: str | None = None
    impact_score: float | None = None

    class Config:
        from_attributes = True


router = APIRouter()


@router.get("/", response_model=List[PlayerOut])
def list_players(team: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Player)
    if team:
        query = query.filter(Player.team == team)
    return query.limit(200).all()

