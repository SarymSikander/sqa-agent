# Purchase Orders Domain — Business Logic

## What This Domain Does

Purchase Orders (POs) track incoming stock from suppliers into a Zambeel warehouse. When goods arrive at the warehouse, a PO is marked as received (fully or partially), and the warehouse inventory is incremented by the received quantities. POs progress through a lifecycle: Draft → Submitted → Partially Received → Received (or Cancelled).

This is distinct from Return Orders (inbound from customers) — POs represent B2B supplier-to-warehouse inbound stock.

---

## Key Model: `purchase_order` table

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `PO_ID` | STRING (unique) | Human-readable ID, auto-generated as `PO-0000`, `PO-0001`, etc. |
| `fk_country_id` | INTEGER FK → countries | Country the PO is for |
| `fk_created_by` | INTEGER FK → users | User who created the PO |
| `fk_warehouse_id` | INTEGER FK → warehouse | Target warehouse |
| `status` | ENUM | `Draft`, `Received`, `Partially Received`, `Cancelled`, `Submitted` |
| `createdAt` / `updatedAt` | DATE | Timestamps |

### Associations
- `PurchaseOrder` → `User` as `createdBy`
- `PurchaseOrder` ↔ `Variant` (belongsToMany through `POVariant`, FK `po_fk_id`)
- `PurchaseOrder` → `POVariant[]` (hasMany, FK `po_fk_id`)
- `PurchaseOrder` → `Country` as `country`
- `PurchaseOrder` → `Warehouse` as `warehouse`

### `POVariant` join table (model: `poVariants`)
| Field | Description |
|---|---|
| `po_fk_id` | References `purchase_order.id` |
| `variant_fk_id` | References `variants.id` |
| `quantity_total` | Total ordered quantity |
| `quantity_received` | Quantity actually received at warehouse (starts 0) |

---

## All Key Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/purchase-orders` | verifyUser | List all POs with pagination, search, status filter, date range |
| `GET` | `/purchase-orders/:poId` | verifyUser | Get a single PO by ID |
| `POST` | `/purchase-orders` | verifyUser | Create a new PO (Draft) |
| `PUT` | `/purchase-orders/:poId` | verifyUser | Update PO details (country, warehouse, line items) |
| `PUT` | `/purchase-orders/:poId/mark-as-received` | verifyUser | Record received quantities; increments warehouse stock; auto-sets status |
| `PUT` | `/purchase-orders/:poId/mark-as-submitted` | verifyUser | Transition PO to `Submitted` status |
| `GET` | `/purchase-orders/countries` | verifyAgentAdminAndSeller | List all countries (for PO creation form) |
| `GET` | `/purchase-orders/warehouses/country/:countryId` | verifyUser | List warehouses for a country |
| `GET` | `/purchase-orders/warehouses/:warehouseId/search` | verifyUser | Search a SKU in a specific warehouse (checks it exists there) |
| `POST` | `/purchase-orders/warehouses/:warehouseId/validate-variants` | verifyUser | Validate a CSV array of SKUs for a warehouse before PO creation |

---

## Business Logic — Step by Step

### Creating a PO (`POST /purchase-orders`)
All steps run inside a single database transaction:

1. **Validate country** — `countryId` must exist.
2. **Resolve SKUs to IDs** — if any `lineItem` provides `sku` without `id`, find variant by SKU. Missing SKUs → 404 with list of missing SKUs.
3. **Validate variant IDs** — confirm all resolved IDs exist.
4. **Validate warehouse** — `warehouseId` must exist.
5. **Generate PO_ID** — find latest PO by `createdAt DESC`, increment numeric suffix. Format: `PO-{zero-padded 4-digit number}`. First = `PO-0000`.
6. **Create `PurchaseOrder`** record with provided status (typically `Draft`).
7. **Create `POVariant`** records for each line item: `quantity_total = variant.quantity`, `quantity_received = 0`.
8. **Commit** → return new `PO_ID`.

### Updating a PO (`PUT /purchase-orders/:poId`)
1. Validates existing PO, country, warehouse.
2. Resolves any SKU-based variants.
3. Updates PO header (country, warehouse, status).
4. **Destroys all existing `POVariant` records** for the PO and recreates them fresh from request body. Received quantities are reset to 0 — editing a PO resets receiving progress.
5. Full transaction with rollback on error.

### Marking as Received (`PUT /purchase-orders/:poId/mark-as-received`)
1. Load PO with existing `poVariants`.
2. **Validate quantities**: `quantity_received` cannot exceed `quantity_total` for any variant.
3. For each variant in request:
   - Find existing `POVariant` for this PO → update `quantity_received`.
   - If no existing `POVariant` → create one.
4. **Upsert warehouse inventory**: for each variant, add `quantity_received` to `WarehouseVariant.quantity` (create if not exists). Minimum 0.
5. **Auto-calculate status**: if all variants have `quantity_received === quantity_total` → `"Received"`; otherwise → `"Partially Received"`.
6. Update PO status.
7. Commit transaction.

### Marking as Submitted (`PUT /purchase-orders/:poId/mark-as-submitted`)
Simple status transition: sets `status = "Submitted"`. No inventory changes.

### Validating CSV Variants (`POST /purchase-orders/warehouses/:warehouseId/validate-variants`)
Used by the frontend before PO creation to pre-validate a CSV upload:
1. Fetch all variant records for given SKUs in one query.
2. Fetch all `WarehouseVariant` records for given warehouse.
3. For each row: check SKU exists, no duplicates, quantity > 0, SKU is present in warehouse.
4. Returns `validRows` and `invalidRows` arrays with specific error messages per row.

---

## Status Lifecycle

```
(created) → Draft → Submitted → Partially Received → Received
                              ↘ Cancelled
```

| Status | When |
|---|---|
| `Draft` | Default on creation |
| `Submitted` | Manually set via `mark-as-submitted` endpoint |
| `Partially Received` | When some but not all variant quantities have been received |
| `Received` | When all variants have been fully received (`quantity_received === quantity_total` for all) |
| `Cancelled` | Can be set directly (no dedicated endpoint — via general update) |

---

## Interactions with Other Domains

| Domain/Service | How |
|---|---|
| **Inventory (WarehouseVariant)** | Warehouse stock incremented on `mark-as-received`; upserts by `(warehouse_id, variant_fk_id)` |
| **Variants/Products** | Line items reference variants; product images returned in list view |
| **Country/Warehouse** | PO is scoped to a specific country and warehouse |
| **Users** | Creator recorded for audit |

---

## Constraints and Rules

1. **`quantity_received` cannot exceed `quantity_total`** — enforced in `markAsReceived` before any DB writes (returns 400 if violated).
2. **Editing a PO resets receiving progress** — `updatePurchaseOrder` destroys all `POVariant` rows and recreates them with `quantity_received = 0`. Do not update a PO that is partially received unless intended.
3. **SKU or ID accepted for line items** — controller resolves SKUs before writing.
4. **PO_ID sequential numbering** — based on latest record by `createdAt`; concurrent creates under high load could theoretically produce the same ID attempt (no row-level lock on the read, though `PO_ID` is `unique` which will cause a DB error on collision).
5. **Warehouse stock can never go below 0** — `Math.max(0, existing + received)` is enforced.
6. **No link to customer orders** — POs are purely supply-chain / inventory management records.
7. **Full rollback on error** for create, update, and mark-as-received operations.
