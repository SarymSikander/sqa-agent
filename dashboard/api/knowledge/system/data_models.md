# Zambeel Backend — Data Models

## Database

All models use **MySQL** via Sequelize ORM (`mysql2` driver). There is no MongoDB/Mongoose.

Timestamps: Most models use Sequelize `timestamps: true`. Some use custom column names (`createdAt`/`updatedAt` vs `created_at`/`updated_at`).

---

## Core Models

### User (`users` table)

Central identity record for every platform user.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `firebase_uid` | STRING UNIQUE | Firebase Auth identity |
| `username` | STRING | |
| `email` | STRING UNIQUE | |
| `phone_number` | STRING | |
| `country` | STRING | |
| `role` | ENUM | `"Admin"`, `"Agent"`, `"Seller"`, `"Agency"` |
| `archived` | BOOLEAN | Soft delete flag |
| `status` | STRING | Default `"Active"` |
| `provider` | ENUM | `"Email"`, `"Facebook"`, `"Google"`, `"Apple"` |
| `team_id` | INTEGER FK → `teams` | Agent's team assignment |
| `subscription_plan` | ENUM | `"Free"`, `"Gold"` |
| `billing_method` | ENUM | `"PAYTABS"`, `"SHOPIFY"` |
| `email_verified` | BOOLEAN | |
| `promo_code` | STRING | |
| `terms_accepted` | BOOLEAN | |
| `terms_accepted_at` | DATE | |
| `terms_version` | STRING | |

**Associations**: has many `Store`, `Order` (assigned), `Ticket`, `Comment`, `InventoryTransaction`, `DispatchBatch`, `Agency` (1:1), `AgencyMerchantConnection`, `AgencyCommissionRecord`, `AgencyTeamMember`

---

### Store (`stores` table)

Represents a connected seller store. One user can have multiple stores, one per platform connection.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `user_id` | INTEGER FK → `users` | Owning seller |
| `store_id` | STRING | External platform store ID |
| `default_store_name` | STRING | Platform-provided name |
| `store_name` | STRING | Seller-chosen nickname |
| `owner_name` | STRING | |
| `domain` | STRING | e.g., `mystore.myshopify.com` |
| `store_domain` | STRING | |
| `store_url` | STRING | Public store URL |
| `store_email` | STRING | |
| `store_country` | STRING | |
| `store_currency` | STRING | Default `"AED"` |
| `timezone` | STRING | |
| `platform` | STRING | `"shopify"`, `"salla"`, `"lightfunnels"`, `"youcan"`, `"woocommerce"`, `"Manual"` |
| `status` | BOOLEAN | Active flag |
| `phone_number` | STRING | |
| `slug` | STRING | URL slug |
| `access_token` | TEXT | AES-encrypted platform token |
| `refresh_token` | TEXT | AES-encrypted refresh token (Salla, YouCan, LightFunnels) |
| `iv` | STRING(32) | AES IV for token decryption |
| `confirm_orders` | ENUM | `"on"`, `"off"`, `"default"` |
| `auto_process_orders` | BOOLEAN | Default `true` |
| `bifurcation` | ENUM | `"360"`, `"3PL"`, `"Dropshipper"`, `"Partner"` |
| `confirmation_setting` | ENUM | `"On"`, `"Off"`, `"Default"`, `"Mandatory"`, `"Call Only"` |
| `store_protocol` | ENUM | `"Standard"`, `"Important"`, `"VIP"` |
| `ndr_treatment` | ENUM | `"ON"`, `"OFF"` |
| `integrated_at` | DATE | When the store was connected |
| `account_id` | STRING | Platform account ID (LightFunnels) |
| `archived` | BOOLEAN | Soft delete; **default scope filters `archived: false`** |
| `is_trusted` | BOOLEAN | Default `true` |
| `woocommerce_consumer_key` | STRING | WooCommerce REST API key |
| `woocommerce_consumer_secret` | TEXT | WooCommerce REST API secret |
| `woocommerce_user_id` | INTEGER | WooCommerce user ID |
| `woocommerce_webhook_id` | STRING | Registered webhook ID on WooCommerce |

**Associations**: belongs to `User`; has many `Order`, `Ticket`, `Invoice`, `StoreBankAccount`, `StoreCountryRatio`

**Important**: `Store.unscoped()` must be used when querying archived stores (e.g., during reconnection).

---

### Order (`orders` table)

The central business entity. Represents a customer order flowing through the fulfillment pipeline.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `order_number` | STRING | Human-readable order number |
| `fk_customer_id` | INTEGER FK → `customers` | |
| `fk_store_id` | INTEGER FK → `stores` | |
| `platform` | ENUM | `"Shopify"`, `"Easy orders"`, `"Youcan"`, `"Lightfunnels"`, `"Manual"` |
| `total_cost` | DECIMAL(10,2) | |
| `total_payable` | DECIMAL(10,2) | Amount customer pays |
| `total_discount` | DECIMAL(10,2) | |
| `post_dispatch_discount` | DECIMAL(10,2) | Discount applied after dispatch |
| `total_tax` | DECIMAL(10,2) | |
| `shipping_price` | DECIMAL(10,2) | |
| `currency` | STRING | |
| `status` | TEXT (JSON) | Serialized `{status, substatus, tag}` — getter/setter auto-parse |
| `status_value` | STRING(100) | Denormalized status string for quick queries |
| `status_tag` | STRING(100) | Denormalized tag |
| `status_substatus` | STRING(100) | Denormalized substatus |
| `payment_method` | STRING | |
| `order_date` | DATE | |
| `utm_source` | STRING | |
| `utm_campaign` | STRING | |
| `refunded_amount` | FLOAT | |
| `tracking_number` | STRING | |
| `payment_id` | STRING | |
| `admin_graphql_api_id` | STRING | Shopify GraphQL ID |
| `reschedule_date` | DATE | Delivery reschedule |
| `shipment_date` | DATE | |
| `tracking_company` | STRING | |
| `activity_counter` | INTEGER | Count of status changes/activities |
| `bifurcation` | ENUM | `"Partner"`, `"Reseller"`, `"360"`, `"3PL"` |
| `fk_assign_to` | INTEGER FK → `users` | Assigned agent |
| `zambeel_tracking_id` | STRING | Internal tracking ID |
| `courier_tracking_id` | STRING | Courier AWB/tracking number |
| `ndr_meta_data` | JSON | NDR (Non-Delivery Report) metadata |
| `meta` | TEXT (JSON) | Flexible metadata blob — auto-parse getter/setter |
| `archive` | BOOLEAN | Default `false` |
| `platform_order_id` | STRING UNIQUE | External platform order ID (dedup key) |
| `fk_courier_id` | INTEGER FK → `courier_partners` | Primary courier |
| `fk_integrator_id` | INTEGER FK → `courier_partners` | Integrator courier |
| `fk_vendor_id` | INTEGER FK → `vendors` | |
| `awb_file_path` | TEXT | S3 path to AWB PDF |
| `sub_courier_id` | INTEGER FK → `courier_partners` | Sub-courier |

**Associations**: belongs to `Customer`, `User` (assignee), `Store`, `CourierPartner` (×3 roles), `Vendor`; has many `OrderLog`, `Ticket`, `OrderBatchAuditLog`, `BatchOrder` (1:1); many-to-many with `Variant` (through `order_product_variants`) and `Remark` (through `order_remarks`)

---

### Customer (`customers` table)

End-consumer data (the person who placed the order on the seller's store).

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `full_name` | STRING | |
| `phone` | STRING | Used for WATI WhatsApp messages |
| `email` | STRING | |
| `country` | STRING | Used to route WATI account |
| `city` | STRING | |
| `notes` | TEXT | |
| `account_id` | STRING | Platform customer ID |
| `shipping` | STRING | Shipping address (serialized) |
| `billing` | STRING | Billing address |
| `area_name` | STRING | |
| `building_society` | STRING | |
| `national_address_short_code` | STRING | Saudi national address |

**Associations**: has many `Order`

---

### Product (`products` table)

Platform product catalog entry.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `product_id` | STRING | External platform product ID |
| `store_id` | INTEGER | FK → `stores` |
| `title` | STRING | |
| `body_html` | TEXT | |
| `vendor` | STRING | |
| `product_type` | STRING | |
| `handle` | STRING | URL slug |
| `status` | STRING | |
| `tags` | TEXT | |
| `admin_graphql_api_id` | STRING | Shopify GraphQL ID |
| `published_at` | DATE | |
| `visibility` | BOOLEAN | Default `true` |
| `has_variants` | BOOLEAN | Default `false` |

**Associations**: has many `Variant`, `Image`

---

### Variant (`variants` table)

SKU-level product item. The unit that gets ordered, inventoried, and shipped.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `product_id` | INTEGER FK → `products` | |
| `fk_owned_by` | INTEGER FK → `users` | Reseller owner |
| `owner` | ENUM | `"Zambeel"`, `"Reseller-3PL"`, `"Reseller-360"`, `"Zambeel-Exclusive Product"`, `"Zambeel Financing"` |
| `product_tier` | STRING | |
| `dispatching_time` | STRING | |
| `expected_delivery_ratio` | STRING | |
| `market_saturation` | STRING | |
| `expected_roas` | STRING | |
| `ships_from` | STRING | |
| `gold_product_status` | STRING | Status in Gold subscription catalog |
| `inventory_location` | STRING | |
| `title` | STRING | |
| `option1_name` / `option1_value` | STRING | e.g., Color / Red |
| `option2_name` / `option2_value` | STRING | e.g., Size / XL |
| `option3_name` / `option3_value` | STRING | |
| `variant_id` | STRING | External platform variant ID |
| `price` | DECIMAL(10,2) | |
| `sale_price` | DECIMAL(10,2) | |
| `pixel_price` | DECIMAL(10,2) | Price shown in ad pixels |
| `in_cart` | BOOLEAN | |
| `position` | INTEGER | Sort position |
| `inventory_policy` | STRING | |
| `track_inventory` | BOOLEAN | Default `true` |
| `sku` | STRING | SKU code |
| `weight` | DECIMAL(10,2) | |
| `weight_unit` | STRING | |
| `inventory_quantity` | INTEGER | |

**Associations**: belongs to `Product`, `User`; many-to-many with `Order` (through `OrderProductVariant`), `PurchaseOrder` (through `POVariant`), `Warehouse` (through `WarehouseVariant`), `ReturnOrder` (through `ReturnOrdersVariant`); has many `VariantCountryRatio`, `InventoryTransaction` (×2 — source and destination), `DamagedBinMovement`

---

### Ticket (`tickets` table)

Support ticket raised by seller or initiated by Zambeel ops.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `fk_store_id` | INTEGER FK → `stores` | |
| `fk_order_id` | INTEGER FK → `orders` | Optional — ticket may relate to a specific order |
| `fk_team_id` | INTEGER FK → `teams` | Assigned ops team |
| `category` | ENUM | `"Order Processing"`, `"Delivery Complaint"`, `"Payments & Invoices"`, `"Onboarding & Integration"`, etc. (see full enum in model) |
| `sub_category` | ENUM | Detailed subcategory (25+ values) |
| `status` | ENUM | `"Pending"`, `"In Progress"`, `"Awaiting Seller Action"`, `"Resolved"` |
| `description` | TEXT | |
| `fk_created_by` | INTEGER FK → `users` | Who created the ticket |
| `assigned_to` | ENUM | `"Zambeel"` or `"Seller"` — whose court the ticket is in |
| `fk_seller_id` | INTEGER FK → `users` | The seller the ticket belongs to |

**Associations**: belongs to `Store`, `Order`, `Team`, `User` (creator), `User` (seller); has many `TicketLog`, `Comment`, `TicketImage`

---

### Invoice (`invoices` table)

Payout invoices generated by Zambeel and sent to sellers.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `s3_file_url` | STRING | Full URL to the PDF on S3 |
| `store_id` | INTEGER FK → `stores` | |
| `filename` | STRING | |
| `payment_status` | ENUM | `"Paid"`, `"Not Paid Yet"`, `"Failed Transaction"`, `"Missing Banking Details"`, `"Ineligible for Payment"` |
| `reason` | STRING | Reason for non-payment status |

**Associations**: belongs to `Store`

---

### OrderLog (`order_logs` table)

Audit trail of every status change and action on an order.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `fk_order_id` | INTEGER FK → `orders` | |
| `fk_user_id` | INTEGER FK → `users` | Who performed the action |
| *(additional fields in model)* | | Action type, old/new status, timestamp |

**Associations**: belongs to `Order`, `User`

---

### PurchaseOrder (`purchase_order` table)

Inbound stock purchase orders (inventory arriving at warehouse from supplier).

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `PO_ID` | STRING UNIQUE | Human-readable PO number |
| `fk_country_id` | INTEGER FK → `countries` | |
| `fk_created_by` | INTEGER FK → `users` | |
| `fk_warehouse_id` | INTEGER FK → `warehouse` | Destination warehouse |
| `status` | ENUM | `"Draft"`, `"Received"`, `"Partially Received"`, `"Cancelled"`, `"Submitted"` |

**Associations**: belongs to `User`, `Country`, `Warehouse`; many-to-many with `Variant` (through `POVariant`)

---

### DispatchBatch (`dispatch_batches` table)

Groups multiple orders for bulk courier dispatch (AWB generation).

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `batch_id` | STRING UNIQUE | Human-readable batch ID |
| `fk_vendor_id` | INTEGER FK → `vendors` | |
| `fk_courier_id` | INTEGER FK → `courier_partners` | |
| `fk_country_id` | INTEGER FK → `countries` | |
| `created_by_user_id` | INTEGER FK → `users` | |
| `tracking_status` | ENUM | `"New"`, `"Generating"`, `"Partial"`, `"Generated"`, `"Failed"` |
| `document_status` | ENUM | `"Not Ready"`, `"Preparing"`, `"Ready"`, `"Invalidated"` |
| `has_removed_orders` | BOOLEAN | Flag if orders were removed from batch |
| `total_orders` | INTEGER | |
| `failed_orders_count` | INTEGER | |
| `document_s3_path` | TEXT | S3 path to generated dispatch manifest |
| `courier_request_id` | STRING | Courier-side request/batch ID |
| `last_tracking_generation_attempt_at` | DATE | |
| `last_document_generation_attempt_at` | DATE | |

**Associations**: belongs to `Vendor`, `CourierPartner`, `Country`, `User`; has many `BatchOrder`

---

### InventoryTransaction (`inventory_transactions` table)

Records physical inventory movements between warehouses or SKU-to-SKU remappings.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `movement_type` | ENUM | `"SKU_TO_SKU"` (remap SKU), `"WAREHOUSE_TRANSFER"` (move between locations) |
| `status` | ENUM | `"In Transit"`, `"Received"` |
| `reason` | ENUM | `"SKU Merge"`, `"Wrong SKU Mapping"`, `"Repackaging"`, `"Services Deal"`, `"Variant Consolidation"`, `"Internal Adjustment"`, `"Demand Fulfillment"`, `"Purchase Transfer"` |
| `fk_moved_by` | INTEGER FK → `users` | |
| `fk_source_warehouse_id` | INTEGER FK → `warehouse` | |
| `fk_destination_warehouse_id` | INTEGER FK → `warehouse` | |
| `fk_from_variant_id` | INTEGER FK → `variants` | Source SKU |
| `fk_to_variant_id` | INTEGER FK → `variants` | Destination SKU (same for warehouse transfers) |
| `movement_number` | STRING | Human-readable movement ID |
| `quantity` | INTEGER (min 1) | Units being moved |
| `received_quantity` | INTEGER | Units confirmed received at destination |

**Associations**: belongs to `User`, `Warehouse` (×2), `Variant` (×2); has many `InventoryTransactionLog`

---

### Agency (`agencies` table)

Agency portal entity. An Agency is a user with role `"Agency"` who manages multiple merchants.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `fk_user_id` | INTEGER FK → `users` UNIQUE | 1:1 with User |
| `agency_unique_id` | STRING(20) UNIQUE | Auto-generated identifier |
| `name` | STRING | Agency display name |
| `country` | STRING | |
| `city` | STRING | |
| `phone` | STRING | |
| `poc_name` | STRING | Point-of-contact name |
| `poc_photo_url` | STRING | S3 URL to POC photo |
| `identity_proof_url` | STRING | S3 URL to ID document |
| `registration_status` | ENUM | `"Pending"`, `"Approved"`, `"OnHold"`, `"Rejected"` |
| `license_status` | ENUM | `"Inactive"`, `"Active"`, `"Revoked"` |
| `hold_reason` | TEXT | |
| `reject_reason` | TEXT | |
| `rejected_at` | DATE | |
| `cooldown_until` | DATE | Cooldown period after rejection |
| `allow_resubmit` | BOOLEAN | |
| `terms_accepted_at` | DATE | |
| `fk_commission_model_id` | INTEGER FK → `agency_commission_models` | |

**Associations**: belongs to `User`, `AgencyCommissionModel`; has many `AgencyMerchantConnection`, `AgencyCommissionRecord`, `AgencyInvoice`, `AgencyTeamMember`

---

### AgencyCommissionModel (`agency_commission_models` table)

Named commission model (e.g., "Standard 5%"). Has multiple rules.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `name` | STRING | |
| `archived` | BOOLEAN | |

**Associations**: has many `Agency`, `AgencyCommissionModelRule`

---

### Team (`teams` table)

Internal ops teams (used for ticket assignment and agent grouping).

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `name` | STRING | |

**Associations**: has one `User` (team leader or representative); has many `Ticket`, `Comment`

---

### OrderStatus (`order_statuses` table)

Reference table for valid order status values.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AI | |
| `status` | STRING | Status name |
| `archived` | BOOLEAN | |

**Associations**: has many `OrderSubStatus`, `Remark`

---

## Junction / Supporting Models

| Model | Table | Links | Purpose |
|---|---|---|---|
| `OrderProductVariant` | `order_product_variants` | `orders` ↔ `variants` | Line items — each order-variant pair with quantity |
| `POVariant` | (po_variants) | `purchase_order` ↔ `variants` | PO line items |
| `BatchOrder` | (batch_orders) | `dispatch_batches` ↔ `orders` | Which orders are in a dispatch batch |
| `ReturnOrdersVariant` | — | `return_orders` ↔ `variants` | Return order line items |
| `WarehouseVariant` | (warehouse_variants) | `warehouse` ↔ `variants` | Stock levels per warehouse per SKU |
| `StoreCountryRatio` | — | `stores` ↔ `countries` | Delivery ratio config per store per country |
| `VariantCountryRatio` | — | `variants` ↔ `countries` | Delivery ratio config per variant per country |
| `StoreBankAccount` | — | `stores` ↔ bank accounts | Links a store to its payout bank |
| `AgencyMerchantConnection` | — | `agencies` ↔ `users` (merchants) | Agency-managed merchant relationships |
| `AgencyTeamMember` | — | `agencies` ↔ `users` | Agency staff members |
| `AgencyCommissionRecord` | — | tracks commission earned | |
| `OrderBatchAuditLog` | — | `orders`, `users`, `dispatch_batches` | Who added/removed an order from a batch |
| `InventoryTransactionLog` | — | `inventory_transactions` | Step-by-step audit of a movement |
| `DamagedBinMovement` | — | `variants`, `users` | Damaged stock tracking |
| `TicketLog` | — | `tickets`, `users` | Ticket status change history |
| `TicketImage` | — | `tickets` | Attached images on tickets |
| `Comment` | — | `tickets`, `users`, `teams` | Ticket thread comments |
| `OrderLog` | `order_logs` | `orders`, `users` | Order activity timeline |
| `OrderRemark` / `Remark` | `order_remarks` / `remarks` | `orders` ↔ `order_statuses` | Preset remarks assigned to orders |
| `UnprocessedOrder` | `unprocessed_orders` | — | Staging table for SQS-received raw orders before processing |
| `BroadcastNotification` | — | — | Admin-sent push notifications to sellers |
| `BroadcastNotificationRecipient` | — | — | Per-seller delivery tracking |
| `Contract` / `ContractTemplate` | — | — | Seller contract management |

---

## Key Relationships Diagram (Text)

```
User (Seller)
  ├─── Store (1:many)
  │      ├─── Order (1:many)
  │      │      ├─── Customer (many:1)
  │      │      ├─── OrderProductVariant → Variant
  │      │      ├─── OrderLog (audit trail)
  │      │      ├─── Ticket (1:many)
  │      │      └─── BatchOrder → DispatchBatch
  │      └─── Invoice (1:many)
  ├─── Ticket (as creator/seller)
  └─── Agency (1:1) → AgencyMerchantConnection → User (merchants)

Variant
  ├─── Product (many:1)
  ├─── WarehouseVariant → Warehouse
  ├─── InventoryTransaction (source/destination)
  └─── POVariant → PurchaseOrder

DispatchBatch
  ├─── CourierPartner
  ├─── Vendor
  ├─── Country
  └─── BatchOrder → Order

Ticket
  ├─── Store
  ├─── Order (optional)
  ├─── Team
  ├─── TicketLog
  ├─── Comment
  └─── TicketImage
```

---

## Important Sequelize Notes

- `Store` has a **default scope** of `{ where: { archived: false } }`. Always use `Store.unscoped()` when you need to find archived stores (e.g., reconnection flows).
- `Order.status` is a **JSON column** stored as TEXT — it's a serialized `{status, substatus, tag}` object. The denormalized `status_value`, `status_tag`, `status_substatus` fields exist for indexed queries.
- `Order.meta` is a LONGTEXT JSON blob for flexible platform-specific metadata.
- `User.role` determines which portal a user can access: `"Seller"` → seller portal, `"Admin"` / `"Agent"` → OMS admin portal, `"Agency"` → agency portal.
