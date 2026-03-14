from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ml_model import predict_outcome, load_model_and_mappings
from ml_live_model import predict_live_win_probability
from ml_toss_model import recommend_toss_decision
from ml_target_model import predict_par_score
from historical_stats import get_historical_stats


class SimulationRequest(BaseModel):
    team_a: str
    team_b: str
    venue: str
    toss_winner: str
    toss_decision: str


class FormOptionsResponse(BaseModel):
    teams: list[str]
    venues: list[str]

router = APIRouter()

@router.get("/form-options", response_model=FormOptionsResponse)
def get_form_options():
    _, team_to_idx, venue_to_idx = load_model_and_mappings()
    return FormOptionsResponse(
        teams=sorted(list(team_to_idx.keys())),
        venues=sorted(list(venue_to_idx.keys()))
    )


class SimulationResponse(BaseModel):
    winner: str
    win_probability_team_a: float
    win_probability_team_b: float
    reasons: list[str]


class LiveStateRequest(BaseModel):
    batting_team: str
    bowling_team: str
    venue: str
    runs: float
    wickets: int
    overs: float
    target: float


class LiveStateResponse(BaseModel):
    win_probability_batting: float
    win_probability_bowling: float
    explanation: str


class TossDecisionRequest(BaseModel):
    team: str
    opponent: str
    venue: str


class TossDecisionResponse(BaseModel):
    recommended_decision: str
    confidence: float


class TargetScoreRequest(BaseModel):
    venue: str


class TargetScoreResponse(BaseModel):
    par_score: float
    recommended_target_low: float
    recommended_target_high: float


@router.post("/predict", response_model=SimulationResponse)
def predict_match(req: SimulationRequest):
    # Get exact historical statistics from dataset
    historical_stats = get_historical_stats(
        team_a=req.team_a,
        team_b=req.team_b,
        venue=req.venue,
        toss_winner=req.toss_winner,
        toss_decision=req.toss_decision,
    )

    # Use Machine Learning logic to determine complex non-linear probabilities
    prob_a = predict_outcome(
        team_a=req.team_a,
        team_b=req.team_b,
        venue=req.venue,
        toss_winner=req.toss_winner,
        toss_decision=req.toss_decision,
    )
    prob_b = 1.0 - prob_a

    winner = req.team_a if prob_a >= prob_b else req.team_b

    return SimulationResponse(
        winner=winner,
        win_probability_team_a=round(prob_a, 3),
        win_probability_team_b=round(prob_b, 3),
        reasons=[
            "Prediction is calculated using the historical database."
        ] + historical_stats,
    )


@router.post("/live", response_model=LiveStateResponse)
def live_win_probability(req: LiveStateRequest):
    prob_batting = predict_live_win_probability(
        runs=req.runs,
        wickets=req.wickets,
        overs=req.overs,
        target=req.target,
    )
    prob_bowling = 1.0 - prob_batting
    explanation = (
        "Live win probability based on current run rate, required run rate, "
        "wickets lost, overs remaining, and model trained with regularization "
        "to avoid overfitting."
    )
    return LiveStateResponse(
        win_probability_batting=round(prob_batting, 3),
        win_probability_bowling=round(prob_bowling, 3),
        explanation=explanation,
    )


@router.post("/toss-decision", response_model=TossDecisionResponse)
def toss_decision(req: TossDecisionRequest):
    decision, prob = recommend_toss_decision(req.team, req.opponent, req.venue)
    return TossDecisionResponse(
        recommended_decision=decision,
        confidence=round(prob, 3),
    )


@router.post("/target-score", response_model=TargetScoreResponse)
def target_score(req: TargetScoreRequest):
    par = predict_par_score(req.venue)
    # Recommend a range around par to aim for a winning total
    low = par + 5
    high = par + 20
    return TargetScoreResponse(
        par_score=round(par, 1),
        recommended_target_low=round(low, 1),
        recommended_target_high=round(high, 1),
    )

