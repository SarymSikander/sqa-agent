# Agency Domain — Business Logic

## What This Domain Does

The Agency domain enables marketing/sales agencies to formally register on Zambeel, connect to merchant (seller) accounts, and earn commission on orders delivered through those merchants. An agency is reviewed and approved by a Zambeel admin before it becomes active. Once approved, merchants can voluntarily connect to the agency (with configurable store-level access scope). When a connected merchant's order is delivered, commission is automatically calculated and recorded using a per-country commission rule set assigned to the agency.

---

## Key Endpoints

### Agency Self-Service (`/api/agency/...`, roles: `Seller` or `Agency`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agency/register` | Start agency registration; creates Agency + Owner team member row; returns S3 signed upload URLs for POC photo and identity proof |
| POST | `/agency/register/complete` | Finalize registration by saving the S3 URLs for uploaded documents |
| GET | `/agency/me` | Fetch the current user's agency details (status, license, hold/reject reasons, unique ID) |
| PUT | `/agency/settings` | Update agency name, city, phone, POC name (country is immutable after creation) |
| GET | `/agency/cities?country=<name>` | Return cities for a given country (used during registration) |
| GET | `/agency/dashboard` | Aggregate dashboard: active merchants, stores, delivered order counts, revenue and commission grouped by currency |
| GET | `/agency/merchants?status=all\|Active\|Pending\|Inactive` | List all merchant connections with store breakdown and access scope |
| PATCH | `/agency/merchants/:id/status` | Agency accepts/rejects/disconnects/reconnects a merchant connection |
| POST | `/agency/connect` | Merchant sends connection request to an agency by unique ID, with optional specific store-scope |
| GET | `/agency/my-connection` | Merchant fetches their current Pending or Active agency connection |
| POST | `/agency/my-connection/disconnect` | Merchant disconnects from their current agency |
| GET | `/agency/commission?range=30d&from=&to=` | Detailed commission record list + summary totals and amounts due |
| GET | `/agency/invoices?range=30d&from=&to=` | Agency invoices list with amounts paid/due |
| GET | `/agency/invoices/:id/download` | Stream agency invoice PDF from S3 |
| GET | `/agency/team-members` | List all non-archived team members (Owner always shown) |
| POST | `/agency/team-members/invite` | Invite a member by email; creates AgencyTeamMember row and sends SES invite email with JWT token |
| POST | `/agency/team-members/invite/preview` | Validate and preview an invite token without accepting |
| POST | `/agency/team-members/accept` | Accept an invite (token + matching logged-in user email) |
| POST | `/agency/team-members/decline` | Decline an invite (archives the AgencyTeamMember row) |
| DELETE | `/agency/team-members/:id` | Remove a non-Owner team member (sets `archived=true`) |

### Admin Routes (`/api/admin/agency-registrations/...`, role: `Admin` only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/agency-registrations/applications?status=<val>` | List all agency applications, optionally filtered by `registration_status` |
| GET | `/admin/agency-registrations/applications/:id` | Full detail view of one application including assigned commission model |
| GET | `/admin/agency-registrations/commission-models` | List active commission models (with at least one rule) |
| GET | `/admin/agency-registrations/commission-models/manage` | List with full rule details and assigned-agency count |
| POST | `/admin/agency-registrations/commission-models` | Create a named commission model with per-country rules |
| PUT | `/admin/agency-registrations/commission-models/:id` | Replace all rules on an existing model (full replace, not merge) |
| POST | `/admin/agency-registrations/applications/:id/approve` | Approve an application; assigns commission model; sets `registration_status=Approved`, `license_status=Active`; promotes user role to `Agency` |
| POST | `/admin/agency-registrations/applications/:id/hold` | Put on hold with reason; optionally allow resubmit |
| POST | `/admin/agency-registrations/applications/:id/reject` | Reject with reason; sets `rejected_at` timestamp |
| POST | `/admin/agency-registrations/applications/:id/revert-to-pending` | Revert any non-final status back to Pending |
| POST | `/admin/agency-registrations/applications/:id/revoke` | Revoke the license of an already-approved agency (sets `license_status=Revoked`) |

---

## Business Logic — Step by Step

### Agency Registration Flow

1. **Start** (`POST /agency/register`):
   - Checks for an existing agency row for this user.
   - If status is `OnHold` and `allow_resubmit=true`, or status is `Rejected`, resets the row and allows a new submission.
   - If an application already has `poc_photo_url` and `identity_proof_url` and is not Rejected or re-submittable → 409.
   - Creates or updates Agency row with `registration_status=Pending`, `license_status=Inactive`.
   - Creates an `AgencyTeamMember` row for the owner with `role=Owner`, `invite_accepted_at=now`.
   - Returns S3 signed upload URLs for `poc_photo` and `identity_proof` documents.

2. **Complete** (`POST /agency/register/complete`):
   - Saves the final S3 URLs (`poc_photo_url`, `identity_proof_url`) on the existing agency row.
   - Does not change `registration_status`; admin review is still needed.

3. **Admin Review**:
   - Admin transitions: `Pending → Approved | OnHold | Rejected`.
   - `OnHold → Pending` (via revert), `OnHold → Approved | Rejected`.
   - `Rejected → Pending` (via revert).
   - `Approved → Revoked` (license revoke only, `registration_status` stays `Approved`).
   - On Approve: commission model is assigned, user's role is set to `Agency`.
   - State transitions are enforced by `ensureTransition()` utility.

4. **Unique Agency ID**: A short alphanumeric unique agency ID (`agency_unique_id`, up to 20 chars) is generated on approve or on first `GET /agency/me` if missing.

### Merchant–Agency Connection Flow

1. Merchant calls `POST /agency/connect` with an `agency_unique_id` and optional `access_scope`:
   - `access_scope = "all"`: agency can see all merchant stores.
   - `access_scope = "specific"`: `store_ids` must be provided; must all be active stores of the merchant; stored as JSON in `disconnect_details`.
2. A merchant can only have **one** active or pending agency at a time. Connecting to a second agency while one is pending/active returns 409.
3. Self-connection (connecting to your own agency) is blocked.
4. If already connected to the same agency (Active or Pending), the call updates the access scope instead.
5. If a previous Disconnected/Rejected connection to same agency exists, it is reused and set to Pending.
6. Agency can accept/reject/disconnect from their side via `PATCH /agency/merchants/:id/status`.
7. Merchant can disconnect from their side via `POST /agency/my-connection/disconnect` (sets status to `Disconnected`, `disconnect_reason="Disconnected by merchant"`).
8. Agency disconnecting a merchant sets `disconnect_reason="Disconnected by agency"`.
9. Agency can reconnect Disconnected/Rejected connections (sets to Pending for merchant to accept again).

### Commission Calculation (automatic on order delivery)

Triggered from `agencyCommissionService.maybeRecordCommissionOnDelivered()`, called when an order status transitions **to `Delivered`**.

1. Guard: only fires if `newStatus.status === "Delivered"` and `previousStatus.status !== "Delivered"`.
2. Guard: idempotent — if a commission record already exists for `fk_order_id`, skips.
3. Finds the store from `order.fk_store_id`, then the merchant (store owner).
4. Finds an `AgencyMerchantConnection` with `status=Active` for that merchant's user, joined to an agency with `registration_status=Approved` and `license_status=Active`.
5. Checks that the specific store is in the connection's `access_scope` (if `specific`).
6. Checks that delivery happened **after** the effective commission start date = max(connection.responded_at, store.createdAt).
7. Resolves the customer's country from `order.customer.country`, normalized (e.g., "uae" → "united arab emirates"). For Pakistan orders or when no match found, falls back to the `vendor.fk_country_id`.
8. Looks up the rule in `AgencyCommissionModelRule` for that `(commission_model_id, country_id)`.
9. **Two commission types:**
   - `percentage_of_delivered_revenue`: `commission = order_revenue * (rule.value / 100)`, rounded to 2dp.
   - `flat_per_delivered_order`: `commission = rule.value` (fixed amount).
10. `order_revenue` = `order.total_payable` or fallback `order.total_cost`.
11. Creates one `AgencyCommissionRecord` row (linked to order, merchant, store, agency, rule).

### Team Member Invites

- Owner invites by email → `AgencyTeamMember` row created with `role=Member`, `invite_accepted_at=null`.
- JWT invite token (`type="agency_invite"`, 7-day expiry) is generated and emailed via AWS SES.
- Invite link: `{FRONTEND_URL}/agency/invite?token=...&email=...`.
- Accept: JWT validated, user email must match token email; sets `fk_user_id` and `invite_accepted_at`.
- Decline: archives the member row.
- Owner cannot be removed (role check blocks deletion).
- Team member status shown as `"Active"` if `invite_accepted_at` is set, else `"Invite Pending"`.

---

## Domain Interactions

| Domain | How It's Used |
|--------|--------------|
| Orders | `AgencyCommissionRecord.fk_order_id` ties commission to a delivered order; commission service is called on order status change |
| Stores | Agency dashboard aggregates per-store revenue; connection scope references store IDs |
| Users | Merchant connections link to `users.id`; approval promotes user role to `Agency` |
| Countries / Cities | Registration and commission rule matching use `Country` and `City` models |
| Invoices | `AgencyInvoice` records period-based commission invoices; `AgencyCommissionRecord` feeds them |
| S3 / AWS SES | Document uploads (POC photo, identity proof) via S3; invite emails via SES |
| LightFunnels / Zajel / iMile | Those webhook handlers call `maybeRecordCommissionOnDelivered` when they update order status to Delivered |

---

## Key Models

### `agencies` table
| Column | Type | Notes |
|--------|------|-------|
| `id` | INT PK | |
| `fk_user_id` | INT UNIQUE | One agency per user |
| `agency_unique_id` | VARCHAR(20) UNIQUE | Alphanumeric, auto-generated on approve |
| `name` | VARCHAR(255) | |
| `country` | VARCHAR(100) | Immutable after creation |
| `city` | VARCHAR(255) | |
| `phone` | VARCHAR(50) | |
| `poc_name` | VARCHAR(255) | Point-of-contact name |
| `poc_photo_url` | VARCHAR(500) | S3 URL |
| `identity_proof_url` | VARCHAR(500) | S3 URL |
| `registration_status` | ENUM | `Pending`, `Approved`, `OnHold`, `Rejected` |
| `license_status` | ENUM | `Inactive`, `Active`, `Revoked` |
| `hold_reason` | TEXT | |
| `reject_reason` | TEXT | |
| `rejected_at` | DATE | |
| `cooldown_until` | DATE | |
| `allow_resubmit` | BOOLEAN | Set on Hold, permits re-registration |
| `terms_accepted_at` | DATE | |
| `fk_commission_model_id` | INT | Assigned on approval |

### `agency_commission_model_rules` table
| Column | Type | Notes |
|--------|------|-------|
| `fk_commission_model_id` | INT | |
| `fk_country_id` | INT | One rule per country per model |
| `commission_type` | ENUM | `percentage_of_delivered_revenue`, `flat_per_delivered_order` |
| `value` | DECIMAL(10,2) | Percent or flat amount |
| `currency` | VARCHAR(3) | Currency of `value` (for flat; for % it's the order's currency) |

### `agency_merchant_connections` table
| Column | Type | Notes |
|--------|------|-------|
| `fk_agency_id` | INT | |
| `fk_user_id` | INT | Merchant's user ID |
| `status` | ENUM | `Pending`, `Active`, `Rejected`, `Disconnected` |
| `disconnect_details` | TEXT | JSON: `{accessScope, allowedStoreIds}` |
| `disconnect_reason` | TEXT | |
| `disconnected_at` | DATE | |
| `requested_at` | DATE | |
| `responded_at` | DATE | |

### `agency_team_members` table
| Column | Type | Notes |
|--------|------|-------|
| `fk_agency_id` | INT | |
| `fk_user_id` | INT NULLABLE | Null until invite accepted |
| `invite_email` | VARCHAR(255) | |
| `role` | ENUM | `Owner`, `Member` |
| `invite_accepted_at` | DATE NULLABLE | |
| `archived` | BOOLEAN | Soft-delete for removed/declined members |

---

## Important Constraints and Rules

1. **One agency per user**: `agencies.fk_user_id` is UNIQUE.
2. **One active/pending connection per merchant**: A merchant cannot connect to two agencies simultaneously.
3. **Country is immutable**: `PUT /agency/settings` blocks country changes.
4. **Commission is idempotent**: Only one `AgencyCommissionRecord` per order (unique on `fk_order_id`).
5. **Commission requires active status on both sides**: Agency must be `Approved + Active`; connection must be `Active`.
6. **Commission back-dating guard**: Commission is only recorded for orders delivered *after* `max(connection.responded_at, store.createdAt)`.
7. **Country resolution fallback for Pakistan**: If order customer country = Pakistan or no match found, vendor country is used.
8. **Duplicate country in commission model**: Admin cannot create/update a commission model with two rules for the same country.
9. **Owner cannot be removed**: Attempt returns 400.
10. **License revoke does not change registration_status**: `Revoked` is a `license_status` value only.
11. **Archived members are hidden**: `GET /agency/team-members` filters `archived=false`.
12. **AWB invoice download**: Tries stored S3 URL first, then reconstructs from known bucket/key patterns; falls back to localhost in dev.
