# Knowledge Base

This directory is where your AI assistant learns about your product.

## How to populate it

1. Read your actual backend codebase (routes, controllers, models)
2. Write markdown files describing what each domain does in plain English
3. Include: API endpoints, business logic, page names, UI element names
4. Organize by domain (orders/, users/, billing/ etc.)

The more specific and accurate your knowledge base, the better the AI assistant and test case generation will be.

## Recommended structure

knowledge/
├── README.md          (this file)
├── shared/
│   ├── auth.md        (how authentication works)
│   ├── api_endpoints.md (all your API endpoints)
│   └── test_rules.md  (testing conventions)
├── your-feature/
│   ├── business_logic.md
│   ├── pages.md
│   └── selectors.md
└── system/
    ├── architecture.md
    └── integrations.md
