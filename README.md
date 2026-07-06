SQA Agent

An AI-powered QA automation dashboard for software teams. Connect it to your Project Management tool, your product portals, your APIs, and let it handle the testing.

Built by [Sarim Sikander](https://github.com/SarymSikander).

What it does

* Run QA on any Jira ticket automatically: reads the ticket, navigates to the right page, takes screenshots, extracts the live DOM, generates Playwright test cases, runs them, and posts results back to Jira.
* API security testing: detects API bug tickets, extracts endpoints from the description, and tests auth/rate-limiting directly via HTTP (no browser needed).
* Live portal page discovery: crawls your actual product sidebar on every run so it always knows the current pages, no hardcoding.
* AI assistant: answers questions about your product using a knowledge base you build from your own codebase.
* API test suite: Hundreds of endpoint tests across performance, auth, input validation, and security dimensions.
* Automatic Jira updates: moves tickets through QA In Progress → Ready for Review automatically, starts sprints, adds/reads comments, and so much more.
* Slack notifications: posts a formatted report after every run.

Stack
| Layer | Tech |
|-------|------|
| Frontend | Vanilla HTML/CSS/JS — deployed on Vercel |
| Backend | Python + FastAPI — deployed on HuggingFace Spaces |
| Browser automation | Playwright (Chromium headless) |
| AI models | Groq (free) + Azure GPT-4o fallback |
| Test runner | Jest + Supertest |

Setup in 4 steps
1. Clone this template
Click "Use this template" above, or:

```bash
git clone https://github.com/SarymSikander/sqa-agent.git
cd sqa-agent
```

2. Configure your environment
```bash
cp dashboard/api/.env.example dashboard/api/.env
```

Open `.env` and fill in your values — Jira credentials, portal URLs, portal login credentials, Groq API key, Slack webhook. Every variable is documented in the file.

3. Deploy the backend to HuggingFace

1. Create a free account at [huggingface.co](https://huggingface.co)
2. Create a new Space → Docker → name it anything
3. Add all your `.env` values as Space secrets
4. Push the backend:

```bash
git remote add hf https://YOUR_HF_USERNAME:YOUR_HF_TOKEN@huggingface.co/spaces/YOUR_HF_USERNAME/YOUR_SPACE_NAME
git push hf main
```

4. Deploy the frontend to Vercel

1. Create a free account at [vercel.com](https://vercel.com)
2. Import your GitHub repo
3. Set the root directory to `dashboard/frontend`
4. Deploy

Open your Vercel URL, log in with the credentials you set in `SQA_USERS`, and you're done.

Building your knowledge base
The `dashboard/api/knowledge/` directory is where your AI assistant gets its information about your product. It comes empty — you fill it in.

Recommended structure:
```
knowledge/
├── shared/ # Auth flows, API endpoints, test rules
├── your-portal/ # Pages, selectors, flows for each portal
└── system/ # Architecture, integrations, data models
```

The more accurate your knowledge base, the better the AI assistant and test generation will be. Build it by reading your actual codebase, not documentation.

Customizing the appearance
Click the user icon → Appearance to customize:

* Sidebar gradient colors
* Navbar gradient colors
* Hero banner colors
* Primary button color
* Your company logo

All changes are saved automatically and persist across sessions.

API Test Suite
The `api-test-suite/` directory contains a separate Jest test suite for your API endpoints. See the [api-test-suite README](api-test-suite/README.md) for setup.

License

MIT © 2026 Sarim Sikander

You're free to use, modify, and distribute this for any purpose — commercial or personal — as long as you keep the copyright notice.

Contributing
Pull requests welcome. If you build something useful on top of this, open a PR or reach out.
