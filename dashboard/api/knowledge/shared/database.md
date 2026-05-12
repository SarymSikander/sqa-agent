# Zambeel Staging Database — Complete Reference

**Database:** `zambeel_staging`  
**Host:** `zambeel-staging.c2knh0obsufa.eu-west-3.rds.amazonaws.com`  
**Engine:** MySQL (InnoDB)  
**Total tables:** 59  
**Last analysed:** 2026-05-07  

---

## Table of Contents

1. [Table Inventory](#1-table-inventory)
2. [Relationship Map (ERD)](#2-relationship-map-erd)
3. [Core Domain: Orders](#3-core-domain-orders)
4. [Core Domain: Users, Stores & Products](#4-core-domain-users-stores--products)
5. [Core Domain: Inventory & Warehouses](#5-core-domain-inventory--warehouses)
6. [Core Domain: Dispatch & Couriers](#6-core-domain-dispatch--couriers)
7. [Core Domain: Agencies & Commissions](#7-core-domain-agencies--commissions)
8. [Core Domain: Tickets & Support](#8-core-domain-tickets--support)
9. [Core Domain: Invoices & Payments](#9-core-domain-invoices--payments)
10. [Core Domain: Purchase Orders & Returns](#10-core-domain-purchase-orders--returns)
11. [Reference & Config Tables](#11-reference--config-tables)
12. [Audit & Log Tables](#12-audit--log-tables)
13. [Key Business Logic](#13-key-business-logic)
14. [Sample Data Patterns](#14-sample-data-patterns)

---

## 1. Table Inventory

| Table | Row Count | Purpose |
|---|---|---|
| `orders` | 7,975 | Core order records from all platforms |
| `customers` | 18,670 | End-customer contact and address data |
| `order_product_variant` | 7,989 | Line items: which variants are in each order |
| `order_logs` | 16,322 | Full audit trail of every change to an order |
| `order_statuses` | 10 | Reference: top-level status labels |
| `order_sub_statuses` | 21 | Reference: sub-status labels per status |
| `order_tags` | 35 | Reference: tag labels per sub-status |
| `order_remarks` | 26 | Order-level remark associations |
| `remarks` | — | Remark definitions (text pool) |
| `unprocessed_orders` | 156 | Shopify webhook payloads awaiting ingestion |
| `mock_order_logs` | — | Same schema as order_logs, for test/demo orders |
| `order_batch_audit_logs` | — | Audit log for batch/AWB actions |
| `users` | 95 | Platform users: Seller, Admin, Agent, Agency |
| `stores` | 77 | Shopify/other-platform store integrations |
| `store_bank_accounts` | 74 | Payout bank accounts linked to stores |
| `users_bank_accounts` | 190 | Bank/wallet accounts per user |
| `teams` | 9 | Internal CS/ops teams |
| `Sessions` | — | Express session store |
| `products` | 533 | Product catalogue (synced from Shopify) |
| `variants` | 777 | Product variants with SKU, pricing, inventory info |
| `images` | — | Product images |
| `featured_products` | — | Admin-curated featured product list |
| `warehouse` | 8 | Zambeel fulfilment warehouses by country |
| `warehouse_variants` | 62 | Stock quantity per variant per warehouse |
| `vendors` | 10 | Warehouse vendor records (Zambeel-owned per country) |
| `inventory_transactions` | 23 | SKU-to-SKU or warehouse transfer movements |
| `inventory_transaction_logs` | 57 | Audit log for inventory movements |
| `damaged_bin_movement` | 20 | Damaged/unsellable stock write-off records |
| `dispatch_batches` | 49 | Shipment batches grouped for courier handoff |
| `batch_orders` | 88 | Junction: orders inside a dispatch batch |
| `courier_partners` | 20 | Courier companies with tracking URL templates |
| `courier_sub_couriers` | 13 | Sub-couriers under integrator couriers (e.g. Smartlane) |
| `agencies` | 9 | Agency accounts (reseller partners) |
| `agency_commission_models` | 37 | Named commission plan templates |
| `agency_commission_model_rules` | 43 | Per-country rate rules within a commission model |
| `agency_commission_records` | 42 | Per-order commission earned by an agency |
| `agency_invoices` | 0 | Agency payout invoices (not yet used in staging) |
| `agency_merchant_connections` | 7 | Agency–Seller connection requests/status |
| `agency_team_members` | 10 | Users (Owner/Member) within an agency |
| `tickets` | 113 | Customer-support tickets |
| `ticket_logs` | 239 | Audit log for ticket field changes |
| `ticket_images` | 30 | Attachments on tickets |
| `comments` | — | Thread comments on tickets (internal + seller-visible) |
| `invoices` | 105 | Seller payout invoices (PDF on S3) |
| `purchase_order` | 32 | Inventory purchase orders (POs) |
| `po_variants` | 97 | Line items inside a PO |
| `return_order` | 14 | Return inbound shipment headers |
| `return_orders_variants` | 23 | Variant quantities in a return shipment |
| `countries` | — | Country reference (id 9=UAE, 10=Qatar, 11=Kuwait, 12=KSA, 13=Pakistan, 14=Oman, 15=Bahrain, 16=Iraq) |
| `cities` | — | Cities per country |
| `country_threshold` | — | Delivery-ratio thresholds per country |
| `stores_country_ratio` | — | Per-store delivery ratio & rating per country |
| `variants_country_ratio` | — | Per-variant delivery ratio & rating per country |
| `notifications` | 0 | In-app push notifications per user |
| `creative_analytics` | — | Ad creative analytics upload jobs |
| `event_dedupe` | — | Idempotency store for webhook events |
| `ticker_config` | — | Configurable announcement ticker for the portal |
| `user_subscription_transactions` | — | PayTabs/Shopify billing transactions for Gold plan |
| `SequelizeMeta` | — | Sequelize migration tracking |

---

## 2. Relationship Map (ERD)

```
countries (reference)
  ├── cities.fk_country_id
  ├── warehouse.fk_country_id
  ├── vendors.fk_country_id
  ├── agency_commission_model_rules.fk_country_id
  ├── purchase_order.fk_country_id
  └── return_order.fk_country_id

users
  ├── stores.user_id ──────────────────────────────────────────┐
  ├── agencies.fk_user_id                                      │
  ├── agency_team_members.fk_user_id                           │
  ├── agency_merchant_connections.fk_user_id                   │
  ├── users_bank_accounts.fk_user_id                           │
  ├── teams.id (users.team_id → teams.id)                      │
  ├── notifications.fk_user_id                                 │
  ├── creative_analytics.fk_user_id                            │
  ├── order_logs.fk_user_id                                    │
  └── ticker_config.updated_by                                 │
                                                               │
stores ←───────────────────────────────────────────────────────┘
  ├── orders.fk_store_id
  ├── tickets.fk_store_id
  ├── invoices.store_id
  ├── store_bank_accounts.store_id
  └── stores_country_ratio.fk_store_id

customers
  └── orders.fk_customer_id

orders
  ├── order_product_variant.order_id
  ├── order_logs.fk_order_id
  ├── order_remarks.order_id
  ├── batch_orders.order_id
  ├── tickets.fk_order_id
  ├── agency_commission_records.fk_order_id (UNIQUE — 1 record per delivered order)
  ├── orders.fk_courier_id → courier_partners.id
  ├── orders.fk_vendor_id → vendors.id
  ├── orders.fk_assign_to → users.id
  ├── orders.sub_courier_id → courier_sub_couriers.id
  └── orders.fk_integrator_id → courier_partners.id

order_product_variant
  ├── order_product_variant.order_id → orders.id
  └── order_product_variant.variant_id → variants.id

variants
  ├── order_product_variant.variant_id
  ├── warehouse_variants.variant_fk_id
  ├── po_variants.variant_fk_id
  ├── return_orders_variants.fk_variant_id
  ├── inventory_transactions.fk_from_variant_id / fk_to_variant_id
  ├── damaged_bin_movement.fk_variant_id
  └── variants_country_ratio.fk_variant_id
  └── variants.product_id → products.id

products
  ├── variants.product_id
  ├── images.product_id
  └── featured_products.product_id

agencies
  ├── agencies.fk_user_id → users.id
  ├── agencies.fk_commission_model_id → agency_commission_models.id
  ├── agency_team_members.fk_agency_id
  ├── agency_merchant_connections.fk_agency_id
  └── agency_commission_records.fk_agency_id

agency_commission_models
  ├── agency_commission_model_rules.fk_commission_model_id
  └── agencies.fk_commission_model_id

dispatch_batches
  ├── dispatch_batches.fk_vendor_id → vendors.id
  ├── dispatch_batches.fk_courier_id → courier_partners.id
  ├── dispatch_batches.fk_country_id → countries.id
  ├── dispatch_batches.created_by_user_id → users.id
  └── batch_orders.batch_id → dispatch_batches.batch_id

courier_partners
  ├── orders.fk_courier_id
  ├── dispatch_batches.fk_courier_id
  └── courier_sub_couriers.fk_integrator_id (integrator courier → sub-couriers)

courier_sub_couriers
  ├── fk_integrator_id → courier_partners.id
  └── fk_sub_courier_id → courier_partners.id

warehouse
  ├── warehouse_variants.warehouse_id
  ├── inventory_transactions.fk_source_warehouse_id / fk_destination_warehouse_id
  ├── damaged_bin_movement.fk_warehouse_id
  ├── purchase_order.fk_warehouse_id
  └── return_order.fk_warehouse_id

purchase_order
  └── po_variants.po_fk_id

return_order
  └── return_orders_variants.fk_return_id

tickets
  ├── ticket_logs.ticket_id
  ├── ticket_images.fk_ticket_id (implied)
  ├── comments.fk_ticket_id
  └── tickets.fk_team_id → teams.id

order_statuses
  └── order_sub_statuses.fk_status_id

order_sub_statuses
  └── order_tags.fk_sub_status_id
```

---

## 3. Core Domain: Orders

### `orders` (7,975 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | Internal order ID |
| `order_number` | varchar(255) NOT NULL | Human-readable: `ORD-1473` |
| `fk_customer_id` | int FK→customers | End customer |
| `platform` | enum | `Shopify`, `Easy orders`, `Youcan`, `Lightfunnels`, `Manual` |
| `total_cost` | decimal(10,2) | Gross item total |
| `total_discount` | decimal(10,2) | Discount applied |
| `post_dispatch_discount` | decimal(10,2) | Discount applied after dispatch |
| `total_tax` | decimal(10,2) | Tax (nullable) |
| `shipping_price` | decimal(10,2) | Shipping charge |
| `total_payable` | decimal(10,2) DEFAULT 0 | Final amount due |
| `currency` | varchar(255) NOT NULL | e.g. `USD`, `AED`, `PKR` |
| `payment_method` | varchar(255) | `COD` (93%), `paid` (7%) |
| `bifurcation` | enum | `Partner`, `Reseller`, `360`, `3PL` |
| `status` | text NOT NULL | **JSON blob**: `{"status":"…","substatus":"…","tag":"…"}` |
| `status_value` | varchar(100) GENERATED | Extracted from JSON — indexed, queryable |
| `status_substatus` | varchar(100) GENERATED | Extracted from JSON — indexed |
| `status_tag` | varchar(100) GENERATED | Extracted from JSON — indexed |
| `fk_store_id` | int FK→stores DEFAULT 1 | Owning store |
| `fk_assign_to` | int FK→users NULL | CS agent assigned |
| `fk_courier_id` | int FK→courier_partners NULL | Selected courier |
| `fk_vendor_id` | int FK→vendors NULL | Fulfilment vendor/warehouse |
| `sub_courier_id` | int FK→courier_sub_couriers NULL | Sub-courier when integrator used |
| `fk_integrator_id` | int FK→courier_partners NULL | Integrator courier (e.g. Smartlane) |
| `batch_id` | varchar(255) NULL | Dispatch batch reference |
| `zambeel_tracking_id` | varchar(255) NULL | Internal tracking ID |
| `courier_tracking_id` | varchar(255) NULL | External courier AWB |
| `platform_order_id` | varchar(255) UNIQUE NULL | Shopify order ID |
| `admin_graphql_api_id` | varchar(255) NULL | Shopify Admin API GID |
| `tracking_number` | varchar(255) NULL | Legacy tracking field |
| `tracking_company` | varchar(255) NULL | Legacy courier name |
| `awb_file_path` | text NULL | S3 path to AWB PDF |
| `ndr_meta_data` | json NULL | NDR (Non-Delivery Report) metadata |
| `meta` | longtext NULL | Arbitrary metadata blob |
| `utm_source` | varchar(255) NULL | Marketing attribution |
| `utm_campaign` | varchar(255) NULL | Campaign attribution |
| `payment_id` | varchar(255) NULL | Payment gateway reference |
| `refunded_amount` | float NULL | Amount refunded |
| `reschedule_date` | datetime NULL | Requested reschedule date |
| `shipment_date` | datetime NULL | Actual shipment date |
| `order_date` | datetime NOT NULL | Date order was placed |
| `activity_counter` | int DEFAULT 0 | Count of actions on order |
| `archive` | tinyint(1) DEFAULT 0 | Soft delete flag |
| `tags` | varchar(255) NULL | Shopify tags string |
| `createdAt` / `updatedAt` | datetime | Timestamps |

**CRITICAL:** `status` is a raw JSON text column. The system uses three **generated stored columns** for filtering:
- `status_value` → top-level status name
- `status_substatus` → substatus name
- `status_tag` → tag name
Always query via `status_value`, `status_substatus`, `status_tag` — NOT the `status` JSON directly.

### `order_statuses` — Complete Status List (10)

| ID | Status |
|---|---|
| 611 | Received |
| 612 | Confirmation Pending |
| 613 | Cancelled |
| 614 | Approved |
| 615 | Dispatching in Process |
| 616 | Shipped |
| 617 | Delivered |
| 618 | Undelivered |
| 619 | Return in Transit |
| 620 | Return |

### `order_sub_statuses` — Complete Sub-Status List (21)

| ID | Parent Status | Sub-Status |
|---|---|---|
| 24 | Received | Pending Reseller Submission |
| 25 | Confirmation Pending | Confirmation in Process |
| 26 | Confirmation Pending | On Hold by Customer |
| 27 | Confirmation Pending | Address Verification in Process |
| 28 | Confirmation Pending | Scheduled Before Delivery |
| 29 | Cancelled | Invalid Order |
| 30 | Cancelled | Customer Refused |
| 31 | Approved | Checking Inventory For Dispatching |
| 32 | Approved | Inventory In Transit |
| 33 | Dispatching in Process | Awaiting Courier Pickup |
| 34 | Shipped | In Transit |
| 37 | Shipped | In Delivery |
| 38 | Shipped | Scheduled by Customer |
| 39 | Delivered | Delivered |
| 40 | Undelivered | Customer Refused - Assigned to CS Team |
| 41 | Undelivered | Customer Uncontactable - Assigned to CS Team |
| 42 | Undelivered | Request to Return |
| 43 | Undelivered | Request to Re-Scheduled |
| 44 | Return in Transit | Returning |
| 45 | Return | Returned |
| 46 | Cancelled | Product Not Available *(added 2026-03-12)* |

### Order Status Distribution (live data)

| Status | Count | % |
|---|---|---|
| Received | 3,750 | 47% |
| Confirmation Pending | 1,879 | 24% |
| Delivered | 1,365 | 17% |
| Dispatching in Process | 340 | 4% |
| Return | 217 | 3% |
| Cancelled | 157 | 2% |
| Shipped | 89 | 1% |
| Undelivered | 65 | <1% |
| Approved | 61 | <1% |
| Return in Transit | 52 | <1% |

### Order Order Tags (35 total — select key tags)

Tags are attached to sub-statuses and give operational granularity:
- `Message Sent` / `Customer Replied` (Confirmation in Process)
- `Address Details Pending From Customer` / `Address Verification in Process`
- `Scheduled` / `Customer Requested Future Delivery`
- `Checking Inventory` / `Calculating Dispatching Time`
- `Ready to Dispatch` / `Awaiting Courier Pickup`
- `Rider on the Way` / `In Delivery`
- `Delivery Attempt in 1-2 Days` / `2-3 Days` / `3-5 Days`
- `Delivered`
- `Cancelled by Customer` / `Did not order` / `No Cash`
- `Uncontactable (No Response)` / `Uncontactable and Unreachable`
- `Did not attend call` / `Long Reschedule`
- `Uncontactable (No Response)` (returning)
- `Product Not Available`

### `customers` (18,670 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `full_name` | varchar(255) NOT NULL | Indexed |
| `phone` | varchar(255) | Indexed |
| `email` | varchar(255) NULL | |
| `country` | varchar(255) | Indexed |
| `city` | varchar(255) NULL | |
| `area_name` | varchar(255) NULL | |
| `building_society` | varchar(255) NULL | |
| `national_address_short_code` | varchar(255) NULL | KSA national address code |
| `notes` | text NULL | |
| `account_id` | varchar(255) NULL | External account ref |
| `shipping` | varchar(255) NULL | Shipping address JSON |
| `billing` | varchar(255) NULL | Billing address JSON |
| `created_at` / `updated_at` | datetime | |

### `order_product_variant` (7,989 rows)

Junction table — one row per line item in an order.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `order_id` | int FK→orders | |
| `variant_id` | int FK→variants NULL | NULL if variant deleted/unmapped |
| `quantity` | int NOT NULL | |
| `price` | decimal(10,2) NOT NULL | Unit price at time of order |
| `discount` | decimal(10,2) NULL | Line-item discount |
| `title` | varchar(255) NULL | Variant title snapshot |
| `created_at` / `updated_at` | datetime | |

### `unprocessed_orders` (156 rows)

Shopify webhook payloads queued for processing.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `payload` | longtext NOT NULL | Raw Shopify webhook JSON |
| `shopify_order_id` | bigint NULL | Indexed |
| `processing_status` | enum | `pending`, `processing`, `processed`, `failed`, `duplicate`, `store_not_found` |
| `error_message` | text NULL | Failure reason |
| `processed_at` | datetime NULL | |
| `started_processing_at` | datetime NULL | |
| `created_at` / `updated_at` | datetime | |

---

## 4. Core Domain: Users, Stores & Products

### `users` (95 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `firebase_uid` | varchar(255) UNIQUE NOT NULL | Firebase auth UID |
| `username` | varchar(255) NULL | Indexed |
| `email` | varchar(255) NULL | |
| `phone_number` | varchar(255) NULL | |
| `country` | varchar(255) NULL | |
| `role` | enum | `Admin` (22), `Agent` (8), `Seller` (60), `Agency` (5) |
| `archived` | tinyint(1) DEFAULT 0 | Soft delete |
| `status` | varchar(255) DEFAULT 'Active' | |
| `provider` | enum | `Email`, `Facebook`, `Google`, `Apple` |
| `team_id` | int FK→teams NULL | Assigned CS team (agents) |
| `subscription_plan` | enum | `Free`, `Gold` |
| `email_verified` | tinyint(1) DEFAULT 0 | |
| `promo_code` | varchar(255) NULL | |
| `total_orders` | int unsigned DEFAULT 0 | Cached total order count |
| `billing_method` | enum NULL | `PAYTABS`, `SHOPIFY` |
| `first_order_date` | datetime NULL | |
| `last_order_date` | datetime NULL | |
| `received_orders_count` | int DEFAULT 0 | Cached received count |
| `non_received_orders_count` | int DEFAULT 0 | Cached non-received count |
| `terms_accepted` | tinyint(1) DEFAULT 0 | T&C acceptance flag |
| `terms_accepted_at` | datetime NULL | |
| `terms_version` | varchar(255) NULL | |
| `createdAt` / `updatedAt` | datetime | |

**User role breakdown:** Seller=60, Admin=22, Agent=8, Agency=5.

### `stores` (77 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `store_id` | varchar(255) NOT NULL | External platform store ID |
| `store_name` | varchar(255) NOT NULL | Indexed |
| `default_store_name` | varchar(255) NOT NULL | |
| `owner_name` | varchar(255) NULL | |
| `domain` | varchar(255) NULL | |
| `store_url` | varchar(255) NOT NULL | Indexed |
| `store_domain` | varchar(255) NULL | |
| `store_email` | varchar(255) NULL | |
| `store_country` | varchar(255) NULL | |
| `store_currency` | varchar(255) NULL | |
| `timezone` | varchar(255) NULL | |
| `platform` | varchar(255) NULL | `Shopify`, `Easy orders`, etc. |
| `status` | tinyint(1) DEFAULT 1 | 1=active, 0=inactive |
| `phone_number` | varchar(255) NULL | |
| `slug` | varchar(255) NULL | |
| `access_token` | text NULL | Encrypted OAuth token |
| `refresh_token` | text NULL | |
| `iv` | varchar(32) NULL | AES IV for token encryption |
| `account_id` | varchar(255) NULL | Platform account ID |
| `integrated_at` | datetime NOT NULL | Integration date |
| `user_id` | int FK→users NULL | Owning seller |
| `confirm_orders` | enum | `on`, `off`, `default` |
| `auto_process_orders` | tinyint(1) DEFAULT 0 | |
| `confirmation_setting` | enum | `On`, `Off`, `Default` |
| `bifurcation` | enum | `360`, `3PL`, `Dropshipper`, `Partner` |
| `archived` | tinyint(1) DEFAULT 0 | |
| `is_trusted` | tinyint(1) DEFAULT 1 | Trusted seller flag |
| `createdAt` | timestamp DEFAULT CURRENT_TIMESTAMP | |
| `updatedAt` | datetime NOT NULL | |

### `products` (533 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `product_id` | varchar(255) NOT NULL | External (Shopify) product ID |
| `store_id` | int NULL | Owning store (non-FK, no constraint) |
| `title` | varchar(255) NOT NULL | |
| `body_html` | text NULL | Description HTML |
| `vendor` | varchar(255) NULL | |
| `product_type` | varchar(255) NULL | |
| `handle` | varchar(255) NULL | Shopify handle/slug |
| `status` | varchar(255) NULL | `active`, `draft`, `archived` |
| `tags` | text NULL | Comma-separated tags |
| `admin_graphql_api_id` | varchar(255) NULL | Shopify GID |
| `published_at` | datetime NULL | |
| `visibility` | tinyint(1) DEFAULT 1 | |
| `has_variants` | tinyint(1) DEFAULT 0 | |
| `created_at` / `updated_at` | datetime | |

### `variants` (777 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `product_id` | int FK→products NOT NULL | |
| `variant_id` | varchar(255) UNIQUE NOT NULL | External (Shopify) variant ID |
| `sku` | varchar(255) UNIQUE NULL | Stock-keeping unit |
| `title` | varchar(255) NOT NULL | |
| `price` | decimal(10,2) NOT NULL | List price |
| `sale_price` | decimal(10,2) NULL | Promotional price |
| `pixel_price` | decimal(10,2) NULL | Ad pixel price |
| `in_cart` | tinyint(1) DEFAULT 0 | Cart visibility |
| `position` | int NULL | Sort order |
| `inventory_policy` | varchar(255) NULL | `continue` or `deny` |
| `track_inventory` | tinyint(1) DEFAULT 1 | |
| `weight` | decimal(10,2) NULL | |
| `weight_unit` | varchar(255) NULL | |
| `inventory_quantity` | int NULL | Shopify quantity (may differ from warehouse) |
| `fk_owned_by` | int FK→users NULL | Who owns the inventory |
| `owner` | enum NULL | `Zambeel`, `Reseller-3PL`, `Reseller-360`, `Zambeel-Exclusive Product`, `Zambeel Financing` |
| `product_tier` | varchar(255) NULL | |
| `dispatching_time` | varchar(255) NULL | Expected dispatch days |
| `expected_delivery_ratio` | varchar(255) NULL | |
| `market_saturation` | varchar(255) NULL | |
| `expected_roas` | varchar(255) NULL | |
| `ships_from` | varchar(255) NULL | |
| `option1_name` / `option1_value` | varchar(255) NULL | Variant dimension 1 |
| `option2_name` / `option2_value` | varchar(255) NULL | Variant dimension 2 |
| `option3_name` / `option3_value` | varchar(255) NULL | Variant dimension 3 |
| `inventory_location` | varchar(255) NULL | |
| `created_at` / `updated_at` | datetime | |

### `store_bank_accounts` (74 rows)

Links stores to payout bank accounts.

| Column | Type | Notes |
|---|---|---|
| `id` | char(36) PK | UUID |
| `store_id` | int FK→stores | |
| `bank_id` | char(36) FK→users_bank_accounts | |
| `archived` | tinyint(1) DEFAULT 0 | |
| `created_at` / `updated_at` | datetime | |

### `users_bank_accounts` (190 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | char(36) PK | UUID |
| `fk_user_id` | int FK→users | |
| `bank_name` | varchar(255) NULL | |
| `account_title` | varchar(255) NOT NULL | |
| `account_nick` | varchar(255) NOT NULL | Nickname/label |
| `iban_wallet_address` | varchar(255) NULL | |
| `bank_exchange_name` | varchar(255) NOT NULL | |
| `country` | varchar(100) NOT NULL | |
| `is_primary` | tinyint(1) NOT NULL | |
| `payment_type` | enum | `Bank Account`, `PayPal`, `Payoneer`, `Binance`, `USDT` |
| `archived` | tinyint(1) DEFAULT 0 | |
| `ifsc_code` | varchar(255) NULL | India IFSC |
| `swift_code` | varchar(255) NULL | |
| `fed_wire_code` | varchar(255) NULL | |
| `exchange_name` / `exchange_id` | varchar(255) NULL | Crypto exchange info |
| `created_at` / `updated_at` | datetime | |

### `teams` (9 rows)

Simple CS team grouping.

| Column | Type |
|---|---|
| `id` | int PK AI |
| `name` | varchar(255) NOT NULL |
| `createdAt` / `updatedAt` | datetime |

---

## 5. Core Domain: Inventory & Warehouses

### `warehouse` (8 rows)

| ID | Name | Country ID |
|---|---|---|
| 1 | UAE | 9 |
| 2 | KSA | 12 |
| 3 | Kuwait | 11 |
| 4 | Qatar | 10 |
| 18 | Karachi | 13 |
| 19 | Oman | 14 |
| 20 | Bahrain | 15 |
| 21 | Iraq | 16 |

Schema: `id`, `name`, `fk_country_id` FK→countries, `createdAt`, `updatedAt`.

### `warehouse_variants` (62 rows)

Stock on-hand per variant per warehouse.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `warehouse_id` | int FK→warehouse | |
| `variant_fk_id` | int FK→variants | |
| `quantity` | int DEFAULT 0 | Current stock count |
| `createdAt` / `updatedAt` | datetime | |

### `vendors` (10 rows)

Zambeel-operated warehouses per country. Vendors are the physical warehouse entities used in dispatch batches.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_country_id` | int FK→countries | |
| `name` | varchar(255) NOT NULL | e.g. `Zambeel UAE Warehouse` |
| `warehouse_name` | varchar(255) NULL | Hub name |
| `warehouse_address` | text NULL | |
| `warehouse_city` | varchar(255) NULL | |
| `warehouse_id_general` | varchar(255) NULL | Generic WMS ID |
| `warehouse_id_smartlane` | varchar(255) NULL | Smartlane WMS ID |
| `warehouse_id_tawseel` | varchar(255) NULL | Tawseel WMS ID |
| `createdAt` / `updatedAt` | datetime | |

Real vendors: UAE (Dubai Hub, Sharjah), Qatar (Doha), Kuwait, KSA (Riyadh x2, Jeddah), Pakistan (Karachi), Oman (Muscat), Bahrain (Manama).

### `inventory_transactions` (23 rows)

Records movement of stock between warehouses or SKU remapping.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `movement_number` | varchar(255) NOT NULL | Human-readable e.g. `MOV-001` |
| `movement_type` | enum | `SKU_TO_SKU`, `WAREHOUSE_TRANSFER` |
| `status` | enum | `In Transit`, `Received` |
| `reason` | enum | `SKU Merge`, `Wrong SKU Mapping`, `Repackaging`, `Services Deal`, `Variant Consolidation`, `Internal Adjustment`, `Demand Fulfillment`, `Purchase Transfer` |
| `fk_moved_by` | int FK→users | Admin who initiated |
| `fk_source_warehouse_id` | int FK→warehouse | |
| `fk_destination_warehouse_id` | int FK→warehouse | |
| `fk_from_variant_id` | int FK→variants | Source SKU |
| `fk_to_variant_id` | int FK→variants | Destination SKU |
| `quantity` | int NOT NULL | Units moved |
| `received_quantity` | int NULL | Units confirmed received |
| `createdAt` / `updatedAt` | datetime | |

### `inventory_transaction_logs` (57 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_inventory_transaction_id` | int FK→inventory_transactions NULL | |
| `fk_damaged_bin_movement_id` | int FK→damaged_bin_movement NULL | |
| `fk_moved_by` | int FK→users | |
| `action` | varchar(255) NOT NULL | e.g. `created`, `received`, `rejected` |
| `meta` | json NULL | Extra context |
| `createdAt` / `updatedAt` | datetime | |

### `damaged_bin_movement` (20 rows)

Stock written off as damaged/unsellable.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `movement_number` | varchar(255) NOT NULL | e.g. `DMG-001` |
| `reason` | enum | `Physical Damage`, `Expired Product`, `Quality Failure`, `Packaging Damage`, `Customer Return - Unsellable`, `Purchase Order Correction`, `Lost / Missing in Audit`, `Outdated Stock` |
| `fk_moved_by` | int FK→users | |
| `fk_warehouse_id` | int FK→warehouse | |
| `fk_variant_id` | int FK→variants | |
| `quantity` | int NOT NULL | |
| `createdAt` / `updatedAt` | datetime | |

---

## 6. Core Domain: Dispatch & Couriers

### `dispatch_batches` (49 rows)

A batch groups multiple orders for a single courier handoff.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `batch_id` | varchar(255) UNIQUE | Human-readable batch ID |
| `fk_vendor_id` | int FK→vendors | Dispatching vendor/warehouse |
| `fk_courier_id` | int FK→courier_partners | |
| `fk_country_id` | int FK→countries | Destination country |
| `created_by_user_id` | int FK→users | Admin who created |
| `tracking_status` | enum | `New`, `Generating`, `Partial`, `Generated`, `Failed` |
| `document_status` | enum | `Not Ready`, `Preparing`, `Ready`, `Invalidated` |
| `total_orders` | int DEFAULT 0 | Count of orders in batch |
| `failed_orders_count` | int DEFAULT 0 | |
| `has_removed_orders` | tinyint(1) DEFAULT 0 | Flag: orders were removed post-creation |
| `document_s3_path` | text NULL | S3 path for AWB PDF bundle |
| `courier_request_id` | varchar(255) NULL | External courier API request ID |
| `last_tracking_generation_attempt_at` | datetime NULL | |
| `last_document_generation_attempt_at` | datetime NULL | |
| `createdAt` / `updatedAt` | datetime | |

### `batch_orders` (88 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `batch_id` | varchar(255) FK→dispatch_batches.batch_id | |
| `order_id` | int UNIQUE | One order belongs to at most one batch |
| `createdAt` / `updatedAt` | datetime | |

### `courier_partners` (20 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `name` | varchar(255) NOT NULL | |
| `country` | varchar(255) NOT NULL | |
| `tracking_url_template` | varchar(255) NULL | URL prefix for tracking links |
| `tracking_url_default` | varchar(255) NULL | Fallback tracking URL |
| `deeplink_support` | tinyint(1) NOT NULL | Whether deeplink tracking works |
| `is_integrator` | tinyint(1) DEFAULT 0 | Integrator = manages sub-couriers |
| `integrator_type` | varchar(100) NULL | |
| `fk_parent_courier_id` | int FK→courier_partners NULL | For hierarchical courier setups |
| `createdAt` / `updatedAt` | datetime | |

**Active couriers by country:**
- UAE: iMile, Logistiq-UAE, IW Express, Tawseel
- KSA: Logistiq-KSA
- Pakistan: leopards, **Smartlane** *(integrator)*, dex, stallion, barq_raftar, tcs, ahl, fast_ex, next_step, trax, M&P, Do Deliver, trazno, Arrtx, qwqer

**Smartlane (id=6)** is an `is_integrator=1` courier. It dispatches orders through sub-couriers (dex, stallion, barq_raftar, tcs, etc.) tracked via `courier_sub_couriers`.

### `courier_sub_couriers` (13 rows)

Maps integrator couriers to their sub-couriers.

| Column | Type |
|---|---|
| `id` | int PK AI |
| `fk_integrator_id` | int FK→courier_partners (is_integrator=1) |
| `fk_sub_courier_id` | int FK→courier_partners |
| `external_sub_courier_name` | varchar(255) NULL |
| `createdAt` / `updatedAt` | datetime |

All 13 records are Smartlane sub-couriers: dex, stallion, barq_raftar, tcs, ahl, fast_ex, next_step, trax, M&P, Do Deliver, trazno, Arrtx, qwqer.

---

## 7. Core Domain: Agencies & Commissions

Agencies are reseller partner businesses. They recruit merchants (sellers), manage their orders, and earn commission per delivered order.

### `agencies` (9 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_user_id` | int UNIQUE FK→users | The Agency user account |
| `agency_unique_id` | varchar(20) UNIQUE NULL | Human-readable ID e.g. `AGN-001` |
| `name` | varchar(255) NOT NULL | Agency business name |
| `country` | varchar(100) NOT NULL | |
| `city` | varchar(255) NULL | |
| `phone` | varchar(50) NULL | |
| `poc_name` | varchar(255) NOT NULL | Point of contact name |
| `poc_photo_url` | varchar(500) NULL | S3 URL |
| `identity_proof_url` | varchar(500) NULL | S3 URL |
| `registration_status` | enum | `Pending`, `Approved`, `OnHold`, `Rejected` |
| `license_status` | enum | `Inactive`, `Active`, `Revoked` |
| `hold_reason` | text NULL | |
| `reject_reason` | text NULL | |
| `rejected_at` / `cooldown_until` | datetime NULL | |
| `allow_resubmit` | tinyint(1) NULL | |
| `terms_accepted_at` | datetime NULL | |
| `fk_commission_model_id` | int FK→agency_commission_models NULL | Assigned model |
| `createdAt` / `updatedAt` | datetime | |

**Agency status distribution:**
- Approved + Active: 4
- Approved + Revoked: 1
- Rejected + Inactive: 1
- Rejected + Active: 1
- Pending + Inactive: 2

### `agency_commission_models` (37 rows)

Named templates for commission structures.

| Column | Type |
|---|---|
| `id` | int PK AI |
| `name` | varchar(255) NOT NULL |
| `archived` | tinyint(1) DEFAULT 0 |
| `createdAt` / `updatedAt` | datetime |

Sample models: `PAK-UAE-KSA`, `Percentage Pay UAE`, `Flat Rate`, `UAE Agencies for all`.

### `agency_commission_model_rules` (43 rows)

Per-country rate rules within a model.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_commission_model_id` | int FK→agency_commission_models | |
| `fk_country_id` | int FK→countries | Per-country rate |
| `commission_type` | enum | `percentage_of_delivered_revenue`, `flat_per_delivered_order` |
| `value` | decimal(10,2) | Rate value |
| `currency` | varchar(3) | e.g. `AED`, `SAR`, `PKR` |
| `createdAt` / `updatedAt` | datetime | |

**Example rules:**
- Flat Rate model, KSA: 10 SAR per delivered order
- Flat Rate model, UAE: 10% of delivered revenue (AED)
- Percentage Pay UAE, UAE: 5% (AED), KSA: 5% (SAR)
- PAK-UAE-KSA, Pakistan: PKR 100 flat per order

### `agency_commission_records` (42 rows)

One record created per delivered order for an agency-managed merchant.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_agency_id` | int FK→agencies | |
| `fk_merchant_id` | int FK→users | The seller whose order delivered |
| `fk_store_id` | int FK→stores | |
| `fk_order_id` | int UNIQUE FK→orders | Unique: one commission per order |
| `commission_type` | enum | Same as model_rules enum |
| `value` | decimal(10,2) | Rate at time of commission |
| `commission_amount` | decimal(12,2) | Computed commission in currency |
| `order_revenue` | decimal(12,2) NULL | Order revenue used in calculation |
| `currency` | varchar(3) | |
| `createdAt` / `updatedAt` | datetime | |

### `agency_merchant_connections` (7 rows)

Tracks agency–seller relationship lifecycle.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_agency_id` | int FK→agencies | |
| `fk_user_id` | int FK→users | The seller |
| `status` | enum | `Pending`, `Active`, `Rejected`, `Disconnected` |
| `disconnect_reason` / `disconnect_details` | text NULL | |
| `disconnected_at` | datetime NULL | |
| `requested_at` | datetime DEFAULT CURRENT_TIMESTAMP | |
| `responded_at` | datetime NULL | |
| `createdAt` / `updatedAt` | datetime | |

### `agency_team_members` (10 rows)

Users within an agency (Owner or Member).

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_agency_id` | int FK→agencies | |
| `fk_user_id` | int FK→users NULL | NULL until invite accepted |
| `invite_email` | varchar(255) NOT NULL | |
| `role` | enum | `Owner`, `Member` |
| `invite_accepted_at` | datetime NULL | |
| `archived` | tinyint(1) DEFAULT 0 | |
| `createdAt` / `updatedAt` | datetime | |

### `agency_invoices` (0 rows)

Will store agency payout invoices. Schema mirrors `invoices` conceptually.

---

## 8. Core Domain: Tickets & Support

### `tickets` (113 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_store_id` | int FK→stores NOT NULL | |
| `fk_order_id` | int FK→orders NULL | |
| `fk_team_id` | int FK→teams NULL | Assigned team |
| `fk_created_by` | int FK→users NOT NULL | |
| `fk_seller_id` | int FK→users NULL | Seller context |
| `category` | enum | See full list below |
| `sub_category` | enum | See full list below |
| `status` | enum | `Pending`, `In Progress`, `Awaiting Seller Action`, `Resolved` |
| `assigned_to` | enum | `Zambeel`, `Seller` |
| `description` | text NOT NULL | |
| `created_at` / `updated_at` | datetime | |

**Ticket categories:**
`Onboarding & Integration`, `Order Processing`, `Order Sending & Inventory Issue`, `Order Changes & Updates`, `Product Complaint`, `Delivery Complaint`, `Payments & Invoices`, `Other`, `Order Issue`, `Catalog & Pricing Updates`, `Payments & Payouts`

**Ticket sub-categories (43 values):**
Store integration failure, Cant find SKU of the product, Cannot send orders to Zambeel, Manual order upload error, Inventory Not Showing Correctly, Request to Cancel the order, Change Price, Change Quantity, Modify SKU (add/replace), Customer requested color/size change, Update address/phone, Expedite dispatch (order confirmed), Request to Reschedule, Initiate return, Other order update, Order Proofs & Updates, Damaged/defective item delivered, Wrong item/SKU delivered, Missing item/parts, Product quality complaint, Rider did not contact customer, Rider misbehaved, Invoice not received, Invoice incorrect / needs correction, Payment not received, Short/partial payment received, General Inquiry, Request to Open Parcel by Customer, Order is Prepaid, Price is less than Zambeel Price, Invalid Customer Phone Number, Prepaid Order-Need Confirmation, Product Price has changed, Product delisted / temporarily unavailable, Incorrect payout account details, General, Order Complaint, Product Quantity / SKU Confirmation, Price Issue, High Value Order

### `ticket_logs` (239 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `ticket_id` | int FK→tickets | |
| `user_id` | int FK→users | Who made the change |
| `action` | varchar(255) | e.g. `status_changed`, `assigned_to_changed` |
| `previous_value` | text NULL | |
| `new_value` | text NULL | |
| `created_at` / `updated_at` | datetime | |

### `ticket_images` (30 rows)

Attachments uploaded to tickets. FK→tickets (implied by fk_ticket_id).

### `comments`

Thread on a ticket. Supports internal notes and seller-visible comments.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_ticket_id` | int FK→tickets | |
| `fk_user_id` | int FK→users | Author |
| `fk_team_id` | int FK→teams NULL | |
| `comment` | text NULL | |
| `notes_type` | enum | `comment`, `resolution_notes` |
| `is_internal` | tinyint(1) DEFAULT 0 | True = agent-only |
| `createdAt` / `updatedAt` | datetime | |

---

## 9. Core Domain: Invoices & Payments

### `invoices` (105 rows)

Seller payout invoices (PDF generated and stored on S3).

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `store_id` | int FK→stores | |
| `filename` | varchar(255) NOT NULL | |
| `s3_file_url` | varchar(255) NOT NULL | Full S3 URL |
| `payment_status` | enum NULL | `Paid`, `Not Paid Yet`, `Failed Transaction`, `Missing Banking Details`, `Ineligible for Payment` |
| `reason` | varchar(255) NULL | Reason for non-payment |
| `created_at` / `updated_at` | datetime | |

### `user_subscription_transactions`

Tracks PayTabs/Shopify billing for Gold plan subscriptions.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_user_id` | int NOT NULL | |
| `tran_ref` | varchar(255) | PayTabs transaction reference |
| `tran_type` / `tran_id` | varchar(255) | |
| `description` | varchar(255) | |
| `currency` / `amount` / `tran_total` | varchar/float | |
| `payment_channel` | varchar(255) NULL | |
| `profile_id` / `merchant_id` | int | PayTabs IDs |
| `trace` | varchar(255) | |
| `payment_status` | varchar(255) | e.g. `A` (Approved) |
| `payment_message` | varchar(255) | |
| `response_code` / `acquirer_ref` | varchar(255) | |
| `subscription_expiry` | datetime NULL | When the Gold plan expires |
| `billing_method` | enum NULL | `PAYTABS`, `SHOPIFY` |
| `created_at` / `updated_at` | datetime | |

---

## 10. Core Domain: Purchase Orders & Returns

### `purchase_order` (32 rows)

Inbound inventory purchase orders from suppliers.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `PO_ID` | varchar(255) UNIQUE | Human-readable e.g. `PO-001` |
| `fk_created_by` | int FK→users | Admin who created |
| `fk_country_id` | int FK→countries DEFAULT 1 | |
| `fk_warehouse_id` | int FK→warehouse DEFAULT 1 | Destination warehouse |
| `status` | enum | `Draft`, `Received`, `Partially Received`, `Cancelled`, `Submitted` |
| `createdAt` / `updatedAt` | datetime | |

### `po_variants` (97 rows)

Line items in a purchase order.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `po_fk_id` | int FK→purchase_order | |
| `variant_fk_id` | int FK→variants | |
| `quantity_total` | int NOT NULL | Ordered qty |
| `quantity_received` | int DEFAULT 0 | Received qty so far |
| `createdAt` / `updatedAt` | datetime | |

### `return_order` (14 rows)

Inbound return shipments (customer returns received at warehouse).

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `RETURN_ID` | varchar(255) NOT NULL | Human-readable return ID |
| `fk_created_by` | int FK→users | |
| `fk_country_id` | int FK→countries | |
| `fk_warehouse_id` | int FK→warehouse | Receiving warehouse |
| `status` | enum | `Submitted` *(currently only one value)* |
| `createdAt` / `updatedAt` | datetime | |

### `return_orders_variants` (23 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_return_id` | int FK→return_order | |
| `fk_variant_id` | int FK→variants | |
| `quantity_received` | int DEFAULT 0 | |
| `createdAt` / `updatedAt` | datetime | |

---

## 11. Reference & Config Tables

### Countries (key IDs)

| ID | Country |
|---|---|
| 9 | UAE |
| 10 | Qatar |
| 11 | Kuwait |
| 12 | KSA (Saudi Arabia) |
| 13 | Pakistan |
| 14 | Oman |
| 15 | Bahrain |
| 16 | Iraq |

### `cities`
`id`, `fk_country_id` FK→countries, `name`, `createdAt`, `updatedAt`.

### `country_threshold`
Thresholds for delivery-ratio scoring per country: `country`, `product_threshold` (float), `store_threshold` (float).

### `stores_country_ratio`
Per-store, per-country delivery ratio and rating: `fk_store_id`, `fk_country_id`, `delivery_ratio` (float), `rating` (tinyint 0–5).

### `variants_country_ratio`
Same as stores_country_ratio but for variants: `fk_variant_id`, `fk_country_id`, `delivery_ratio`, `rating`.

### `ticker_config`
Portal announcement banner: `is_enabled`, `message`, `bg_color` (default `#e9b20c`), `text_color` (default `#000000`), `updated_by` FK→users.

### `featured_products`
Admin-curated product highlights: `product_id` FK→products, `display_order` UNIQUE.

### `images`
Product images: `product_id` FK→products, `src`, `height`, `width`, `position`.

### `creative_analytics`
Ad creative upload jobs: `fk_user_id`, `status` (`Pending`/`Processing`/`Processed`/`Failed`), `s3_key`, `analytics_meta`, `error`.

### `notifications`
In-app notifications: `fk_user_id`, `type` (`order`/`system`/`message`/`custom`), `title`, `message`, `payload`, `status` (`read`/`unread`), `read_at`. (Currently 0 rows.)

### `event_dedupe`
Webhook idempotency: `event_id` (varchar PK), `created_at`. Prevents duplicate processing of the same Shopify webhook.

### `Sessions`
Express session store: `sid` (varchar PK), `expires`, `data` (text), `createdAt`, `updatedAt`.

### `SequelizeMeta`
Sequelize ORM migration log: `name` (varchar PK). Lists all migration files that have been run.

---

## 12. Audit & Log Tables

### `order_logs` (16,322 rows)

Complete change history for every order.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `fk_order_id` | int FK→orders | |
| `fk_user_id` | int FK→users NULL | Actor (NULL = system) |
| `action` | varchar(255) | e.g. `status_updated`, `assigned_to_changed`, `courier_assigned` |
| `field_changed` | varchar(255) NULL | |
| `previous_value` | json NULL | |
| `new_value` | json NULL | |
| `createdAt` / `updatedAt` | datetime | |

### `mock_order_logs`

Identical schema to `order_logs`. Used for staging/demo orders to keep audit trails separate.

### `order_batch_audit_logs`

Audit for batch-level admin actions.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK AI | |
| `action_type` | enum | `CLEAR_COURIER_ASSIGNMENT`, `UPLOAD_VENDOR_COURIER`, `BATCH_CREATED`, `BATCH_REMOVED`, `DOWNLOAD_AWB` |
| `performed_by_user_id` | int FK→users | |
| `performed_at` | datetime | |
| `order_id` | int FK→orders NULL | |
| `batch_id` | varchar(255) NULL | |
| `previous_batch_id` / `previous_vendor_id` | varchar(255) NULL | |
| `previous_courier_id` | int NULL | |
| `previous_awb_file_path` | text NULL | |
| `previous_courier_tracking_id` | varchar(255) NULL | |
| `notes` | text NULL | |

### `inventory_transaction_logs` (57 rows)

Audit trail for stock movements and damaged-bin events. Links to either `inventory_transactions` or `damaged_bin_movement`.

### `ticket_logs` (239 rows)

Tracks every field change on tickets (status, assignment, category, etc.).

### `order_remarks`

Junction between orders and remarks (predefined remark templates): `order_id` FK→orders, `remark_id` FK→remarks.

---

## 13. Key Business Logic

### Order Lifecycle

```
[Shopify Webhook] → unprocessed_orders (pending)
        ↓
  [Ingestion Worker] → orders (Received / Pending Reseller Submission)
        ↓
  [CS Confirmation] → Confirmation Pending
    ├── Confirmation in Process (Message Sent → Customer Replied)
    ├── Address Verification in Process
    ├── Scheduled Before Delivery
    └── On Hold by Customer
        ↓ Confirmed
  [Admin Approval] → Approved
    ├── Checking Inventory For Dispatching
    └── Inventory In Transit
        ↓
  [Batch Creation] → Dispatching in Process → Awaiting Courier Pickup
        ↓
  [Courier Pickup] → Shipped
    ├── In Transit
    ├── In Delivery
    └── Scheduled by Customer
        ↓
  [Delivery] → Delivered ✓
        OR
  [NDR] → Undelivered
    ├── Customer Refused - Assigned to CS Team
    ├── Customer Uncontactable - Assigned to CS Team
    ├── Request to Return
    └── Request to Re-Scheduled
        ↓ Return
  Return in Transit → Returning
        ↓
  Return → Returned ✗
        OR
  Cancelled (Invalid Order / Customer Refused / Product Not Available)
```

### Status JSON Structure

The `orders.status` column stores a JSON string:
```json
{"status": "Confirmation Pending", "substatus": "Confirmation in Process", "tag": "Message Sent"}
```
Three generated columns extract these for indexing: `status_value`, `status_substatus`, `status_tag`.

**Always filter by generated columns, not the raw JSON.**

### Bifurcation Model

Orders and stores have a `bifurcation` field classifying the fulfilment model:
- `Partner` — Zambeel handles fulfilment end-to-end (93% of orders)
- `3PL` — Third-party logistics (seller uses own courier, 9 orders)
- `Reseller` — Reseller model
- `360` — Full 360 service model

### User Roles

| Role | Count | Access Level |
|---|---|---|
| Admin | 22 | Full platform access, batch/dispatch management |
| Agent | 8 | CS agents; assigned to teams; handle order confirmations |
| Seller | 60 | Merchant; can see their store's orders, tickets, invoices |
| Agency | 5 | Agency user; recruits merchants, earns commissions |

### Commission Calculation

1. Agency gets assigned a `commission_model` (template)
2. Model has per-country `rules` (flat fee or % of revenue)
3. When an order is **delivered**, a `commission_record` is created:
   - `flat_per_delivered_order`: fixed amount per order (e.g. PKR 100, SAR 10)
   - `percentage_of_delivered_revenue`: `commission_amount = order_revenue × value / 100`
4. `agency_invoices` will aggregate records into payable invoices (not yet used)

### Integrator Courier Pattern

When `orders.fk_integrator_id` is set, the order uses an integrator like Smartlane:
- `orders.fk_courier_id` = the integrator's courier_partners id
- `orders.sub_courier_id` = the actual sub-courier from courier_sub_couriers
- The integrator dispatches to the appropriate sub-courier based on city/zone

### Seller Invoice Payment Lifecycle

```
Invoice generated → payment_status = NULL (just created)
→ "Not Paid Yet" (default)
→ "Paid" (confirmed payment)
   OR "Failed Transaction" (payment attempt failed)
   OR "Missing Banking Details" (seller hasn't added bank account)
   OR "Ineligible for Payment" (rejected/flagged)
```

### PO Lifecycle

```
Draft → Submitted → Partially Received → Received
                  → Cancelled
```
`po_variants.quantity_received` increments as stock arrives. PO is `Received` when all lines received, `Partially Received` if some are.

### Agency Registration Lifecycle

```
Pending (new application)
→ Approved + Active (admin approved, license granted)
→ Approved + Revoked (license revoked post-approval)
OR
→ OnHold (under review)
→ Rejected (declined, cooldown_until set, may allow_resubmit)
```

Agency–Merchant connection:
```
Pending (agency sent invite) → Active (seller accepted)
→ Rejected (seller declined)
→ Disconnected (either party disconnected)
```

---

## 14. Sample Data Patterns

### Typical Order Record

```
order_number:     ORD-1473
platform:         Shopify
total_cost:       200.00
total_discount:   8.00
shipping_price:   5.00
total_payable:    200.00
currency:         USD
payment_method:   COD
bifurcation:      Partner
status_value:     Confirmation Pending
status_substatus: Confirmation in Process
status_tag:       Message Sent
fk_store_id:      21
activity_counter: 0
archive:          0
```

### Typical Ticket

```
category:     Order Issue
sub_category: General
status:       Pending / In Progress
assigned_to:  Zambeel
description:  Free text from seller
```

### Commission Record Pattern

```
agency:           agency_id=4 (PAK-based)
merchant/store:   store_id=149
order:            order_id=18595
commission_type:  flat_per_delivered_order
value:            100.00
commission_amount: 100.00
currency:         PKR
order_revenue:    2200.00
```

### Platform Distribution

| Platform | Orders | % |
|---|---|---|
| Shopify | 4,889 | 61% |
| Manual / Unknown | 3,072 | 39% |
| Easy orders | 7 | <1% |
| Lightfunnels | 7 | <1% |

### Payment Method Distribution

| Method | Orders | % |
|---|---|---|
| COD (Cash on Delivery) | 7,435 | 93% |
| Paid (prepaid) | 540 | 7% |

### Warehouses in Use

UAE (Dubai + Sharjah), KSA (Riyadh + Jeddah), Kuwait, Qatar, Pakistan (Karachi), Oman, Bahrain, Iraq.

---

*Generated by SQA Agent from live staging database on 2026-05-07.*
