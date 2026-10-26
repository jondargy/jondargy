"""
Level 3: when things go wrong. Retries, backoff, and idempotency.

Needs the server running in FLAKY mode:  FLAKY=1 uvicorn server:app --reload
Then run:                                python level3_retries.py
"""

import asyncio
import random
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8000"

# Worth retrying: the problem is temporary. NOT worth retrying: 404, 422... those
# will fail the exact same way every time.
RETRYABLE = {429, 500, 502, 503, 504}


async def request_with_retries(client, method, url, max_attempts=6, **kwargs):
    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in RETRYABLE:
                return response
            reason = str(response.status_code)
        except httpx.TransportError as error:  # timeouts, dropped connections...
            reason = type(error).__name__

        if attempt == max_attempts:
            raise RuntimeError(f"{method} {url} still failing after {max_attempts} tries ({reason})")

        # Exponential backoff: wait 0.25s, 0.5s, 1s, 2s (never more) plus a little randomness
        # ("jitter") so a crowd of clients doesn't all retry at the exact same instant.
        wait = min(0.25 * 2 ** (attempt - 1), 2) + random.uniform(0, 0.1)
        print(f"   ↻ {method} {url} got {reason}, retry #{attempt} in {wait:.2f}s")
        await asyncio.sleep(wait)


async def count_sauces_named(client, name):
    response = await request_with_retries(client, "GET", "/sauces")
    return sum(1 for s in response.json() if s["name"] == name)


async def create_and_count(client, sauce, headers=None):
    try:
        await request_with_retries(client, "POST", "/sauces", json=sauce, headers=headers)
    except RuntimeError as error:
        # Giving up is a valid outcome. Say so clearly instead of crashing.
        print(f"   🏳️  gave up: {error}")
    print(f"   copies of '{sauce['name']}' on the server: {await count_sauces_named(client, sauce['name'])}")


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        print("Part 1: fetch 5 sauces from a flaky server")
        results = await asyncio.gather(
            *(request_with_retries(client, "GET", f"/sauces/{i}") for i in range(1, 6)),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                print("   ❌", r)
            else:
                print("   ✅", r.json()["name"])

        print("\nPart 2: create a sauce WITHOUT an idempotency key (retries can create duplicates)")
        run = uuid.uuid4().hex[:4]  # tags this run's sauces, so each run counts from zero
        await create_and_count(client, {"name": f"Duplicate Danger #{run}", "scoville": 9_000})

        print("\nPart 3: create a sauce WITH an idempotency key (retries are safe)")
        key = str(uuid.uuid4())  # one key per *intended* action, reused on every retry of it
        await create_and_count(client, {"name": f"Safe Retry Sauce #{run}", "scoville": 9_000}, {"Idempotency-Key": key})


asyncio.run(main())

# 🧪 Try this: run it a few times. Part 2 sometimes ends with 2+ copies. Part 3 never does. Why?
