# Zambeel Backend — System Architecture

## Runtime & Entry Point

- **Runtime**: Node.js with Express 4.x
- **Entry point**: `server.js` (starts HTTP server + optional SQS worker in same process)
- **Port**: 3000 (env: `PORT`)
- **Logging**: Bunyan (piped via `| ./node_modules/.bin/bunyan` in npm scripts)
- **Error monitoring**: Sentry (`@sentry/node`) — enabled when `SENTRY_DSN` is set; profiling via `@sentry/profiling-node`

## HTTP Server Structure

```
server.js
  └─ Express app
       ├─ Middleware stack (in order)
       │    ├─ cookie-parser
       │    ├─ express.static("assets")
       │    ├─ express.json / bodyParser.json  (limit: 50mb)
       │    ├─ express.urlencoded / bodyParser.urlencoded (limit: 10mb/50mb)
       │    ├─ CORS (all origins, credentials: true)
       │    └─ express-session (scoped to /api/shopify, /api/youcan, /api/lightfunnels)
       ├─ /proxy  → proxyRouter (unauthenticated pass-through)
       ├─ /api    → main router (routes/index.js)
       ├─ /api/webhooks → webhookRouter (routes/webhooks/index.js)
       ├─ /api/wbhook/salla/orders → sallaWebhook (webhooks/salla.js)
       └─ /api/n1llc → n1llcRoutes
```

## Session Store

Sessions for OAuth flows (Shopify, YouCan, LightFunnels) are stored in the **MySQL `Sessions` table** via `connect-session-sequelize`. Session TTL = 24 h, cleanup check every 15 min.

## Database

**Single database: MySQL** (via Sequelize ORM, `mysql2` driver).

Config keys (env vars):
- `DATABASE_HOST`, `DATABASE_NAME`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_PORT` (default 5432 — note: this default is wrong for MySQL; actual port is 3306 in practice)

The `models/index.js` file bootstraps Sequelize and registers all associations. All models use Sequelize `define()` with explicit `tableName`.

There is **no MongoDB/Mongoose** in this codebase despite the project looking like it might. Everything is relational SQL.

## Main Route Groups (`/api`)

| Prefix | Router/Controller | Description |
|---|---|---|
| `/signUp`, `/login` | controllers/index.js | Auth |
| `/auth/check-email` | controllers/index.js | Email availability |
| `/verify-email` | controllers/index.js | Email verification |
| `/user/profile` | controllers/index.js | Profile update |
| `/user/accept-terms` | controllers/index.js | Terms acceptance |
| `/products` | routes/products.js | Product catalog |
| `/orders` | routes/orders.js | Order CRUD + lifecycle |
| `/purchase-orders` | routes/purchaseOrders.js | Purchase orders (warehouse inbound) |
| `/return-orders` | routes/returnOrders.js | Return order management |
| `/inventory` | routes/sellerInventoryRoutes.js | Seller-facing inventory |
| `/inventory-movements` | routes/inventoryMovementRoutes.js | Warehouse inventory moves |
| `/tickets` | routes/ticketRoutes.js | Support tickets |
| `/comments` | routes/commentRoutes.js | Ticket comments |
| `/payments` | routes/paymentRoutes.js | PayTabs payments |
| `/invoices` | routes/invoiceRoutes.js | PDF invoices |
| `/billing` | routes/billingRoutes.js | Subscription billing |
| `/agency` | routes/agencyRoutes.js | Agency portal |
| `/admin/agency-registrations` | routes/agencyRegistrationAdminRoutes.js | Admin: agency approval |
| `/admin/gold-subscriptions` | routes/goldSubscriptionAdminRoutes.js | Admin: gold subscriptions |
| `/admin/broadcast-notifications` | routes/broadcastNotificationAdminRoutes.js | Admin: push blasts |
| `/broadcast-notifications` | routes/broadcastNotificationRoutes.js | Seller: notifications |
| `/store` | routes/storeRoutes.js | Store management |
| `/shopify` | routes/shopify-routes.js | Shopify OAuth + webhooks |
| `/lightfunnels` | routes/lightFunnels-routes.js | LightFunnels OAuth |
| `/lightfunnels/oauth` | routes/lightFunnelsOAuthRoutes.js | LightFunnels token refresh |
| `/salla` | routes/sallaRoutes.js | Salla OAuth |
| `/woocommerce` | routes/woocommerceRoutes.js | WooCommerce OAuth |
| `/youcan` | routes/youcanRoutes.js | YouCan OAuth |
| `/easyOrders` / `/easyorders` | routes/easyOrderRoutes.js | EasyOrder integration |
| `/accounts` | routes/bankRoutes.js | Bank account management |
| `/data` | routes/thresholdAndRatio.js | Country thresholds/ratios |
| `/imile` | routes/imileRoutes.js | iMile courier |
| `/tawseel` | routes/tawseelRoutes.js | Tawseel courier |
| `/zajel` | routes/zajelRoutes.js | Zajel courier |
| `/contracts` | routes/contractRoutes.js | Contract management |
| `/orderTags` | routes/orderTags.js | Order tag bulk updates |
| `/tags` | routes/tagRoutes.js | Tag management |
| `/ticker-config` | routes/tickerRoutes.js | Ticker configuration |
| `/s3` | routes/s3Routes.js | S3 upload/signed URLs |
| `/creative-analytics` | routes/aiVideoCreatorRoutes.js | AI video creator |
| `/notion` | routes/notion-routes.js | Notion integration |
| `/proxy` | routes/proxyRoutes.js | External API proxy |
| `/remarks` | controllers/remarks.js | Bulk order remarks |
| `/tags` | controllers/orderTags.js | Tag-based status updates |
| `/sub-statuses` | controllers/subStatuses.js | Sub-status lookup |
| `/teams` | controllers/teams.js | Agent teams |
| `/agents` | controllers/index.js | Agent user list |
| `/dashboard/data` | controllers/dashboardController.js | Dashboard aggregates |

## Webhook Route Groups (`/api/webhooks`)

Located in `routes/webhooks/` directory with files for: `shopify.js`, `lightFunnels.js`, `woocommerce.js`, `youcan.js`, `easyOrder.js`, `productsWebhook.js`, `watiInbound.js`, `webhooks.js`, `shopifyBilling.js`.

Salla has a special path: `POST /api/wbhook/salla/orders` (outside the main webhook router).

## Background Worker (SQS)

Enabled by `ENABLE_WORKER=true` (or `config.app.enableWorker`). Runs **in-process** with the HTTP server (not a separate process). Located in `workers/orderProcessor.js`.

**What it does:**
1. Polls AWS SQS queue (`SQS_QUEUE_URL`) every 1 second for new Shopify order messages
2. Calls `processOrderFromQueue()` to consume and process one message at a time
3. Every 5 minutes runs `recoverStuckOrders()` to pick up any orders stuck in `processing_status = 'processing'`

**Order processing flow in the worker:**
1. Receive SQS message containing raw Shopify order JSON + shop domain
2. Deduplicate: check if `platform_order_id` already exists in `orders` table → mark as `duplicate` and skip
3. Find store by `shopDomain`
4. Resolve customer (create or find by phone)
5. Match order line items to variants by SKU
6. Compute amounts (price, discount, tax, shipping)
7. Create `Order` + `OrderProductVariant` junction records in a transaction
8. Decrement `WarehouseVariant.quantity`
9. Create `OrderLog` entry
10. Send WATI confirmation message to customer
11. Delete SQS message on success; leave it for retry on failure

## Cron Jobs

`cron/` directory exists. The cron is **disabled** in production (`// require("./cron")` commented out in server.js). The `jobs/deliveryRatioJob.js` handles delivery ratio recalculation.

## AWS Services Used

| Service | Purpose | Config Key |
|---|---|---|
| S3 | File storage (invoices, tickets, AWBs, broadcast images, agency docs) | `S3_BUCKET_NAME`, `AGENCY_S3_BUCKET_NAME`, `S3_INVOICES_TICKETS_BUCKET_NAME`, `BROADCAST_S3_BUCKET_NAME` |
| SQS | Order processing queue | `SQS_QUEUE_URL` |
| SES | Transactional email (agency invites) | `AWS_SES_FROM_EMAIL` |

## Real-Time (Socket.io)

Socket.io is mounted on the same HTTP server. Sellers join `user_{userId}` rooms on connect. Server pushes real-time updates to specific users via `io.to('user_X').emit(...)`.

## Key Middleware

| Middleware | Applied to | Purpose |
|---|---|---|
| `verifySeller` | Most seller routes | JWT validation, attaches `req.user` |
| `verifyUser` | Some admin routes | JWT validation (any role) |
| `validateRequest(schema)` | POST/PUT routes | Joi/express-validator schema validation |
| `express-session` | `/api/shopify`, `/api/youcan`, `/api/lightfunnels` | OAuth state storage |

## Authentication

- Firebase Authentication is used for identity (`firebase_uid` stored on every User)
- The backend issues its own JWT (`JWT_SECRET`) after verifying the Firebase token
- `verifySeller` middleware validates the JWT and loads the User from the database
- Encryption of store `access_token` values uses AES (`APP_CRYPTO_SECRET` / `APP_IV`)
