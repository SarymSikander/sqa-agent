# Products Domain — Business Logic

## What This Domain Does

The products domain manages the product catalog that sellers can browse and order from. Products have variants (each with a SKU, price, and inventory attributes). The domain exposes:

- A generic product list (all products with variants, used internally).
- A **Gold Products** catalogue — a curated tier of premium Zambeel-managed products that sellers can add to their stores.
- A **Featured Products** list — up to 3 pinned products shown on the seller dashboard.

Products are synced in from e-commerce integrations (Shopify, LightFunnels, etc.) via webhooks. The products controller itself is read-oriented; mutations come from the integration layer.

---

## Key Endpoints

Routes are mounted at `/products`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/products` | none | All products with variants (search supported) |
| GET | `/products/gold-products` | `verifySeller` | Paginated Gold-tier product catalogue with filters |
| GET | `/products/gold-product/:id` | none | Single Gold product detail with variant colors and description |
| GET | `/products/featured` | none | Up to 3 featured products for the dashboard |
| POST | `/products/featured` | `verifySeller` | Replace the featured products list (max 3) |

There is also a `productsWebhookRoutes` sub-router mounted at `/products/` (handles inbound product webhook payloads from integrations).

---

## Business Logic

### Get All Products (`GET /products`)

- Fetches all `Product` rows with their `Variant` associations.
- `?search=term` applies a broad LIKE filter across all Product columns (including id, title, vendor, etc.).
- No pagination — returns everything. Intended for internal/admin use or small catalogues.

### Get Gold Products (`GET /products/gold-products`)

Gold products are variants where `product_tier = 'Gold'` on an active product (`product.status = 'active'`).

**Filters (all optional, query params):**
- `search` — product title LIKE match
- `minPrice` / `maxPrice` — variant price range
- `availableIn` — comma-separated location strings; matched against `variant.inventory_location` (normalized)
- `page` / `limit` (default 6 per page)

**Step-by-step:**
1. Fetch all Gold variants with their products and warehouse-variant-country chain.
2. For each variant, build a set of normalized `inventory_location` values. Filter out variants that don't match `availableIn` if that filter is set.
3. Group variants by `product.id`, deduplicate countries and locations.
4. Compute the listing "From" price using only `owner = 'Zambeel'` variants that have a non-zero price and a SKU.
5. Paginate the grouped product list.
6. Batch-fetch images for the page's product IDs and attach them.
7. Return `availableInOptions` (all distinct locations for the filter UI).

**Owner priority for price display:** only `owner = 'Zambeel'` variants contribute to the listing price. Reseller variants are shown in the detail view but not used for the card price.

### Get Gold Product Detail (`GET /products/gold-product/:id`)

- Loads a single active product with Gold variants.
- Strips HTML from `body_html` using `cheerio` — removes boilerplate labels (product name, "About Product:", "Features:") to extract plain-text description.
- Filters variants to `owner` in `['Zambeel', 'Zambeel-Exclusive Product']` for display. Falls back to all variants if none match.
- Infers `color` from variant title by splitting on `/` and taking the last segment.
- Sorts variants: `Zambeel` first, then `Zambeel-Exclusive Product`, then others.
- Returns: product metadata, cleaned description, images (ordered by position), `colorVariants` array, `availableCountries`.

### Featured Products (`GET /products/featured`)

- Returns up to 3 `FeaturedProduct` rows ordered by `display_order ASC`.
- Each record joins `Product → Variant (first 1) + Image (first 1 by position)`.
- Price shown is `sale_price` if set, otherwise `price`.

### Update Featured Products (`POST /products/featured`)

- Body: `{ productIds: [id1, id2, id3] }` (max 3 implied by the `limit: 3` on GET).
- Validates all IDs exist in `products`.
- Deletes all existing `FeaturedProduct` rows, bulk-creates new ones with `display_order = index + 1`.

---

## Key Model Fields

### `products`
| Field | Type | Notes |
|-------|------|-------|
| `product_id` | STRING | External ID from the integration (Shopify product ID etc.) |
| `store_id` | INTEGER | FK → stores (nullable for catalogue products) |
| `title` | STRING | Product name |
| `body_html` | TEXT | HTML description (stripped to plain text in API responses) |
| `vendor` | STRING | Brand/vendor name |
| `status` | STRING | `active`, `draft`, `archived` (free text) |
| `handle` | STRING | URL slug |
| `visibility` | BOOLEAN | Default `true` |
| `has_variants` | BOOLEAN | Default `false` |
| `published_at` | DATE | When published on the integration |

### `variants`
| Field | Type | Notes |
|-------|------|-------|
| `product_id` | INTEGER | FK → products |
| `fk_owned_by` | INTEGER | FK → users (seller who owns this variant; null for Zambeel-owned) |
| `owner` | ENUM | `Zambeel`, `Reseller-3PL`, `Reseller-360`, `Zambeel-Exclusive Product`, `Zambeel Financing` |
| `product_tier` | STRING | `Gold` for premium products; other values possible |
| `sku` | STRING | Stock-keeping unit code |
| `price` | DECIMAL(10,2) | Listed price |
| `sale_price` | DECIMAL(10,2) | Discounted price (nullable) |
| `pixel_price` | DECIMAL(10,2) | Price for ad pixel reporting (nullable) |
| `in_cart` | BOOLEAN | Default `false` |
| `track_inventory` | BOOLEAN | Default `true` |
| `inventory_quantity` | INTEGER | Denormalized quantity (may differ from warehouse_variants sum) |
| `inventory_location` | STRING | Free-text location label used for Gold product filtering |
| `dispatching_time` | STRING | Estimated dispatch window |
| `ships_from` | STRING | Origin location text |
| `gold_product_status` | STRING | Status label for Gold programme |
| `market_saturation` | STRING | Merchandising signal |
| `expected_roas` | STRING | Expected return on ad spend |
| `option1_name` / `option1_value` | STRING | First variant option (e.g. Color / Red) |
| `option2_name` / `option2_value` | STRING | Second variant option |
| `option3_name` / `option3_value` | STRING | Third variant option |
| `variant_id` | STRING | External variant ID from integration |

---

## Inter-Domain Interactions

- **Inventory**: `WarehouseVariant` records hang off variants — the inventory domain reads these; the products domain only reads warehouse/country info for display.
- **Orders**: `OrderProductVariant` links orders to variants (M:M through join table).
- **Purchase Orders**: `POVariant` links POs to variants.
- **Return Orders**: `ReturnOrdersVariant` links return orders to variants.
- **Images**: `Image` model has `product_id` FK; used in gold product listing and detail.
- **Stores**: Products can be scoped to a store via `store_id`.
- **Integrations (Shopify, LightFunnels, etc.)**: Products are created/updated via webhook routes mounted on the same `/products` router. The products controller only reads.

---

## Important Constraints

- **Gold products** require `product_tier = 'Gold'` on the variant AND `status = 'active'` on the product. An inactive product's Gold variants will not appear.
- **Price calculation for Gold listings** uses only `owner = 'Zambeel'` variants. If no Zambeel-owned variant has a price, the listing shows `0.00`.
- **Featured products** are replaced atomically — the `POST /featured` endpoint deletes all existing featured records before inserting the new set. There is no partial update.
- Variant `owner` drives a lot of display logic — `Zambeel-Exclusive Product` variants are shown on the detail page but excluded from the listing card price.
- `inventory_location` is a free-text field and is normalized (case/trim) before comparison in the Gold products filter.
