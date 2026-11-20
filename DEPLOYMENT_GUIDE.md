# Deploy Relay, one click at a time

This guide assumes you've never deployed an app before. You'll publish **one GitHub repository**, **one backend on Railway**, and **one frontend on Vercel**. You will need a browser, a GitHub account, a Vercel account, a Railway account, and two valid AI provider keys. Railway may require a payment method or paid resources, especially for persistent volumes. Check pricing before proceeding.

## Part A — Put the project on GitHub

1. Download and unzip `relay-ai-workspace.zip` on your computer. You should see the `backend`, `frontend`, `docker-compose.yml`, `Makefile`, `.env.example`, and `README.md` **immediately inside** the unzipped folder.
2. Go to https://github.com/ and log in (create an account if needed).
3. Click the **+** in the top-right → **New repository**.
4. Repository name: `relay-ai`. Set visibility to **Public**. Do not tick README, `.gitignore`, or license generation because this project includes those files. Click **Create repository**.
5. Install **Git** from https://git-scm.com/downloads and open Terminal / PowerShell **inside the unzipped project directory**. On Windows, you can open the folder in File Explorer, click its address bar, type `powershell`, and press Enter.
6. Run the following one line at a time (replace `YOUR_USERNAME`):

```bash
git init
git add .
git commit -m "Build Relay AI full-stack chatbot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/relay-ai.git
git push -u origin main
```

7. Open the GitHub repository in a browser. Confirm the folders and files appear. **Never upload `.env`, actual API keys or local `.db` files.** The included `.gitignore` protects common secret files, but review before pushing.

**Alternative without Git commands:** on the new empty repository page choose **uploading an existing file**, then drag in the project files/folders (GitHub's browser upload has limitations). Command-line Git is more reliable.

## Part B — Get TWO API keys

1. Open https://aistudio.google.com/apikey and sign in to Google.
2. Create two **different** API keys with access to the model selected in `.env.example` (default: `gemini/gemini-2.5-flash`). Prefer separately provisioned projects/quotas if possible. Two keys sharing the same project's quota may both be rate-limited simultaneously.
3. Copy them somewhere safe temporarily. **Do not** put them on GitHub, in screenshots, in the frontend, or in the video.
4. Their format in the backend will be `LLM_API_KEYS=firstkey,secondkey`, without quotation marks and without a space between the two keys.
5. If the default Gemini model has been retired or isn't enabled for your key, choose an available **text chat** Gemini model from https://ai.google.dev/gemini-api/docs/models and set `LLM_MODEL=gemini/MODEL_NAME`. Both keys should support it. Do not change response API field names.

## Part C — Deploy the backend on Railway FIRST

1. Go to https://railway.com/ and log in using GitHub.
2. Click **New Project** → **Deploy from GitHub repo** and select `relay-ai`. Grant Railway permission if requested.
3. Open the new service **Settings**. Configure its **Root Directory** as `/backend` (the project has a Dockerfile inside `backend`). Verify Railway is building from the backend's Dockerfile. Leave its start command empty: the Dockerfile already starts Uvicorn. The container reads Railway's automatically assigned `PORT`.
4. Open the service **Variables** area and add these entries, one by one:

| Variable name | Value to enter |
|---|---|
| `LLM_API_KEYS` | `YOUR_FIRST_REAL_KEY,YOUR_SECOND_REAL_KEY` |
| `LLM_MODEL` | `gemini/gemini-2.5-flash` (or a confirmed available Gemini model) |
| `DATABASE_URL` | `sqlite:////data/app.db` |
| `ALLOWED_ORIGINS` | `http://localhost:3000` for now; later add Vercel domain |
| `ENABLE_FAILURE_SIMULATION` | `true` |
| `LLM_TIMEOUT_SECONDS` | `45` |
| `RAILWAY_RUN_UID` | `0` (Railway mounts persistent volumes as root; this avoids SQLite permission errors with the non-root Docker image) |

5. **CRITICAL STEP — persistent SQLite volume:** open the Railway service's **Volumes** / **Add Volume** option, create a persistent volume, and mount it at **`/data`** (exactly that path). **Without a volume, history will disappear after redeploys**. One backend instance / one worker is intended for this assignment.
6. In Railway service **Settings → Networking**, create a **Public Domain** (or **Generate Domain**). Copy the full HTTPS URL, e.g. `https://relay-backend-production.up.railway.app` (your URL will differ).
7. In your browser, open `https://YOUR-RAILWAY-DOMAIN/health`. You should see `{"status":"ok","keys_configured":2,"cache_enabled":true}`. If you see 503 or a deployment error, inspect Railway **Deployments → Logs** and check keys, volume, variables and model.
8. After the backend is working, keep the Railway URL for the next step.

**Cost note:** do not assume Railway has free persistent storage or that Google allows unlimited model usage. Confirm your accounts' plan, quotas and billing before using them.

## Part D — Deploy the frontend on Vercel

1. Go to https://vercel.com/ and log in using GitHub.
2. Click **Add New → Project**. Import your `relay-ai` GitHub repository.
3. Set **Root Directory** to `frontend` (not the repository root).
4. Framework preset should detect **Vite**. If needed, select Vite manually. Set **Build Command** to `npm run build` and **Output Directory** to `dist`. The installation command can stay `npm install`.
5. Under **Environment Variables**, add:

   - Name: `VITE_API_BASE_URL`
   - Value: your exact Railway backend URL, e.g. `https://relay-backend-production.up.railway.app` (no trailing `/`)

6. Click **Deploy**. When deployment succeeds, click **Visit** and copy your Vercel URL, e.g. `https://relay-ai-sample.vercel.app`.
7. **IMPORTANT — connect the two:** go back to Railway → backend service → **Variables**. Change `ALLOWED_ORIGINS` to **both** your development and Vercel URLs separated by a comma, like:

   `http://localhost:3000,https://relay-ai-sample.vercel.app`

   Use your *real* Vercel URL and **no trailing slash**. Railway redeploys when variables change.
8. Refresh your Vercel page and look at the top-right status pill. It must say **All systems operational**. Open DevTools → Network if you're seeing cross-origin / CORS errors.
9. Send a message. If the chat returns an actual AI response and metadata chips, your frontend and backend are connected.

**Remember:** `VITE_API_BASE_URL` is compiled into the frontend during build. If you change it on Vercel, you must **redeploy** the frontend. Don't put API secrets in any `VITE_` variable.

## Part E — Check everything BEFORE submitting

1. Open a terminal in the project root. With Python installed, run:

   `python scripts/check_contract.py https://YOUR-RAILWAY-BACKEND-URL`

2. It prints PASS/FAIL lines. All lines must pass. This performs **real** inference and therefore can use a small amount of API quota. If it fails, use Railway logs and the README verification section to diagnose.
3. In the Vercel app, make a new conversation and send `Remember my favorite color is green.`. Then ask `What color did I say?`. The answer should remember green.
4. Click **New conversation**, type `What is the capital of France?`, send. Create **another** new conversation, type the exact same question, send. The second answer should display `LLM_CACHE` with identical reply text. It should be faster than the first response. For repeatability, use a fresh prompt not already in cache for the live step.
5. Open **Configuration** → choose `key_1 → 429` → send a new question → open **Request inspector**. Confirm `key_id: "key_2"`, `fallback_attempts: 1`.
6. Select `All keys → 429` → send another message. The app should show a visible error instead of crashing. Using the backend directly, this is HTTP 503 and no messages get persisted.
7. Open **Request inspector**. Open the health and session history links; confirm the expected JSON.
8. Open the app on your phone (or resize your desktop browser). Check that chat works and isn't cut off.

## Part F — Update the repository README with your REAL links

Open `README.md` in GitHub → click the pencil **Edit** icon → replace placeholders in **1. Live URLs** with the actual frontend, backend, GitHub and later the video URL → click **Commit changes**. Nothing must require sign-in to view. If the README change triggers frontend/backend redeployment, that's normal. Verify again afterwards.

## Part G — Record your 2–3 minute demo video

Read `DEMO_VIDEO_SCRIPT.md` for a timed walkthrough and suggested spoken narration. Use **OBS Studio** (free: https://obsproject.com/), **Loom**, or your computer's built-in recording tool. Record your screen **and voice**. Hide private tabs and credentials. Show the **deployed Vercel app** and **deployed Railway endpoints**, not just localhost. Upload to YouTube as **Unlisted** (not Private) or a publicly accessible Drive/Loom link and verify it opens in an incognito browser without signing in.

## Part H — Final submission

Submit your **public Vercel frontend URL**, **public Railway backend URL**, **public GitHub repository URL**, and **public video URL** to the assignment submission form from the original PDF, before its 24-hour deadline. Use `SUBMISSION_CHECKLIST.md` to avoid missing anything.

## If something goes wrong

| Symptom | Check |
|---|---|
| Railway won't deploy | Root Directory `/backend`, correct Dockerfile, build logs |
| `/health` says 503 | Two keys present? SQLite path/volume mounted? Logs? |
| App says backend disconnected | Vercel `VITE_API_BASE_URL`, Railway public domain, Railway running, CORS origin |
| Chat errors with all providers unavailable | Keys valid? Project quotas? Model name available? Test each key separately outside this app |
| Cache never hits | Exact new-session first message? Same model and system prompt? Same backend instance? Backend not redeployed? |
| Failover key_2 doesn't work | Second key valid and independently quota-enabled? Simulation `true` set? |
| SQLite history disappears | Persistent Railway volume mounted at `/data`? Same deployment service? |
| Vercel shows build error | Root Directory `frontend`, Vite preset, `npm install` logs |
| `make` not found on Windows | Use `docker compose up --build -d` |

