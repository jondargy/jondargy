"""
The Hot Sauce API — a tiny practice server.

Run it:          uvicorn server:app --reload
Run it flaky:    FLAKY=1 uvicorn server:app --reload
Click around:    http://127.0.0.1:8000/docs
"""

import asyncio
import os
import random

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Hot Sauce API")

# Flaky mode makes the server fail at random, like real APIs sometimes do.
FLAKY = os.getenv("FLAKY") == "1"

# Our "database" is just a dictionary in memory. It resets when the server restarts.
SAUCES = {
    1: {"id": 1, "name": "Sriracha", "scoville": 2_200},
    2: {"id": 2, "name": "Tabasco", "scoville": 5_000},
    3: {"id": 3, "name": "Cholula", "scoville": 3_600},
    4: {"id": 4, "name": "Da Bomb Beyond Insanity", "scoville": 135_600},
    5: {"id": 5, "name": "Mad Dog 357", "scoville": 357_000},
}

# Remembers the answer we gave for each Idempotency-Key (see level 3).
ANSWERED_KEYS: dict[str, dict] = {}


class NewSauce(BaseModel):
    """What a client must send to create a sauce. FastAPI rejects anything else with a 422."""

    name: str = Field(min_length=1)
    scoville: int = Field(ge=0)


@app.middleware("http")
async def slow_and_maybe_flaky(request: Request, call_next):
    if request.url.path.startswith(("/docs", "/openapi")):
        return await call_next(request)

    # Every request takes a moment, like a real network call. This is what makes
    # sending requests one-by-one slow (level 2).
    await asyncio.sleep(0.2)

    if FLAKY:
        roll = random.random()
        if roll < 0.15:
            return JSONResponse({"detail": "Server had a bad day"}, status_code=500)
        if roll < 0.30:
            return JSONResponse(
                {"detail": "Too many requests, slow down"},
                status_code=429,
                headers={"Retry-After": "1"},
            )

    return await call_next(request)


@app.get("/sauces")
def list_sauces():
    return list(SAUCES.values())


@app.get("/sauces/{sauce_id}")
def get_sauce(sauce_id: int):
    if sauce_id not in SAUCES:
        raise HTTPException(status_code=404, detail=f"No sauce with id {sauce_id}")
    return SAUCES[sauce_id]


@app.post("/sauces", status_code=201)
def create_sauce(sauce: NewSauce, idempotency_key: str | None = Header(default=None)):
    # Seen this key before? Then this is a retry: hand back the same answer
    # instead of creating the sauce a second time.
    if idempotency_key and idempotency_key in ANSWERED_KEYS:
        return ANSWERED_KEYS[idempotency_key]

    new_id = max(SAUCES) + 1
    SAUCES[new_id] = {"id": new_id, **sauce.model_dump()}
    if idempotency_key:
        ANSWERED_KEYS[idempotency_key] = SAUCES[new_id]

    # The sneakiest failure: the work got done, but the client never hears back.
    # A naive retry now creates a duplicate.
    if FLAKY and random.random() < 0.3:
        raise HTTPException(status_code=500, detail="Saved it, then crashed before replying")

    return SAUCES[new_id]
