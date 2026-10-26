"""
Level 1: one request at a time, and what the status code tells you.

Needs the server running (normal mode):  uvicorn server:app --reload
Then run:                                python level1_one_request.py
"""

import httpx

BASE_URL = "http://127.0.0.1:8000"


def handle(response: httpx.Response):
    """Look at the status code FIRST, then decide what to do with the body."""
    code = response.status_code
    what = f"{response.request.method} {response.request.url.path} -> {code}"

    if code in (200, 201):
        print(f"✅ {what}  got: {response.json()}")
    elif code == 404:
        print(f"🔍 {what}  doesn't exist: {response.json()['detail']}")
    elif code == 422:
        # 422 = "I understood you, but what you sent is invalid". The server says exactly why.
        problems = [err["msg"] for err in response.json()["detail"]]
        print(f"🙅 {what}  bad input: {problems}")
    elif code == 429:
        print(f"🐢 {what}  rate limited, try again in {response.headers.get('Retry-After')}s")
    elif code >= 500:
        print(f"💥 {what}  the server broke, not our fault")
    else:
        print(f"🤷 {what}  unexpected: {response.text}")


with httpx.Client(base_url=BASE_URL) as client:
    handle(client.get("/sauces/1"))  # exists
    handle(client.get("/sauces/999"))  # doesn't exist
    handle(client.post("/sauces", json={"name": "", "scoville": -5}))  # invalid
    handle(client.post("/sauces", json={"name": "Jon's Revenge", "scoville": 250_000}))  # created

# 🧪 Try this: add a request for GET /sauces (all of them) and print just the names.
