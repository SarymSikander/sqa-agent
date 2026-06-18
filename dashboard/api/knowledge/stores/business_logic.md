# Stores Domain — Business Logic

## What This Domain Does

A **Store** is a seller's e-commerce storefront connected to the Zambeel OMS. Each seller (user) can have multiple stores. Stores can be integrated automatically via platform OAuth (Shopify, LightFunnels, EasyOrders, YouCan, Salla, WooCommerce) or created manually. The store record holds the configuration that governs how orders from that store are handled: whether confirmation calls are made, how orders bifurcate into fulfilment tiers, whether the store is trusted, and which bank account receives payouts.

The store controller handles CRUD on store records and a few special operations (trust promotion, bank account linking, manual creation). Platform OAuth flows live in their own route files (`shopify-routes.js`, `sallaRoutes.js`, etc.) and are not covered here.

---

## Key Endpoints

Routes are mounted at `/store` and `/store-names`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/store` | `verifyAdminAndSellerWithAgencyContext` | List all stores (paginated, searchable) |
| GET | `/store/trust/confirmation-pending-tags` | `verifyAdminAndSellerWithAgencyContext` | List valid tags for "Confirmation Pending" status (used when trusting a store) |
| GET | `/store/:id` | `verifyAdminAndSellerWithAgencyContext` | Get a single store by ID |
| PUT | `/store/:id` | `verifyAdminAndSellerWithAgencyContext` | Update store settings |
| DELETE | `/store/:id` | `verifyAdminAndSellerWithAgencyContext` | Archive a store (soft delete) |
| GET | `/store/user/:userId` | `verifyAdminAndSellerWithAgencyContext` | Get stores for a specific user |
| GET | `/store/user/stores/:userId` | `verifyAdminAndSellerWithAgencyContext` | Alias for the above |
| POST | `/store/check-name` | `verifyAdminAndSellerWithAgencyContext` | Check if a store name is unique |
| POST | `/store/create/storeManually` | `verifyAdminAndSellerWithAgencyContext` | Create a manual (non-OAuth) store |
| GET | `/store-names` | none | Return just store names (id + store_name) sorted A-Z |

---

## Business Logic

### List All Stores (`GET /store`)

- Default page size 1000 (effectively returns all stores unless paginated).
- Supports `?search=` (matches `store_name`, `store_url`, `platform`, `user_id`).
- `?untrustedManualOnly=true` — filters to `is_trusted = false` AND platform NOT IN `['Shopify', 'EasyOrders', 'LightFunnels', 'YouCan']`.
- Includes bank connections via `StoreBankAccount → UsersBankAccount`.
- Access tokens and IVs are excluded from the response.
- Default scope on the `Store` model excludes archived stores (`archived = false`), so deleted stores never appear.

### Update Store (`PUT /store/:id`)

Updatable fields: `store_name`, `confirmation_setting`, `auto_process_orders`, `bank_account_id`, `bifurcation`, `is_trusted`, `target_tag`, `store_protocol`, `ndr_treatment`.

**Trust promotion (is_trusted false → true):**
1. Requires `req.user.role === 'Admin'`.
2. Requires `target_tag` in the request body.
3. Validates `target_tag` is a real `OrderTag` that is:
   - Not the special `ORDER_ON_HOLD_CONTACT_SUPPORT` tag.
   - Not archived.
   - Associated with the `Confirmation Pending` order status sub-status.
4. Inside a transaction:
   - Saves the store with `is_trusted = true`.
   - Finds all un-archived orders for this store that are in `status_value = 'Confirmation Pending'` AND `status_tag = ORDER_ON_HOLD_CONTACT_SUPPORT`.
   - Updates each such order's `status.tag` to `target_tag`.
   - Creates `OrderLog` rows for each affected order with action `TAG_UPDATE`.

**Bank account linking:** If `bank_account_id` is provided, upserts a `StoreBankAccount` record linking the store to that bank account.

**Confirmation setting mapping:** accepts lowercase keys (`on`, `off`, `default`, `mandatory`, `call_only`) and normalises to Title Case (`On`, `Off`, `Default`, `Mandatory`, `Call Only`).

### Delete Store (`DELETE /store/:id`)

Soft delete only — sets `archived = true`, clears `access_token` and `iv`. The default scope then hides the record from all queries.

### Create Manual Store (`POST /store/create/storeManually`)

Used when a seller wants to connect a store that doesn't have automated OAuth (or a Shopify store added manually).

**Steps:**
1. Resolve `userId` from proxy context or `req.user.id`.
2. Verify the user exists.
3. For Shopify Manual stores (`platform = 'shopify'` or `'Shopify Manual'`): `storeUrl`/`storeDomain` is required and is normalised to a bare domain (strip `https://`, trailing paths).
4. Requires a primary bank account (`UsersBankAccount` where `is_primary = true` and `archived = false`) — returns 400 `NO_PRIMARY_BANK_ACCOUNT` if missing.
5. Creates the `Store` with:
   - `auto_process_orders = true`
   - `confirmation_setting = 'Off'`
   - `is_trusted = false` (manual stores start untrusted)
   - `status = false` for Shopify Manual (webhook must connect first), `true` otherwise
6. Creates a `StoreBankAccount` linking the store to the primary bank.
7. If an agency is acting in `specific` access scope for this merchant, auto-adds the new store ID to the agency's `allowedStoreIds` list in `disconnect_details`.

### Warehouse-level operations (warehouseController)

The `warehouseController` (used by a separate route) provides batch/dispatch helpers:
- `getDIPBatches` — returns distinct `batch_id` values from orders in `Dispatching In Process` status, optionally filtered by customer country.
- `downloadAWBs` — returns AWB (Air Waybill) file URLs for a set of order IDs or a batch ID.
- `downloadPackingList` — aggregates product SKUs and quantities across all orders in a batch, enriched with product images.

---

## Key Model Fields

### `stores`
| Field | Type | Allowed Values / Notes |
|-------|------|------------------------|
| `store_id` | STRING | UUID generated on creation |
| `user_id` | INTEGER | FK → users (store owner) |
| `platform` | STRING | `Shopify`, `Shopify Manual`, `LightFunnels`, `EasyOrders`, `YouCan`, `Salla`, `WooCommerce`, `Manual`, etc. |
| `bifurcation` | ENUM | `360`, `3PL`, `Dropshipper`, `Partner` — determines fulfilment track and inventory access |
| `confirmation_setting` | ENUM | `On`, `Off`, `Default`, `Mandatory`, `Call Only` |
| `store_protocol` | ENUM | `Standard`, `Important`, `VIP` |
| `ndr_treatment` | ENUM | `ON`, `OFF` — controls NDR (Non-Delivery Report) handling |
| `auto_process_orders` | BOOLEAN | Default `true` |
| `is_trusted` | BOOLEAN | Default `true`; manual stores start as `false` |
| `status` | BOOLEAN | `true` = active/connected, `false` = inactive/pending |
| `archived` | BOOLEAN | Default `false`; soft-delete flag; default scope excludes archived |
| `access_token` | TEXT | Encrypted OAuth token (excluded from list responses) |
| `iv` | STRING(32) | Encryption IV for access_token |
| `confirm_orders` | ENUM | `on`, `off`, `default` (legacy field, use `confirmation_setting`) |
| `woocommerce_consumer_key` | STRING | WooCommerce API key |
| `account_id` | STRING | External platform account identifier |

---

## Inter-Domain Interactions

- **Orders**: `Store.hasMany(Order)` via `fk_store_id`. Order confirmation, trust status, and bifurcation are driven by the store's settings.
- **Invoices**: `Store.hasMany(Invoice)` — store is the billing entity for invoices.
- **Tickets**: `Store.hasMany(Ticket)` via `fk_store_id`.
- **Bank Accounts**: `Store.hasMany(StoreBankAccount)` → `UsersBankAccount` — determines the payout account for seller payments.
- **Country/Ratio**: `Store.belongsToMany(Country)` through `StoreCountryRatio` — defines which countries a store ships to and their delivery ratios.
- **Inventory**: `stores.bifurcation` in `['360', '3PL']` gates the seller inventory display and CSV export.
- **Agency**: When an agency creates a store in specific-scope mode, the new store is automatically added to the agency's allowed store list.
- **Users**: `Store.belongsTo(User)` — the seller who owns the store.

---

## Important Constraints

- **Trust promotion is admin-only**. Non-admin users cannot set `is_trusted = true`.
- When promoting a store to trusted, a `target_tag` is mandatory. It must be a valid `Confirmation Pending` sub-status tag and must not be `ORDER_ON_HOLD_CONTACT_SUPPORT`.
- Manual store creation requires a **primary bank account** — will reject with 400 if the user has none.
- Shopify Manual stores require a proper domain string (e.g. `store.myshopify.com`). Domain is normalised (stripped of protocol and path) before storage.
- Deleting a store is a soft delete — it is never physically removed. `access_token` and `iv` are nulled on deletion for security.
- The default Sequelize scope on `Store` always adds `WHERE archived = false`, so archived stores are invisible to all normal queries.
- `bifurcation = '360'` or `'3PL'` means the seller's inventory is managed by Zambeel's warehouse. `Dropshipper` and `Partner` bifurcations do not get inventory UI.
- Proxy context (`req.proxyContext`) is honoured throughout — admins and agencies can manage stores on behalf of merchants.
