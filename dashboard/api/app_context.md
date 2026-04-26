# Zambeel Platform — Comprehensive Technical Reference

> Generated from source: `zambeel-FE` and `zambeel-api`  
> Date: 2026-04-20

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack](#2-tech-stack)
3. [User Roles](#3-user-roles)
4. [Frontend Routes — Complete Map](#4-frontend-routes--complete-map)
5. [Portal Navigation Structures](#5-portal-navigation-structures)
   - 5.1 [Admin / Agent Portal (OMS)](#51-admin--agent-portal-oms)
   - 5.2 [Seller Portal](#52-seller-portal)
   - 5.3 [Agency Portal](#53-agency-portal)
6. [All Features by Portal](#6-all-features-by-portal)
   - 6.1 [Admin/Agent Features](#61-adminagent-features)
   - 6.2 [Seller Features](#62-seller-features)
   - 6.3 [Agency Features](#63-agency-features)
7. [All Forms — Fields & Validation Rules](#7-all-forms--fields--validation-rules)
8. [All User Flows — Step by Step](#8-all-user-flows--step-by-step)
9. [Role-Based Access Control](#9-role-based-access-control)
10. [Key Business Logic](#10-key-business-logic)
11. [Backend API Endpoints — Complete List](#11-backend-api-endpoints--complete-list)
12. [Store Integrations](#12-store-integrations)
13. [Webhook Integrations](#13-webhook-integrations)

---

## 1. System Overview

Zambeel is a B2B cross-border e-commerce and logistics platform serving the GCC region. It connects:

- **Sellers (Merchants)** — run dropshipping or 3PL stores, send orders, manage products and payments
- **Admins & Agents** — operations team that manages order fulfillment, courier assignment, inventory, invoicing
- **Agencies** — sales/growth agencies that connect to multiple sellers, earn commissions on delivered orders

Authentication is powered by **Firebase** (email/password and social OAuth). After Firebase auth, users get a JWT from the Zambeel API for all protected calls.

WhatsApp Support: **+971568472271**

---

## 2. Tech Stack

### Frontend (`zambeel-FE`)
| Layer | Technology |
|-------|-----------|
| Framework | React 18, TypeScript, Vite |
| Routing | React Router v7 (`createBrowserRouter`) |
| State | Zustand (with persist) |
| Server State | TanStack React Query (5-min stale time, 1 retry) |
| UI | Tailwind CSS, Flowbite React, Iconify |
| Forms | React Hook Form |
| Auth | Firebase SDK |
| i18n | react-i18next (English, Arabic RTL, Urdu) |
| PDF | jsPDF + jspdf-autotable |
| Real-time | Socket.io (SocketProvider wraps the app) |
| Toast | React Toastify (top-right, 3s, max 4) |

### Backend (`zambeel-api`)
| Layer | Technology |
|-------|-----------|
| Runtime | Node.js, Express |
| ORM | Sequelize |
| Validation | Joi |
| Auth | JWT + Firebase UID verification |
| Storage | AWS S3 |
| Queue | AWS SQS |
| PDF | (external courier/invoice services) |
| DB | PostgreSQL (implied by Sequelize config) |

---

## 3. User Roles

| Role | Description | Portal |
|------|-------------|--------|
| `Admin` | Full OMS access, can manage everything | OMS (`/orders-management/*`) |
| `Agent` | Limited OMS access (Orders + Ticketing only) | OMS (`/orders-management/*`) |
| `Seller` | Merchant seller account | Seller (`/dashboard`, `/orders`, etc.) |
| `Agency` | Agency account (seller that registered an agency) | Both Seller + Agency (`/agency/*`) |

Role guards are enforced both on the frontend (route guards) and on every backend route (JWT middleware with role check).

---

## 4. Frontend Routes — Complete Map

### Public Routes (no auth required — `PublicLayout`)

| Path | Component | Purpose |
|------|-----------|---------|
| `/login` | `Login` | Firebase email/password + social login |
| `/register` | `Register` | New seller registration |
| `/forgot-password` | `ForgotPassword` | Password reset |
| `/verify-email` | `VerifyEmail` | Email verification landing page |
| `/profile-completion` | `ProfileCompletion` | Finish profile after social sign-in |
| `/agency/invite` | `AgencyInviteAccept` | Accept agency team invitation (token-based) |
| `/subscription/shopify-callback` | `ShopifyCallbackPage` | Shopify billing subscription OAuth callback |
| `/terms` | `Terms` | Terms of service page |
| `*` | `NotFound` | 404 fallback |
| `/` | `RootRedirect` | Redirects to appropriate portal based on role |

### Seller Portal Routes (auth required — `SellerProtectedRoute` → role: `Seller` or `Agency` — `RootLayout`)

| Path | Component | Purpose |
|------|-----------|---------|
| `/dashboard` | `DashBoard` | Seller analytics dashboard |
| `/orders` | `SellerOrdersPage` | Seller's own orders list & management |
| `/orders-analytics` | `OrdersAnalyticsPage` | Order analytics charts/reporting |
| `/products` | `ProductsPage` | Seller's product catalog |
| `/gold-products` | `GoldProductListing` | Browse gold-tier product catalog |
| `/gold-products/:id` | `GoldProductDetailsPage` | Single gold product detail |
| `/gold-subscription` | `GoldSubscriptionPage` | Subscribe to gold plan |
| `/stores/integration` | `StoreIntegrations` | Connect/manage e-commerce stores |
| `/settings` | `Settings` | Bank account management (payment vault) |
| `account/:id` | `PaymentMethodDetailsPage` | Single payment method detail |
| `/payments` | `Payments` | Payment history & COD settlements |
| `/payment-status` | `PaymentStatus` | Payment transaction result page |
| `/seller/inventory` | `SellerInventoryPage` | View own inventory levels |
| `/my-invoices` | `Invoices` | View/download Zambeel invoices |
| `/ticketing` | `Ticketing` | Create and view support tickets |
| `/profile` | `Profile` | User profile page |
| `/get-started` | `GetStartedPage` | Onboarding landing page |
| `/get-started/dropshipping` | `GetStartedPage` | Dropshipping onboarding flow |
| `/get-started/zambeel-360` | `GetStartedPage` | Zambeel 360 onboarding flow |
| `/get-started/3pl-services` | `GetStartedPage` | 3PL services onboarding flow |
| `/academy` | `AcademyPage` | Zambeel Academy (English) |
| `/zambeel-academy-arabic` | `AcademyArabicPage` | Zambeel Academy (Arabic) |
| `/zambeel-academy-urdu` | `AcademyUrduPage` | Zambeel Academy (Urdu) |
| `/shopify/bind` | `ShopifyBind` | Bind Shopify store OAuth modal |

### Agency Routes (auth required — `SellerProtectedRoute` + `AgencyApprovedRoute` — `RootLayout`)

| Path | Component | Guard | Purpose |
|------|-----------|-------|---------|
| `/agency` | `AgencyPage` | SellerProtected only | Agency registration/status dashboard |
| `/agency/application-submitted` | `ApplicationSubmittedPage` | SellerProtected only | Application submitted confirmation |
| `/agency/portal/commission` | `AgencyCommissionHub` | SellerProtected + ApprovedAgency | Commission overview & invoices |
| `/agency/portal/team-members` | `AgencyTeamMembers` | SellerProtected + ApprovedAgency | Manage agency team |
| `/agency/portal/merchants` | `AgencyMerchants` | SellerProtected + ApprovedAgency | Manage connected merchants |
| `/agency/portal/settings` | `AgencySettingsPage` | SellerProtected + ApprovedAgency | Agency profile settings |

### Admin / Agent Portal Routes (auth required — `ProtectedRoute` → role: `Admin` or `Agent` — `FullLayout`)

| Path | Component | Role Required | Purpose |
|------|-----------|--------------|---------|
| `/orders-management/dashboard` | `OrdersDashBoard` | Admin/Agent | OMS analytics dashboard |
| `/orders-management/orders` | `Orders` | Admin/Agent | All orders management |
| `/orders-management/dispatch-batches` | `DispatchBatches` | Admin/Agent | Courier dispatch batch management |
| `/orders-management/agents` | `AgentsTable` | Admin/Agent | Manage agent accounts |
| `/orders-management/ratings-settings` | `ThresholdManager` | Admin/Agent | Configure seller rating thresholds |
| `/orders-management/stores-settings` | `OmsStoreSettingsPage` | Admin/Agent | View/edit all stores |
| `/orders-management/tags-management` | `TagsManagementPage` | Admin/Agent | Manage order tags |
| `/orders-management/purchase-orders` | `PurchaseOrdersPage` | Admin/Agent | IMS purchase order list |
| `/orders-management/purchase-orders/create` | `CreatePurchaseOrderComponent` | Admin/Agent | Create new purchase order |
| `/orders-management/purchase-orders/:poId/receive` | `ReceiveItemsComponents` | Admin/Agent | Receive items against PO |
| `/orders-management/purchase-orders/:poId/submit` | `SubmitPurchaseOrderComponent` | Admin/Agent | Submit PO to warehouse |
| `/orders-management/return-orders` | `ReturnOrdersPage` | Admin/Agent | IMS return order list |
| `/orders-management/return-orders/create` | `CreateReturnOrderComponent` | Admin/Agent | Create new return order |
| `/orders-management/ticketing` | `TicketingV2` | Admin/Agent | Admin ticket queue |
| `/orders-management/inventory-movements` | `InventoryMovements` | Admin/Agent | Warehouse inventory movements |
| `/orders-management/gold-subscriptions` | `OMSGoldSubscriptionsPage` | Admin/Agent | Manage seller gold subscriptions |
| `/orders-management/agency-registrations` | `AgencyRegistrationsPage` | Admin/Agent | Review agency applications |
| `/orders-management/commission-models` | `CommissionModelsPage` | Admin/Agent | Manage agency commission models |
| `/orders-management/invoice-upload` | `InvoiceUploadPage` | Admin/Agent | Upload invoices for sellers |
| `/orders-management/invoice-update` | `InvoiceUpdatePage` | Admin/Agent | Update existing invoices |
| `/orders-management/ticker-config` | `TickerConfigPage` | Admin/Agent | Configure marquee ticker bar |
| `/orders-management/profile` | `Profile` | Admin/Agent | Admin user profile |

---

## 5. Portal Navigation Structures

### 5.1 Admin / Agent Portal (OMS)

The OMS uses `FullLayout` with a vertical collapsible `Sidebar`. Sidebar items are defined in `Sidebaritems.tsx`.

**Sidebar items with role restrictions:**

| Menu Item | URL | Visible To |
|-----------|-----|-----------|
| Dashboard | `/orders-management/dashboard` | Admin + Agent |
| Orders | `/orders-management/orders` | Admin + Agent |
| Dispatch Batches | `/orders-management/dispatch-batches` | Admin only (+ Gold Sellers in special config) |
| Agents | `/orders-management/agents` | Admin only |
| Ratings Settings | `/orders-management/ratings-settings` | Admin only |
| Stores Settings | `/orders-management/stores-settings` | Admin only |
| Tags Management | `/orders-management/tags-management` | Admin only |
| Purchase Orders | `/orders-management/purchase-orders` | Admin only |
| Return Orders | `/orders-management/return-orders` | Admin only |
| Ticketing | `/orders-management/ticketing` | Admin + Agent (with new-ticket badge notification) |
| Gold Subscriptions | `/orders-management/gold-subscriptions` | Admin only |
| Inventory Movements | `/orders-management/inventory-movements` | Admin only |
| Ticker Config | `/orders-management/ticker-config` | Admin only |
| Agency Registrations | `/orders-management/agency-registrations` | Admin only |
| Commission Models | `/orders-management/commission-models` | Admin only |
| Invoice (group) | — | Admin only |
| ↳ Invoice Upload | `/orders-management/invoice-upload` | Admin only |
| ↳ Update Invoice | `/orders-management/invoice-update` | Admin only |

An **AgencyContextBanner** appears in the FullLayout header when admin is viewing in agency proxy mode.

### 5.2 Seller Portal

The Seller portal uses `RootLayout` → `AuthWrapper` with a custom `Sidebar` component. The sidebar supports two themes: **default** (dark purple/indigo), **gold** (amber, for gold subscribers), and **agency** (emerald/cyan, when in agency view).

The sidebar has two portal tabs at the top: **Merchant** and **Agency**, allowing quick switch.

**Merchant sidebar items (all Sellers):**

| Menu Item | URL | Notes |
|-----------|-----|-------|
| Get Started ▾ | `/get-started` | Dropdown with 3 sub-items |
| ↳ Dropshipping | `/get-started/dropshipping` | |
| ↳ Zambeel 360 | `/get-started/zambeel-360` | |
| ↳ 3PL Services | `/get-started/3pl-services` | |
| Dashboard | `/dashboard` | |
| Zambeel Academy | `/academy` | |
| Orders | `/orders` | |
| Orders Analytics | `/orders-analytics` | |
| Gold Subscription | `/gold-subscription` | |
| Bank Accounts | `/settings` | |
| Stores Integration | `/stores/integration` | |
| Ticketing | `/ticketing` | Green pulse badge if new tickets |
| My Invoice | `/my-invoices` | Green pulse badge if new invoices |
| My Inventory | `/seller/inventory` | **Only shown if `showInventory` flag is enabled** |

**When in Agency Proxy Mode** (admin viewing as agency), merchant sidebar is filtered to only:
`/orders`, `/orders-analytics`, `/stores/integration`, `/ticketing`, `/my-invoices`, `/seller/inventory`

### 5.3 Agency Portal

Shown when sidebar tab "Agency" is clicked. Navigation depends on registration status:

**If registration NOT approved:**
| Menu Item | URL |
|-----------|-----|
| Dashboard | `/agency` |

**If registration IS approved:**
| Menu Item | URL |
|-----------|-----|
| Dashboard | `/agency` |
| Merchants | `/agency/portal/merchants` |
| Commission | `/agency/portal/commission` |
| Team Members | `/agency/portal/team-members` |
| Settings | `/agency/portal/settings` |

---

## 6. All Features by Portal

### 6.1 Admin/Agent Features

#### Dashboard
- View KPI metrics and analytics for all orders
- Real-time order status data

#### Orders Management (`/orders-management/orders`)
- View all orders across all stores
- Filter by: status, sub-status, tag, store name, date range, platform, courier, agent, batch ID
- Search by: order ID, tracking number, customer name, phone number, store URL
- View order detail modal (full product, pricing, customer, tracking info)
- Edit order fields: address, city, phone, customer name
- Update order status: Approve / Cancel individual orders
- Bulk approve/cancel orders
- Add products to existing orders (by SKU search)
- Remove products from orders
- Update product variant quantities and prices
- Update customer info (address, city, phone, country, area, building, national address short code)
- Update order metadata: total cost, discount, post-dispatch discount, tax, shipping price, payment method, reschedule date
- Apply/update NDR metadata (activity counter, remark IDs)
- Assign tags to single or bulk orders
- Assign sub-statuses to single or bulk orders
- Bulk CSV update orders (sub-status, tag, tracking, courier, vendor)
- Bulk CSV upload new orders
- Bulk vendor/courier upload from CSV
- Revert orders to Confirmation Pending status
- View order activity logs
- View duplicate orders for a given order
- View WhatsApp (Watti) conversation for an order
- Get/download DIP (Dispatch In Progress) batches
- Download AWB (Air Waybill) files
- Download packing list
- Check order availability for courier assignment

#### Courier Assignment & Dispatch Batches
- View all dispatch batches with filters (country, date, vendor, courier, tracking_status)
- tracking_status values: `New`, `Generating`, `Partial`, `Generated`, `Failed`
- document_status values: `Not Ready`, `Preparing`, `Ready`, `Invalidated`
- Generate batches (auto-groups orders by vendor/courier)
- Generate tracking IDs for a batch (`All` mode or `Missing` mode)
- Generate documents (packing lists/manifests) for a batch
- Download tracking generation report (CSV)
- Assign courier manually to bulk orders
- Clear courier assignment for selected orders
- Download courier assignment report (CSV)
- Get available couriers (filtered by country)
- Get vendors (filtered by country)
- Get batch IDs (for filter dropdowns)

#### Purchase Orders (IMS)
- List POs with filters (search, date range, status)
- PO statuses: `Draft`, `Received`, `Partially Received`, `Cancelled`, `Submitted`
- Create new purchase order (country, warehouse, line items with SKU + quantity)
- View single PO detail
- Update PO details
- Receive items against a PO (mark quantities received per variant)
- Submit PO to warehouse (moves to Submitted status)
- Search SKU in warehouse before creating PO
- Validate CSV variants against a warehouse
- Get available warehouses by country
- Export PO list to PDF (client-side jsPDF)

#### Return Orders (IMS)
- List return orders (search, date range, pagination)
- Create new return order (country, warehouse, line items)
- View single return order detail

#### Ratings Settings
- Configure thresholds for seller performance ratings by country
- Add or update threshold values per country

#### Tags Management
- Create new order tags (associated with status + sub-status)
- View all tags
- Edit tags
- Soft-delete tags
- View all available order statuses
- View sub-statuses by status ID

#### Stores Settings
- View all stores in the system
- View/edit individual store settings
- View stores by user ID
- Check if a store name is available
- Create manual stores
- Delete stores

#### Ticketing (Admin View)
- View all tickets with filters: status, search, store ID, team ID, assigned-to-me toggle
- Ticket statuses: `Pending`, `In Progress`, `Awaiting Seller Action`, `Resolved`
- Create admin-initiated tickets on behalf of stores
  - Admin ticket categories: `Order Issue`, `Catalog & Pricing Updates`, `Payments & Payouts`
- Update ticket: status, description, resolution notes, assign team
- View ticket by ID
- View ticket logs (audit trail)
- Add comments to tickets
- Search stores by name or store ID
- Find order within a store by order ID or order number

#### Gold Subscriptions (Admin)
- Search all users
- List users who have gold access
- View individual user details
- Give gold access to a user (with expiry date)
- Extend existing gold access
- Remove gold access

#### Inventory Movements (Admin)
- List inventory movements with filters: movement ID, SKU, warehouse name, status, type, date range
- Movement types: `SKU_TO_SKU`, `WAREHOUSE_TRANSFER`, `DAMAGED`
- Status types: `In Transit`, `Received`
- Create inventory transaction (array of moves with: movement_type, reason, source_warehouse_id, destination_warehouse_id [for transfers], from_variant_id, to_variant_id, quantity)
  - Reasons: `SKU Merge`, `Wrong SKU Mapping`, `Repackaging`, `Services Deal`, `Variant Consolidation`, `Internal Adjustment`, `Demand Fulfillment`, `Purchase Transfer`
- Create damaged bin movement (warehouse_id, variant_id, quantity, reason)
  - Damaged reasons: `Physical Damage`, `Expired Product`, `Quality Failure`, `Packaging Damage`, `Customer Return - Unsellable`, `Purchase Order Correction`, `Lost / Missing in Audit`, `Outdated Stock`
- Find variant by SKU in a specific warehouse
- Get all warehouses
- Receive quantity against a transaction (update In Transit → Received)

#### Agency Registrations (Admin)
- List all agency applications filtered by status: `All`, `Pending`, `Approved`, `OnHold`, `Rejected`
- View single application detail
- Approve application (assign a commission model)
- Put application on hold (with reason + allow_resubmit flag)
- Reject application (with reason)
- Revert approved/held/rejected application back to Pending
- Revoke an approved agency's license

#### Commission Models (Admin)
- List all commission models
- List commission models with their rules
- Create commission model:
  - name (required)
  - rules: array of `{fk_country_id, commission_type, value, currency}`
  - commission_type: `percentage_of_delivered_revenue` or `flat_per_delivered_order`
  - value: positive number
  - currency: 3-character uppercase ISO code
- Update existing commission model

#### Invoice (Admin)
- Upload invoices for seller stores
- Update existing invoices
- Check if stores exist (validation before upload)
- View invoices by store ID
- Download individual invoice PDF

#### Ticker Config (Admin)
- View current ticker/marquee settings
- Update ticker settings (message, speed, visibility, etc.)

#### Agents Management (Admin)
- View all agents in the system

### 6.2 Seller Features

#### Dashboard (`/dashboard`)
- KPI overview: order counts by status, revenue metrics
- Date range selector

#### Orders (`/orders`)
- View own orders from all connected stores
- Filter by status, tags, date range, platform, store
- Manual order creation (single order form)
- CSV bulk order upload
- View order detail (product list, pricing, tracking, customer info)
- Approve/Cancel own orders
- Track order statuses in real-time

#### Orders Analytics (`/orders-analytics`)
- Visual charts of order performance over time
- Status breakdown, trend analysis

#### Products (`/products`)
- Browse own product catalog
- View product variants, SKUs, pricing

#### Gold Products (`/gold-products`, `/gold-products/:id`)
- Browse the Zambeel gold product catalog (sourced products available for dropshipping)
- View product details, images, pricing

#### Gold Subscription (`/gold-subscription`)
- View current subscription status and days remaining
- Subscribe to gold plan (via PayTabs payment gateway)
- Gold plan grants access to gold products and special features

#### Stores Integration (`/stores/integration`)
- Connect stores from supported platforms:
  - **Shopify** — OAuth integration, bind store to account, check store existence, manage webhooks
  - **Salla** — OAuth integration, order creation webhook
  - **YouCan** — OAuth integration, store info, webhooks, disconnect
  - **LightFunnels** — Integration
  - **EasyOrder** — Integration
  - **Manual Store** — Create a store manually (no e-commerce platform)
- Disconnect/delete stores
- View all connected stores

#### Settings / Bank Accounts (`/settings`, `account/:id`)
- Add payment accounts for receiving settlements:
  - Payment types: `Bank Account`, `USDT`, `PayPal`
  - Country-specific IBAN validation (Pakistan: 24 chars, UAE/Oman/Iraq: 23, Bahrain: 22)
  - India: account number (9-18 digits) + IFSC code (11 chars)
  - USA: account number + SWIFT (min 8) + FedWire (min 9)
  - USDT: exchange name, exchange ID, wallet address, first name, last name, country
- View all accounts
- Set primary account
- Update account settings (title, auto-withdrawal settings, withdrawal day, threshold)
- Delete accounts (cannot delete if attached to a store)

#### Payments (`/payments`)
- View payment history and COD settlements
- Create payment request (via PayTabs)
- Check subscription status

#### Seller Inventory (`/seller/inventory`)
- View own inventory levels per SKU/variant
- Export inventory report
- View purchase orders per variant
- View orders per inventory variant
- View inventory movements per variant

#### Ticketing (`/ticketing`)
- Create support tickets:
  - Select store
  - Optionally link to an order
  - Category: `Onboarding & Integration`, `Order Sending & Inventory Issue`, `Order Changes & Updates`, `Product Complaint`, `Delivery Complaint`, `Payments & Invoices`
  - Sub-category: dependent on category (validated server-side)
  - Description (min 10, max 2000 chars)
  - Attach image (S3 upload via presigned URL)
- View own tickets (filterable by status, searchable)
- View ticket detail and conversation history
- Add comments to tickets

#### My Invoices (`/my-invoices`)
- View invoices issued by Zambeel to seller's stores
- Download invoice PDFs
- New invoice badge notification in sidebar

#### Profile (`/profile`)
- Update: username, phone number, country, promo code
- Customize sidebar color (hex), button color (hex)

#### Academy
- `/academy` — Zambeel Academy (English content)
- `/zambeel-academy-arabic` — Arabic version
- `/zambeel-academy-urdu` — Urdu version

#### Get Started
- Onboarding guide for different service types (Dropshipping, Zambeel 360, 3PL Services)

### 6.3 Agency Features

#### Agency Dashboard (`/agency`)

**Pre-registration / Pending:**
- Shows registration status (Pending, OnHold, Rejected)
- Shows hold reason and reject reason if applicable
- Option to start or continue registration
- Option to resubmit if `allow_resubmit` is true

**Post-approval (redirects to portal pages):**
- Summary metrics: active merchants, total stores, delivered orders
- Revenue by currency
- Commission earned / due by currency
- Per-merchant breakdown with store-level detail
- Date range filter: `7d`, `30d`, `all`, or custom from/to

#### Commission Hub (`/agency/portal/commission`)
- Summary: total earned, total paid, commission due (per currency)
- Store-level breakdown: date, store, merchant, currency, commission type, value, revenue, commission amount
- Commission types:
  - `percentage_of_delivered_revenue` — percentage of store revenue from delivered orders
  - `flat_per_delivered_order` — fixed amount per delivered order
- Date range filter: `7d`, `30d`, `all`, custom

#### Invoices (within Commission Hub)
- View agency invoices: period, amount, paid, due, currency, status
- Invoice statuses: `Draft`, `Sent`, `Paid`
- Download invoice PDF

#### Merchants (`/agency/portal/merchants`)
- View all merchants connected to the agency
- Connection statuses: `Pending`, `Active`, `Inactive`
- Raw statuses: `Pending`, `Active`, `Rejected`, `Disconnected`
- Accept/reject incoming merchant connection requests
- Disconnect a merchant
- Reconnect a disconnected merchant
- Filter by connection status

#### Team Members (`/agency/portal/team-members`)
- View all agency team members
- Member roles: `Owner`, `Member`
- Member statuses: `Active`, `Invite Pending`
- Invite new team member (by email, optional full name)
- View invite link and email sent status
- Remove team members

#### Agency Settings (`/agency/portal/settings`)
- Update agency profile: name, city, phone, poc_name
- Country field optional in updates

---

## 7. All Forms — Fields & Validation Rules

### 7.1 Registration Form (`/register`)

| Field | Type | Rules | Notes |
|-------|------|-------|-------|
| Username | Text | Required | Sent as `username` |
| Email | Email | Required | Used for Firebase auth |
| Password | Password | Required | Firebase-validated |
| Confirm Password | Password | Required, must match password | Client-side validation |
| Phone | Phone | Required | Combined with country code |
| Country Code | Select | Required | Phone country code prefix |
| Country | Select | Required | From COUNTRIES constant |
| Promo Code | Text | Optional | Referral/promo code |

**Submission flow:** Firebase `createUserWithEmailAndPassword` → send verification email → `POST /signUp` with `{username, email, firebase_uid, phone_number, country, provider: 'Email', role: 'Seller', team_id: null, promo_code}`

Social sign-up (Google, Apple, Shopify) available via `BoxedSocialButtons`.

---

### 7.2 Login Form (`/login`)

- Email / Password → Firebase `signInWithEmailAndPassword` → get ID token → `POST /login` with `{idToken}`
- Or social providers (Google, Apple)

---

### 7.3 Profile Update Form

**API:** `PUT /user/profile`

| Field | Validation |
|-------|-----------|
| username | Optional string |
| phone_number | Optional, pattern `/^\+\d{10,15}$/` (international format) |
| country | Optional string |
| promo_code | Optional string, allow empty |
| sidebar_color | Optional hex color `/^#[0-9A-Fa-f]{6}$/` |
| button_color | Optional hex color `/^#[0-9A-Fa-f]{6}$/` |

---

### 7.4 Agency Registration Form — Step 1 (Start)

**API:** `POST /agency/register`

| Field | Type | Rules |
|-------|------|-------|
| name | String | Required, min 2, max 255, trimmed |
| country | String | Required, min 2, max 100, trimmed |
| city | String | Required, min 1, max 255 (from `/agency/cities?country=X`) |
| phone | String | Required, min 5, max 50 |
| poc_name | String | Required, min 2, max 255 |
| poc_photo_filename | String | Required, min 3, max 255 (filename for S3 upload) |
| identity_proof_filename | String | Required, min 3, max 255 (filename for S3 upload) |
| terms_accepted | Boolean | Required, must be `true` |

**Returns:** Signed S3 upload URLs for `poc_photo` and `identity_proof`.

---

### 7.5 Agency Registration Form — Step 2 (Complete)

**API:** `POST /agency/register/complete`

| Field | Type | Rules |
|-------|------|-------|
| agency_id | Integer | Required, positive |
| poc_photo_url | String URI | Required, max 500 chars |
| identity_proof_url | String URI | Required, max 500 chars |

---

### 7.6 Agency Settings Form

**API:** `PUT /agency/settings`

| Field | Type | Rules |
|-------|------|-------|
| name | String | Required, min 2, max 255 |
| city | String | Required, allow empty, max 255 |
| phone | String | Required, allow empty, max 50 |
| poc_name | String | Required, min 2, max 255 |
| country | String | Optional, min 2, max 100 |

---

### 7.7 Connect Merchant to Agency Form

**API:** `POST /agency/connect`

| Field | Type | Rules |
|-------|------|-------|
| agency_unique_id | String | Required, min 8, max 30 (format: `ZMB-AG-XXXXXX`) |
| access_scope | String | `"all"` or `"specific"`, default `"all"` |
| store_ids | Array of integers | Required (min 1) when access_scope is `"specific"`, optional otherwise |

---

### 7.8 Invite Agency Team Member

**API:** `POST /agency/team-members/invite`

| Field | Type | Rules |
|-------|------|-------|
| email | String | Required, valid email, lowercase |
| full_name | String | Optional, min 2, max 255 |

---

### 7.9 Create Ticket Form (Seller)

**API:** `POST /tickets`

| Field | Type | Rules |
|-------|------|-------|
| fk_store_id | Integer | Required, positive |
| fk_order_id | Integer | Optional, allow null |
| category | String | Required, one of: `Onboarding & Integration`, `Order Sending & Inventory Issue`, `Order Changes & Updates`, `Product Complaint`, `Delivery Complaint`, `Payments & Invoices` |
| sub_category | String | Required, must belong to selected category (server-validated) |
| description | String | Required, min 10, max 2000 |
| image | URI string | Optional, allow null/empty |

---

### 7.10 Create Admin Ticket

**API:** `POST /tickets/admin`

| Field | Type | Rules |
|-------|------|-------|
| fk_store_id | Integer | Required, positive |
| fk_order_id | Integer | Optional, allow null |
| category | String | Required, one of: `Order Issue`, `Catalog & Pricing Updates`, `Payments & Payouts` |
| sub_category | String | Required, must belong to category |
| description | String | Required, min 10, max 2000 |
| image | URI string | Optional |

---

### 7.11 Update Ticket

**API:** `PUT /tickets/:ticket_id`

| Field | Type | Rules |
|-------|------|-------|
| status | String | Optional: `Pending`, `In Progress`, `Awaiting Seller Action`, `Resolved` |
| description | String | Optional, min 10, max 2000 |
| resolution_notes | String | Optional, max 2000, allow null/empty |
| fk_team_id | Integer | Optional, allow null |

---

### 7.12 Bank Account Form (Create)

**API:** `POST /accounts`

| Field | Type | Rules |
|-------|------|-------|
| fk_user_id | Integer | Required, positive |
| account_title | String | Required, allow empty |
| account_nick | String | Optional, max 50 |
| payment_type | String | Required: `Bank Account`, `USDT`, `PayPal` |
| country | String | Required for USDT, optional otherwise |
| bank_name | String | Required (except USDT/PayPal), US is optional |
| iban | String | Country-specific length: PK=24, UAE/Oman/Iraq=23, Bahrain=22, others=20-32 alphanumeric; not required for US/India/HK/USDT/PayPal |
| iban_wallet_address | String | Required for USDT, Bank Account, PayPal |
| account_number | String | India: 9-18 digits; US: 5-18 digits; HK: 15-18 digits |
| ifsc_code | String | India only, exactly 11 chars |
| swift_code | String | US: required min 8; most countries: required min 8; PK/IN/UAE/Oman/Bahrain/Iraq: optional |
| fed_wire_code | String | US only, min 9 chars |
| exchange_name | String | Required for USDT, max 100 |
| exchange_id | String | Required for USDT (min 3), optional otherwise (min 3 if provided) |
| first_name | String | Required for USDT, max 100 |
| last_name | String | Required for USDT, max 100 |
| account_country | String | Optional, max 100 |
| bank_exchange_name | String | Optional, max 100 |
| is_primary | Boolean | Default false |

---

### 7.13 Bank Account Update Form

**API:** `PUT /accounts/:id`

| Field | Type | Rules |
|-------|------|-------|
| account_title | String | Optional, max 100 |
| is_primary | Boolean | Optional |
| autoWithdrawal | Boolean | Optional |
| withdrawalDay | String | Optional |
| withdrawalThreshold | Number | Optional |

---

### 7.14 Create Purchase Order

**API:** `POST /purchase-orders`

| Field | Type | Rules |
|-------|------|-------|
| countryId | Integer | Required, positive |
| warehouseId | Integer | Required, positive |
| status | String | Required: `Draft`, `Received`, `Partially Received`, `Cancelled`, `Submitted` |
| lineItems | Array | Required, min 1 item |
| lineItems[].id | Integer | Optional (variant ID) |
| lineItems[].quantity | Integer | Required, positive |

---

### 7.15 Receive Items (Mark PO as Received)

**API:** `PUT /purchase-orders/:poId/mark-as-received`

| Field | Type | Rules |
|-------|------|-------|
| variants | Array | Required, min 1 |
| variants[].variant_id | Integer | Required, positive |
| variants[].quantity_total | Integer | Required, min 0 |
| variants[].quantity_received | Integer | Required, min 0 |

---

### 7.16 Create Return Order

**API:** `POST /return-orders`

| Field | Type | Rules |
|-------|------|-------|
| countryId | Integer | Required, positive |
| warehouseId | Integer | Required, positive |
| lineItems | Array | Required, min 1 |
| lineItems[].id | Integer | Optional (variant ID) |
| lineItems[].quantity | Integer | Required, positive |

---

### 7.17 Update Order Details

**API:** `PUT /orders/:orderId`

| Field | Type | Rules |
|-------|------|-------|
| total_cost | Number | Optional, precision 2, min 0 |
| total_discount | Number | Optional, precision 2, min 0 |
| post_dispatch_discount | Number | Optional, precision 2, min 0 |
| total_tax | Number | Optional, precision 2, min 0 |
| shipping_price | Number | Optional, precision 2, min 0 |
| tags | String | Optional, allow null/empty |
| activity_counter | Integer | Optional, min 0 |
| ndr_meta_data | Object | Optional, allow null |
| reschedule_date | Date ISO | Optional, allow null |
| payment_method | String | Optional, allow null/empty |
| customer_name | String | Optional, allow null/empty |

---

### 7.18 Update Customer Info

**API:** `PUT /orders/customers/:customerId`

| Field | Type | Rules |
|-------|------|-------|
| address | String | Optional |
| city | String | Optional |
| country | String | Optional |
| phone | String | Optional, allow null/empty, pattern `/^\+?[0-9\s\-]{10,20}$/` |
| area_name | String | Optional, allow null/empty |
| building_society | String | Optional, allow null/empty |
| national_address_short_code | String | Optional, allow null/empty |

---

### 7.19 Update Order Product Variant

**API:** `PUT /orders/:orderId/order-product-variants/:orderProductVariantId`

| Field | Type | Rules |
|-------|------|-------|
| quantity | Integer | Optional, min 1 |
| price | Number | Optional, precision 2, min 0 |

---

### 7.20 Add Product to Order

**API:** `POST /orders/add-product`

| Field | Type | Rules |
|-------|------|-------|
| order_id | Integer | Required |
| variant_id | Integer | Required |
| quantity | Integer | Required, min 1 |
| price | Number | Required, precision 2, min 0 |
| discount | Number | Optional, precision 2, min 0, default 0 |

---

### 7.21 CSV Bulk Order Upload

**API:** `POST /orders/bulk-order-upload`

Fields per order row:
| Field | Notes |
|-------|-------|
| store_url | Store identifier |
| customer_name | |
| customer_phone_number | |
| delivery_country | |
| delivery_city | |
| address | |
| order_reference_id | |
| total_amount | |
| currency | |
| payment_mode | |
| platform | |
| tag | |
| discount | Optional |
| shipping_charges | Optional |
| variants | Optional array: `{product_sku, quantity, price}` |

---

### 7.22 Inventory Transaction Form (Admin)

**API:** `POST /inventory-movements/transactions` (array of transactions)

| Field | Type | Rules |
|-------|------|-------|
| movement_type | String | Required: `SKU_TO_SKU` or `WAREHOUSE_TRANSFER` |
| reason | String | Required: one of 8 valid reasons |
| source_warehouse_id | Integer | Required, positive |
| destination_warehouse_id | Integer | Required for WAREHOUSE_TRANSFER only |
| from_variant_id | Integer | Required, positive |
| to_variant_id | Integer | Required, positive |
| quantity | Integer | Required, min 1 |

---

### 7.23 Damaged Bin Movement Form (Admin)

**API:** `POST /inventory-movements/damaged-bin` (array)

| Field | Type | Rules |
|-------|------|-------|
| warehouse_id | Integer | Required, positive |
| variant_id | Integer | Required, positive |
| quantity | Integer | Required, min 1 |
| reason | String | Required: one of 8 valid damage reasons |

---

### 7.24 Commission Model Form (Admin)

**API:** `POST /admin/agency-registrations/commission-models`

| Field | Type | Rules |
|-------|------|-------|
| name | String | Required, min 2, max 255 |
| rules | Array | Required, min 1 rule |
| rules[].fk_country_id | Integer | Required, positive |
| rules[].commission_type | String | Required: `percentage_of_delivered_revenue` or `flat_per_delivered_order` |
| rules[].value | Number | Required, positive |
| rules[].currency | String | Required, uppercase, exactly 3 chars (ISO 4217) |

---

### 7.25 Approve Agency Application (Admin)

**API:** `POST /admin/agency-registrations/applications/:id/approve`

| Field | Type | Rules |
|-------|------|-------|
| fk_commission_model_id | Integer | Required, positive |

---

### 7.26 Hold Agency Application (Admin)

**API:** `POST /admin/agency-registrations/applications/:id/hold`

| Field | Type | Rules |
|-------|------|-------|
| hold_reason | String | Required, min 3 |
| allow_resubmit | Boolean | Required |

---

### 7.27 Reject Agency Application (Admin)

**API:** `POST /admin/agency-registrations/applications/:id/reject`

| Field | Type | Rules |
|-------|------|-------|
| reject_reason | String | Required, min 3 |

---

### 7.28 Ratings Threshold Form (Admin)

**API:** `POST /data/thresholds`

Fields defined in `thresholdAndRatio` validation — country-specific threshold configuration for seller rating calculations.

---

## 8. All User Flows — Step by Step

### 8.1 New Seller Registration

1. Navigate to `/register`
2. Fill Registration Form (username, email, password, phone, country, optional promo code)
3. OR click Google/Apple social sign-in button
4. Firebase creates user → sends verification email to user's address
5. API `POST /signUp` creates Zambeel user record with `role: 'Seller'`
6. User is shown a message to verify their email
7. User clicks verification link in email → redirected to `/verify-email`
8. `GET /verify-email` marks email as verified in Zambeel DB
9. User is redirected to `/login`
10. User logs in → `POST /login` with Firebase ID token → receives JWT
11. `RootRedirect` checks role → Seller → redirects to `/get-started` or `/dashboard`

### 8.2 Seller Login

1. Navigate to `/login`
2. Enter email + password (or social)
3. Firebase `signInWithEmailAndPassword` → get ID token
4. `POST /login` with `{idToken}` → Zambeel returns JWT + user data
5. Zustand `useAuthStore` saves token and userRole
6. `RootRedirect` routes to appropriate portal:
   - Admin/Agent → `/orders-management/dashboard`
   - Seller/Agency → `/dashboard` (or `/get-started` if first time)

### 8.3 Seller Connects a Shopify Store

1. Navigate to `/stores/integration`
2. Click "Connect Shopify"
3. Enter Shopify shop URL → `GET /shopify/shop?shop=X` validates it
4. `GET /shopify/check-store-exists` checks if already connected
5. `GET /shopify/auth?shop=X` initiates OAuth → redirected to Shopify
6. Shopify redirects back to the app with OAuth code
7. Backend exchanges code for access token
8. `POST /shopify/bind-store` binds store to user account
9. Store appears in store list

### 8.4 Seller Creates an Order (Manual)

1. Navigate to `/orders`
2. Click "Create Order"
3. Fill order form: store, customer name, phone, delivery address, city, country, products (SKU, quantity, price), payment mode, tag
4. Submit → `POST /orders/uploadOrderCSV` (single order via CSV mechanism) or manual create endpoint
5. Order appears with status `Confirmation Pending`
6. Seller can approve own order → `PUT /orders/:orderId/approve-status` with `{status: "Approved"}`
7. Admin receives order in OMS for fulfillment

### 8.5 Seller Bulk Uploads Orders (CSV)

1. Navigate to `/orders`
2. Click "Bulk Upload"
3. Download CSV template
4. Fill CSV with order rows (store_url, customer info, address, products, etc.)
5. Upload CSV file
6. `POST /orders/bulk-order-upload` processes all rows
7. Response shows: `successCount`, `skippedOrders`, `totalProcessed`

### 8.6 Admin Approves Orders and Assigns Courier

1. Navigate to `/orders-management/orders`
2. Filter orders by status = `Confirmation Pending`
3. Review orders — check customer info, products, pricing
4. Select orders → Bulk approve → `PUT /orders/approve-status/bulk` with `{orderIds, status: "Approved"}`
5. Orders move to `Approved` → substatus `Checking Inventory For Dispatching`
6. Navigate to `/orders-management/dispatch-batches`
7. Click "Generate Batches" → `POST /orders/generate-batches` with `{country_id}`
8. System auto-groups orders by vendor/courier → batches created
9. Select a batch → Click "Generate Tracking IDs" → `POST /orders/generate-tracking-ids` with `{batch_id, mode: 'All'}`
10. Tracking IDs generated → AWB files created
11. Click "Generate Documents" → `POST /orders/generate-documents` with `{batch_id}`
12. Download AWB → `POST /orders/download-awbs`
13. Download packing list → `POST /orders/download-packing-list`

### 8.7 Admin Creates a Purchase Order

1. Navigate to `/orders-management/purchase-orders`
2. Click "Create PO"
3. Select country → `GET /purchase-orders/countries` (list countries)
4. Select warehouse → `GET /purchase-orders/warehouses/country/:countryId`
5. Search for SKUs → `GET /purchase-orders/warehouses/:warehouseId/search?sku=X`
6. Add line items (SKU + quantity)
7. Optionally upload CSV of variants → `POST /purchase-orders/warehouses/:warehouseId/validate-variants`
8. Submit with status `Draft` → `POST /purchase-orders`
9. PO created

### 8.8 Admin Receives a Purchase Order

1. Navigate to PO detail or `/orders-management/purchase-orders/:poId/receive`
2. For each variant, enter `quantity_received`
3. Submit → `PUT /purchase-orders/:poId/mark-as-received`
4. PO status updates to `Received` or `Partially Received`

### 8.9 Admin Submits a Purchase Order to Warehouse

1. Navigate to `/orders-management/purchase-orders/:poId/submit`
2. Review PO details
3. Click Submit → `PUT /purchase-orders/:poId/mark-as-submitted`
4. PO status moves to `Submitted`

### 8.10 Seller Creates a Support Ticket

1. Navigate to `/ticketing`
2. Click "Create Ticket"
3. Select store from dropdown
4. Optionally search and select an order
5. Select category → sub-category populates based on category
6. Write description (min 10 chars)
7. Optionally upload image (generates S3 presigned URL via `POST /s3/presigned`, uploads file, saves URL)
8. Submit → `POST /tickets`
9. Ticket appears in list with status `Pending`
10. Admin responds → status updates → seller sees `Awaiting Seller Action`
11. Seller adds comment → `POST /comments`
12. Admin resolves → status `Resolved`

### 8.11 Agency Registration Flow

1. Seller navigates to `/agency` (clicks "Agency" tab in sidebar)
2. Clicks "Register as Agency"
3. **Step 1 — Start Registration:**
   - Fill: agency name, country, city (from autocomplete), phone, POC name
   - Upload POC photo file (image)
   - Upload identity proof file
   - Accept terms (checkbox must be checked)
   - Submit → `POST /agency/register`
   - Response includes S3 signed upload URLs
4. **Step 2 — Upload Documents:**
   - PUT files directly to the signed S3 URLs
   - Submit complete with URLs → `POST /agency/register/complete`
5. Application status: `Pending`
6. Admin reviews at `/orders-management/agency-registrations`
7. Admin approves (assigns commission model) / holds (with reason) / rejects (with reason)
8. If approved: agency gets unique ID (`ZMB-AG-XXXXXX`), status → `Approved`
9. Seller now sees full Agency portal menu items

### 8.12 Merchant Connects to Agency

1. Seller navigates to `/agency` (or a connection page in settings)
2. Enters agency's unique ID (`ZMB-AG-XXXXXX`)
3. Selects access scope: `all` stores or `specific` stores
4. If specific, selects which store IDs to share
5. Submit → `POST /agency/connect`
6. Connection created with status `Pending`
7. Agency owner reviews in `/agency/portal/merchants`
8. Agency accepts (`PATCH /agency/merchants/:id/status` with `{action: "accept"}`) → status `Active`
9. Agency can now see merchant's orders/data for connected stores

### 8.13 Agency Invites Team Member

1. Navigate to `/agency/portal/team-members`
2. Click "Invite Member"
3. Enter email and optional full name → `POST /agency/team-members/invite`
4. System sends invite email with token link
5. Invitee receives email, clicks link → `/agency/invite?token=X`
6. `AgencyInviteAccept` page calls `POST /agency/team-members/invite/preview` to preview invite
7. Invitee accepts → `POST /agency/team-members/accept` with `{token}`
8. Member status → `Active`, added to team

### 8.14 Admin Manages Gold Subscriptions

1. Navigate to `/orders-management/gold-subscriptions`
2. Search for a user by name/email → `GET /admin/gold-subscriptions/users?search=X`
3. View user details → `GET /admin/gold-subscriptions/users/:userId`
4. Click "Give Access" → `POST /admin/gold-subscriptions/give` with `{userId, expiryDate}`
5. Or "Extend" → `POST /admin/gold-subscriptions/extend`
6. Or "Remove" → `POST /admin/gold-subscriptions/remove`

### 8.15 Admin Uploads Seller Invoice

1. Navigate to `/orders-management/invoice-upload`
2. Select stores to verify they exist → `POST /invoices/check-stores`
3. Fill invoice data (store, amount, period, etc.)
4. Submit → `POST /invoices`
5. Invoice appears in seller's `/my-invoices` with badge notification

---

## 9. Role-Based Access Control

### Frontend Route Guards

| Guard | Roles Allowed | Used For |
|-------|--------------|---------|
| `ProtectedRoute` | `Admin`, `Agent` | All `/orders-management/*` routes |
| `SellerProtectedRoute` | `Seller`, `Agency` | All seller portal routes |
| `AgencyApprovedRoute` | `Seller`/`Agency` with `registration_status === "Approved"` | All `/agency/portal/*` routes |
| No guard | Any | Public routes (`/login`, `/register`, etc.) |

### Backend Role Definitions

| Middleware | Allowed Roles |
|-----------|--------------|
| `verifySeller` | `Seller`, `Agency` |
| `verifyUser` | Any authenticated user |
| `verifyAdminOnly` | `Admin` |
| `verifyAgentOnly` | `Agent` |
| `verifyAdminAndSeller` | `Admin`, `Seller`, `Agency` |
| `verifyAdminAndSellerWithAgencyContext` | `Admin`, `Seller`, `Agency` (+ agency store context) |
| `verifyAgentAndSeller` | `Agent`, `Seller`, `Agency` |
| `verifyAgentAdminAndSeller` | `Agent`, `Admin`, `Seller`, `Agency` |
| `verifyAdminAndAgent` | `Admin`, `Agent` |
| `verifyJWTWithRoles(['Seller', 'Agency'])` | `Seller`, `Agency` (all agency endpoints) |

### Key Permission Differences by Feature

| Feature | Admin | Agent | Seller | Agency |
|---------|-------|-------|--------|--------|
| View all orders (OMS) | ✅ | ✅ | ❌ | ❌ |
| View own orders | ✅ | ✅ | ✅ | ✅ |
| Approve/edit orders | ✅ | ✅ | ✅ (own) | ✅ (own) |
| Bulk approve orders | ✅ | ✅ | ✅ | ✅ |
| Add product to order | ✅ | ✅ | ✅ | ✅ |
| Assign courier | ✅ | ✅ | ❌ | ❌ |
| Generate dispatch batches | ✅ | ✅ | ❌ | ❌ |
| Purchase Orders | ✅ | ✅ | ❌ | ❌ |
| Return Orders | ✅ | ✅ | ❌ | ❌ |
| Inventory Movements | ✅ | ❌ | ❌ | ❌ |
| Tags Management | ✅ | ❌ | ❌ | ❌ |
| Gold Subscription admin | ✅ | ❌ | ❌ | ❌ |
| Agency application review | ✅ | ❌ | ❌ | ❌ |
| Commission model CRUD | ✅ | ❌ | ❌ | ❌ |
| Invoice upload/update | ✅ | ✅ | ❌ | ❌ |
| Ticker config | ✅ | ✅ | ❌ | ❌ |
| Threshold/ratings config | ✅ | ✅ | ❌ | ❌ |
| Store management (admin) | ✅ | ✅ | own only | own only |
| Products management | ✅ | ✅ | own only | own only |
| Seller inventory | ✅ | ✅ | own only | own only |
| Bank accounts | ❌ | ❌ | ✅ | ✅ |
| Gold subscription (purchase) | ❌ | ❌ | ✅ | ✅ |
| Ticketing (create) | ✅ | ✅ | ✅ | ✅ |
| Ticketing (admin view) | ✅ | ✅ | ❌ | ❌ |
| Agency registration | ❌ | ❌ | ✅ | ✅ |
| Agency portal | ❌ | ❌ | If approved | If approved |

---

## 10. Key Business Logic

### 10.1 Order Lifecycle

Order statuses flow in this sequence:

```
Confirmation Pending
    ↓
Approved  ←→  Cancelled
    ↓
Checking Inventory For Dispatching (substatus)
    ↓
Inventory In Transit (substatus: Calculating Dispatching Time)
    ↓
[Courier Assigned → Dispatch Batch → Tracking Generated]
    ↓
Delivered / NDR (Non-Delivery Report)
```

When an order is approved, the system auto-maps to:
- `{status: 'Approved', substatus: 'Checking Inventory For Dispatching', tag: 'Checking Inventory'}`
- `{status: 'Approved', substatus: 'Inventory In Transit', tag: 'Calculating Dispatching Time'}`

**NDR (Non-Delivery Report):** Orders can have NDR metadata (`activity_counter`, `remark_ids`). Activity counter tracks how many delivery attempts have been made. NDR remarks are bulk-updated via `POST /orders/ndr-remarks`.

Orders can be reverted to `Confirmation Pending` with `PUT /orders/revert-to-confirmation-pending`.

### 10.2 Dispatch Batch Lifecycle

```
Batch Created (tracking_status: New)
    ↓
Generate Tracking IDs → Generating → Partial | Generated | Failed
    ↓
Generate Documents → Preparing → Ready | Invalidated
    ↓
Download AWBs + Packing List
    ↓
Physical dispatch to courier
```

- `has_removed_orders`: flag indicating some orders were removed after batch creation
- Batches can have `vendor_id` (logistics vendor) and `courier_id` (courier service)

### 10.3 Purchase Order Lifecycle

```
Draft → Submitted (by admin)
     → Received (all items received)
     → Partially Received (some items received)
     → Cancelled
```

### 10.4 Inventory Movement Logic

**SKU_TO_SKU:** Stock moved from one SKU/variant to another within the same warehouse. Used for SKU merges, wrong mappings, repackaging.

**WAREHOUSE_TRANSFER:** Stock physically moved from `source_warehouse_id` to `destination_warehouse_id`.

**DAMAGED:** Stock moved to damaged bin with a damage reason. Transaction starts as `In Transit` → admin receives with quantity → `Received`.

### 10.5 Agency Commission Calculation

Two commission models are supported, configured per country:

| Type | How Calculated |
|------|---------------|
| `percentage_of_delivered_revenue` | `commission = revenue × (value / 100)` |
| `flat_per_delivered_order` | `commission = delivered_order_count × value` |

- Commission is calculated only on **delivered** orders
- Each rule has a currency (ISO 3-char code)
- Agency commission hub shows: `totalEarned`, `totalPaid`, `commissionDue` per currency
- Invoices are issued by Zambeel to the agency with statuses: `Draft` → `Sent` → `Paid`

### 10.6 Agency Connection Access Scopes

When a merchant connects to an agency:
- `access_scope: "all"` — agency can see all merchant stores
- `access_scope: "specific"` — agency can only see specified `store_ids`

Agency store context is enforced by `verifyAgencyStoreContext` middleware on relevant endpoints.

### 10.7 Gold Subscription

- Sellers can subscribe to a Gold plan via PayTabs payment
- Gold status tracked in `useGoldProductsStore` (`isGoldPlanActive`, `planExpiryTime`)
- Gold subscribers get:
  - Access to Gold Products catalog (sourced products for dropshipping)
  - Gold-themed sidebar UI (amber/honey color scheme)
  - Access to Dispatch Batches in the OMS (via `goldSellerOnly` sidebar flag)
- Admin can grant/extend/remove gold access manually from OMS
- Subscription check: `GET /payments/checkUserSubscription` → returns `{gold_subscription, days_left}`

### 10.8 Store Bifurcation

Orders have a `bifurcation` field used to distinguish handling type. Available as a filter in order queries. This likely distinguishes between auto-fulfilled (platform webhook) vs. manually uploaded orders.

### 10.9 Seller Performance Ratings

The Ratings Settings page (`/orders-management/ratings-settings`) configures thresholds per country. These thresholds presumably define cutoffs for rating bands (e.g., confirmation rate %, delivery rate %) used to score sellers.

### 10.10 Ticker / Marquee Bar

A top marquee bar (`TopMarqueeBar`) runs across the seller portal. The content is configurable by admins via `/orders-management/ticker-config`:
- `GET /ticker-config` — public endpoint, returns current settings
- `PUT /ticker-config/admin` — authenticated, update settings

### 10.11 WhatsApp Integration (Watti)

Orders have an associated WhatsApp conversation viewable in the admin order detail:
- `GET /orders/:orderId/conversation` — fetches messages between agent and customer
- Returns: message list, summary (total/customer/agent messages, last message), order info (orderId, orderNumber, customerPhone)

### 10.12 Promo Code System

Users can enter a promo code at registration (`promo_code` in signup payload) and update it later via profile update. The business logic for how promo codes are processed is in the backend controller.

---

## 11. Backend API Endpoints — Complete List

Base path: all routes mounted under `/api` (or equivalent prefix in `app.js`).

### Authentication & User

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/signUp` | None | `controller.signUp` |
| POST | `/login` | None | `controller.login` |
| GET | `/auth/check-email` | None | `controller.checkEmailExists` |
| GET | `/verify-email` | None | `controller.updateEmailVerified` |
| PUT | `/user/profile` | `validateRequest(updateUserProfileSchema)`, `verifySeller` | `controller.updateUserProfile` |
| POST | `/user/accept-terms` | `verifySeller` | `controller.acceptTerms` |
| GET | `/agents` | None | `controller.getAgents` |
| GET | `/teams` | None | `teamsController.getTeams` |
| GET | `/dashboard/data` | `verifySeller` | `DashboardController.getDashboardData` |

### Orders

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/orders` | `verifyUser` | `getOrders` |
| GET | `/orders/status-counts` | `verifyUser` | `getOrderStatusCounts` |
| GET | `/orders/order-analytics` | `verifySeller` | `ordersAnalytics` |
| GET | `/orders/substatusOrders` | `verifySeller` | `getOrdersBySubStatus` |
| GET | `/orders/substatus-orders-for-csv` | `verifySeller` | `getOrdersBySubStatusForCSV` |
| GET | `/orders/seller-orders` | `verifySeller`, validate query | `getSellerOrders` |
| GET | `/orders/proccessedOrders` | `verifySeller`, validate query | `getProcessedOrders` |
| GET | `/orders/orderDetails/:orderId` | `verifyAgentAdminAndSeller` | `getModalOrderDetails` |
| GET | `/orders/:orderId/logs` | `verifyAgentAdminAndSeller` | `getOrderLogs` |
| GET | `/orders/:orderId/conversation` | `verifyAgentAdminAndSeller` | `getOrderConversation` |
| GET | `/orders/duplicates/:orderId` | `verifyUser` | `getDuplicateOrders` |
| GET | `/orders/couriers` | `verifyUser` | `getCouriers` |
| GET | `/orders/vendors` | `verifyUser` | `getVendors` |
| GET | `/orders/batch-ids` | `verifyUser` | `getBatchIds` |
| GET | `/orders/tags` | `verifyUser` | `getOrderTags` |
| GET | `/orders/remarks` | `verifyUser` | `getAllRemarks` |
| GET | `/orders/batches/dip` | `verifyUser` | `getDIPBatches` |
| GET | `/orders/dispatch-batches` | `verifyUser`, validate | `getDispatchBatches` |
| GET | `/orders/tracking-generation-report` | `verifyUser`, validate | `getTrackingGenerationReport` |
| GET | `/orders/store/:storeId` | validate | `getStoreOrders` |
| GET | `/orders/sub-statuses` | None (via `/sub-statuses`) | `getSubstatusesByStatusName` |
| POST | `/orders/bulk-order-upload` | `verifyUser`, validate | `bulkCsvUploadOrders` |
| POST | `/orders/bulk-vendor-courier-upload` | `verifyUser`, validate | `bulkVendorCourierUpload` |
| POST | `/orders/add-product` | `verifyAgentAdminAndSeller`, validate | `addProductToOrder` |
| POST | `/orders/assign-courier` | `verifyUser`, validate | `assignCourier` |
| POST | `/orders/check-availability` | `verifyUser`, validate | `checkOrderAvailability` |
| POST | `/orders/variants/price` | `verifyAgentAdminAndSeller`, validate | `getVariantPrice` |
| POST | `/orders/variants/search` | `verifyAgentAdminAndSeller` | `searchVariantBySKU` |
| POST | `/orders/sub-statuses/bulk-update` | `verifyAgentAdminAndSeller`, validate | `updateOrdersBySubstatus` |
| POST | `/orders/ndr-remarks` | `verifyUser` | `bulkUpdateNdrRemarks` |
| POST | `/orders/download-awbs` | `verifyUser` | `downloadAWBs` |
| POST | `/orders/download-packing-list` | `verifyUser` | `downloadPackingList` |
| POST | `/orders/generate-batches` | `verifyUser`, validate | `generateBatches` |
| POST | `/orders/generate-tracking-ids` | `verifyUser`, validate | `generateTrackingIds` |
| POST | `/orders/generate-documents` | `verifyUser`, validate | `generateDocuments` |
| POST | `/orders/courier-assignment/report` | `verifyUser` | `downloadAssignmentReport` |
| POST | `/orders/clear-courier-assignment` | `verifyAgentAdminAndSeller`, validate | `clearCourierAssignment` |
| POST | `/orders/uploadOrderCSV` | `verifySeller`, validate | `csvOrderUpload` |
| PUT | `/orders/bulk-csv-update` | `verifyUser`, validate | `bulkCsvUpdateOrders` |
| PUT | `/orders/revert-to-confirmation-pending` | `verifyUser` | `revertOrdersToConfirmationPending` |
| PUT | `/orders/approve-status/bulk` | `verifyAgentAdminAndSeller` | `bulkApproveOrders` |
| PUT | `/orders/:orderId` | `verifyAgentAdminAndSeller`, validate | `updateOrderDetails` |
| PUT | `/orders/:orderId/approve-status` | `verifyAgentAdminAndSeller` | `updateOrderStatus` |
| PUT | `/orders/:orderId/status` | `verifyAdminAndSellerWithAgencyContext` | `updateOrderStatusFromReceived` |
| PUT | `/orders/:orderId/edit` | `verifyAgentAdminAndSeller`, validate | `editOrderFields` |
| PUT | `/orders/:orderId/order-product-variants/:opvId` | `verifyAgentAdminAndSeller`, validate | `updateOrderProductVariant` |
| PUT | `/orders/customers/:customerId` | `verifyAgentAdminAndSeller`, validate | `updateCustomerInfo` |
| PUT | `/orders/address/:orderId` | `verifyAdminAndSeller` | `updateOrderFields` |
| DELETE | `/orders/delete/:orderId` | `verifySeller` | `deleteOrder` |
| DELETE | `/orders/:orderId/delete-product/:variantId` | `verifyAgentAdminAndSeller` | `deletedProduct` |

### Orders — Remarks (nested under `/orders/:orderId/remarks`)

| Method | Path | Handler |
|--------|------|---------|
| GET | `/orders/:orderId/remarks` | `getRemarksByOrderId` |
| PUT | `/orders/:orderId/remarks` | `associateRemarksToOrder` |

Also: `POST /remarks` (bulk update order remarks) — `verifyUser`

### Orders — Tags (nested under `/orders/:orderId/tags`)

| Method | Path | Handler |
|--------|------|---------|
| PUT | `/orders/:orderId/tags/:tagId` | `updateOrderStatusByTag` |

Also:
- `POST /tags` — `updateOrderStatusesByTag` (bulk)
- `GET /orderTags` — separate router

### Tags (Admin)

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/tags/createTag` | `verifyUser` | `createTag` |
| GET | `/tags` | `verifyAdminAndSeller` | `getAllTags` |
| DELETE | `/tags/:id` | `verifyUser` | `softDeleteTag` |
| PUT | `/tags/:id` | `verifyUser` | `updateTag` |
| GET | `/tags/statuses` | `verifyAdminAndSeller` | `getAllStatuses` |
| GET | `/tags/substatuses/:statusId` | `verifyAdminAndSeller` | `getSubStatusesByStatusId` |

### Products

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/products` | None | `getAllProducts` |
| GET | `/products/gold-products` | `verifySeller` | `getGoldProducts` |
| GET | `/products/gold-product/:id` | None | `getGoldProductById` |
| GET | `/products/featured` | None | `getFeaturedProducts` |
| POST | `/products/featured` | `verifySeller`, validate | `updateFeaturedProducts` |

### Purchase Orders

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/purchase-orders` | `verifyUser`, validate | `getPurchaseOrders` |
| GET | `/purchase-orders/countries` | `verifyAgentAdminAndSeller` | `getAllCountries` |
| GET | `/purchase-orders/:poId` | `verifyUser` | `getSinglePurchaseOrder` |
| PUT | `/purchase-orders/:poId` | `verifyUser` | `updatePurchaseOrder` |
| POST | `/purchase-orders` | `verifyUser`, validate | `createPurchaseOrder` |
| GET | `/purchase-orders/warehouses/country/:countryId` | `verifyUser`, validate | `getWarehousesByCountry` |
| GET | `/purchase-orders/warehouses/:warehouseId/search` | `verifyUser`, validate | `searchSkuInWarehouse` |
| PUT | `/purchase-orders/:poId/mark-as-received` | `verifyUser`, validate | `markAsReceived` |
| PUT | `/purchase-orders/:poId/mark-as-submitted` | `verifyUser`, validate | `markAsSubmitted` |
| POST | `/purchase-orders/warehouses/:warehouseId/validate-variants` | `verifyUser` | `validateCSVVariants` |

### Return Orders

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/return-orders` | `verifyUser`, validate | `getReturnOrders` |
| GET | `/return-orders/:returnId` | `verifyUser` | `getSingleReturnOrder` |
| POST | `/return-orders` | `verifyUser`, validate | `createReturnOrder` |

### Inventory (Seller)

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/inventory/seller-inventory` | `verifySeller` | `getSellerInventory` |
| GET | `/inventory/seller-inventory/export` | `verifySeller` | `exportSellerInventory` |
| GET | `/inventory/purchase-order/:variantId` | `verifySeller` | `getVariantPOs` |
| GET | `/inventory/purchase-order/orders/:variantId` | `verifySeller` | `getInvetoryProductOrders` |
| GET | `/inventory/inventory-movements/:variantId` | `verifySeller` | `getVariantInventoryMovements` |

### Inventory Movements (Admin)

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/inventory-movements/transactions` | `verifyAdminOnly`, validate | `createInventoryTransaction` |
| POST | `/inventory-movements/damaged-bin` | `verifyAdminOnly`, validate | `createDamagedBinMovement` |
| POST | `/inventory-movements/find-variant` | `verifyAdminOnly`, validate | `getVariantBySkuInWarehouse` |
| GET | `/inventory-movements/warehouses` | `verifyAdminOnly` | `getWarehouses` |
| GET | `/inventory-movements/movements` | `verifyAdminOnly`, validate | `getInventoryMovements` |
| PUT | `/inventory-movements/transactions/:id/receive` | `verifyAdminOnly`, validate | `receiveQuantity` |

### Payments

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/payments/create` | `verifySeller` | `createPayment` |
| POST | `/payments/callback` | None | `payTabCallBack` |
| POST | `/payments/redirect` | urlencoded | `payTabRedirect` |
| POST | `/payments/verify` | `verifySeller` | `verifyPayment` |
| GET | `/payments/checkUserSubscription` | `verifySeller` | `checkUserSubscription` |

### Bank Accounts

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/accounts` | `verifySeller`, validate | `createAccount` |
| GET | `/accounts/:userId` | `verifySeller`, validate params | `getUserAccounts` |
| GET | `/accounts/:userId/all` | `verifySeller`, validate params | `getAllUserAccounts` |
| PUT | `/accounts/:id` | `verifySeller`, validate | `updateAccount` |
| DELETE | `/accounts/:id` | `verifySeller`, validate | `deleteAccount` |
| PATCH | `/accounts/:id/set-primary` | `verifySeller`, validate | `setPrimaryAccount` |
| GET | `/accounts/myaccount/:id` | `verifySeller`, validate | `getAccountById` |
| GET | `/accounts/store/:storeId` | `verifySeller`, validate | `getStoreBankAccounts` |

### Stores

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/store` | `verifyAdminAndSellerWithAgencyContext` | `getAllStores` |
| GET | `/store/:id` | `verifyAdminAndSellerWithAgencyContext`, validate | `getStoreById` |
| PUT | `/store/:id` | `verifyAdminAndSellerWithAgencyContext`, validate | `updateStore` |
| DELETE | `/store/:id` | `verifyAdminAndSellerWithAgencyContext`, validate | `deleteStore` |
| GET | `/store/user/:userId` | `verifyAdminAndSellerWithAgencyContext` | `getStoresByUserId` |
| GET | `/store/user/stores/:userId` | `verifyAdminAndSellerWithAgencyContext` | `getStoresByUserId` |
| POST | `/store/check-name` | `verifyAdminAndSellerWithAgencyContext`, validate | `checkStoreName` |
| POST | `/store/create/storeManually` | `verifyAdminAndSellerWithAgencyContext` | `createManualStore` |
| GET | `/store-names` | None | `getAllStoreNames` |

### Tickets

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/tickets` | `verifyJWT`, `verifyAgencyStoreContext`, validate | `getSellerTickets` |
| POST | `/tickets` | `verifyJWT`, `verifyAgencyStoreContext`, validate | `createSellerTicket` |
| POST | `/tickets/admin` | `verifyJWT`, validate | `createAdminTicket` |
| GET | `/tickets/admin` | `verifyJWT`, validate | `getAdminTickets` |
| GET | `/tickets/search-orders` | `verifyJWT`, `verifyAgencyStoreContext`, validate | `searchOrders` |
| GET | `/tickets/user-stores` | `verifyJWT`, `verifyAgencyStoreContext` | `getUserStores` |
| GET | `/tickets/find-store-order` | `verifyJWT`, `verifyAgencyStoreContext`, validate | `findStoreOrder` |
| GET | `/tickets/search/stores` | `verifyJWT`, validate | `searchStores` |
| GET | `/tickets/:ticket_id` | `verifyJWT`, `verifyAgencyStoreContext` | `getTicketById` |
| PUT | `/tickets/:ticket_id` | `verifyJWT`, validate | `updateTicket` |
| GET | `/tickets/:ticket_id/logs` | `verifyJWT`, `verifyAgencyStoreContext`, validate | `getTicketLogs` |

### Comments

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/comments` | `verifyJWT`, validate | `createComment` |
| GET | `/comments/ticket/:ticketId` | `verifyJWT`, validate | `getTicketComments` |

### Invoices

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/invoices` | `verifyUser`, validate | `createInvoices` |
| PUT | `/invoices` | `verifyUser`, validate | `updateInvoices` |
| POST | `/invoices/check-stores` | `verifyUser`, validate | `checkStoresExist` |
| GET | `/invoices/:storeId` | `verifySeller` | `getInvoicesByStore` |
| GET | `/invoices/invoices/download/:id` | None | `downloadInvoice` |

### Agency

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/agency/register` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `registerAgencyStart` |
| POST | `/agency/register/complete` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `completeAgencyRegistration` |
| GET | `/agency/cities` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `getAgencyCities` |
| GET | `/agency/me` | `verifyJWTWithRoles(['Seller', 'Agency'])` | `getCurrentUserAgency` |
| PUT | `/agency/settings` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `updateAgencySettings` |
| POST | `/agency/connect` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `connectMerchantToAgency` |
| GET | `/agency/my-connection` | `verifyJWTWithRoles(['Seller', 'Agency'])` | `getMerchantAgencyConnection` |
| POST | `/agency/my-connection/disconnect` | `verifyJWTWithRoles(['Seller', 'Agency'])` | `disconnectMerchantAgencyConnection` |
| GET | `/agency/dashboard` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `getAgencyDashboard` |
| GET | `/agency/merchants` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `getAgencyMerchants` |
| PATCH | `/agency/merchants/:id/status` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `updateAgencyMerchantConnectionStatus` |
| GET | `/agency/commission` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `getAgencyCommission` |
| GET | `/agency/invoices` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `getAgencyInvoices` |
| GET | `/agency/invoices/:id/download` | `verifyJWTWithRoles(['Seller', 'Agency'])` | `downloadAgencyInvoice` |
| GET | `/agency/team-members` | `verifyJWTWithRoles(['Seller', 'Agency'])` | `getAgencyTeamMembers` |
| POST | `/agency/team-members/invite` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `inviteAgencyMember` |
| DELETE | `/agency/team-members/:id` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `removeAgencyMember` |
| POST | `/agency/team-members/invite/preview` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `previewAgencyInvite` |
| POST | `/agency/team-members/accept` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `acceptAgencyInvite` |
| POST | `/agency/team-members/decline` | `verifyJWTWithRoles(['Seller', 'Agency'])`, validate | `declineAgencyInvite` |

### Agency Admin (Admin Only)

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/admin/agency-registrations/applications` | `verifyAdminOnly`, validate query | `listAgencyApplications` |
| GET | `/admin/agency-registrations/applications/:id` | `verifyAdminOnly`, validate params | `getAgencyApplicationById` |
| GET | `/admin/agency-registrations/commission-models` | `verifyAdminOnly` | `listCommissionModels` |
| GET | `/admin/agency-registrations/commission-models/manage` | `verifyAdminOnly` | `listCommissionModelsWithRules` |
| POST | `/admin/agency-registrations/commission-models` | `verifyAdminOnly`, validate | `createCommissionModel` |
| PUT | `/admin/agency-registrations/commission-models/:id` | `verifyAdminOnly`, validate | `updateCommissionModel` |
| POST | `/admin/agency-registrations/applications/:id/approve` | `verifyAdminOnly`, validate | `approveAgencyApplication` |
| POST | `/admin/agency-registrations/applications/:id/hold` | `verifyAdminOnly`, validate | `holdAgencyApplication` |
| POST | `/admin/agency-registrations/applications/:id/reject` | `verifyAdminOnly`, validate | `rejectAgencyApplication` |
| POST | `/admin/agency-registrations/applications/:id/revert-to-pending` | `verifyAdminOnly`, validate | `revertAgencyApplicationToPending` |
| POST | `/admin/agency-registrations/applications/:id/revoke` | `verifyAdminOnly`, validate | `revokeAgencyLicense` |

### Gold Subscription Admin

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/admin/gold-subscriptions/users/gold` | `verifyAdminOnly`, validate query | `listGoldUsers` |
| GET | `/admin/gold-subscriptions/users` | `verifyAdminOnly`, validate query | `searchUsers` |
| GET | `/admin/gold-subscriptions/users/:userId` | `verifyAdminOnly`, validate params | `getUserDetails` |
| POST | `/admin/gold-subscriptions/give` | `verifyAdminOnly`, validate | `giveGoldAccess` |
| POST | `/admin/gold-subscriptions/extend` | `verifyAdminOnly`, validate | `extendGoldAccess` |
| POST | `/admin/gold-subscriptions/remove` | `verifyAdminOnly`, validate | `removeGoldAccess` |

### Billing (Shopify)

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/billing/status` | `verifySeller` | `checkUserBillingStatus` |
| POST | `/billing/shopify/create` | `verifySeller` | `createShopifySubscription` |
| GET | `/billing/shopify/callback` | None | `handleShopifySubscriptionCallback` |
| GET | `/billing/shopify/stores` | `verifySeller` | `getUserShopifyStores` |

### Thresholds / Ratings

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| POST | `/data/thresholds` | validate | `addOrUpdateThreshold` |
| GET | `/data/thresholds` | None | `getThresholds` |

### S3

| Method | Path | Notes |
|--------|------|-------|
| (various) | `/s3/*` | Presigned URL generation and file operations |

### Ticker Config

| Method | Path | Middleware | Handler |
|--------|------|-----------|---------|
| GET | `/ticker-config` | None | `getSettings` |
| PUT | `/ticker-config/admin` | `verifyUser` | `updateSettings` |

### Sub-statuses

| Method | Path | Handler |
|--------|------|---------|
| GET | `/sub-statuses` | `getSubstatusesByStatusName` |

### AI Creative Analytics

| Method | Path | Notes |
|--------|------|-------|
| (various) | `/creative-analytics/*` | AI video creator routes (feature appears commented out in frontend) |

### Proxy

| Method | Path | Notes |
|--------|------|-------|
| (various) | `/proxy/*` | Proxy routes |

---

## 12. Store Integrations

Zambeel integrates with the following e-commerce platforms:

| Platform | Auth Type | Webhooks | Routes |
|----------|-----------|----------|--------|
| **Shopify** | OAuth 2.0 | Products, Orders | `/shopify/*` |
| **Salla** (Saudi) | OAuth 2.0 | Order Created | `/salla/*` |
| **YouCan** | OAuth 2.0 | Order webhook | `/youcan/*` |
| **LightFunnels** | Integration | Orders | `/lightfunnels/*` |
| **EasyOrder** | Integration | Orders | `/easyorders/*` |
| **Manual** | N/A (no platform) | None | `POST /store/create/storeManually` |

### Shopify Specifics
- OAuth flow: `GET /shopify/auth` → Shopify → callback
- Check store existence: `GET /shopify/check-store-exists`
- Bind store to user: `POST /shopify/bind-store`
- Check user login status: `GET /shopify/checkUser`
- Delete specific webhooks: `DELETE /shopify/webhooks/delete`
- Shopify App installation status check: `POST /shopify/app/installation-status`

### Salla Specifics
- OAuth flow: `GET /salla/auth` → Salla → callback
- Disconnect: `DELETE /salla/disconnect`
- Order created webhook: `POST /salla/order/created`

### YouCan Specifics
- OAuth flow: `GET /youcan/auth` → YouCan → callback
- Store info: `GET /youcan/store-info`
- Disconnect: `POST /youcan/disconnect`
- Webhook handler: `POST /youcan/webhooks`
- Unsubscribe webhooks: `DELETE /youcan/webhooks/delete`

---

## 13. Webhook Integrations

Inbound webhooks at `/webhooks/*`:

| Source | Path | Purpose |
|--------|------|---------|
| Shopify | `/webhooks/shopify/*` | Product/order sync |
| Shopify App | `/webhooks/shopifyApp/*` | App lifecycle events |
| Salla | `/webhooks/salla/*` | Order sync |
| LightFunnels | `/webhooks/lightFunnels/*` | Order sync |
| EasyOrder | `/webhooks/easyOrder/*` | Order sync |
| YouCan | `/webhooks/youcan/*` | Order sync |
| Smartlane | `/webhooks/smartlane/*` | Courier tracking updates |

---

*End of Zambeel Platform Documentation*

## UI Selector Reference — Admin Portal (OMS)

### Commission Models (/orders-management/commission-models)
- Page title: 'Commission Models'
- Create button text: '+ New Model'
- Empty state button: 'Create First Model'
- Modal title: 'Create Commission Model'
- Field label: 'Model Name*' — placeholder: 'Enter model name'
- Field label: 'Value* (%)' — number input
- Field label: 'Country*' — dropdown
- Field label: 'Type*' — dropdown options: '% of Revenue', 'Flat per Order'
- Add rule button: '+ Add Rule'
- Save button: 'Save Model'
- Cancel button: 'Cancel'
- Table has Edit button per row
- Alert text: 'Each country can only appear once inside the same model.'

### Orders (/orders-management/orders)
- Search placeholder: 'Search orders'
- Tabs: 'All Orders', 'Confirmation Pending', 'Approved', 'Dispatching in Process', 'In Delivery', 'Undelivered', 'Delivered', 'Return in Transit', 'Return', 'Cancelled'
- Filter button: 'Filter'
- Actions dropdown button: 'Actions'
- Actions include: 'Update Statuses', 'Upload Orders', 'Approve', 'Cancel', 'Update Tag', 'Update Remarks', 'Assign Courier'
- Empty state: 'No orders found'

### Agency Registrations (/orders-management/agency-registrations)
- Page title: 'Agency Registrations'
- Tabs: 'All', 'Pending', 'Approved', 'OnHold', 'Rejected'
- Row action button: 'Review'
- Approve button: 'Approve Agency'
- Hold button: 'Put on Hold'
- Reject button: 'Confirm Reject'
- Commission model selector: 'Select commission model'

### Gold Subscriptions (/orders-management/gold-subscriptions)
- Search options: 'Email', 'Phone', 'User ID'
- Buttons: 'Search', 'Clear'
- Tabs: 'All users', 'Gold users'
- User action: 'View Details', 'Give Gold Access', 'Extend Gold Access', 'Remove Gold Access'

### Agents (/orders-management/agents)
- Search placeholder: 'Search by Name, Email or Country'
- Create button: 'Create Agent'
- Modal fields: 'Full Name' (placeholder: 'John Doe'), 'Email', 'Phone Number', 'Country', 'Team'

### IMPORTANT: React Playwright Selector Rules
Since this is a React/Tailwind app with NO IDs on elements, always use these selector patterns:
- Buttons: button:has-text('exact button text') or role=button[name='text']
- Inputs by label: input[placeholder='exact placeholder text']
- Inputs by nearby label text: label:has-text('Label Text') + input
- Navigation: a:has-text('Menu Item Text')
- Modals: div[role='dialog'] or .modal
- Tables: table or [role='grid']
- Form submission: button:has-text('Save Model'), button:has-text('Confirm')
- Never use #id selectors — this React app does not use element IDs
