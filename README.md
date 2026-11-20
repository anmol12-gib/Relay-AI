
# Relay-AI

### Resilient AI Chat Application with Multi-Key Failover and Response Caching

Relay-AI is a full-stack AI chat application built with React, FastAPI, and Google Gemini. It focuses on improving the reliability of AI-powered applications through API-key failover, response caching, failure simulation, and request-level metadata.

The application is deployed with a Vercel frontend and a Render backend, allowing users to access it through a public website without running the application locally.

## Live Deployment

| Component | Link |
|-----------|------|
| Live Application | https://relay-ai-steel.vercel.app |
| Backend API | https://relay-ai-0g9j.onrender.com |
| API Health Check | https://relay-ai-0g9j.onrender.com/health |
| Source Code | https://github.com/anmol12-gib/Relay-AI |

> **Note:** The backend uses Render's free hosting tier. After a period of inactivity, the service may sleep, resulting in a slower initial response.

## Key Features

### 1. AI-Powered Chat
- Integrates Google Gemini through LiteLLM.
- Provides a responsive chat interface.
- Supports user-assistant conversations.
- Displays AI-generated responses in a clean interface.

### 2. Multi-Key API Failover
- Supports multiple Gemini API keys.
- Implements fallback handling when an API request fails.
- Improves resilience against individual key failures.
- Provides a foundation for reliable LLM request routing.

### 3. Response Caching
- Supports caching to reduce repeated model requests.
- Improves response time for eligible repeated requests.
- Helps reduce unnecessary API usage.

### 4. Failure Simulation
- Includes configurable failure simulation for testing.
- Allows the application to demonstrate fallback behavior.
- Helps validate resilience under simulated API failures.

### 5. Request Metadata
- Exposes request-related information for monitoring and debugging.
- Supports visibility into model usage and request execution.
- Helps demonstrate the behavior of the AI request pipeline.

### 6. Full-Stack Cloud Deployment
- React frontend deployed on Vercel.
- FastAPI backend deployed on Render.
- Public HTTPS communication between frontend and backend.
- Configured CORS for the production application and supported Vercel deployment URLs.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI, Uvicorn |
| AI Integration | Google Gemini, LiteLLM |
| Database | SQLite |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |
| Version Control | Git, GitHub |

## System Architecture

```text
                  USER
                    |
                    v
             React Frontend
               (Vercel)
                    |
                    | HTTPS Requests
                    v
             FastAPI Backend
                (Render)
                    |
          +---------+---------+
          |                   |
          v                   v
     Cache / SQLite      LLM Gateway
                              |
                              v
                       Gemini API Keys
                              |
                    +---------+---------+
                    |                   |
                    v                   v
                Primary Key       Fallback Key
                    |                   |
                    +---------+---------+
                              |
                              v
                        AI Response
                              |
                              v
                       React Frontend
```

## Project Structure

```text
Relay-AI/
|
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- ...
|   |
|   |-- requirements.txt
|   |-- .env.example
|
|-- frontend/
|   |-- src/
|   |   |-- App.jsx
|   |   |-- styles.css
|   |   |-- ...
|   |
|   |-- package.json
|   |-- .env.example
|
|-- README.md
```

## Local Installation

### Prerequisites

- Python 3.10 or later
- Node.js and npm
- Git
- Google Gemini API keys

### Step 1: Clone the Repository

```bash
git clone https://github.com/anmol12-gib/Relay-AI.git
cd Relay-AI
```

### Step 2: Configure the Backend

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` directory.

Example configuration:

```dotenv
LLM_API_KEYS=your_first_gemini_key,your_second_gemini_key
LLM_MODEL=gemini/gemini-3.5-flash
DATABASE_URL=sqlite:///./app.db
ALLOWED_ORIGINS=http://localhost:3000
ENABLE_FAILURE_SIMULATION=true
LLM_TIMEOUT_SECONDS=45
DEFAULT_SYSTEM_PROMPT=You are Relay, a thoughtful, precise and helpful AI assistant.
```

Replace the placeholder API keys with valid Gemini API keys.

Never commit your `.env` file or API keys to GitHub.

### Step 3: Start the Backend

From the `backend` directory, run:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend URL:

```text
http://127.0.0.1:8000
```

Health endpoint:

```text
http://127.0.0.1:8000/health
```

### Step 4: Configure the Frontend

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a `.env.local` file:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Step 5: Start the Frontend

```bash
npm run dev
```

Open the local URL displayed by Vite in your terminal.

For local development, ensure the frontend origin matches an entry in the backend's `ALLOWED_ORIGINS` configuration.

## Deployment

### Frontend — Vercel

The React frontend is deployed on Vercel.

Configuration:

| Setting | Value |
|---------|-------|
| Framework | Vite |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

Production environment variable:

```dotenv
VITE_API_BASE_URL=https://relay-ai-0g9j.onrender.com
```

The `VITE_API_BASE_URL` variable contains a public backend address and is safe to expose in frontend code.

Gemini API keys must never be stored in frontend environment variables.

### Backend — Render

The FastAPI backend is deployed as a Render Web Service.

Configuration:

| Setting | Value |
|---------|-------|
| Service Type | Web Service |
| Runtime | Python |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

Backend environment variables:

```dotenv
LLM_API_KEYS=<comma-separated-gemini-api-keys>
LLM_MODEL=gemini/gemini-3.5-flash
DATABASE_URL=sqlite:///./app.db
ALLOWED_ORIGINS=https://relay-ai-steel.vercel.app
ENABLE_FAILURE_SIMULATION=true
LLM_TIMEOUT_SECONDS=45
DEFAULT_SYSTEM_PROMPT=You are Relay, a thoughtful, precise and helpful AI assistant.
```

Additional Vercel deployment origins are handled through the backend's CORS configuration.

Environment variables containing credentials must be configured securely in Render rather than committed to the repository.

## API Overview

### Health Check

```http
GET /health
```

Used to verify that the backend is running and to inspect basic service status.

Example response:

```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

### Chat

```http
POST /chat
```

Processes chat requests through the backend's AI integration, including the configured caching and failover mechanisms.

## Reliability Design

Relay-AI includes multiple mechanisms intended to make AI requests more resilient:

**API-key failover:** Multiple configured keys allow the application to attempt an alternative credential when supported failure conditions occur.

**Caching:** Eligible repeated requests can reuse previously stored responses instead of making additional model calls.

**Failure simulation:** Configurable failure injection supports testing and demonstrating the application's fallback behavior.

**Health monitoring:** The `/health` endpoint provides a simple way to verify backend availability.

These mechanisms are intended to improve reliability; they do not guarantee uninterrupted service during provider outages or hosting failures.

## Testing and Demonstration

The following scenarios can be used to demonstrate the application:

1. Open the deployed website and verify the backend connection.
2. Submit a prompt and observe the generated response.
3. Repeat an eligible request to demonstrate caching.
4. Use the supported failure-simulation mechanism to test fallback behavior.
5. Inspect the available request metadata.
6. Verify that the deployed application works without running the local FastAPI server.

## Hosting Limitations

The application currently uses free hosting services.

- Render may spin down the backend after inactivity.
- The first request after inactivity may experience a cold-start delay.
- SQLite uses Render's ephemeral filesystem on the free tier.
- Stored chat history and cache data may be lost after restarts or redeployments.
- API usage remains subject to the configured Gemini provider limits.

For production use, a persistent managed database and more robust hosting infrastructure would be appropriate.

## Security Considerations

- Gemini API keys are stored in backend environment variables.
- API keys are not included in frontend source code.
- CORS restricts supported browser origins.
- Environment files containing credentials should remain excluded from version control.
- Failure simulation should be disabled when it is no longer required for testing or evaluation.
- Public deployment requires additional protections for sustained production use, including appropriate rate limiting and abuse prevention.

## Future Improvements

- Persistent cloud database integration.
- Improved rate limiting and request quotas.
- Additional LLM provider support.
- Automated integration and reliability testing.
- More detailed monitoring and observability.
- Improved cache management.
- Production-grade deployment configuration.

## Repository

GitHub: https://github.com/anmol12-gib/Relay-AI

## License

No license is specified unless a separate LICENSE file is added to the repository.
