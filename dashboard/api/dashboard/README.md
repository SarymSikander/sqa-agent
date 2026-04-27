# Zambeel SQA Dashboard

## Local Development

### Prerequisites
- Python 3.9+
- Node.js not required (frontend is a single HTML file)

### Setup

```bash
# From the project root
cd /Users/sarimsikandar/Desktop/sqa-agent

# Activate the project virtualenv
source venv/bin/activate

# Install dashboard API dependencies
pip install -r dashboard/api/requirements.txt
```

### Run

**Terminal 1 — API server:**
```bash
source venv/bin/activate
cd dashboard/api
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
open dashboard/frontend/index.html
# or just double-click the file in Finder
```

The dashboard connects to `http://localhost:8000` by default. To change the API URL, edit the `API_BASE` constant at the top of `dashboard/frontend/index.html`.

API docs are available at `http://localhost:8000/docs` (Swagger UI).

---

## Free Deployment (Vercel + Railway)

### Backend → Railway

1. Create a free account at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo → select this repo
3. Set the **Root Directory** to `dashboard/api`
4. Railway auto-detects Python. Set the start command:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Add environment variables (copy from your `.env` file):
   - `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
   - `GITHUB_TOKEN`, `GITHUB_FRONTEND_REPO_API`, `GITHUB_BACKEND_REPO_API`
   - `SLACK_WEBHOOK_URL`
   - `STAGING_URL`, `PRODUCTION_URL`
   - DB credentials as needed
6. Deploy. Railway gives you a public URL like `https://your-app.up.railway.app`.

### Frontend → Vercel

1. Create a free account at [vercel.com](https://vercel.com)
2. New Project → Import Git repository
3. Set **Root Directory** to `dashboard/frontend`
4. Framework Preset: **Other**
5. No build command needed — it's a static file
6. Deploy. Vercel gives you a URL like `https://your-app.vercel.app`.
7. Edit `index.html` — change `API_BASE` to your Railway URL:
   ```js
   const API_BASE = 'https://your-app.up.railway.app';
   ```
   Commit and push; Vercel redeploys automatically.

### CORS

The FastAPI backend already allows all origins (`allow_origins=["*"]`), so no CORS changes are needed when the frontend and backend are on different domains.

---

## Project Structure

```
dashboard/
├── api/
│   ├── main.py          # FastAPI backend
│   └── requirements.txt # Python dependencies
└── frontend/
    └── index.html       # Single-file SPA (no build step)
```
