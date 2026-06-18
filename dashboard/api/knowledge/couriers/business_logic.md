# Couriers Domain — Business Logic

## What This Domain Does

The Couriers domain integrates Zambeel's OMS with multiple third-party last-mile delivery providers. It handles:
- Creating shipments with courier APIs.
- Fetching and uploading AWB (Air Waybill) labels to S3.
- Receiving webhook status updates from couriers and translating them into Zambeel order statuses.
- When an order is delivered via webhook, triggering agency commission recording.

Current integrated couriers:
- **iMile** — UAE/GCC; integrator + direct courier; REST API with token auth.
- **Tawseel** — form-encoded API; AWB labels downloaded and uploaded to S3.
- **Zajel** — UAE; REST API with `X-AUTH-API-KEY` header.
- **Smartlane** — Integrator/aggregator for Pakistan (e.g., TCS, Leopards); REST API with Bearer token; consignment webhooks assign tracking IDs to batched orders.
- **EasyOrders** — e-commerce integration platform (OAuth install link, order sync webhook).

---

## Key Endpoints

### iMile (`/api/imile/...`, roles: `Agent`, `Admin`, `Seller`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/imile/token` | Fetch/return cached iMile access token |
| POST | `/imile/create-order` | Create a shipment on iMile |
| POST | `/imile/track` | Track an order by `orderNo` + `expressNo` |
| POST | `/imile/cancel` | Cancel an order by `orderCode` or `waybillNo` |
| POST | `/imile/reprint-awb` | Reprint AWB labels; max 50 per call; `orderCodeType`: 1=orderNo, 2=waybillNo |
| POST | `/imile/pod` | Query POD (Proof of Delivery) attributes by `orderNo` + `podType` |
| POST | `/imile/webhook` | iMile pushes status updates here (no auth required; public) |

### Tawseel (`/api/tawseel/...`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tawseel/webhook` | Tawseel pushes status updates here (public) |

_(Create/cancel/track calls to Tawseel are made internally by the order-creation flow and batch controller, not exposed as standalone REST endpoints on this router.)_

### Zajel (`/api/zajel/...`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/zajel/webhook` | Zajel pushes status updates here; verified by `X-AUTH-API-KEY` header |

_(Create/cancel/track calls are made internally by order and batch controllers.)_

### EasyOrders (`/api/easyorders/...` and `/api/easyOrders/...`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/easyorders/install-link` | Generate OAuth install link for EasyOrders store connection (seller auth required) |
| POST | `/easyorders/callback` | OAuth callback after merchant authorization; completes store connection |
| DELETE | `/easyorders/disconnect` | Remove EasyOrders store webhooks and disconnect (seller auth required) |

---

## Business Logic — iMile

### Token Management
- Tokens are cached in memory with a 5-minute early-expiry buffer (`expiresAt - 5min`).
- Auth method: `signMethod=SimpleKey`, `grantType=clientCredential`.
- Base URL: `https://openapi.imile.com` (same for staging and production — no env switch currently).
- Config keys: `imile.customerId`, `imile.apiKey`.

### Create Order
- Calls `/client/order/v2/createOrder` with `senderInfo`, `consigneeInfo`, `packageInfo`, `skuInfos`.
- `orderType` defaults to `"100"` (standard delivery).
- Returns `{ success, data, message, rawResponse }`.

### AWB Reprint + S3 Upload (`getAWBAndUploadToS3`)
1. Calls `/client/order/batchRePrintOrder` with `orderCodeList` and `orderCodeType` (1=orderNo, 2=waybillNo).
2. Extracts AWB URL from response (tries fields: `label`, `fileUrl`, `url`, `awbUrl`, `filePath`).
3. Downloads the PDF from the AWB URL using the iMile access token as Bearer.
4. Validates content: checks `Content-Type` header and first 4 bytes for `%PDF`.
5. If response is JSON (not PDF) with `resultCode=30070`, returns specific error: "iMile label template not configured."
6. Uploads validated PDF to S3 under `awbs/AWB_{orderNumber}_{orderCode}.pdf`.
7. Returns `{ success, s3Url }`.

### iMile Webhook Pipeline (`POST /imile/webhook`)

Seven-step ordered pipeline:

| Step | Name | Action |
|------|------|--------|
| 0 | Parse | Extract `latestStatus`, `locus` array, count OFD events (`ofdCount = locus entries where latestStatus==="OFD"`) |
| 1 | Mapping Lookup | Look up `latestStatus` code in CSV file (`data/Status Mapping Final - Sheet5-2.csv`); maps to Zambeel `{status, substatus, tag}` |
| 2 | Terminal Status Gate | If current order status = `Delivered` and candidate ≠ `Delivered` → exit (block downgrade) |
| 3 | FA- Tag Gate | If current order tag starts with `FA -` and candidate status is not `Return in Transit` or `Delivered` → exit |
| 4 | Uncontactable Gate | If candidate substatus = `Customer Uncontactable - Assigned to CS Team` and tag = `Uncontactable and Unreachable` and `ofdCount < 2` → override to `{Shipped, In Delivery, Delivery Attempt Failed → Customer Unreachable}` |
| 5 | Scheduled Gate | If candidate substatus = `Scheduled by Customer` and tag = `Customer Requested Future Delivery` and `ofdCount >= 2` → override to `{Undelivered, Customer Uncontactable - Assigned to CS Team, Uncontactable and Unreachable}` |
| 6 | Return Tag Preservation | If mapping lands on `Return in Transit / Returning` and incoming iMile code is a logistics-only return code, preserve the *existing* order tag (reason) instead of mapping's default tag |
| 7 | Write | Update `Order.status` (locked row), log `OrderLog`, call `maybeRecordCommissionOnDelivered`, sync LightFunnels |

**Order lookup**: Finds order by `courier_tracking_id` matching any of `billNo`, `orderNo`, `waybillNo`, `expressNo` from the payload. Then filters to iMile orders only via `isImileOrder()` util.

**Idempotency**: If status/substatus/tag are unchanged after pipeline, no DB update is made.

**Commission trigger**: Whenever a webhook transitions an order to `Delivered`, `maybeRecordCommissionOnDelivered` is called inside the transaction.

---

## Business Logic — Tawseel

### Service Operations
- Auth: `api` and `pwd` headers (form-encoded POST requests).
- **Create order**: POST to `/CreateOrder`; success = `response.response === true`.
- **Cancel order**: POST to `/CancelOrder` with `awb_number`.
- **Track order**: POST to `/OrderStatus` with `awb_number`; returns `{status_desc, remarks, trans_datetime}`.
- **Track all history**: POST to `/OrderStatusAll`; returns full array of history events.
- **Pickup request**: POST to `/CreateRequest` with `{pickup_date, pickup_id, pickup_time, order_id: [awbs]}`.
- **AWB fetch + S3 upload**: Downloads via GET with `api`/`pwd`/`awb` params; validates PDF header (`%PDF`); uploads to S3 as `awbs/AWB_{orderNumber}_{awb}.pdf`.

### Tawseel Webhook
- Receives POST at `/tawseel/webhook`; handled by `tawseelWebhookController`.
- (Full webhook controller code not read in this session; presumed to follow same pattern as other couriers: look up order by AWB, map status, update, log, trigger commission.)

---

## Business Logic — Zajel

### Service Operations
- Auth: `X-AUTH-API-KEY` header.
- **Create shipment**: POST to `/api/Merchant/CreateShipment`; success = `raw.success === true`; returns `{reference_number, customer_reference_number}`.
- **Cancel shipment**: POST to `/api/Merchant/CancelShipment` with `{reference_number}`; 2 retries on transient network errors.
- **Track shipment**: GET to `/api/Merchant/TrackShipment?reference_number=...`; returns `{status, status_applied_on}`.
- **Get label + S3 upload**: GET to `/api/Merchant/GetShipmentLabel?reference_number=...`; validates PDF (`%PDF` or base64 fallback); uploads to S3 as `awbs/AWB_{orderNumber}_{ref}.pdf`.

### Zajel Webhook (`POST /zajel/webhook`)
1. Validates `X-AUTH-API-KEY` against `zajel.webhookApiKey` config (if set; otherwise no auth).
2. Requires `reference_number` in body.
3. Looks up order by `courier_tracking_id = reference_number`.
4. Checks that `courierPartner.integrator_type` identifies it as a Zajel order (`isZajelCourierPartner()`).
5. Calls `applyZajelTrackingToOrder()`:
   - Maps Zajel `status` (+ optional `failure_reason`) to Zambeel `{status, substatus, tag}` via `mapZajelStatusToOrderStatus()`.
   - Merges Zajel tracking metadata into `order.meta.zajel_tracking`.
   - Sets `order.shipment_date` if the mapped status is `Shipped` and `shipment_date` not already set.
   - If status changed: calls `maybeRecordCommissionOnDelivered`; creates `OrderLog` with `action=STATUS_UPDATE_ZAJEL_WEBHOOK`.
6. Always returns 200 (even on order-not-found, to prevent courier retries).

---

## Business Logic — Smartlane

### Service Operations (integrator for Pakistan)
- Auth: Bearer token.
- **Create consignment**: POST to `{gcpBaseUrl}/consignment/create`; returns array of consignments.
- **Cancel consignment**: POST to `{gcpBaseUrl}/consignment/cancel` with `{store_order_id}`.
- **Get airway bill**: GET to `{gcpBaseUrl}/consignment/airway/bill?store_order_id[]=...`; returns HTML (not PDF).
- **Get load sheet**: POST to `{baseUrl}/shipments/load-sheet` with `{shipmentIds}`; returns PDF arraybuffer.

### Smartlane Webhook (consignment assignment)
- Receives POST at (route not mounted on a standalone router; mounted elsewhere; controller = `smartlaneWebhookController.processConsignments`).
- Payload may be an array of consignments or a single object with a `consignments` array.
- For each consignment:
  1. Parse `store_order_id` — must be `ZAMPAK-{id}` format or numeric.
  2. Skip if `consignment_number` is missing or equals `"Not Assigned Yet"` placeholder.
  3. Skip if `order.zambeel_tracking_id` ends with `-C` (courier assignment was cleared by a user; webhook must not overwrite).
  4. Resolve sub-courier: look up `courierPartner` by `consignment.courier` name to get `sub_courier_id`.
  5. Update `Order.courier_tracking_id = consignmentNumber`; also update `sub_courier_id` and `fk_courier_id` to the resolved sub-courier (e.g., TCS), replacing the Smartlane integrator assignment.
  6. Fetch AWB HTML from Smartlane and upload to S3 as `awbs/AWB_{storeOrderId}.html`.
  7. After AWB saved, check if all orders in the batch now have tracking + AWB; if so, set `DispatchBatch.tracking_status = "Generated"` (else `"Partial"`).

### Integrator/Sub-Courier Model
- `courier_partners.is_integrator = true` marks Smartlane as an integrator.
- `courier_sub_couriers` maps integrator → actual sub-courier (e.g., Smartlane → TCS).
- Order stores both `fk_courier_id` (initially Smartlane; replaced by sub-courier on webhook) and `sub_courier_id`.
- `fk_integrator_id` preserved for lineage tracking.

---

## Key Model — `courier_partners`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT PK | |
| `name` | VARCHAR | Display name (also used for Smartlane sub-courier lookup) |
| `tracking_url_template` | VARCHAR | URL pattern for customer-facing tracking links |
| `tracking_url_default` | VARCHAR | Fallback tracking URL |
| `country` | VARCHAR | Operating country |
| `deeplink_support` | BOOLEAN | Whether tracking deeplinks are supported |
| `fk_parent_courier_id` | INT NULLABLE | Parent in a courier hierarchy |
| `is_integrator` | BOOLEAN | True for Smartlane (aggregator); false for direct couriers |
| `integrator_type` | VARCHAR(100) | Identifies the integration (e.g., "imile", "zajel", "smartlane") |

### `courier_sub_couriers` table
| Column | Type | Notes |
|--------|------|-------|
| `fk_integrator_id` | INT | The integrator (e.g., Smartlane's partner id) |
| `fk_sub_courier_id` | INT | The actual courier (e.g., TCS) |
| `external_sub_courier_name` | VARCHAR | Name as returned by the integrator API |

---

## Domain Interactions

| Domain | How It's Used |
|--------|--------------|
| Orders | Webhook handlers update `Order.status`, `courier_tracking_id`, `sub_courier_id`, `awb_file_path`, `shipment_date`, `meta` |
| Agency Commissions | All courier webhooks call `maybeRecordCommissionOnDelivered` when status transitions to Delivered |
| Dispatch Batches | Smartlane webhook updates `DispatchBatch.tracking_status` when all batch orders have tracking + AWB |
| S3 | All AWB PDFs/HTML files are uploaded to S3 under the `awbs/` prefix |
| LightFunnels | iMile webhook calls `syncLightfunnelsOrderStatus()` after updating order status |
| OrderLog | All status changes from webhooks are recorded in `OrderLog` with the courier-specific action constant |

---

## Important Constraints and Rules

1. **iMile token is cached in-process**: If the server restarts, a fresh token is fetched. Cache includes a 5-minute early-expiry buffer to avoid using near-expired tokens.
2. **iMile AWB label template must be configured**: If iMile API returns error code `30070` (Chinese: 模板未配置), the error is translated to a human-readable message about configuring the label template in the iMile dashboard.
3. **iMile max AWB reprint batch**: 50 orders per request.
4. **iMile Delivered is terminal**: Once an order is Delivered, the webhook will block any status downgrade (checked both before and inside the DB transaction).
5. **FA- tag gate**: Orders with a tag starting with `FA -` can only be updated by iMile webhooks to `Return in Transit` or `Delivered`. All other status updates are blocked, preserving the forced-action state.
6. **OFD count gates**: The number of Out-For-Delivery events determines whether an "Uncontactable" candidate gets overridden to a milder status (< 2 OFDs) or a "Scheduled" candidate escalates to Undelivered (≥ 2 OFDs).
7. **Smartlane cleared-assignment guard**: If `zambeel_tracking_id` ends with `-C`, Smartlane webhooks will not overwrite the courier tracking state. This prevents a race condition where a user manually clears a courier assignment and Smartlane re-assigns it.
8. **Zajel webhook authorization**: If `zajel.webhookApiKey` is set in config, the webhook checks `X-AUTH-API-KEY` header. If not set, all calls are accepted (open for development/staging).
9. **Zajel retry on network errors**: `cancelOrder` and `trackOrder` retry up to 2 times on transient network errors (ECONNRESET, ETIMEDOUT, socket hang up, etc.).
10. **Status mapping is CSV-driven (iMile)**: Adding new iMile status codes or changing Zambeel status mappings requires updating `data/Status Mapping Final - Sheet5-2.csv` — no code changes needed.
11. **Commission is only recorded once per order**: `AgencyCommissionRecord` has a unique constraint on `fk_order_id`; the service does an existence check before inserting.
12. **Smartlane orders use `ZAMPAK-{orderId}` as store_order_id**: This is the canonical format for identifying Zambeel orders within the Smartlane system.
