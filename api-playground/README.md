# 🌶️ API Playground

A hands-on way to learn how APIs *really* work, from one simple request up to handling a flood of events. Each level is one small Python file you run and poke at.

| Level | File | What you learn |
|---|---|---|
| 1 | `level1_one_request.py` | Requests, responses, and what status codes mean |
| 2 | `level2_many_requests.py` | Sending lots of requests at once (async) |
| 3 | `level3_retries.py` | Surviving failures: retries, backoff, idempotency |
| 4–5 | `webhook_receiver.py` + `level4_send_events.py` | Receiving events (webhooks) and queueing them |

The server you'll talk to is `server.py`, a tiny **Hot Sauce API**.

---

## 🚀 Get started (no installs needed)

1. On GitHub, open this repo, tap the green **Code** button → **Codespaces** → **Create codespace**.
2. Wait a minute while it sets up. It installs everything for you.
3. You'll get VS Code in your browser with a **terminal** at the bottom. Type:

   ```
   cd api-playground
   ```

> **Running on your own computer instead?** Install Python 3, then run `pip install -r requirements.txt` inside this folder.

You'll need **two terminals**: one runs a server, the other runs the level scripts. In Codespaces, click the **+** in the terminal panel to open a second one (and `cd api-playground` in it too).

---

## Level 1: one request

**Terminal 1** (start the API):
```
uvicorn server:app --reload
```
**Terminal 2:**
```
python level1_one_request.py
```

You'll see four requests and how each status code gets handled:

```
✅ GET /sauces/1 -> 200      got the sauce
🔍 GET /sauces/999 -> 404    doesn't exist
🙅 POST /sauces -> 422       bad input (and the server says exactly why)
✅ POST /sauces -> 201       created
```

**The lesson:** always check the status code *before* trusting the response.

| Code | Means | What you do |
|---|---|---|
| 200 / 201 | OK / Created | Use the data |
| 404 | Not found | Tell the user, don't retry |
| 422 | Your input is invalid | Fix what you sent, don't retry |
| 429 | Too many requests | Wait, then retry |
| 500+ | Server broke | Wait, then retry |

💡 **Bonus:** with the server running, open `/docs` on port 8000 (Codespaces pops up a link from the **Ports** tab). It's a clickable page where you can try every endpoint by hand.

---

## Level 2: many requests at once

Same server. **Terminal 2:**
```
python level2_many_requests.py
```

```
🐌 One by one: 18 requests in 3.75s
🚀 All at once: 18 requests in 0.51s
```

**The lesson:** most of an API call is *waiting*. Instead of waiting for each answer before asking the next question, send them all and wait for the answers together. That's what `async`/`await` and `asyncio.gather` do. The **semaphore** caps how many requests are in flight at once, so you don't hammer the server.

---

## Level 3: when things go wrong

Restart the server in **flaky mode**. In Terminal 1, press `Ctrl+C`, then:
```
FLAKY=1 uvicorn server:app --reload
```
Now it randomly fails with 500s and 429s, like real APIs on a bad day. **Terminal 2:**
```
python level3_retries.py
```

You'll see retries happening (`↻ got 429, retry #1 in 0.28s`), and then the sneaky part:

```
copies of 'Duplicate Danger' on the server: 2     ← oops
copies of 'Safe Retry Sauce' on the server: 1     ← always exactly 1
```

**The lessons:**
- **Retry only temporary failures** (429, 500s, timeouts). A 404 will fail the same way forever.
- **Back off:** wait a bit longer between each retry, plus a little randomness.
- **Idempotency:** sometimes the server *did* the work but crashed before telling you. Retry blindly and you create duplicates (or charge someone twice!). Sending an `Idempotency-Key` lets the server recognise "I've already done this one" and hand back the original answer.

Run it a few times. Duplicates only happen sometimes, which is exactly what makes them nasty in real life.

---

## Levels 4 & 5: events coming to YOU (webhooks)

So far *you* asked the server for things. With **webhooks**, a service (GitHub, Stripe, Discord...) calls *you* the moment something happens. Your code becomes the API.

**Terminal 1** (`Ctrl+C` the old server first):
```
uvicorn webhook_receiver:app --port 8001
```
**Terminal 2** (pretends to be a service sending a burst of events):
```
python level4_send_events.py
```

Watch **Terminal 1**:
```
📥 queued sauce.created (evt_1)  [1 waiting]
...
♻️  ignored duplicate evt_1
🚨 rejected an event with a bad signature
🔥 processed sauce.created (evt_1): Ghost Pepper Gold  [4 left]
...
```

**The lessons:** every webhook receiver does these three things:
1. **Check the signature.** Anyone can send you a request. The signature proves it really came from the service (they share a secret with you).
2. **Ignore duplicates.** Services resend events if they aren't sure you got them. Remember the event IDs you've seen.
3. **Answer fast, work later.** Put the event in a **queue**, reply right away, and let a background **worker** process it. If you're slow to reply, the sender times out and resends, making more duplicates.

---

## 🧪 Challenges

Each file ends with a `Try this` line. Some bigger ones:

- Add a `DELETE /sauces/{id}` endpoint to `server.py`, then call it from a script.
- Start 3 workers in `webhook_receiver.py` instead of 1. How much faster does the queue drain? Does processing order still hold?
- Add an `"order"` number to each event and make the receiver ignore events that arrive out of order.
- Point a script at a real public API, like `https://api.github.com/users/jondargy`.
