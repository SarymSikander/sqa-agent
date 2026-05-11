# Shared — Business Rules

Business rules enforced in code, not just convention.

---

## Order Lifecycle Rules

### CSV Upload
- `payment_mode` must be `"COD"` — no other value accepted (case-insensitive)
- `quantity` must be integer ≥ 1
- All monetary values (`price`, `total_amount`) must be ≥ 0
- `shipping_charges` and `Discount` are optional

### Order Approval (bulk approve flow)
- Phone number must match country-specific digit length from `countryData`
- City must be in the hardcoded `validCitiesByCountry` list for the order's country
- If `payment_method === "paid"`, `total_cost` must be ≤ 0
- Countries validated: UAE, Saudi Arabia, Kuwait, Qatar, Pakistan, Oman, Bahrain, Iraq, USA

### Order Status Display
The raw status from DB maps to a display name:
| DB status | Display label |
|-----------|--------------|
| `"All Orders"` | All Orders |
| `"Confirmation Pending"` | Confirmation Pending |
| `"Approved"` | Approved |
| `"Dispatching in Process"` | Dispatching in Process |
| `"In Delivery"` | **Shipped** _(renamed in UI)_ |
| `"Undelivered"` | Undelivered |
| `"Delivered"` | Delivered |
| `"Return in Transit"` | Return in Transit |
| `"Return"` | Return |
| `"Cancelled"` | Cancelled |

### Initial order statuses (for new orders entering the system)
| Status constant | Value |
|----------------|-------|
| `ORDER_STATUS.RECEIVED` | `"Received"` |
| `ORDER_STATUS.PRE_APPROVAL_PROCESSING` | `"Confirmation Pending"` |

### Sub-status constants
| Constant | Value |
|---------|-------|
| `ORDER_SUBSTATUS.PENDING_RESELLER` | `"Pending Reseller Submission"` |
| `ORDER_SUBSTATUS.IN_QUEUE` | `"Confirmation in Process"` |

### Order tag constants
| Constant | Value |
|---------|-------|
| `ORDER_TAGS.AWAITING_PUSH` | `"Awaiting Push To Zambeel"` |
| `ORDER_TAGS.CONFIRMATION_REQUIRED` | `"Message Sent"` |
| `ORDER_TAGS.NO_CONFIRMATION_REQUIRED` | `"Send Message"` |

### Approval status mapping (`constants/order.constants.js`)
When an order is approved, it transitions through:
1. `{ status: "Approved", substatus: "Checking Inventory For Dispatching", tag: "Checking Inventory" }`
2. `{ status: "Approved", substatus: "Inventory In Transit", tag: "Calculating Dispatching Time" }`

---

## Dispatch Batch Rules

- Tracking ID generation `mode` must be `"All"` or `"Missing"`
- Valid `tracking_status` values: `"New"`, `"Generating"`, `"Partial"`, `"Generated"`, `"Failed"`
- Documents can only be downloaded when `tracking_status === "Generated"`
- Warning shown if batch is currently generating (status `"Generating"`) — cannot re-trigger

---

## Ticketing: Category → Team Mapping (`constants/ticket.constants.js`)

| Category | Assigned Team |
|----------|--------------|
| Order Changes & Updates | AM Team |
| Product Complaint | OP Team |
| Order Issue | AM Team |
| Delivery Complaint | NDR Team |
| Promotional & Marketing | AM Team |
| Payment & Financial | AM Team |
| Technical & Website | AM Team |
| General Inquiry | AM Team |
| Account Management | AM Team |

### Categories that require an order to be linked
- "Order Changes & Updates"
- "Product Complaint"
- "Delivery Complaint"
- "Order Issue"

### Category → Sub-category mapping (9 categories, selected sub-categories)
| Category | Sub-categories |
|----------|---------------|
| Order Changes & Updates | Address Update, Cancellation Request, Product Change, Payment Method Change, Quantity Change, Other |
| Product Complaint | Wrong Product, Damaged Product, Missing Item, Quality Issue, Other |
| Order Issue | Late Delivery, Not Received, Partial Delivery, Other |
| Delivery Complaint | Wrong Address Delivered, Damaged on Delivery, Missing Items, Other |
| Promotional & Marketing | Discount Code Issue, Promotional Offer, Other |
| Payment & Financial | Payment Failure, Refund Request, Billing Issue, Other |
| Technical & Website | Website Error, App Issue, Login Problem, Other |
| General Inquiry | Product Inquiry, Shipping Info, Return Policy, Other |
| Account Management | Account Setup, Password Reset, Profile Update, Other |

---

## User / Auth Rules

### First-time user detection
`useAuthStore.isFirstTimeUser()` returns `true` if the user's `createdAt` is within the last 24 hours.

### Role definitions
| Role | Portal | Capabilities |
|------|--------|-------------|
| `Admin` | OMS | Full access — all pages and actions |
| `Agent` | OMS | Orders page + Ticketing only; no admin-only pages |
| `Seller` | Seller portal | Own orders, products, payments, inventory |
| `Agency` | Agency portal + Seller proxy | Agency commission hub, team, merchants; can proxy as a seller's store |

### Agency proxy mode
When `useAgencyViewStore.isAgencyView === true`, the HTTP client automatically injects `x-agency-context-store-id: <storeId>` header on every protected request. This allows agency users to act as a specific merchant store.

### Gold plan check
`useGoldPlanStore.isGoldPlanActive` determines access to Gold-plan-only features (e.g. Dispatch Batches sidebar item: `goldSellerOnly: true`).

---

## Store Rules

- A seller cannot create a store without at least one primary bank account
- Store names must be unique (the `GET /store-names` endpoint checks availability)

---

## SKU Validation
- Backend: SKU must be 3–50 characters (trimmed)
- Frontend: Duplicate SKUs cannot be added to the same order

---

## Inventory

### Cron Jobs
| Schedule | Timezone | Job |
|----------|----------|-----|
| `0 2 * * *` | Asia/Karachi (PKT, UTC+5) | `calculateProductRatios()` + `calculateStoreRatios()` |
| `*/5 * * * *` | System time | `recoverStuckOrders()` |

### Stuck order recovery
Every 5 minutes, `recoverStuckOrders()` worker runs to detect and recover orders stuck in intermediate states.

### Delivery ratio calculation
Runs at 2:00 AM PKT daily. Calculates delivery ratios for products and stores — used for the ratings/threshold system.

---

## Agency Registration

- Agency IDs auto-generated: prefix `"ZMB-AG-"` + 6 random alphanumeric chars
- Up to 12 retries for uniqueness
- Applications go through states: Pending → Approved/Rejected/On Hold
- Admin actions: `approve`, `reject`, `hold`, `revoke`, `revert_to_pending`
- Agency merchant connection actions: `accept`, `reject`, `disconnect`, `reconnect`

---

## File Upload Limits

- General file upload: **5MB max** (`"File size exceeds 5MB limit"`)
- CSV upload: separate size limit (shows `"CSV file size limit exceeded"`)
- Presigned URL upload type for tickets: `fileType: 'ticket'`

---

## Order Actions Log

Order activity is tracked with these action types (`constants/logActions.constants.js`):
- `VARIANT_UPDATE` — product variant changed
- `ORDER_UPDATE` — order metadata changed
- `PRODUCT_ADDED` — product added to order
- `PRODUCT_REMOVED` — product removed from order
- `STATUS_UPDATE` — order status changed
- `TAG_UPDATE` — order tag changed
- `IMILE_WEBHOOK_STATUS_UPDATE` — iMile courier webhook updated status
