# Orders Domain — Business Logic

## What This Domain Does

Orders is the core domain of the Zambeel OMS. It manages the full lifecycle of customer orders from creation (via CSV upload or e-commerce platform webhooks) through confirmation, courier assignment, dispatch, shipping, delivery, and cancellation. Every order belongs to a store, belongs to a customer, and contains one or more product variants.

---

## Key Model: `orders` table

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `order_number` | STRING | Human-readable order reference (e.g. from platform) |
| `fk_customer_id` | INTEGER FK → customers | |
| `fk_store_id` | INTEGER FK → stores | |
| `platform` | ENUM | `Shopify`, `Easy orders`, `Youcan`, `Lightfunnels`, `Manual` |
| `total_cost` | DECIMAL(10,2) | |
| `total_payable` | DECIMAL(10,2) | Mirrors total_cost on creation; updated if cost changes |
| `total_discount` | DECIMAL(10,2) | |
| `post_dispatch_discount` | DECIMAL(10,2) | Discount applied after dispatch |
| `total_tax` | DECIMAL(10,2) | |
| `shipping_price` | DECIMAL(10,2) | |
| `currency` | STRING | |
| `status` | TEXT (JSON) | `{ status, substatus, tag }` — stored as JSON string |
| `status_value` | STRING(100) | Generated column copy of `status.status` — used for fast indexed queries |
| `status_tag` | STRING(100) | Generated column copy of `status.tag` |
| `status_substatus` | STRING(100) | Generated column copy of `status.substatus` |
| `payment_method` | STRING | `cod` or `paid` (prepaid); affects confirmation flow |
| `order_date` | DATE | |
| `tracking_number` | STRING | Legacy field |
| `zambeel_tracking_id` | STRING | Internal Zambeel tracking ID (prefix + 6 digits) |
| `courier_tracking_id` | STRING | Courier-assigned tracking ID (from iMile, Zajel, Tawseel, etc.) |
| `fk_courier_id` | INTEGER FK → courier_partners | Assigned courier |
| `fk_integrator_id` | INTEGER FK → courier_partners | Smartlane integrator courier (when order goes through Smartlane) |
| `sub_courier_id` | INTEGER FK → courier_partners | Sub-courier assigned by Smartlane |
| `fk_vendor_id` | INTEGER FK → vendors | |
| `fk_assign_to` | INTEGER FK → users | Agent assigned to this order |
| `bifurcation` | ENUM | `Partner`, `Reseller`, `360`, `3PL` — defaults to `Partner` |
| `reschedule_date` | DATE | |
| `shipment_date` | DATE | Set automatically when status becomes `Shipped` |
| `activity_counter` | INTEGER | Number of confirmation attempts |
| `ndr_meta_data` | JSON | Non-delivery report data; contains `remarks` array |
| `meta` | TEXT (JSON) | Platform-specific metadata; used for confirmation messages |
| `archive` | BOOLEAN | Soft-delete flag; archived orders cannot be updated |
| `platform_order_id` | STRING (unique) | External platform order ID |
| `awb_file_path` | TEXT | S3 path to generated AWB document |

### Associations
- `Order` → `Customer` (belongsTo, FK `fk_customer_id`)
- `Order` ↔ `Variant` (belongsToMany through `OrderProductVariant`)
- `Order` → `User` as `assignedUser` (belongsTo, FK `fk_assign_to`)
- `Order` → `Store` (belongsTo, FK `fk_store_id`)
- `Order` ↔ `Remark` (belongsToMany through `order_remarks`)
- `Order` → `OrderLog[]` (hasMany, FK `fk_order_id`)
- `Order` → `Ticket[]` (hasMany, FK `fk_order_id`)
- `Order` → `BatchOrder` (hasOne, FK `order_id`)
- `Order` → `CourierPartner` as `courierPartner`/`integrator`/`subCourier`
- `Order` → `Vendor`

---

## Order Status State Machine

Status is stored as a JSON object `{ status, substatus, tag }`. The `status_value`, `status_tag`, and `status_substatus` generated columns mirror these for efficient querying.

### Status Flow

```
Received → Confirmation Pending → Approved → Dispatching in Process → Shipped → Delivered
                                ↓                                    ↓
                            Cancelled                          Undelivered → Return in Transit → Return
```

**Main statuses:** `Received`, `Confirmation Pending`, `Approved`, `Dispatching in Process`, `Shipped`, `Delivered`, `Undelivered`, `Return in Transit`, `Return`, `Cancelled`

**Pre-dispatch statuses (PRE_SHIPPED_STATUSES):** Received, Confirmation Pending, Approved

**Post-dispatch statuses (SHIPPED_STATUSES):** Shipped, Delivered, Undelivered, Return in Transit, Return

### Enforcement Rules
- **Cannot move backward** from `Dispatching in Process` to `Approved` via the single/bulk approve endpoints.
- **DIP→Confirmation Pending is allowed** via `PUT /orders/revert-dispatching-in-process` (see below). This is the only supported backward transition out of Dispatching in Process.
- **Cannot update** archived orders (`archive === true`).
- **Bulk CSV update** cannot push a shipped order back to a pre-shipped status.
- Orders in `Received` status appear only in the seller's `getSellerOrders` (pending confirmation queue), not in the main OMS admin order list.

---

## All Key Endpoints

### Querying Orders

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/orders` | verifyUser | Main OMS order list with rich filters |
| `GET` | `/orders/status-counts` | verifyUser | Count orders by status (for dashboard tabs) |
| `GET` | `/orders/order-analytics` | verifySeller | Pre/post dispatch analytics with substatus breakdown |
| `GET` | `/orders/seller-orders` | verifySeller | Seller's own queue of `Received`-status orders needing push |
| `GET` | `/orders/substatusOrders` | verifySeller | Orders filtered by substatus (for OMS substatus view) |
| `GET` | `/orders/proccessedOrders` | verifySeller | Seller's non-Received orders with pagination |
| `GET` | `/orders/store/:storeId` | — | Orders for a store that are in `Received` status |
| `GET` | `/orders/orderDetails/:orderId` | verifyAgentAdminAndSeller | Full order modal data with variants |
| `GET` | `/orders/:orderId/logs` | verifyAgentAdminAndSeller | Audit log for a specific order |
| `GET` | `/orders/duplicates/:orderId` | verifyUser | Detect duplicate orders by phone number |

### Creating Orders

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/orders/uploadOrderCSV` | verifySeller | Seller CSV upload (groups by order_reference_id, validates SKUs/warehouse) |
| `POST` | `/orders/bulk-order-upload` | verifyUser | OMS admin bulk CSV upload (validates SKU, tag, store, payment_mode) |
| `PUT` | `/orders/bulk-csv-update` | verifyUser | Bulk status update via CSV (order_id, sub_status, tag, tracking_id, courier_id, vendor_id) |

### Updating Orders

| Method | Path | Auth | Description |
|---|---|---|---|
| `PUT` | `/orders/:orderId` | verifyAgentAdminAndSeller | Update order cost, discount, tax, NDR data, reschedule date, payment method, customer name, tags |
| `PUT` | `/orders/:orderId/order-product-variants/:orderProductVariantId` | verifyAgentAdminAndSeller | Update variant quantity/price |
| `DELETE` | `/orders/:orderId/delete-product/:orderProductVariantId` | verifyAgentAdminAndSeller | Remove a product from an order |
| `POST` | `/orders/add-product` | verifyAgentAdminAndSeller | Add a product variant to an existing order |
| `PUT` | `/orders/customers/:customerId` | verifyAgentAdminAndSeller | Update customer address, city, country, phone, area_name, building_society, national_address_short_code |
| `PUT` | `/orders/address/:orderId` | verifyAdminAndSeller | Update order fields (legacy address update endpoint) |
| `PUT` | `/orders/:orderId/edit` | verifyAgentAdminAndSeller | Edit order fields via courierAssignment controller |

### Status Transitions

| Method | Path | Auth | Description |
|---|---|---|---|
| `PUT` | `/orders/:orderId/status` | verifyAdminAndSellerWithAgencyContext | Move order from `Received` → `Confirmation Pending` (initiates confirmation flow) |
| `PUT` | `/orders/:orderId/approve-status` | verifyAgentAdminAndSeller | Approve or Cancel a single order |
| `PUT` | `/orders/approve-status/bulk` | verifyAgentAdminAndSeller | Bulk approve or cancel orders |
| `PUT` | `/orders/revert-to-confirmation-pending` | verifyUser | Revert orders back to Confirmation Pending |
| `PUT` | `/orders/revert-dispatching-in-process` | verifyUser | Revert dispatching-in-process orders |
| `POST` | `/orders/dip-revert-summary` | verifyUser | Get summary before reverting DIP orders |
| `POST` | `/orders/sub-statuses/bulk-update` | verifyAgentAdminAndSeller | Bulk update orders by substatus |

### Courier Assignment & Batching

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/orders/assign-courier` | verifyUser | Assign courier to orders (checks inventory, generates tracking ID, deducts warehouse stock) |
| `GET` | `/orders/couriers` | verifyUser | List available courier partners |
| `GET` | `/orders/batch-ids` | verifyUser | List dispatch batch IDs |
| `POST` | `/orders/courier-assignment/report` | verifyUser | Download courier assignment report |
| `POST` | `/orders/bulk-vendor-courier-upload` | verifyUser | Bulk assign vendor/courier via CSV |
| `POST` | `/orders/clear-courier-assignment` | verifyAgentAdminAndSeller | Clear courier assignment from orders |
| `GET` | `/orders/dispatch-batches` | verifyUser | List dispatch batches |
| `POST` | `/orders/generate-batches` | verifyUser | Generate dispatch batches for orders |
| `POST` | `/orders/generate-tracking-ids` | verifyUser | Generate tracking IDs for a batch |
| `GET` | `/orders/tracking-generation-report` | verifyUser | Report on tracking ID generation |
| `GET` | `/orders/vendors` | verifyUser | List vendors |
| `POST` | `/orders/generate-documents` | verifyUser | Generate AWB/packing list documents |
| `GET` | `/orders/batches/dip` | verifyUser | Get DIP (Dispatching in Process) batches |
| `POST` | `/orders/download-awbs` | verifyUser | Download AWB documents |
| `POST` | `/orders/download-packing-list` | verifyUser | Download packing list |

### Auxiliary

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/orders/check-availability` | verifyUser | Check if order variants are available in warehouse |
| `POST` | `/orders/variants/search` | verifyAgentAdminAndSeller | Search variant by SKU and country |
| `POST` | `/orders/variants/price` | verifyAgentAdminAndSeller | Get variant price by SKU |
| `GET` | `/orders/tags` | verifyUser | List order tags |
| `GET` | `/orders/remarks` | verifyUser | List all remarks |
| `POST` | `/orders/ndr-remarks` | verifyUser | Bulk update NDR remarks |
| `GET` | `/orders/sub-statuses` | — | Get sub-statuses by status name |
| `DELETE` | `/orders/delete/:orderId` | verifySeller | Delete an order |
| `GET` | `/orders/substatus-orders-for-csv` | verifySeller | Export substatus orders to CSV |
| `GET` | `/orders/:orderId/conversation` | verifyAgentAdminAndSeller | WATI WhatsApp conversation for order |
| `GET` | `/orders/:orderId/conversation/media` | verifyAgentAdminAndSeller | WATI conversation media |

---

## Business Logic — Step by Step

### 1. Order Creation via Seller CSV Upload (`POST /orders/uploadOrderCSV`)
1. Validate that `order_reference_id` exists for every row.
2. Group rows by `order_reference_id` (multi-product orders have one row per SKU).
3. Detect duplicate SKUs within an order group → return 400.
4. For each order group:
   - Resolve country → find warehouse for that country (required).
   - Validate all SKUs exist in the database.
   - Validate all SKUs are stocked in the country warehouse (`WarehouseVariant` record exists).
   - If any SKU fails → skip this order with error; continue to next.
   - Create `Customer` record.
   - Create `Order` with status `{ status: "Received", substatus: "Pending Reseller Submission", tag: "Awaiting Push" }`.
   - Log order creation to `OrderLog`.
   - Create `OrderProductVariant` records for each item.
   - Recalculate and update `total_cost`/`total_payable` from variants.
5. Return success/skipped counts.

### 2. Pushing Order from Received → Confirmation Pending (`PUT /orders/:orderId/status`)
This is the "accept order" action triggered by a seller or agency. Logic:
1. Verify order exists and is not archived.
2. Check customer has a `country` field.
3. Call `checkOrderVariantsCountryAvailability` to ensure all variants are offered in customer's country.
4. **Gold subscription gate**: If requester is Seller or Agency, and any variant is a Gold-tier product, verify the seller has an active Gold subscription. If not → 403 with code `GOLD_SUBSCRIPTION_REQUIRED`.
5. Determine initial `tag` based on store settings:
   - **Untrusted store** → tag = `Order on Hold - Contact Support`
   - `confirmation_setting = "Call Only"` → tag = `Calling Required Only`
   - `confirmation_setting = "On"/"Mandatory"` → tag = `Message Sent`
   - `confirmation_setting = "Off"` → tag = `Address Verification`
   - `confirmation_setting = "Default"` → calculate from `StoreCountryRatio.rating` × `VariantCountryRatio.rating`: if both 1 → `Address Verification`; otherwise → `Message Sent`
   - **Prepaid orders** always get `tag = Address Verification` (skip confirmation message).
6. Set `substatus`:
   - `Address Verification` tag → `Address Verification in Process`
   - Anything else → `Confirmation in Process`
7. Update order status in DB; create `OrderLog`.
8. Normalize customer phone via `normalizePhone(phone, country)`.
9. If tag is `Confirmation Required` and phone is valid → send WATI WhatsApp confirmation message to customer.

### 3. Approving / Cancelling an Order (`PUT /orders/:orderId/approve-status`)
- Only accepts `status = "Approved"` or `"Cancelled"`.
- Cannot move DIP → Approved.
- **Approved** → sets `{ status: "Approved", substatus: "Checking Inventory", tag: "Checking Inventory" }`.
- **Cancelled** → sets `{ status: "Cancelled", substatus: "Customer Refused", tag: "Did Not Attend Call" }`.
- Logs to `OrderLog`.

### 4. Courier Assignment (`POST /orders/assign-courier`)
1. Accepts array of `orderIds`; processes them in sorted order.
2. For each order:
   - Skip if already in `Dispatching in Process` status.
   - Skip if already has a `zambeel_tracking_id`.
   - Look up customer country → find warehouse.
   - Check warehouse inventory for every variant — must have sufficient stock.
   - If insufficient → skip order with inventory details.
   - If courier is a Smartlane integrator (`is_integrator = true`): call Smartlane API to create shipment → get back `courier_tracking_id` and `courier_name` → map to internal sub-courier via `CourierSubCourier`.
   - Generate internal Zambeel tracking ID (prefix + 6 random alphanumeric chars).
   - **Transaction**: deduct `WarehouseVariant.quantity` for each variant; update order to `Dispatching in Process` / `Awaiting Courier Pickup` / `Ready to Dispatch`; set `shipment_date` if not set; create `OrderLog`.
   - If transaction fails → rollback, skip order.

### 5. Bulk CSV Status Update (`PUT /orders/bulk-csv-update`)
1. Accepts array of `{ order_id, sub_status, tag?, tracking_id?, courier_id?, vendor_id? }`.
2. Validates each row: order must exist; must not be in `Received` or pre-shipped status; `sub_status` must be in `VALID_SUB_STATUSES`; tag (if provided) must be valid for that sub_status per `SUB_STATUS_TAG_MAP`.
3. Cannot downgrade a shipped order to pre-shipped sub_status.
4. Runs up to 10 concurrent update transactions.
5. Each transaction: locks order row (`LOCK.UPDATE`); updates `status`, `courier_tracking_id`, `fk_courier_id`, `fk_vendor_id`; sets `shipment_date` if transitioning to `Shipped`.
6. Calls `maybeRecordCommissionOnDelivered` (agency commission service) after each status change.
7. Logs all changes to `OrderLog`.

### 6. Reverting Orders from Dispatching in Process (`PUT /orders/revert-dispatching-in-process`)

This is the only supported backward transition out of `Dispatching in Process`. It reverts selected orders to `Confirmation Pending` with a specific tag/substatus chosen by the admin.

**Request body:** `{ orderIds: number[], tagId: number }`
- `tagId` must correspond to an `OrderTag` whose sub-status belongs to the `Confirmation Pending` status — enforced in the controller.

**For each order (per-order transaction; failures are skipped, not aborted globally):**
1. **Cancel courier shipment** (if one was assigned):
   - iMile courier → calls `imileService.cancelOrder(imileOrderNo, waybill)`; fails hard if no waybill found.
   - Smartlane integrator → calls `smartlaneService.cancelConsignment("ZAMPAK-{orderId}")`.
   - Tawseel courier → calls `tawseelService.cancelOrder(awbNumber)`; fails hard if no AWB found.
   - Zajel couriers are **not** auto-cancelled by this flow (no Zajel cancel call here).
2. **Restore warehouse inventory:** for each `OrderProductVariant`, increments `WarehouseVariant.quantity` for the variant in the customer's country warehouse (resolves "UAE" alias → `United Arab Emirates`).
3. **Remove from batch:** if order is in a `BatchOrder`, destroys the `BatchOrder` row.
4. **Reset order fields:**
   - `status → { status: "Confirmation Pending", substatus: tag.subStatus.sub_status, tag: tag.tag }`
   - `fk_courier_id`, `fk_integrator_id`, `fk_vendor_id`, `tracking_number`, `courier_tracking_id`, `awb_file_path`, `zambeel_tracking_id` — all set to `null`.
5. **Creates `OrderLog`** with `action: STATUS_UPDATE`, `field_changed: "status"`, previous and new status recorded.
6. On any error for an order: rolls back the transaction and adds to `skippedOrders` with reason. Continues processing remaining orders.

**Response:** `{ updatedCount, skippedCount, updatedOrders: [{orderId, orderNumber}], skippedOrders: [{orderId, reason}] }`

**When to use:** Admin uses this when orders were incorrectly dispatched, the shipment needs to be recalled, or there's a system error that put orders in DIP before they were ready. It is a destructive action that cancels the courier booking and restores stock.

### 7. Duplicate Detection
Orders are flagged as duplicates if the customer's phone number appears on at least one other non-`Received` order. Uses the `status_value` generated column for efficient filtering.

---

## Interactions with Other Domains

| Domain/Service | How |
|---|---|
| **Inventory (WarehouseVariant)** | Checked before courier assignment; stock deducted atomically during assignment |
| **Courier Services (iMile, Tawseel, Zajel, Smartlane)** | Called during `generateTrackingIds`/`generateBatches` for direct courier integrations |
| **WATI** | WhatsApp confirmation message sent via `sendConfirmationMessageToCustomer` when order pushed from Received |
| **Customer.io** | Order status change events may trigger Customer.io notifications (see services) |
| **Agency Commission** | `maybeRecordCommissionOnDelivered` called on every bulk-CSV status update |
| **Tickets** | Orders are joined with Tickets in order list response (`fk_ticket_id` field) |
| **Stores** | Confirmation flow reads `store.confirmation_setting`, `store.is_trusted`, `store.ndr_treatment` |
| **Country/Warehouse** | Variant availability and courier assignment are country-scoped |
| **Gold Subscription** | Checked before order can be pushed from Received if variants are Gold-tier |
| **BatchOrder / DispatchBatch** | Orders grouped into dispatch batches for bulk document/tracking generation |

---

## Constraints and Rules

1. **Archived orders cannot be updated** — all mutation endpoints check `order.archive === true` and reject with 400.
2. **Status generally moves forward** — DIP → Approved is blocked; shipped → pre-shipped is blocked in bulk CSV update. Exception: `PUT /orders/revert-dispatching-in-process` allows DIP → Confirmation Pending (cancels courier booking and restores inventory).
3. **Variants must exist in country warehouse** — both for seller CSV upload (creation) and for courier assignment.
4. **Duplicate SKUs not allowed** in a single CSV order group.
5. **Payment method = prepaid** bypasses confirmation message and sets tag directly to `Address Verification`.
6. **Untrusted stores** always put orders on hold (`Order on Hold - Contact Support`).
7. **Agency users** must have `proxyContext.merchantUserId` set to upload orders.
8. **Gold products** require active Gold subscription for sellers; OMS admin users bypass this gate.
9. **Phone normalization** runs before sending confirmation messages; normalization failure changes tag to `Send Message` (deferred state).
10. **`platform_order_id`** has a `unique` constraint — prevents duplicate ingestion of the same platform order.

---

## OrderLog

Every mutation that changes an order creates an `OrderLog` record:

| Field | Description |
|---|---|
| `fk_order_id` | Order that changed |
| `fk_user_id` | User who made the change (null for system-generated) |
| `action` | Action constant (e.g. `ORDER_CREATED`, `STATUS_UPDATE`, `VARIANT_UPDATE`, `PRODUCT_ADDED`, `PRODUCT_REMOVED`) |
| `field_changed` | Which field was affected |
| `previous_value` | JSON snapshot of the old value |
| `new_value` | JSON snapshot of the new value |

---

## Dispatch Batches

The `dispatch_batches` and `batch_orders` tables group orders for bulk courier operations:

| Field | Description |
|---|---|
| `batch_id` | String identifier (unique) |
| `fk_vendor_id` / `fk_courier_id` / `fk_country_id` | Batch scope |
| `tracking_status` | `New → Generating → Partial/Generated/Failed` |
| `document_status` | `Not Ready → Preparing → Ready/Invalidated` |
| `document_s3_path` | S3 path to generated AWB/packing list PDF |
| `total_orders` / `failed_orders_count` | Stats |
