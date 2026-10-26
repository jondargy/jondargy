"""
Level 4 & 5: receiving events (webhooks) and working through them with a queue.

This time YOU are the API. Someone else calls you whenever something happens.

Run it:  uvicorn webhook_receiver:app --port 8001
Then, in another terminal, fire events at it:  python level4_send_events.py
"""

import asyncio
import hashlib
import hmac
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

# The sender and receiver both know this secret. It's how we know an event is real.
SECRET = b"practice-secret"

queue: asyncio.Queue = asyncio.Queue()
seen_event_ids: set[str] = set()


async def worker():
    """Works through the queue one event at a time, in the background."""
    while True:
        event = await queue.get()
        await asyncio.sleep(0.5)  # pretend this is slow work: emailing someone, updating a database...
        print(f"   🔥 processed {event['type']} ({event['id']}): {event['data']['name']}  [{queue.qsize()} left]")
        queue.task_done()


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(worker())
    yield
    task.cancel()


app = FastAPI(title="Webhook Receiver", lifespan=lifespan)


@app.post("/webhook", status_code=202)
async def receive_event(request: Request, x_signature: str | None = Header(default=None)):
    body = await request.body()

    # 1. Is it real? Recompute the signature with our secret and compare.
    expected = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    if not x_signature or not hmac.compare_digest(expected, x_signature):
        print("   🚨 rejected an event with a bad signature")
        raise HTTPException(status_code=401, detail="Bad signature")

    event = json.loads(body)

    # 2. Have we seen it already? Senders resend events when they're not sure you got them.
    if event["id"] in seen_event_ids:
        print(f"   ♻️  ignored duplicate {event['id']}")
        return {"status": "duplicate, ignored"}
    seen_event_ids.add(event["id"])

    # 3. Answer fast, work later. If we did the slow work here, the sender would time out
    #    and resend, causing even more duplicates.
    await queue.put(event)
    print(f"   📥 queued {event['type']} ({event['id']})  [{queue.qsize()} waiting]")
    return {"status": "queued"}
