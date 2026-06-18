# Inventory Domain — Business Logic

## What This Domain Does

The inventory domain tracks the physical stock of product variants across warehouses. It has two layers:

1. **Admin Inventory Movement** (`/inventory-movements`) — admin-only operations that physically move stock between warehouses or between SKUs, and log damaged goods.
2. **Seller Inventory View** (`/inventory`) — seller-facing read-only view of their own variant stock with computed metrics.

Stock quantity is maintained in the `warehouse_variants` join table (variant × warehouse). All mutations are atomic Sequelize transactions with negative-stock prevention at the database level.

---

## Key Endpoints

### Admin: `/inventory-movements` (all require `verifyAdminOnly`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/inventory-movements/transactions` | Create one or more inventory movement transactions |
| POST | `/inventory-movements/damaged-bin` | Move stock into the damaged bin (write-off) |
| POST | `/inventory-movements/find-variant` | Look up a variant by SKU within a specific warehouse |
| GET  | `/inventory-movements/warehouses` | List all warehouses (sorted by name) |
| GET  | `/inventory-movements/movements` | Paginated list of all movements (transactions + damaged) |
| PUT  | `/inventory-movements/transactions/:id/receive` | Mark a WAREHOUSE_TRANSFER as received and credit destination stock |

### Seller: `/inventory` (all require `verifySeller`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/inventory/seller-inventory` | Paginated inventory list for the authenticated seller |
| GET | `/inventory/seller-inventory/export` | CSV export of seller inventory (requires 360 or 3PL store bifurcation) |
| GET | `/inventory/purchase-order/:variantId` | All POs that have received quantity for a variant |
| GET | `/inventory/purchase-order/orders/:variantId` | Delivered orders for a variant filtered by country |
| GET | `/inventory/inventory-movements/:variantId` | All movement history for a variant owned by the seller |

---

## Business Logic

### Creating Inventory Transactions (`POST /inventory-movements/transactions`)

Accepts an array of entries. Each entry specifies:
- `from_variant_id`, `to_variant_id` (optional for WAREHOUSE_TRANSFER)
- `source_warehouse_id`, `destination_warehouse_id`
- `movement_type`: `SKU_TO_SKU` or `WAREHOUSE_TRANSFER`
- `quantity`
- `reason` (see allowed values below)

**Step-by-step:**
1. Validate that both from/to variants exist.
2. For `SKU_TO_SKU`: `source_warehouse_id` is required.
3. Confirm both variants are registered in their respective warehouses via `warehouse_variants`.
4. Accumulate total deductions per `warehouse_variants.id` and check against current `quantity` — throws `INSUFFICIENT_STOCK` if exceeded.
5. Generate sequential movement numbers prefixed `MOVE-` (zero-padded to 4 digits, e.g. `MOVE-0003`). Numbers are assigned atomically inside the transaction by scanning existing numbers.
6. Atomically update `warehouse_variants.quantity`:
   - **Source**: `quantity - totalDeduction` with `WHERE quantity >= totalDeduction` to prevent negatives. Zero-affected-rows → throws `INSUFFICIENT_STOCK`.
   - **Destination (SKU_TO_SKU only)**: `quantity + totalAddition`.
7. Create `InventoryTransaction` rows. Initial status:
   - `WAREHOUSE_TRANSFER` → `In Transit`
   - `SKU_TO_SKU` → `Received` (immediately sets `received_quantity = quantity`)
8. Log each creation to `InventoryTransactionLog` with action `Create Transaction`.

### Creating Damaged Bin Movements (`POST /inventory-movements/damaged-bin`)

- Query param `receiveFlow=true` skips stock deduction (used when recording damage during a receive operation).
- Otherwise: same deduction logic as transactions — accumulate deductions per warehouse_variant, atomic update with negative-stock guard.
- Movement numbers prefixed `DAMAGE-` (e.g. `DAMAGE-0001`).
- Creates `DamagedBinMovement` + `InventoryTransactionLog` row with action `Moved to Damaged Bin`.

### Receiving a Warehouse Transfer (`PUT /inventory-movements/transactions/:id/receive`)

- Only valid when transaction `status` is `In Transit`. Throws if already `Received`.
- `quantity_received` must not exceed `transaction.quantity`.
- Increments `warehouse_variants.quantity` at the destination warehouse by `quantity_received`.
- Sets transaction `status → Received`, `received_quantity = quantity_received`.
- Logs action `Received Quantity` with previous/new received quantity in meta.

### Listing Movements (`GET /inventory-movements/movements`)

Merges `InventoryTransaction` and `DamagedBinMovement` records in memory, sorts by `createdAt DESC`, then paginates. Supports filters:
- `movement_id` (movement number string)
- `sku` (matches from or to variant)
- `warehouse_name`
- `status` (only applies to transactions; damaged movements have no status)
- `type` (`SKU_TO_SKU`, `WAREHOUSE_TRANSFER`, or `DAMAGED`)
- `start_date` / `end_date`

Damaged movements appear with `movement_type: 'DAMAGED_BIN_MOVEMENT'` in the merged response.

### Seller Inventory View (`GET /inventory/seller-inventory`)

- Fetches variants owned by the requesting user (`fk_owned_by = userId`).
- Supports search by SKU, product title, or country name.
- Checks if any of the seller's stores has `bifurcation` in `['360', '3PL']` — sets `inventoryDisplay` flag that the frontend uses to decide whether to show inventory columns.
- Computes per-variant metrics via `loadSellerInventoryMetrics`:
  - `totalReceivedPO` = sum of `po_variants.quantity_received` + inward `Received` transactions
  - `inventoryMovement` = outward SKU_TO_SKU + WAREHOUSE_TRANSFER + damaged quantities
  - `orderStatusCounts` — counts of orders in each delivery status for this variant
  - `totalWarehouseQuantity` — sum of current `warehouse_variants.quantity`

### CSV Export (`GET /inventory/seller-inventory/export`)

- Only allowed if seller has a store with `bifurcation` in `['360', '3PL']` — returns 403 otherwise.
- Exports all variants (no pagination) with columns: Product Name, SKU Code, Warehouse, Total Received, Inventory Movement, Inventory in Warehouse, Dispatching in Process, In transit, Delivered, Undelivered, Returning in Transit.

---

## Key Model Fields

### `inventory_transactions`
| Field | Type | Values / Notes |
|-------|------|----------------|
| `movement_type` | ENUM | `SKU_TO_SKU`, `WAREHOUSE_TRANSFER` |
| `status` | ENUM | `In Transit`, `Received` |
| `reason` | ENUM | `SKU Merge`, `Wrong SKU Mapping`, `Repackaging`, `Services Deal`, `Variant Consolidation`, `Internal Adjustment`, `Demand Fulfillment`, `Purchase Transfer` |
| `movement_number` | STRING | Format: `MOVE-NNNN` |
| `quantity` | INTEGER | Min 1 |
| `received_quantity` | INTEGER | Nullable; set on SKU_TO_SKU creation or on WAREHOUSE_TRANSFER receive |

### `warehouse_variants`
| Field | Type | Notes |
|-------|------|-------|
| `warehouse_id` | INTEGER | FK → warehouse |
| `variant_fk_id` | INTEGER | FK → variants |
| `quantity` | INTEGER | Default 0; min 0 (DB validation); unique composite key (warehouse_id, variant_fk_id) |

### `warehouse`
| Field | Type | Notes |
|-------|------|-------|
| `name` | STRING | Display name |
| `fk_country_id` | INTEGER | FK → countries |

### Damaged Bin Movement (table: `damagedBinMovements`)
| Field | Notes |
|-------|-------|
| `movement_number` | Format: `DAMAGE-NNNN` |
| `fk_warehouse_id`, `fk_variant_id`, `fk_moved_by` | FKs |
| `quantity`, `reason` | Free-form reason string |

---

## Inter-Domain Interactions

- **Purchase Orders**: `po_variants.quantity_received` feeds into `totalReceivedPO` metrics.
- **Orders**: `order_product_variants` + `orders.status` JSON field used to compute `orderStatusCounts`.
- **Stores**: `stores.bifurcation` gates CSV export and the `inventoryDisplay` flag.
- **Variants / Products**: Inventory is keyed on `variants.id`; the seller inventory view joins `product.title`.
- **Users**: `fk_moved_by` on every movement row; proxy context (`req.proxyContext.merchantUserId`) allows admin/agency to act as a seller.

---

## Important Constraints

- **Negative stock is impossible**: all deductions use `WHERE quantity >= deduction` — if 0 rows affected, the whole transaction rolls back.
- **Admins only** can create transactions, damaged movements, and receive quantities.
- **WAREHOUSE_TRANSFER** starts `In Transit`; must be explicitly received via the `/receive` endpoint to credit destination stock.
- **SKU_TO_SKU** is immediately `Received` and both source deduction and destination addition happen in the same transaction.
- The `receiveFlow=true` flag on damaged-bin bypasses deduction — intended for damage recorded at the time of a physical receive, not a separate action.
- Proxy context (`req.proxyContext`) is honored in seller inventory and transaction creation so agents can act on behalf of a merchant.
