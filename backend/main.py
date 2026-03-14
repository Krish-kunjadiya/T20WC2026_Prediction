from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import simulator, players, strategy


load_dotenv()

app = FastAPI(title="T20WC 2026 Strategy Platform", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(simulator.router, prefix="/api/simulator", tags=["simulator"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["strategy"])

