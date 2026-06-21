# Seller Portal — Pages Reference

## Route Map

| Route | Component | Purpose |
|-------|-----------|---------|
| `/get-started` | `GetStartedPage` | Onboarding landing page (post-login) |
| `/get-started/dropshipping` | `GetStartedPage` | Dropshipping onboarding flow |
| `/get-started/zambeel-360` | `GetStartedPage` | Zambeel 360 onboarding flow |
| `/get-started/3pl-services` | `GetStartedPage` | 3PL services onboarding flow |
| `/dashboard` | `DashBoard` | Seller analytics dashboard |
| `/orders` | `SellerOrdersPage` | Seller's own orders — unprocessed + processed |
| `/orders-analytics` | `OrdersAnalyticsPage` | Charts and trend analysis |
| `/products` | `ProductsPage` | Seller's product catalog |
| `/gold-products` | `GoldProductListing` | Browse gold-tier product catalog (Gold plan required) |
| `/gold-products/:id` | `GoldProductDetailsPage` | Single gold product detail |
| `/gold-subscription` | `GoldSubscriptionPage` | Subscribe/view gold plan status |
| `/stores/integration` | `StoreIntegrations` | Connect/manage e-commerce stores |
| `/settings` | `Settings` | Bank account management (payment vault) |
| `account/:id` | `PaymentMethodDetailsPage` | Single payment method detail |
| `/payments` | `Payments` | Payment history and COD settlements |
| `/payment-status` | `PaymentStatus` | Payment transaction result |
| `/seller/inventory` | `SellerInventoryPage` | Inventory levels per SKU |
| `/my-invoices` | `Invoices` | Zambeel invoices for seller |
| `/ticketing` | `Ticketing` | Support ticket management |
| `/profile` | `Profile` | User profile (username, phone, country, colors) |
| `/academy` | `AcademyPage` | Zambeel Academy (English) |
| `/zambeel-academy-arabic` | `AcademyArabicPage` | Academy (Arabic) |
| `/zambeel-academy-urdu` | `AcademyUrduPage` | Academy (Urdu) |
| `/shopify/bind` | `ShopifyBind` | Bind Shopify store OAuth modal |
| `/lightfunnels/bind` | `LightFunnelsBind` | LightFunnels OAuth bind page — store selection + confirm after redirect from `/lightfunnels/oauth/callback` |
| `/woocommerce/callback` | `WooCommerceCallbackPage` | WooCommerce OAuth callback landing page — shows success/error state, refreshes connected stores |
| `/gold-subscription/subscription` | `GoldSubscriptionSubscriptionPage` | Gold plan subscription management (plan selection sub-page) |
| `/gold-subscription/products` | `GoldSubscriptionProductsPage` | Gold subscription product catalog sub-page |
| `/notifications` | `NotificationsPage` | Seller broadcast notification inbox — category filter, read/unread tracking, mark-all-read |

---

## Page-by-Page Detail

### Orders Page (`/orders`)

**Page Title:** "Orders Dashboard" (translated)

**Two sections:**
1. "Your Store Orders" — orders not yet processed to Zambeel (unprocessed)
   - Sub-text: "Orders which are not yet processed to Zambeel."
   - Badge: unprocessed count
2. "Orders with Zambeel" — orders sent to Zambeel for fulfillment
   - Sub-text: "Orders that have been processed to Zambeel"
   - Badge: processed count

**Unprocessed Orders Table Column Headers:**
- (checkbox) | Order Number | Customer Name | Total Amount | Phone Number | Country | City | Order Date
- If viewing "all stores": includes `Store` column

**Unprocessed Orders Actions:**
- `Send To Zambeel` (blue, disabled if none selected)
- `Delete` / `Delete Order` / `Delete Orders` / `Deleting...` (red)

**Processed Orders Table Column Headers:**
- Order ID | Customer Name | Total Amount | Phone Number | City | Country | Status | Order Date | Courier name | Courier tracking ID | Actions

**Processed Orders — Actions column:**
- `Ticket` button (Ticket icon, sm size) → opens CreateTicketModal

**Filter Controls (Processed Orders):**
| Field | Type | Options/Placeholder |
|-------|------|---------------------|
| Country | Dropdown | "Select a country" → All Countries + each country |
| Status | Dropdown | "Select Status" → All Statuses |
| Sub-Status | Dropdown | "Select Sub-Status" → All Sub-Statuses |
| Order ID | Text | "Search by Order ID" |
| Phone Number | Text | "Search by Phone" |
| Filter toggle | Icon button | Funnel icon |

**Filter Panel Buttons:** `Reset` | `Apply Filters`

**Pagination:** Show: 5/10/20/50 | Page: N of total | "Showing {{start}} to {{end}} of {{total}} entries"

**Copy Tracking ID:** `Copy` button → shows Check icon "Copied!" for 2 seconds after click

**Validation/Error Messages:**
- "Country" — missing field error
- "Phone Number" — missing field error
- "Phone Number must contain only digits"
- "Order Items" — missing variants error
- "Invalid Order item - SKU is missing"
- `Invalid Country "{{value}}" - Only Saudi Arabia, Qatar, Kuwait, United Arab Emirates, Pakistan, Oman, Bahrain, and Iraq are supported`
- "Gold subscription required for order processing"
- "{{count}} order failed processing."
- "{{count}} order processed successfully to Zambeel."
- "No orders selected for deletion"
- "{{count}} order deleted successfully"
- "{{count}} order failed to delete"
- "An error occurred while deleting orders"

---

### Ticketing Page (`/ticketing`)

**Page Title:** "Ticketing System"
**Subtitle:** "Manage and track support tickets"
**Button:** `Create New Ticket` (blue, Plus icon)

**Tabs (Seller view — left → right):**
- "Tickets Assigned by Zambeel"
- "Tickets Assigned to Zambeel"

**Ticket Table Columns:** TICKET ID | CATEGORY | SUB-CATEGORY | ORDER NUMBER | DATE | STATUS | ACTIONS

**Ticket ID Format:** `TKT-001`, `TKT-042` (padded to 3 digits)

**Stats Cards (5 cards):** Total Tickets | Pending | In Progress | Awaiting Seller Action | Resolved

**Search/Filter Fields:**
| Value | Label | Input |
|-------|-------|-------|
| `store_name` | "Store Name" | text — placeholder: "Search by store name..." |
| `store_id` | "Store ID" | text — placeholder: "Search by store ID..." |
| `status` | "Status" | select — TICKET_STATUS_OPTIONS |
| `team_id` | "Team ID" | select — teams list |

**Status Badge Classes:**
| Status | Tailwind |
|--------|----------|
| Pending | bg-yellow-100 text-yellow-800 border-yellow-200 |
| In Progress | bg-blue-100 text-blue-800 border-blue-200 |
| Awaiting Seller Action | bg-orange-100 text-orange-800 border-orange-200 |
| Resolved | bg-green-100 text-green-800 border-green-200 |

**Error/Empty States:**
- "No tickets assigned to Zambeel" + "Tickets assigned to Zambeel will appear here"
- "No tickets assigned by Zambeel" + "Tickets assigned by your team will appear here"
- "Failed to load tickets" + "Try Again" button
- "Loading tickets..."

---

### Seller Ticket Categories (Create Ticket Wizard)

**Wizard steps:** Select Store → Category & Type → Details & Files → Review

**Categories & Sub-categories:**

| Category | requiresOrderId | Sub-categories |
|----------|-----------------|---------------|
| Onboarding & Integration | false | Store integration failure; Cant find SKU of the product |
| Order Sending & Inventory Issue | false | Cannot send orders to Zambeel; Inventory Not Showing Correctly |
| Order Changes & Updates | true | Request to Cancel the order; Change Price; Change Quantity; Modify SKU (add/replace); Customer requested color/size change; Update address/phone; Expedite dispatch (order confirmed); Request to Reschedule; Initiate return; Order Proofs & Updates; Request to Open Parcel by Customer; Order is Prepaid |
| Product Complaint | true | Damaged/defective item delivered; Wrong item/SKU delivered; Missing item/parts; Product quality complaint (customer dissatisfied) |
| Delivery Complaint | true | Rider did not contact customer; Rider misbehaved |
| Payments & Invoices | false | Invoice not received; Invoice incorrect / needs correction; Payment not received; Short/partial payment received |

**File Upload Constraints:**
- Max files: 3
- Max size per file: 5 MB
- Allowed types: image/jpeg, image/jpg, image/png, image/gif, image/webp
- Error: "Maximum 3 files allowed"
- Error: "File {name} is too large. Maximum size is 5MB."
- Error: "File {name} is not supported. Only image files (JPG, JPEG, PNG, GIF, WebP) are allowed."

**Description:** min 10 chars, max 2000 chars

**Success Screen:** "Ticket Created Successfully!"

---

### Bank Accounts / Settings (`/settings`)

**Payment type options:** Bank Account | USDT | PayPal

**IBAN length rules by country:**
| Country | Length |
|---------|--------|
| Pakistan | 24 chars |
| UAE / Oman / Iraq | 23 chars |
| Bahrain | 22 chars |
| India | account number 9–18 digits + IFSC 11 chars |
| USA | account number 5–18 digits + SWIFT min 8 + FedWire min 9 |
| HK | 15–18 chars |
| Others | 20–32 alphanumeric |

**Payment thresholds:**
| Method | Country | Min Amount | Processing Time |
|--------|---------|-----------|----------------|
| Bank Transfer | UAE | 100 AED | 1-2 Business Days |
| Bank Transfer | KSA | 375 SAR | 2-3 Business Days |
| Bank Transfer | Pakistan | 1 AED | 1-2 Business Days |
| Bank Transfer | Others | 375 AED | 2-3 Business Days |
| Crypto (TRON-20) | — | 10 AED | Same day |
| PayPal | — | 375 AED | 1 Business Day |

---

### Store Integration (`/stores/integration`)

**Platforms:** Shopify | EasyOrder | Light Funnels | YouCan | Manual

**Manual Store Platforms (sub-type):** Facebook Marketplace | Amazon | Whatsapp Marketplace | Salla | Zid | Ebay

**Error Messages:**
- "Store Nick name already exists. Please choose a different name."
- "Unsupported integration type"
- "Failed to connect store"

---

### Profile (`/profile`)

**Editable fields:** username | phone_number | country | promo_code | sidebar_color | button_color

**Phone validation pattern:** `/^\+\d{10,15}$/` (international format, e.g. +9715012345678)

**Color validation:** `/^#[0-9A-Fa-f]{6}$/` (6-char hex)

---

### Notifications (`/notifications`)

**h1:** "Alerts & Notifications"

**Sub-text (unread):** "You have {{count}} unread notification(s)"
**Sub-text (all read):** "You're all caught up!"

**Category filter tabs:** All | Pricing | Inventory | Zambeel Updates | Payments

**Notification card fields:** Category badge | Title | Message | Sent date | Read/unread indicator
**Expand behavior:** Clicking a notification card marks it as read and expands the full message.

**Buttons:**
- `Mark all as read` (top-right; disabled when no unread, shows spinner during mutation)

**Confirm modal for mark-all-read:** "Are you sure you want to mark all notifications as read?"

**Empty states:**
- "No notifications" (per category filter)

**API calls:**
- `GET /broadcast-notifications?category=X` — fetches all notifications; sort: unread first, then newest
- `PATCH /broadcast-notifications/:recipientId/read` — on card expand/click
- `PATCH /broadcast-notifications/read-all` — on "Mark all as read"
- `GET /broadcast-notifications/unread-count` — on page mount (syncs bell badge)

---

### LightFunnels Bind (`/lightfunnels/bind`)

**Purpose:** Landing page after the LightFunnels OAuth2 callback. Seller arrives here after authorizing on LightFunnels' site.

**URL query params on arrival:** `fromLightFunnelsInstall=true&sessionId=<id>`

**Flow:**
1. Calls `GET /lightfunnels/oauth/check-user` — confirms seller is logged in + has primary bank account.
2. Calls `GET /lightfunnels/oauth/account?sessionId=X` — fetches pending LF account data + `stores[]`.
3. If `stores.length > 1`: shows store-selection dropdown.
4. Optionally calls `GET /lightfunnels/oauth/check-store-exists` — warns if store already connected.
5. Seller enters store display name, confirms store selection, submits.
6. Calls `POST /lightfunnels/oauth/bind-store` → on success: redirects to `/stores/integration`.

**Pre-requisite gate:** If seller has no primary bank account, shows blocking error before allowing bind.

---

### WooCommerce Callback (`/woocommerce/callback`)

**Purpose:** OAuth callback landing page after WooCommerce store authorization. No interactive elements — automatically refreshes the seller's connected stores and shows result.

**Success state:** Green checkmark icon, "Store Connected" message, button to go to Store Integrations.
**Error state:** Amber alert icon, error message from store refresh, button to retry or continue.

**API call on mount:** `fetchAllConnectedStores(userId)` — refreshes store list after WC bind completes.

---

### Payment Status (`/payment-status`)

**Purpose:** PayTabs payment result page. Arrived at after PayTabs redirect following a payment attempt.

**URL query params:** `tran_ref` (transaction reference) | `cart_id` | `error`

**States:**
- Loading (spinner) — while verifying payment
- Success — green checkmark, "Payment Successful" + transaction reference + amount
- Error — red X icon, error message

**On error param:** `missing_payment_details` → "Payment details are missing. Please contact support." | Other → "Payment processing error occurred. Please try again."

**API call:** `POST /payments/verify` with `tran_ref` + `cart_id`

---

### Payments (`/payments`)

Currently shows a "coming soon" placeholder. No functional content. Route exists but feature is pending.

**Placeholder text:** "comming soon" (h1, centered)
