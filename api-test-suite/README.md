# API Test Suite

A Jest + Supertest test suite for your API endpoints covering 4 dimensions:

- **PERF** — response time SLA checks (p95 baseline)
- **AUTH** — authentication and authorization enforcement
- **VALID** — input validation and error handling
- **SEC** — SQL injection, XSS, and rate limiting

## Setup

1. Copy the example env file:
```bash
cp .env.example .env
```

2. Fill in your values:
- BASE_URL — your API base URL
- ADMIN_EMAIL / ADMIN_PASSWORD — admin test credentials
- SELLER_EMAIL / SELLER_PASSWORD — seller test credentials
- AGENCY_EMAIL / AGENCY_PASSWORD — agency test credentials

3. Install dependencies:
```bash
npm install
```

4. Run the suite:
```bash
npm test
```

## GitHub Actions

The workflow in .github/workflows/api-tests.yml runs automatically on push and can be triggered manually from the Actions tab. Results are uploaded to your SQA Agent dashboard automatically.

## Adding your own tests

Tests live in the tests/ directory. Each file covers a domain (auth, orders, inventory etc.). Copy an existing test file as a template and adapt the endpoints and assertions for your product.
