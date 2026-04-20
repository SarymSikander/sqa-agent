# Zambeel App Context

> **Instructions for Sarim:** Fill in the placeholder sections below with actual app details.
> This file is read by the QA agent when generating test cases, so the more detail you provide,
> the more accurate and feature-specific the generated tests will be.

---

## Portal Types and Base URLs

| Portal | Environment | Base URL                          | Login Method      |
|--------|-------------|-----------------------------------|-------------------|
| seller | local       | http://localhost:5173             | Google OAuth      |
| seller | staging     | https://staging.myzambeel.com     | Google OAuth      |
| admin  | local       | http://localhost:5173             | Google OAuth      |
| admin  | staging     | https://staging.myzambeel.com     | Google OAuth      |
| agency | local       | http://localhost:5173             | Google OAuth      |
| agency | staging     | https://staging.myzambeel.com     | Google OAuth      |

> **TODO:** Add production URLs if applicable.

---

## Navigation Structure

### Seller Portal
Post-login landing: `/get-started`

| Page Name              | Path                          | Description                          |
|------------------------|-------------------------------|--------------------------------------|
| Get Started / Onboard  | `/get-started`                | Onboarding checklist for new sellers |
| _TODO: add more pages_ | `/...`                        | _Description_                        |

### Admin Portal
Post-login landing: `/orders-management/dashboard`

| Page Name              | Path                              | Description                          |
|------------------------|-----------------------------------|--------------------------------------|
| Orders Dashboard       | `/orders-management/dashboard`    | Main orders overview                 |
| Commission Settings    | `/...`                            | _TODO: fill in path_                 |
| User Management        | `/...`                            | _TODO: fill in path_                 |
| _TODO: add more pages_ | `/...`                            | _Description_                        |

### Agency Portal
Post-login landing: `/get-started`

| Page Name              | Path                          | Description                          |
|------------------------|-------------------------------|--------------------------------------|
| Get Started            | `/get-started`                | Agency onboarding / seller management|
| _TODO: add more pages_ | `/...`                        | _Description_                        |

---

## Key Features Per Portal

### Seller Portal
- **Product Management:** Sellers can add, edit, and remove products from their storefront.
- **Order Management:** View and manage incoming orders.
- **Storefront Setup:** Configure storefront branding and settings.
- **Inventory:** Track stock levels per product variant.
- _TODO: add more features_

### Admin Portal
- **Orders Management:** Platform-wide order overview with filtering and status management.
- **Commission Model:** Configure commission rates per seller or globally. Allows 0% commission.
- **User Management:** Create, suspend, or manage seller and agency accounts.
- **Settings:** Platform-wide configuration.
- _TODO: add more features_

### Agency Portal
- **Seller Accounts:** Manage multiple seller sub-accounts under the agency.
- **Billing / Commission:** View agency earnings and commission breakdowns.
- _TODO: add more features_

---

## Common User Flows

### Seller: Complete Onboarding
1. Log in as seller → land on `/get-started`
2. Complete each checklist item (store name, logo, first product)
3. Submit and proceed to dashboard

### Admin: Update Commission
1. Log in as admin → land on `/orders-management/dashboard`
2. Navigate to Commission Settings
3. Set commission to 0% (or any value ≥ 0)
4. Save — verify confirmation message appears

### Admin: View and Filter Orders
1. Log in as admin → land on `/orders-management/dashboard`
2. Apply filters (status, date range, seller)
3. Export or drill into individual order

### Agency: View Managed Sellers
1. Log in as agency → land on `/get-started`
2. Navigate to seller list
3. Drill into individual seller account

---

## Test Account Types

| Portal | Account Email (placeholder)       | Notes                              |
|--------|-----------------------------------|------------------------------------|
| seller | _TODO: seller test email_         | Has at least one product listed    |
| admin  | _TODO: admin test email_          | Has full platform access           |
| agency | _TODO: agency test email_         | Manages 2+ seller accounts         |

> Auth sessions are saved in `auth/` as JSON files. Use `python tools/auth_setup.py <portal> <env>` to refresh.

---

## Known Edge Cases / Gotchas

- Commission model now allows 0% — previously the minimum was 1%. Tests should verify that entering 0 does not trigger a validation error.
- The seller and agency portals both redirect to `/get-started` after login. Tests must not conflate them.
- The admin portal uses a separate navigation structure from seller/agency.
- _TODO: add more known issues or gotchas_

---

## UI Component Notes

- Forms use standard HTML inputs. Commission inputs are `<input type="number" min="0">`.
- Navigation uses a sidebar component. Selector: `.sidebar` or `[class*='sidebar']`.
- Status indicators use badge components: `.badge`, `.badge-pass`, `.badge-fail`.
- _TODO: add component library name and any design system notes_
