"""
Level 2: many requests at once.

Needs the server running (normal mode):  uvicorn server:app --reload
Then run:                                python level2_many_requests.py
"""

import asyncio
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"
SAUCE_IDS = [1, 2, 3, 4, 5, 999] * 3  # 18 requests, a few of which will 404


def one_by_one():
    """The slow way: wait for each answer before asking the next question."""
    with httpx.Client(base_url=BASE_URL) as client:
        return [client.get(f"/sauces/{i}") for i in SAUCE_IDS]


async def all_at_once():
    """The fast way: send them all, then wait for all the answers together."""
    # A semaphore is a bouncer: at most 10 requests in flight, so we don't flood the server.
    bouncer = asyncio.Semaphore(10)

    async with httpx.AsyncClient(base_url=BASE_URL) as client:

        async def fetch(sauce_id):
            async with bouncer:
                return await client.get(f"/sauces/{sauce_id}")

        # return_exceptions=True: if one request blows up (say, a timeout), we get the
        # error back in the list instead of losing every other result.
        return await asyncio.gather(*(fetch(i) for i in SAUCE_IDS), return_exceptions=True)


def summarize(label, results, seconds):
    found = [r.json()["name"] for r in results if isinstance(r, httpx.Response) and r.status_code == 200]
    missing = sum(1 for r in results if isinstance(r, httpx.Response) and r.status_code == 404)
    errors = sum(1 for r in results if isinstance(r, Exception))
    print(f"{label}: {len(results)} requests in {seconds:.2f}s")
    print(f"   found {len(found)}, missing {missing}, errors {errors}")


start = time.perf_counter()
summarize("🐌 One by one", one_by_one(), time.perf_counter() - start)

start = time.perf_counter()
summarize("🚀 All at once", asyncio.run(all_at_once()), time.perf_counter() - start)

# 🧪 Try this: change the Semaphore from 10 to 1, then to 100. What happens to the time, and why?
