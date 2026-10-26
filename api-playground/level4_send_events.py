"""
Level 4 & 5: pretend to be a service (like GitHub or Stripe) sending you a burst of events.

Needs the receiver running:  uvicorn webhook_receiver:app --port 8001
Then run:                    python level4_send_events.py
Watch the RECEIVER's terminal to see the events get queued and processed.
"""

import asyncio
import hashlib
import hmac
import json

import httpx

RECEIVER_URL = "http://127.0.0.1:8001/webhook"
SECRET = b"practice-secret"

NEW_SAUCES = ["Ghost Pepper Gold", "Reaper Rage", "Habanero Heaven", "Jalapeño Jam", "Scorpion Sting"]


def make_event(number, name):
    return {"id": f"evt_{number}", "type": "sauce.created", "data": {"name": name}}


def sign(body: bytes, secret: bytes = SECRET) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


async def send(client, event, secret=SECRET):
    body = json.dumps(event).encode()
    response = await client.post(RECEIVER_URL, content=body, headers={"X-Signature": sign(body, secret)})
    return f"{event['id']}: {response.status_code} {response.json()}"


async def main():
    events = [make_event(n, name) for n, name in enumerate(NEW_SAUCES, start=1)]

    async with httpx.AsyncClient() as client:
        sends = [send(client, e) for e in events]
        sends.append(send(client, events[0]))  # a resend of event 1 (duplicate)
        sends.append(send(client, events[2]))  # a resend of event 3 (duplicate)
        sends.append(send(client, make_event(666, "Totally Legit Sauce"), secret=b"wrong-secret"))  # forged

        # Everything arrives at once: a burst.
        for line in await asyncio.gather(*sends):
            print(line)

    print("\nNotice: the receiver answered all of these instantly, but is still working")
    print("through its queue in the background. Check its terminal.")


asyncio.run(main())

# 🧪 Try this: change the burst to 20 events. How long does the receiver take to drain the queue?
#    Then start 2 or 3 workers in webhook_receiver.py's lifespan. What changes?
