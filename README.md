# Relay — Intelligence that stays online

**A polished, deployable LLM chat application with multi-key resilience, built-in LiteLLM response caching, and persistent SQLite conversations.** Created for the Lyftr AI Full-Stack Assignment.

> **Deployment status:** Source code is supplied, but public URLs and real-provider calls are not claimed to be live or verified. Add real keys, deploy, and run the live acceptance script before submission.

## 1. Live URLs

| Service | URL |
|---|---|
| Frontend | `https://YOUR-PROJECT.vercel.app` (replace after deployment) |
| Backend | `https://YOUR-PROJECT.up.railway.app` (replace after deployment) |
| Health | `https://YOUR-PROJECT.up.railway.app/health` |
| Public GitHub repository | `https://github.com/YOUR-USERNAME/relay-ai` |
| Demo video | `https://YOUR-VIDEO-LINK` |

**Important:** Replace placeholders before submitting. Public links do not exist merely because code is in this repository.

## 2. Run locally: with Docker and without

### Requirements
- Docker Desktop (Docker Compose included), or Python 3.12 and Node.js 22 if running without Docker.
- Two valid API keys for the same chosen provider. The default model is `gemini/gemini-2.5-flash`. Get keys from [Google AI Studio](https://aistudio.google.com/apikey). For real rate-limit resilience, use keys backed by independently available quotas (ideally different projects), as two keys from one project can share the same quota.

### With Docker (recommended)

1. Copy `.env.example` to `.env` at the **repository root**.
2. Replace `YOUR_FIRST_GEMINI_KEY` and `YOUR_SECOND_GEMINI_KEY` with real separate keys. Keep the entire `LLM_API_KEYS` entry on **one line** and separate keys with one comma.
3. Keep `ALLOWED_ORIGINS=http://localhost:3000,...` so the local frontend can contact the API.
4. From the directory containing this README:

   ```bash
   make up
   ```

   Windows PowerShell users who do not have `make`: use `docker compose up --build -d`.

5. Open http://localhost:3000 and http://localhost:8000/health. Expect `{"status":"ok","keys_configured":2,"cache_enabled":true}`.
6. Stop: `make down` (or `docker compose down`). Your message history remains stored in the named `relay_data` volume. **Do not** run `docker compose down -v` unless you intend to delete history.

### Without Docker

Create `.env` with the same keys. In a terminal:

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
# macOS/Linux:
export LLM_API_KEYS='KEY_ONE,KEY_TWO'
export DATABASE_URL='sqlite:///./app.db'
export ALLOWED_ORIGINS='http://localhost:3000'
export ENABLE_FAILURE_SIMULATION=true
# Windows PowerShell instead: $env:LLM_API_KEYS='KEY_ONE,KEY_TWO' etc.
uvicorn app.main:app --reload --port 8000
```

`uvicorn` loads environment variables; it does not automatically load `.env`. Either export the variables or start with `uvicorn app.main:app --env-file ../.env --reload --port 8000`. For a local run without Docker, set `DATABASE_URL=sqlite:///./app.db` in that file to avoid requiring `/data`.

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Vite forwards the three API paths to localhost:8000 during local development.

### Automated backend tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use a **fake provider** so they do not consume API credits. They validate app routing, response schemas, SQLite history, cross-session cache expectations, input validation, fallback simulation, CORS, prompt persistence, and durable storage. They **do not** prove actual LiteLLM cache/provider integration; verify that separately against live credentials below.

### Live acceptance checks

After the backend is running with real keys:

```bash
python scripts/check_contract.py http://localhost:8000
# after deployment:
python scripts/check_contract.py https://YOUR-BACKEND.up.railway.app
```

The script uses unique messages and sessions to verify health, a genuine model response, cross-session cache, simulated key failover, an all-key 503, no history on failed requests, SQLite history, and a 422. If any check fails, **do not submit until it is fixed**. On macOS/Linux and PowerShell, run the command from repository root.

## 3. Design decisions: key fallback, caching, SQLite session storage

### Request flow

```text
React frontend (new session ID each page load)
      |
      v
POST /chat + optional X-Simulate-Failure
      |
      v
Validate input (422 on bad values)
      |
      v
Load session messages + saved system prompt from SQLite
      |
      v
Build complete [system, history, new user] message list
      |
      v
LiteLLM completion with built-in in-memory caching
      |                 |
      | cache hit       | cache miss or simulated failure
      v                 v
LLM_CACHE          key_1 -> key_2 -> ...
      |                 |                 |
      |                 | success         | all fail
      v                 v                 v
Store 2 messages   Store 2 messages   JSON 503, store nothing
      |                 |
      +--------+--------+
               v
         JSON reply + per-request metadata
```

**Key fallback.** `LLM_API_KEYS` is parsed in order into `key_1`, `key_2`, etc. Provider 429, quota exhaustion, 5xx, connection, and timeout errors trigger the next key, with no hard-coded provider response. A failure header only simulates statuses in that request and is honored solely when `ENABLE_FAILURE_SIMULATION=true`. Simulated calls bypass cache so demonstrations are meaningful. Invalid/other provider errors become sanitized JSON 503 responses without exposing keys.

**Caching.** Uses `litellm.cache = Cache(type="local")` and `litellm.completion(..., caching=True)`, rather than a custom answer cache. LiteLLM creates a deterministic cache key from the model and request data, including the full system/history/user message list. Cached replies are identified from LiteLLM's `_hidden_params['cache_hit']`. A cache hit reuses the provider response and its per-call usage, returns `key_id:null`, `fallback_attempts:0`, and measures wall-clock latency independently. Cache lives in the single backend process: **restarting the backend clears it**. Running multiple replicas would require a shared cache, which is outside the assignment's SQLite-only storage constraint.

**SQLite.** A single SQLite file configured via `DATABASE_URL`, with `messages` plus `sessions` tables. Automatic schema creation, an index on `(session_id, id)`, atomic two-message commits, WAL mode and a per-session async lock protect history ordering. The container stores `/data/app.db` on a persistent Docker/Railway volume. For Railway root-owned volumes, set `RAILWAY_RUN_UID=0` as documented in the deployment guide; Docker Compose uses the image’s non-root user on its initialized named volume. The backend stores one exchange only after LLM success. Session prompts persist but do not appear in returned history.

**Security and operational tradeoffs.** API keys stay server-side; CORS only grants explicitly configured frontend origins; input lengths are bounded; FastAPI errors have JSON `detail` and no secret-bearing stack traces; no analytics service or external database; single Uvicorn worker ensures one in-memory LiteLLM cache and uses the SQLite file safely. The assignment intentionally exposes a failure simulation hook; for a real public production product, protect or disable it. The UI is a proof-of-concept without authentication; don't treat session IDs as private authorization tokens.

## 4. Verification: how to see failover, cache hits and per-message token usage

**Healthy backend**: `GET /health` returns 200, `status: "ok"`, `keys_configured: 2` or greater, and `cache_enabled: true`.

**Cache hit**: send `What is the capital of France?` in a new session. Create another new session with **exactly** the same message and unchanged system prompt. Second reply should say `LLM_CACHE`, with identical text and token counts, `key_id:null`, and faster latency. **Sending the same message twice in the SAME session is NOT a cache hit**, because the second request includes extra history.

**Multi-turn**: send `Remember my favorite color is green.`; then `What color did I say?` in the **same** session. Inspect `GET /sessions/{session_id}/messages` (the inspector shows the URL). History is oldest first and excludes the system prompt.

**Failover**: open **Configuration** → **Failure simulation** → **key_1 → 429**. Send a new message. Inspect response: expect HTTP 200, `key_id:key_2`, `fallback_attempts:1`, `resolution_source:LIVE_INFERENCE`. Repeat with `key_1 → 500`.

**All keys fail**: choose **All keys → 429**. Send a new message; expect a readable error in chat and HTTP 503 `{"detail":"all providers unavailable"}`. That question is **not** added to SQLite history. Turn simulation off afterward.

**Tokens**: for each assistant bubble, inspect the chips (`in`, `out`) or the **Request inspector** JSON. These are provider usage fields `prompt_tokens` and `completion_tokens`, not accumulated conversation totals.

**Direct endpoint tests (terminal)**:

```bash
# Replace the session ID with a fresh value.
curl -X POST 'http://localhost:8000/chat' -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-a","message":"Hello from curl"}'

curl -X POST 'http://localhost:8000/chat' -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: key_1=429' \
  -d '{"session_id":"demo-b","message":"Explain resilience in one sentence"}'

curl -X POST 'http://localhost:8000/chat' -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: *=429' \
  -d '{"session_id":"demo-c","message":"This must fail"}'

curl 'http://localhost:8000/sessions/demo-a/messages'
```

On Windows PowerShell, prefer `curl.exe` (the legacy `curl` command may alias to PowerShell functionality) or use the included `scripts/check_contract.py`.

## 5. Setup Used: your editor and AI tools

- **Implementation assistance:** OpenAI ChatGPT (GPT-6) for architecture, implementation, documentation and initial test generation.
- **Local validation:** Python 3, pytest and static code inspection; deterministic mock-gateway API tests passed in the authoring environment.
- **Tools for deployment and optional further work:** VS Code or another editor, Git/GitHub, Docker Desktop, Vercel, Railway, Google AI Studio.
- **Disclosure:** The creator should edit this section to truthfully reflect any tools actually used after this handoff. The source-generation environment could not install LiteLLM/npm dependencies or run Docker/live provider requests, so a real-provider deployment is not yet verified.

## 6. Bonus features (if any): what you added beyond the requirements and why

- **Premium responsive interface:** polished chat experience, dark-mode design, actionable suggestion cards, loading and error states, markdown rendering, touch-friendly mobile layout.
- **Live operational panel:** health/key count/cache status, recent request metrics, reply count and cache-hit count.
- **Request inspector:** copy structured response JSON and open health/history endpoints for transparent review.
- **Interactive resilience testing:** failure simulation settings with a real `X-Simulate-Failure` request header; no need to type developer commands for every demo.
- **Persistent system instructions:** optional system prompt stored per session, exposed in the UI while hidden from the history endpoint.
- **Acceptance test script:** one command checks the most important deployed API requirements end-to-end.
- **Developer-friendly repository:** Docker Compose, small multi-stage images, Makefile, example env files, isolated deterministic API tests, and an explicit demonstration script.

---

## Exact HTTP contract

| Method | Route | Behavior |
|---|---|---|
| `GET` | `/health` | Key pool + SQLite readiness + cache-enabled flag |
| `POST` | `/chat` | Multi-turn LLM answer, per-request metadata, automatic fallback, caching |
| `GET` | `/sessions/{session_id}/messages` | SQLite history, oldest first, no system prompt |

All errors return JSON with `detail`. Required client `data-testid`: `chat-input`, `send-button`, `assistant-message`, `meta-source`, `meta-model`, `meta-latency`, `meta-input-tokens`, `meta-output-tokens`, `system-prompt-input`.

## Deploying

Follow **`DEPLOYMENT_GUIDE.md`** for beginner instructions. Follow **`DEMO_VIDEO_SCRIPT.md`** to record the required 2–3 minute narrated video. Complete **`SUBMISSION_CHECKLIST.md`** before using the assignment submission form.
