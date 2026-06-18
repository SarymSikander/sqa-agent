# Billing Domain — Business Logic

## What This Domain Does

Billing manages seller subscription upgrades (Free → Gold), payment processing through two gateways (PayTabs and Shopify), financial invoice management for store payouts, and bank account configuration for receiving payouts. It also exposes admin tools to manually grant, extend, or revoke Gold subscriptions.

---

## Subscription Plans

| Plan | Description |
|------|-------------|
| `Free` | Default on signup; limited features |
| `Gold` | Paid plan; unlocks premium features; expires 30 days after payment |

Billing method is tracked per user (`billing_method` field on `users` table): `PAYTABS` (default) or `SHOPIFY`.

---

## Payment Gateways

### PayTabs
Middle-East payment gateway used for direct card payments. Payment flow:
1. **Create** → API call to PayTabs with amount/currency/customer details → returns a `redirect_url` for the hosted payment page.
2. **Callback** → PayTabs POSTs to backend with transaction result (IPN).
3. **Redirect** → PayTabs redirects the browser back with `cart_id` and `tran_ref` → backend redirects to frontend `/payment-status?cart_id=...&tran_ref=...`.
4. **Verify** → Frontend can POST `cart_id` to confirm final status.

### Shopify
Used when the seller has a Shopify store connected. Uses Shopify's `appPurchaseOneTimeCreate` GraphQL mutation:
1. **Create** → Backend calls Shopify GraphQL with the Gold plan price → returns `confirmationUrl` for merchant to approve on Shopify.
2. **Callback** → Shopify redirects with `purchaseId`/`charge_id` → backend verifies purchase status via `currentAppInstallation` query.
3. If purchase status is `ACTIVE`, subscription is treated as paid (30-day expiry computed client-redirect side).

---

## Key Endpoints

### Payments (PayTabs) — `/payments`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/payments/create` | VerifySeller | Initiate a PayTabs payment session |
| POST | `/payments/callback` | Public (IPN) | PayTabs webhook — records transaction, upgrades Gold |
| POST | `/payments/redirect` | Public | PayTabs browser redirect handler → redirects to frontend |
| POST | `/payments/verify` | VerifySeller | Verify transaction status by `cart_id` |
| GET | `/payments/checkUserSubscription` | VerifySeller | Check if user has active Gold subscription |

### Billing (Shopify) — `/billing`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/billing/status` | VerifySeller | Get current billing method, plan, days left, Shopify stores |
| POST | `/billing/shopify/create` | VerifySeller | Create Shopify one-time purchase for Gold plan |
| GET | `/billing/shopify/callback` | Public | Handle Shopify purchase confirmation redirect |
| GET | `/billing/shopify/stores` | VerifySeller | List user's connected Shopify stores |

### Invoices — `/invoices`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/invoices` | verifyUser (Admin/Agent) | Bulk-create invoices for stores |
| PUT | `/invoices` | verifyUser (Admin/Agent) | Bulk-update invoice payment status |
| POST | `/invoices/check-stores` | verifyUser (Admin/Agent) | Validate that given store IDs exist |
| GET | `/invoices/:storeId` | VerifySeller | Get paginated invoices for a store |
| GET | `/invoices/invoices/download/:id` | Public | Download invoice PDF from S3 |

### Bank Accounts — `/accounts`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/accounts` | VerifySeller | Add a payout bank account |
| GET | `/accounts/:userId` | VerifySeller | List non-archived accounts for a user |
| GET | `/accounts/:userId/all` | VerifySeller | List all accounts including archived |
| PUT | `/accounts/:id` | VerifySeller | Update account details |
| DELETE | `/accounts/:id` | VerifySeller | Soft-delete (archive) account |
| PATCH | `/accounts/:id/set-primary` | VerifySeller | Set account as primary (optionally apply to all stores) |
| GET | `/accounts/myaccount/:id` | VerifySeller | Get single account by ID |
| GET | `/accounts/store/:storeId` | VerifySeller | Get bank accounts linked to a specific store |

### Gold Subscription Admin — `/admin/gold-subscriptions`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/gold-subscriptions/users/gold` | Admin only | List active Gold users (paginated) |
| GET | `/admin/gold-subscriptions/users` | Admin only | Search all users by email/phone/user_id |
| GET | `/admin/gold-subscriptions/users/:userId` | Admin only | Get user details + transaction history |
| POST | `/admin/gold-subscriptions/give` | Admin only | Manually grant Gold access to a user |
| POST | `/admin/gold-subscriptions/extend` | Admin only | Extend existing Gold subscription |
| POST | `/admin/gold-subscriptions/remove` | Admin only | Revoke Gold access |

---

## Business Logic — Step by Step

### PayTabs Payment Flow
1. Seller calls `POST /payments/create` with `{ payload: { amount, currency, customer_name, email, phone } }`.
2. Backend generates `cart_id = 'ORD-<timestamp>'`, stores `paymentCache.set(cart_id, user.id)` (in-memory Map).
3. POSTs to PayTabs API with `profile_id`, `tran_type`, cart details, and `return`/`callback` URLs.
4. Returns PayTabs `redirect_url` to frontend; frontend redirects user to hosted payment page.
5. PayTabs hits `POST /payments/callback` (IPN). Backend:
   - Reads `userId = paymentCache.get(cart_id)` (relies on in-memory cache — restarts lose pending payments).
   - Checks for duplicate `tran_ref` to prevent double-processing.
   - Creates `UserSubscriptionTransactions` row.
   - If `payment_result.response_status === 'A'` (Authorized): sets `users.subscription_plan = 'Gold'` and `billing_method = 'PAYTABS'`. Sets `subscription_expiry = now + 30 days`.
   - All DB writes inside a Sequelize transaction — rolled back on error.
6. PayTabs also redirects browser to `POST /payments/redirect` → backend redirects to frontend `/payment-status?cart_id=...&tran_ref=...`.
7. Frontend calls `POST /payments/verify` with `cart_id` to poll final status.

### Subscription Status Check (`GET /payments/checkUserSubscription`)
1. If `req.user.subscription_plan !== 'Gold'` → returns `{ gold_subscription: false }`.
2. Finds latest `UserSubscriptionTransactions` with `payment_status = 'Authorized'` ordered by `subscription_expiry DESC`.
3. If expiry is in the future → returns `{ gold_subscription: true, days_left: N }`.
4. If expiry is in the past → demotes user: updates `users.subscription_plan = 'Free'` → returns `{ gold_subscription: false }`.

### Shopify Billing Flow
1. `POST /billing/shopify/create`: Finds seller's Shopify store, decrypts access token, calls `appPurchaseOneTimeCreate` mutation with Gold plan price. Returns `confirmationUrl` for merchant to approve in Shopify admin.
2. Merchant approves → Shopify redirects to `GET /billing/shopify/callback?userId=...&purchaseId=...&storeId=...`.
3. Backend re-fetches Shopify store access token, calls `currentAppInstallation` query to get all one-time purchases.
4. Finds the purchase matching `gid://shopify/AppPurchaseOneTime/<purchaseId>`.
5. If `status === 'ACTIVE'`: redirects to frontend with `status=success&expiryDate=<+30days>`. Note: the DB subscription record is NOT updated server-side in this flow — the frontend is responsible for recording the Shopify subscription (design gap).
6. `GET /billing/status` checks both the user's `billing_method`, Shopify store list, and latest transaction expiry to return a unified billing status.

### Admin Gold Management
- **Give Gold**: Creates an `ADMIN_GRANT` transaction with `amount = 0`, `payment_channel = 'Manual'`, `payment_status = 'Authorized'`, then sets `users.subscription_plan = 'Gold'`.
- **Extend Gold**: Creates an `ADMIN_EXTEND` transaction. Validates that `new_expiry_date` is strictly after current expiry.
- **Remove Gold**: Creates an `ADMIN_REVOKE` transaction with `subscription_expiry = null`, then sets `users.subscription_plan = 'Free'`.
- All admin operations use Sequelize transactions for atomicity.
- Expired Gold users are auto-demoted to Free on read (no scheduled cron — demotion happens lazily when the admin search endpoint runs).

### Invoice Workflow
1. OMS admin (Admin/Agent) uploads invoices to S3 externally and creates records via `POST /invoices` with `store_id` and `s3_file_url`.
2. On creation, backend emits a Socket.IO event `new_invoices_uploaded` to `user_<store.user_id>` room.
3. Sellers view their invoices via `GET /invoices/:storeId` (paginated, sorted newest first).
4. Admin can update `payment_status` and `reason` on invoices via `PUT /invoices`.
5. Sellers can download PDF directly from S3 via `GET /invoices/invoices/download/:id` — backend streams the S3 URL through.

Invoice payment statuses: `Paid`, `Not Paid Yet`, `Failed Transaction`, `Missing Banking Details`, `Ineligible for Payment`.

### Bank Account Rules
- Each user can have multiple accounts of types: `Bank Account`, `PayPal`, `Payoneer`, `USDT`.
- Only one account can be `is_primary = true` at a time; setting a new primary auto-clears the old one.
- `PATCH /:id/set-primary?applyToAllStores=true` also updates all `StoreBankAccount` junction records to point to the new primary.
- Accounts are soft-deleted (`archived = true`). Archived accounts cannot be updated or set as primary.
- An account attached to a store (has a `StoreBankAccount` record) **cannot be deleted**.
- `GET /:userId` excludes archived accounts; `GET /:userId/all` includes them.

---

## Key Models

### `user_subscription_transactions`
| Field | Type | Notes |
|-------|------|-------|
| `id` | INTEGER PK | |
| `fk_user_id` | INTEGER FK | → users |
| `tran_ref` | STRING | PayTabs transaction reference (or ADMIN_ prefix for manual) |
| `tran_type` | STRING | `SALE`, `ADMIN_GRANT`, `ADMIN_EXTEND`, `ADMIN_REVOKE` |
| `tran_id` | STRING | `cart_id` for PayTabs; auto-generated for admin |
| `currency` | STRING | e.g. `USD`, `AED` |
| `amount` | FLOAT | 0 for admin grants |
| `payment_channel` | STRING | e.g. `Visa`, `Manual` |
| `payment_status` | STRING | `Authorized`, `Pending`, `Declined` |
| `subscription_expiry` | DATE | Expiry of Gold access |
| `billing_method` | ENUM | `PAYTABS`, `SHOPIFY` |

### `invoices`
| Field | Type | Notes |
|-------|------|-------|
| `id` | INTEGER PK | |
| `store_id` | INTEGER FK | → stores |
| `s3_file_url` | STRING | Full S3 URL to PDF |
| `filename` | STRING | Display filename |
| `payment_status` | ENUM | `Paid`, `Not Paid Yet`, `Failed Transaction`, `Missing Banking Details`, `Ineligible for Payment` |
| `reason` | STRING | Optional reason (used for rejected/failed) |

### `users_bank_accounts`
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `fk_user_id` | INTEGER FK | → users |
| `account_title` | STRING | Account holder name |
| `account_nick` | STRING | Nickname for display |
| `iban_wallet_address` | STRING | IBAN or wallet address |
| `bank_name` | STRING | |
| `country` | STRING | |
| `is_primary` | BOOLEAN | Only one primary per user |
| `payment_type` | ENUM | `Bank Account`, `PayPal`, `Payoneer`, `USDT` |
| `ifsc_code` | STRING | Indian bank routing |
| `swift_code` | STRING | International wire |
| `fed_wire_code` | STRING | US federal wire |
| `exchange_name` | STRING | For crypto (USDT) |
| `exchange_id` | STRING | Wallet/exchange ID |
| `archived` | BOOLEAN | Soft-delete |

### `store_bank_accounts` (junction)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `store_id` | INTEGER FK | → stores |
| `bank_id` | UUID FK | → users_bank_accounts |
| `archived` | BOOLEAN | |

### `agency_invoices`
| Field | Type | Notes |
|-------|------|-------|
| `id` | INTEGER PK | |
| `fk_agency_id` | INTEGER FK | → agencies |
| `period_start` / `period_end` | DATEONLY | Commission period |
| `total_commission` | DECIMAL(12,2) | |
| `amount_paid` | DECIMAL(12,2) | |
| `currency` | STRING(3) | ISO currency code |
| `status` | ENUM | `Draft`, `Sent`, `Paid` |
| `payment_date` | DATE | |
| `payment_reference` | STRING | |
| `s3_file_url` | STRING | PDF on S3 |
| `filename` | STRING | |

---

## Domain Interactions

- **Auth domain**: Billing uses `req.user` set by auth middleware; `subscription_plan` is read from the auth cache (30s TTL).
- **Store domain**: Shopify billing looks up `Store` by `platform = 'shopify'`; invoice creation validates store existence; bank accounts are linked to stores.
- **Agency domain**: `AgencyInvoice` tracks commission payouts to agencies (separate from seller invoices).
- **PayTabs**: External API at configured `PAYTAB_API` URL with `Authorization: <serverKey>`.
- **Shopify**: GraphQL endpoint on merchant's shop domain; uses decrypted `access_token` from the store record.
- **Socket.IO**: Invoice creation emits real-time events to seller via `user_<id>` room.
- **S3**: Invoices are stored externally; the API only stores the URL and streams downloads.

---

## Important Constraints & Rules

- The PayTabs `paymentCache` is an **in-memory Map** — if the server restarts between payment creation and the IPN callback, the `userId` lookup will fail (returns `undefined`). Pending payments are vulnerable to server restarts.
- Gold subscription is always **30 days** regardless of payment amount. There is no annual or longer plan.
- The Shopify billing callback does **not** write a subscription transaction record to the DB — it only redirects the browser. The frontend must handle the post-callback DB update (or it doesn't happen). This is a known design gap.
- `checkUserSubscription` auto-demotes expired Gold users on the fly (no cron). This means a user's plan field may lag reality by up to 30s (auth cache TTL).
- Bank accounts cannot be deleted while linked to a store — must detach from store first.
- Admin gold management endpoints are restricted to `Admin` role only (no Agent access).
- `extendGoldAccess` requires the user to already be Gold — cannot be used to convert Free users.
- The Gold plan price and currency are defined in `constants/shopify_billing.constants.js` (`PURCHASE_PLANS.GOLD`).
