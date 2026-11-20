# 2–3 minute demo video — storyboard and exact narration

**Goal:** Show all three deployed API endpoints, real multi-turn memory, a cross-session cache hit, per-message token usage, single-key failover and an all-key 503. Demonstrate the public GitHub repository briefly. Record your **actual voice** and **actual browser**; do not claim an unverified behavior works.

## Preparation before clicking Record

- Open these tabs: deployed Vercel frontend, deployed backend `/health`, and public GitHub repo. Open your terminal with the `scripts/check_contract.py` command ready if you want to use it.
- Use a sufficiently large browser window (e.g. 1440x900), zoom 90–100%, microphone on.
- Ensure `ENABLE_FAILURE_SIMULATION=true` on Railway, second API key works, and the backend has been running without restarts between the first question and the repeat.
- Avoid exposing actual environment values, accounts, keys, billing, or personal data in the recording.
- For a reliable cache demo, choose a sentence you haven't sent before in this running backend process. You can type it before recording, or run a dry rehearsal and choose a NEW sentence for the real recording.

## Timeline (target length: 2 minutes 45 seconds)

**00:00–00:20 — Introduce Relay and the architecture**

*On screen:* Deployed Vercel homepage, the layout and status pill.

*Say:* “This is Relay, a full-stack AI chat application built with React, FastAPI and SQLite. LiteLLM provides model integration, response caching and a key pool with automatic failover. Both frontend and backend are publicly deployed.”

**00:20–00:45 — Multi-turn memory + per-reply metadata**

*On screen:* Type `Remember that my project name is Atlas.` Then `What is my project name?`. Point to the assistant's metadata chips.

*Say:* “The backend saves every successful conversation turn to SQLite. I only send the latest user message; earlier turns are automatically retrieved by session ID. Each reply shows whether it was live or cached, its model, latency, and input and output tokens for that request.”

**00:45–01:15 — Cache hit in a DIFFERENT new session**

*On screen:* New conversation. Ask a fresh simple question. New conversation again. Ask the **exact same question** with the same system instructions. Point out `LIVE_INFERENCE` on the first and `LLM_CACHE` on the second. If the first answer was already cached from rehearsal, pick another unique question.

*Say:* “LiteLLM's in-memory response cache keys off the model and full message sequence, not the session ID. An identical first prompt from a different session returns the exact cached reply, preserving token usage, and the response is faster. Notice the source changes to LLM_CACHE.”

**01:15–01:50 — Simulated fallback**

*On screen:* Open Configuration → failure mode `key_1 → 429`. Send a fresh message. Open Request Inspector and show the JSON: `key_id: key_2`, `fallback_attempts: 1`, `resolution_source: LIVE_INFERENCE`.

*Say:* “This test header makes the first key act as though it was rate-limited. The backend skips that key and uses key two to return a genuine model response. The client receives a normal 200 response, and the metadata records one fallback attempt.”

**01:50–02:10 — Every key fails**

*On screen:* Configuration → `All keys → 429`. Send a question. Show readable error. Optionally open DevTools → Network and click the failed chat call to reveal its HTTP 503 and JSON `detail`. Don't call it a success response.

*Say:* “When every key fails, the backend responds with a clean JSON 503 instead of crashing, and does not add the failed request to SQLite history.”

**02:10–02:35 — All API endpoints and history**

*On screen:* Turn simulation back to Normal. Open backend `/health` tab; open Request Inspector → session history link of a **successful** chat (ensure you've selected a chat with successful messages). Briefly show public GitHub repo with `backend`, `frontend`, Docker Compose and tests.

*Say:* “The required endpoints are GET health, POST chat, and GET session messages. Health verifies the key pool and SQLite readiness. The history endpoint returns ordered messages from SQLite. The repository includes multi-stage Dockerfiles, Docker Compose, a Makefile, tests, and deployment instructions.”

**02:35–02:45 — Close**

*Say:* “That is Relay: multi-turn memory, transparent token tracking, correct caching, and graceful provider failover, ready for verification through the deployed links.”

## Critical recording tips

- A normal browser cannot send custom headers just by entering a URL. Use the UI Configuration dropdown, which sends `X-Simulate-Failure` through `fetch`.
- For cache demonstration, **do not** repeat in the same session; history changes the cache key.
- The spec requires a **2–3 minute** screen recording with voice. Trim excessive typing/waiting but do not splice in misleading responses or present mocked test responses as live inference.
- Make the video **publicly viewable without login**; test the final video link in a private/incognito window.
