# Zambeel Backend — External Integrations

## Overview

Zambeel integrates with multiple e-commerce platforms (order sources), courier partners (last-mile delivery), communication platforms (WhatsApp, email), and infrastructure services (AWS, Firebase).

---

## E-Commerce Platform Integrations

### 1. Shopify

**Purpose**: Largest integration. Sellers connect their Shopify stores to automatically sync orders into Zambeel.

**Auth Flow (OAuth + Token-from-frontend pattern)**:
1. Shopify installs the Zambeel embedded app; the app redirects to the backend with an encrypted `data` query param containing `{shop_url, access_token}`.
2. Backend (`GET /api/shopify/auth/initiate`) decrypts the data, stores it in the SQL `Sessions` table as `pendingShopData`, and redirects the frontend to `FRONTEND_BIND_URL?fromShopifyInstall=true&sessionId=<id>`.
3. Frontend calls `GET /api/shopify/auth/shop-data?sessionId=X` — backend fetches shop metadata from `https://{shop}/admin/api/{version}/shop.json` using the stored access token.
4. Frontend calls `POST /api/shopify/auth/bind-store` — backend creates/updates the `stores` row (platform = `"shopify"`, access token AES-encrypted), links the seller's primary bank account, then registers all required webhooks.

**Webhook Topics Registered** (both REST and GraphQL):
- `orders/create` — new order created
- `orders/updated` — order edited
- `products/create`, `products/update` — product catalog sync
- `app/uninstalled` — store disconnection
- `APP_PURCHASES_ONE_TIME_UPDATE` (GraphQL) — billing purchase status

**Webhook Handling** (`/api/webhooks/shopify/*` and `webhooks/shopify.js`):
- `orders/create` → pushes raw order JSON to SQS queue (`sqsService.sendOrderToQueue`); the worker picks it up and creates the Order record
- `orders/updated` → updates order fields in DB
- `products/*` → syncs product/variant records
- `app/uninstalled` → archives the store, nulls out access_token

**Data Stored per Store**:
- `stores.access_token` (AES-encrypted), `stores.iv`, `stores.domain` (myshopify domain), `stores.store_url`, `stores.platform = "shopify"`
- Token decryption: `decryptToken(store.access_token, store.iv)`

**Key Config Keys**: `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, `SHOPIFY_ADMIN_ACCESS_TOKEN`, `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_API_VERSION` (default: `2026-01`), `SHOPIFY_REDIRECT_URI`, `SHOPIFY_SCOPES`

**Key Files**: `controllers/shopifyAuthController.js`, `controllers/shopifyBillingController.js`, `routes/shopify-routes.js`, `webhooks/shopify.js`, `webhooks/shopifyBilling.js`

---

### 2. Salla

**Purpose**: Saudi e-commerce platform integration. Orders sync into Zambeel.

**Auth Flow (Standard OAuth2)**:
1. `GET /api/salla/auth/initiate?store_name=X&userId=Y` — redirects to `https://accounts.salla.sa/oauth2/auth` with scopes and `state={userId, store_name}`.
2. Salla redirects to `GET /api/salla/callback?code=X&state=Y` — exchanges code for tokens via `https://accounts.salla.sa/oauth2/token`.
3. Backend fetches store info from Salla API, calls `saveOrUpdateSallaStore()` to create/update the `stores` row (platform = `"salla"`, access + refresh tokens AES-encrypted).

**Webhook Endpoint**: `POST /api/wbhook/salla/orders` (special path required by Salla config)
- Handles `order.created`, `order.updated` events

**Token Refresh**: Salla access tokens expire; the backend stores the `refresh_token` and refreshes using `grant_type: refresh_token` against the Salla token endpoint.

**Key Config Keys**: `SALL_CLIENT_ID`, `SALL_CLIENT_SECRET`, `SALL_WEBHOOK_SECRET`

**Key Files**: `controllers/sallaController.js`, `routes/sallaRoutes.js`, `webhooks/salla.js`

---

### 3. LightFunnels

**Purpose**: Funnel-builder platform (popular in MENA). Orders sync into Zambeel via webhook and periodic background sync.

There are **two separate integration paths** — a legacy API-key route and the current OAuth2 flow. The OAuth2 flow is the active one for new integrations.

---

#### 3a. Legacy API-Key Flow (routes: `/api/lightfunnels/`)

Two endpoints still mounted at `/api/lightfunnels/` via `routes/lightFunnels-routes.js`:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/lightfunnels/auth` | `verifySeller` | Authenticate via LightFunnels email/password; returns access token |
| `DELETE` | `/lightfunnels/webhooks/delete` | `verifySeller` | Delete all registered LightFunnels webhooks for the connected store |

**Key Files**: `controllers/lightFunnelsController.js`, `routes/lightFunnels-routes.js`

---

#### 3b. OAuth2 Flow (routes: `/api/lightfunnels/oauth/`)

The current integration path. Six endpoints mounted at `/api/lightfunnels/oauth/` via `routes/lightFunnelsOAuthRoutes.js` and `controllers/lightFunnelsOAuthController.js`:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/lightfunnels/oauth/auth` | None | Initiate OAuth — stores state in session, redirects to LightFunnels |
| `GET` | `/lightfunnels/oauth/callback` | None | Handle OAuth callback — exchanges code, fetches stores, stores pending session data |
| `GET` | `/lightfunnels/oauth/check-user` | `verifySeller` | Check if seller is logged in and has a primary bank account |
| `GET` | `/lightfunnels/oauth/account` | `verifySeller` | Fetch pending LightFunnels account + store list from session |
| `GET` | `/lightfunnels/oauth/check-store-exists` | `verifySeller` | Check if the selected LF store is already connected |
| `POST` | `/lightfunnels/oauth/bind-store` | `verifySeller` | Create or update `stores` row and register `order/created` webhook |

**Step-by-step OAuth flow**:

1. **Initiate** (`GET /lightfunnels/oauth/auth?store_name=X&userId=Y`):
   - Builds `statePayload = {nonce, store_name, userId}` (encoded as base64url JSON).
   - Saves payload to `req.session.pendingLightFunnelsAuth`.
   - Redirects to `https://app.lightfunnels.com/admin/oauth` with `client_id`, `redirect_uri`, `scope=funnels,orders,products,customers`, `state`.

2. **Callback** (`GET /lightfunnels/oauth/callback?code=X&state=Y`):
   - Resolves `userId` and `store_name` from session OR decoded state param (whichever has them).
   - Exchanges `code` for `access_token` via `POST https://api.lightfunnels.com/api/access_token` (Basic auth: `clientId:clientSecret`, `grant_type: authorization_code`).
   - Gets `accountId` via GraphQL (`account.id`; falls back to `profile.connected_accounts[0]._id`).
   - Fetches all stores via paginated GraphQL query (`AccountStoresPaginatedQuery`) — handles accounts with many stores.
   - Stores `{id, access_token, accountId, shopData, stores[], store_name, userId}` into `req.session.pendingLightFunnelsData`.
   - Clears `req.session.pendingLightFunnelsAuth`.
   - Redirects to `{frontendUrl}/lightfunnels/bind?fromLightFunnelsInstall=true&sessionId=<id>`.

3. **Frontend bind page** (`/lightfunnels/bind`):
   - Calls `GET /lightfunnels/oauth/check-user` — confirms seller is logged in and has a primary bank account (required before binding is allowed).
   - Calls `GET /lightfunnels/oauth/account?sessionId=X` — fetches `{account, stores[], store_name}` from the pending session stored in the `Sessions` DB table.
   - If `stores.length > 1`: renders a store-selection UI; user picks one.
   - Optionally calls `GET /lightfunnels/oauth/check-store-exists?sessionId=X&lightFunnelsStoreId=Y` — warns if the store is already connected (shows existing store name + domain).
   - Calls `POST /lightfunnels/oauth/bind-store` with `{pendingLightFunnelsData: {sessionId}, storeName, lightFunnelsStoreId}`.

4. **Bind** (`POST /lightfunnels/oauth/bind-store`):
   - Loads pending session data from `Sessions` table (not just `req.session` — survives page refresh).
   - **Update path**: if `stores.store_id = platformStoreId AND user_id = userId` already exists → updates token, domain, metadata, sets `archived: false`.
   - **Create path**: requires `UsersBankAccount` with `is_primary: true, archived: false`; store name must be globally unique. Creates `stores` row (`platform = "lightfunnels"`, `store_currency = "AED"`, token AES-encrypted into `access_token` + `iv`). Also creates `StoreBankAccount` linking the store to the seller's primary bank.
   - Calls `registerLightFunnelsWebhook(access_token, accountId)` to register `order/created` webhook.

**Pre-bind requirements enforced by the bind endpoint**:
- Seller must be authenticated (`verifySeller`).
- A valid session ID pointing to stored `pendingLightFunnelsData` must exist.
- `lightFunnelsStoreId` must be provided (auto-resolved only if account has exactly one store).
- Seller must have a primary bank account (`UsersBankAccount` with `is_primary: true, archived: false`).
- Store name must be unique across all stores in the `stores` table.

**Token storage** (same pattern as Shopify): `encryptToken(access_token)` → `{encryptedToken, iv}` stored in `stores.access_token` + `stores.iv`.

**LightFunnels GraphQL endpoints used**:
- `https://services.lightfunnels.com/api/v2` — main API (account info, store list, webhooks)
- `https://services.lightfunnels.com/profile` — profile fallback for accountId resolution
- `https://api.lightfunnels.com/api/access_token` — token exchange

**Background Sync**: `services/lightfunnelsOrderSyncService.js` provides periodic order syncing in addition to the `order/created` webhook.

**Key Config Keys**: `lightFunnels.clientId`, `lightFunnels.clientSecret`, `app.frontendUrl`, `LIGHTFUNNELS_REDIRECT_URI`

**Key Files**: `controllers/lightFunnelsOAuthController.js`, `routes/lightFunnelsOAuthRoutes.js`, `constants/lightFunnels.constants.js`, `utils/lightFunnelsUtils.js`, `controllers/lightFunnelsController.js`, `routes/lightFunnels-routes.js`, `webhooks/lightFunnels.js`, `services/lightfunnelsOrderSyncService.js`

---

### 4. YouCan

**Purpose**: Moroccan/MENA e-commerce platform. Orders sync via webhook.

**Auth Flow (OAuth2)**:
1. `GET /api/youcan/auth` → redirects to YouCan OAuth with `YOUCAN_CLIENT_ID`, requested scopes, webhook events config.
2. Callback exchanges code for tokens, fetches store info, creates/updates `stores` row (platform = `"youcan"`).
3. Registers YouCan webhooks for order events.

**Webhook Verification**: Uses `YOUCAN_WEBHOOK_SECRET` to validate HMAC signatures on incoming events.

**Token Refresh**: Stores `refresh_token`; refreshes when needed using `grant_type: refresh_token`.

**Key Config Keys**: `YOUCAN_CLIENT_ID`, `YOUCAN_CLIENT_SECRET`, `YOUCAN_WEBHOOK_SECRET`, `YOUCAN_BASE_URL`

**Key Files**: `controllers/youcanController.js`, `routes/youcanRoutes.js`, `webhooks/youcan.js`

---

### 5. WooCommerce

**Purpose**: Self-hosted WordPress/WooCommerce stores. Orders sync via webhook.

**Auth Flow (WooCommerce REST API OAuth — "Consumer Key/Secret" pattern)**:
1. `GET /api/woocommerce/install?store_url=X&user_id=Y&store_name=Z` — builds a WooCommerce authorize URL and returns it to the frontend.
2. WooCommerce calls back to `GET /api/woocommerce/callback/u/:userId/s/:storeHost/n/:storeName` with `consumer_key` and `consumer_secret`.
3. Backend verifies credentials against the WooCommerce REST API (`/wp-json/wc/v3/system_status`), stores encrypted credentials in `stores.woocommerce_consumer_key`, `stores.woocommerce_consumer_secret`.
4. Registers WooCommerce webhooks for order events; stores `woocommerce_webhook_id`.

**Webhook Verification**: WooCommerce sends `X-WC-Webhook-Signature` HMAC header.

**Platform Detection**: Handles both pretty-permalinks (`/wp-json/wc/v3/`) and plain-permalink stores (`/?wc-api=`).

**Key Config Keys**: `WOOCOMMERCE_APP_NAME` (shown on store authorize screen)

**Key Files**: `controllers/woocommerceController.js`, `routes/woocommerceRoutes.js`, `webhooks/woocommerce.js`

---

### 6. EasyOrder

**Purpose**: EasyOrder funnel platform integration. Orders sync via webhook callback.

**Auth**: API key-based. `EASYORDER_PUBLIC_KEY` used for request signing/verification. `EASYORDER_CALLBACK_URL` / `EASYORDER_ORDERS_WEBHOOK_URL` define where EasyOrder sends order webhooks.

**Key Config Keys**: `EASYORDER_PUBLIC_KEY`, `EASYORDER_CALLBACK_URL`, `EASYORDER_ORDERS_WEBHOOK_URL`, `EASYORDER_REDIRECT_URL`, `EASYORDER_BASE_URL`, `EASYORDER_APP_NAME`

**Key Files**: `controllers/easyOrderController.js`, `routes/easyOrderRoutes.js`, `webhooks/easyOrder.js`

---

### 7. N1LLC (Internal/Whitelabel)

**Purpose**: N1LLC is an internal or whitelabel channel. Has its own route namespace (`/api/n1llc`). Mounted directly in `server.js` outside the main router. Details in `routes/n1llcRoutes.js`.

---

## Courier Partner Integrations

### 8. iMile

**Purpose**: UAE/GCC last-mile courier. Creates shipments, retrieves AWB labels, receives delivery status webhooks.

**Auth**: API key (`IMILE_API_KEY`) + customer ID (`IMILE_CUSTOMER_ID`) — passed in request headers.

**Key Operations**:
- Create shipment → get tracking number + AWB
- Get shipment status
- Receive webhook for delivery events (status updates)

**Webhook Endpoint**: handled via `controllers/imileWebhookController.js`, `services/imileWebhookService.js`

**Key Config Keys**: `IMILE_CUSTOMER_ID`, `IMILE_API_KEY`

**Key Files**: `controllers/imileController.js`, `routes/imileRoutes.js`, `services/imileService.js`, `controllers/imileWebhookController.js`

---

### 9. Tawseel

**Purpose**: UAE-based courier. Creates shipments, fetches AWB PDF.

**Auth**: API key (`TAWSEEL_API_KEY`) + password (`TAWSEEL_PASSWORD`) — likely passed as Basic auth or headers to the Tawseel REST API.

**AWB Fetch**: Separate base URL (`TAWSEEL_AWB_URL` → `https://b2b.tawseel.com/ecommerce/get_awb.php`) to fetch AWB label PDFs.

**Key Config Keys**: `TAWSEEL_API_KEY`, `TAWSEEL_PASSWORD`, `TAWSEEL_BASE_URL` (default: `https://api.tawseel.com/index.php/tawseel_api`), `TAWSEEL_AWB_URL`

**Key Files**: `services/tawseelService.js`, `routes/tawseelRoutes.js`, `webhooks/` (tawseel webhook handler)

---

### 10. Zajel

**Purpose**: UAE courier (Zajel Courier Services). Creates shipments and receives webhook status updates.

**Auth**: `X-AUTH-API-KEY` header with `ZAJEL_API_KEY`. Also uses `ZAJEL_CUSTOMER_CODE` and `ZAJEL_SERVICE_TYPE_ID`.

**Webhook Verification**: Incoming webhooks validated using `ZAJEL_WEBHOOK_API_KEY`.

**Base URL**: `https://api.zajel.com:8443/services/integration` (default).

**Key Config Keys**: `ZAJEL_API_KEY`, `ZAJEL_CUSTOMER_CODE`, `ZAJEL_SERVICE_TYPE_ID`, `ZAJEL_BASE_URL`, `ZAJEL_WEBHOOK_API_KEY`

**Key Files**: `services/zajelService.js`, `routes/zajelRoutes.js`, `controllers/zajelWebhookController.js`

---

### 11. Smartlane

**Purpose**: UAE/GCC courier (Smartlane). Creates shipments, receives webhook status updates.

**Auth**: Bearer token (`SMARTLANE_TOKEN`) sent as `Authorization: Bearer X`.

**Two base URLs**: Main API (`SMARTLANE_BASE_URL` → `https://app.smartlane.ae/api/v1`) and GCP API (`SMARTLANE_GCP_BASE_URL` → `https://gcp.smartlane.dev`) — used for different operations.

**Key Config Keys**: `SMARTLANE_TOKEN`, `SMARTLANE_BASE_URL`, `SMARTLANE_GCP_BASE_URL`

**Key Files**: `services/smartlaneService.js`, `controllers/smartlaneWebhookController.js`

---

## Communication Integrations

### 12. WATI (WhatsApp Business API)

**Purpose**: Primary customer communication channel. Sends order confirmation messages to customers via WhatsApp. Also allows agents to view WhatsApp conversation history for an order.

**Architecture**: WATI is configured per **country** (UAE, Saudi Arabia, Pakistan each have their own WATI account/number):
- Default: `WATI_DEFAULT_API_BASE_URL` + `WATI_DEFAULT_API_KEY` + `WATI_DEFAULT_TEMPLATE_NAME`
- Saudi: `WATI_SAUDI_API_BASE_URL` + `WATI_SAUDI_API_KEY` + `WATI_SAUDI_TEMPLATE_NAME`
- Pakistan: `WATI_PAKISTAN_API_BASE_URL` + `WATI_PAKISTAN_API_KEY` + `WATI_PAKISTAN_TEMPLATE_NAME`

**Key Operations**:
- `sendConfirmationMessageToCustomer(phone, country, orderData)` — called by the SQS worker after creating an order; routes to the correct WATI account by customer country
- `getConversationsInDateRange(phone, country, orderCreatedAt, daysAfter)` — fetches WhatsApp message history (up to N days after order creation) for display in the OMS order detail view
- `getMedia(fileName, country)` — proxies media file downloads from WATI

**URL Shortening**: TinyURL API (`TINYURL_API_TOKEN`) is used to shorten tracking links sent in WATI messages.

**Inbound Webhook**: `webhooks/watiInbound.js` handles incoming WhatsApp messages from WATI.

**Key Files**: `controllers/wattiConversation.js`, `helpers/watiApiService.js`, `helpers/sendWatiMessage.js`, `webhooks/watiInbound.js`

---

### 13. Customer.io

**Purpose**: Lifecycle email and event tracking for sellers/users.

**Architecture**: Uses `customerio-node` SDK (`TrackClient`), US region, identified by email as the user ID.

**Events Tracked**:
- `user_signed_up` — fired in `controllers/index.js` signUp handler; includes `email`, `username`, `country`, `provider`, `role`, `email_verified`, optional `promo_code`
- `profile_updated` — fired when seller updates their profile
- Generic `trackEvent(userId, eventName, data)` wrapper for ad-hoc events

**User Identification**: `identifyUser(userId, attributes)` syncs user attributes to Customer.io. User ID is the email address.

**Non-blocking**: All Customer.io calls catch errors and log warnings but never throw — they do not break the main request flow.

**Key Config Keys**: `CUSTOMERIO_SITE_ID`, `CUSTOMERIO_API_KEY`

**Key Files**: `services/customerioService.js`

---

## Infrastructure Integrations

### 14. Firebase

**Purpose**: Authentication identity provider. Every user has a `firebase_uid`. Firebase Admin SDK (`firebase-admin`) is used server-side to verify tokens.

**Key Files**: `firebase.js`, `firebaseAdminConfig.json`

### 15. AWS S3

**Purpose**: File storage for:
- Invoices and tickets: `S3_INVOICES_TICKETS_BUCKET_NAME`
- Agency documents (POC photos, identity proof): `AGENCY_S3_BUCKET_NAME`
- Broadcast notification images: `BROADCAST_S3_BUCKET_NAME`
- General assets: `S3_BUCKET_NAME`

**Key Files**: `controllers/s3Controller.js`, `routes/s3Routes.js`

### 16. AWS SES

**Purpose**: Transactional email. Used for agency team member invite emails.

**Config**: `AWS_SES_FROM_EMAIL` (verified sender), `AWS_SES_IDENTITY_ARN`

### 17. AWS SQS

**Purpose**: Order processing queue. Shopify webhook handler enqueues raw order payloads; the in-process worker dequeues and processes them asynchronously.

**Key Files**: `config/sqs.js`, `services/sqsService.js`, `workers/orderProcessor.js`

### 18. Sentry

**Purpose**: Error monitoring and performance tracing.

**Config**: `SENTRY_DSN` (empty = disabled), `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` (default 0.1), `SENTRY_PROFILE_SESSION_SAMPLE_RATE` (default 0.1), `SENTRY_ENABLE_LOGS`, `SENTRY_SEND_DEFAULT_PII` (default false)

### 19. Notion

**Purpose**: Integration for syncing data to/from a Notion database. Configured via `NOTION_SECRET` + `NOTION_DATABASE_ID`. Routes: `/api/notion`.

### 20. PayTabs

**Purpose**: Payment gateway for billing (subscription payments). Used via `PAYTABS_PROFILE_ID` + `PAYTABS_SERVER_KEY`. Routes: `/api/payments`, `/api/billing`.

---

## Integration Summary Table

| Integration | Type | Auth Method | Primary Purpose |
|---|---|---|---|
| Shopify | E-commerce platform | OAuth2 + encrypted token | Order sync, product sync |
| Salla | E-commerce platform | OAuth2 + refresh token | Order sync (Saudi market) |
| LightFunnels | Funnel platform | OAuth2 + GraphQL | Order sync (MENA) |
| YouCan | E-commerce platform | OAuth2 + webhook HMAC | Order sync (Morocco/MENA) |
| WooCommerce | E-commerce platform | Consumer key/secret | Order sync |
| EasyOrder | Funnel platform | API key | Order sync |
| N1LLC | Internal/whitelabel | — | Internal channel |
| iMile | Courier | API key + customer ID | Last-mile delivery (UAE/GCC) |
| Tawseel | Courier | API key + password | Last-mile delivery (UAE) |
| Zajel | Courier | X-AUTH-API-KEY | Last-mile delivery (UAE) |
| Smartlane | Courier | Bearer token | Last-mile delivery (UAE/GCC) |
| WATI | WhatsApp | Per-country API keys | Customer confirmation messages |
| Customer.io | Email/events | Site ID + API key | Lifecycle events tracking |
| Firebase | Auth | Admin SDK | User identity |
| AWS S3 | Storage | IAM credentials | File storage |
| AWS SES | Email | IAM credentials | Agency invite emails |
| AWS SQS | Queue | IAM credentials | Order processing queue |
| Sentry | Monitoring | DSN | Error tracking |
| Notion | Database | API secret | Data sync |
| PayTabs | Payments | Profile ID + server key | Subscription billing |
| TinyURL | URL shortener | API token | WATI tracking links |
