# Final 10/10-oriented submission checklist

**Do not submit until these are true.** A polished frontend alone cannot pass the evaluator.

## Public deliverables

- [ ] `https://...vercel.app` frontend works without login.
- [ ] `https://...up.railway.app` backend works without login.
- [ ] Public GitHub repository includes `backend/`, `frontend/`, `docker-compose.yml`, `Makefile`, `.env.example`, `README.md`, tests and both multi-stage Dockerfiles.
- [ ] 2–3 minute video includes your voice and deployed app.
- [ ] Video demonstrates all endpoints plus cache hit plus `X-Simulate-Failure` failover.
- [ ] README placeholders replaced with real URLs; setup and AI-tools disclosure accurate.
- [ ] Submission form completed within 24 hours after receiving assignment.

## Exact API acceptance

- [ ] GET `/health`: 200 and `status:ok`, `keys_configured>=2`, `cache_enabled:true`.
- [ ] POST `/chat`: valid session/question yields a real provider answer and all required metadata fields.
- [ ] GET `/sessions/{session_id}/messages`: chronological SQLite history, no system messages.
- [ ] Bad payloads: 422 JSON `detail`, no records added.
- [ ] Missing session: 404 `{"detail":"session not found"}`.
- [ ] Same first question in new session: `LLM_CACHE`, reply identical, cached tokens, `key_id:null`, `fallback_attempts:0`, faster than live.
- [ ] Different question: no accidental cache hit.
- [ ] Memory works across turns in one session; different sessions are separated.
- [ ] Header `key_1=429` → 200 from `key_2`; `fallback_attempts:1`.
- [ ] Header `key_1=500` → 200 from `key_2`; `fallback_attempts:1`.
- [ ] Header `*=429` → 503 exact JSON error; nothing added to history.
- [ ] Real provider quota/5xx failures attempt later keys.
- [ ] Metadata input and output tokens are per **one request**, not running totals.

## UI and deployment

- [ ] Required `data-testid` attributes all present (including optional system prompt when shown).
- [ ] Session ID changes when the page is reloaded.
- [ ] User input clears after pressing Send.
- [ ] 422 and 503 appear readably in chat.
- [ ] Vercel frontend calls Railway backend; Railway CORS allows Vercel origin.
- [ ] `make up` starts ports 3000 and 8000 locally.
- [ ] SQLite file is inside a mounted `/data` Docker/Railway volume.
- [ ] SQLite survives a **container restart**.
- [ ] Real secrets are *not* in GitHub, frontend environment variables, logs, or video.
- [ ] `python scripts/check_contract.py https://YOUR-BACKEND` passes with real credentials.
