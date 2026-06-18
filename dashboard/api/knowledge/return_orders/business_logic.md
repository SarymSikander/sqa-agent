# Return Orders Domain — Business Logic

## What This Domain Does

Return Orders track physical inventory arriving back at a Zambeel warehouse — goods returned from customers or recalled from the field. When a Return Order is created, the warehouse stock is immediately incremented for each returned variant. This is the inbound inventory replenishment path (as opposed to Purchase Orders, which track new stock from suppliers).

---

## Key Model: `return_order` table

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `RETURN_ID` | STRING | Human-readable ID, auto-generated as `RO-0000`, `RO-0001`, etc. |
| `fk_created_by` | INTEGER FK → users | User who created the return order |
| `fk_country_id` | INTEGER FK → countries | Country the goods are returning to |
| `fk_warehouse_id` | INTEGER FK → warehouse | Target warehouse receiving the stock |
| `status` | ENUM | Only allowed value: `Submitted` |
| `createdAt` / `updatedAt` | DATE | Timestamps |

### Associations
- `ReturnOrder` → `User` as `createdBy`
- `ReturnOrder` → `Country` as `country`
- `ReturnOrder` → `Warehouse` as `warehouse`
- `ReturnOrder` ↔ `Variant` (belongsToMany through `ReturnOrdersVariant`, FK `fk_return_id`)
- `ReturnOrder` → `ReturnOrdersVariant[]` (hasMany, FK `fk_return_id`)

### `ReturnOrdersVariant` join table
| Field | Description |
|---|---|
| `fk_return_id` | References `return_order.id` |
| `fk_variant_id` | References `variants.id` |
| `quantity_received` | How many units of this variant were returned |

---

## All Key Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/return-orders` | verifyUser | List all return orders with pagination and search/date filters |
| `GET` | `/return-orders/:returnId` | verifyUser | Get a single return order by ID |
| `POST` | `/return-orders` | verifyUser | Create a new return order (increments warehouse inventory) |

---

## Business Logic — Step by Step

### Creating a Return Order (`POST /return-orders`)
All steps run inside a single database transaction (rolls back entirely on any error):

1. **Validate country** — `countryId` must exist in `countries` table.
2. **Resolve variant IDs from SKUs** — if any `lineItem` has a `sku` instead of an `id`, look up the variant by SKU. If any SKU is not found → reject with 404 listing missing SKUs.
3. **Validate variant IDs** — confirm all resolved variant IDs actually exist. If count doesn't match → reject with 404 listing missing variant IDs.
4. **Validate warehouse** — `warehouseId` must exist.
5. **Generate RETURN_ID** — find the most recently created `ReturnOrder` and increment its numeric suffix. Format: `RO-{zero-padded 4-digit number}`. First ever = `RO-0000`.
6. **Create `ReturnOrder`** record with `status = "Submitted"`.
7. **Create `ReturnOrdersVariant`** records (one per line item with `quantity_received`).
8. **Increment warehouse inventory**: for each variant, upsert `WarehouseVariant` (add `quantity_received` to existing stock, or create new record if not present). Uses `updateOnDuplicate: ['quantity']` strategy.
9. **Commit transaction** → return new `RETURN_ID`.

### Fetching Return Orders (`GET /return-orders`)
- Supports `search` (by `RETURN_ID` or country name), `startDate`, `endDate`.
- Returns paginated results with associated country, createdBy user, warehouse, and variants (with product title and images).
- Orders sorted by `createdAt DESC`.

### Getting a Single Return Order (`GET /return-orders/:returnId`)
- Looks up by `id` (not `RETURN_ID`).
- Returns associated country and variants (id, title, sku only).

---

## Interactions with Other Domains

| Domain/Service | How |
|---|---|
| **Inventory (WarehouseVariant)** | Warehouse stock is directly incremented during return order creation (inbound replenishment) |
| **Variants/Products** | Line items reference variants by ID or SKU; product image shown in list view |
| **Country/Warehouse** | Return is scoped to a specific country and warehouse |
| **Users** | Creator is recorded for audit purposes |

---

## Constraints and Rules

1. **Status is always `Submitted`** — the ENUM in the model has only one value; there is no approval/draft flow for return orders.
2. **Warehouse inventory increments immediately** on creation — no "pending" state.
3. **SKU or ID** can be provided for line items; the controller resolves SKUs to IDs before proceeding.
4. **Duplicate variants** in a single return order are not explicitly rejected by validation — each variant gets its own `ReturnOrdersVariant` row; multiple rows for the same variant in one RO could create duplicate entries (this is a potential edge case).
5. **RETURN_ID sequential numbering** is based on the last-created record's timestamp; concurrent creates could theoretically collide (no database-level unique constraint guard in the generator — `RETURN_ID` itself is a plain STRING without an auto-lock).
6. **No direct link to `orders` table** — return orders are standalone warehouse replenishment records, not tied to individual customer orders.
7. **Full rollback on any error** — partial inventory updates never happen.
