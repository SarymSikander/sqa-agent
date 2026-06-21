# OMS — Pages Reference (VERIFIED from live portal screenshots)

> Source: 12 screenshots of portal.myzambeel.com — all page titles and routes confirmed.
> Last verified: 2026-05-01

## Route Map (confirmed)

| Route | Verified Page Title (h1) | Component | Role | Purpose |
|-------|--------------------------|-----------|------|---------|
| `/orders-management/dashboard` | (KPI dashboard) | `OrdersDashBoard` | Admin/Agent | Real-time order analytics and KPI metrics |
| `/orders-management/orders` | **Orders Management** | `Orders` | Admin/Agent | All orders; filter, search, edit, approve, cancel |
| `/orders-management/dispatch-batches` | **Dispatch Batches** | `DispatchBatches` | Admin only | Generate tracking IDs, download courier documents |
| `/orders-management/agents` | **Agents** | `AgentsTable` | Admin only | View and create agent accounts |
| `/orders-management/ratings-settings` | (Ratings/Thresholds) | `ThresholdManager` | Admin only | Seller performance rating thresholds by country |
| `/orders-management/stores-settings` | **Integrated Stores** | `OmsStoreSettingsPage` | Admin only | View and edit all seller stores |
| `/orders-management/tags-management` | (Tags Management) | `TagsManagementPage` | Admin only | CRUD on order tags |
| `/orders-management/purchase-orders` | (Purchase Orders) | `PurchaseOrdersPage` | Admin only | IMS purchase order list and creation |
| `/orders-management/purchase-orders/create` | (Create PO) | `CreatePurchaseOrderComponent` | Admin only | Create a new purchase order |
| `/orders-management/purchase-orders/:poId/receive` | (Receive PO) | `ReceiveItemsComponents` | Admin only | Mark quantities received for a PO |
| `/orders-management/purchase-orders/:poId/submit` | (Submit PO) | `SubmitPurchaseOrderComponent` | Admin only | Submit PO to warehouse |
| `/orders-management/return-orders` | (Return Orders) | `ReturnOrdersPage` | Admin only | IMS return order list |
| `/orders-management/return-orders/create` | (Create Return) | `CreateReturnOrderComponent` | Admin only | Create a new return order |
| `/orders-management/ticketing` | **Ticketing Management** | `TicketingV2` | Admin/Agent | Admin ticket queue |
| `/orders-management/inventory-movements` | **Inventory Movements** | `InventoryMovements` | Admin only | Warehouse inventory movement management |
| `/orders-management/gold-subscriptions` | **Gold Subscription Management** | `OMSGoldSubscriptionsPage` | Admin only | Grant/extend/remove seller gold subscriptions |
| `/orders-management/agency-registrations` | **Agency Registrations** | `AgencyRegistrationsPage` | Admin only | Review and action agency applications |
| `/orders-management/commission-models` | **Commission Models** | `CommissionModelsPage` | Admin only | CRUD on agency commission models |
| `/orders-management/invoice-upload` | (Invoice Upload) | `InvoiceUploadPage` | Admin only | Upload invoices for seller stores |
| `/orders-management/invoice-update` | (Invoice Update) | `InvoiceUpdatePage` | Admin only | Update existing invoices |
| `/orders-management/ticker-config` | **Global Ticker Configuration** | `TickerConfigPage` | Admin only | Configure marquee ticker bar |
| `/orders-management/contracts` | **Contracts** | `OMSContractsPage` | Admin only | Manage contract templates and seller contracts |
| `/orders-management/broadcast-notifications` | **Broadcast Notifications** | `BroadcastNotificationsPage` | Admin only | Send FYI messages to sellers; view delivery analytics |
| `/orders-management/profile` | (Profile) | `Profile` | Admin/Agent | Admin user profile page |

> **Bold** = h1 text confirmed from screenshot. Others are inferred from source code.

---

## Page-by-Page Detail (verified from screenshots)

### Orders (`/orders-management/orders`)
**h1:** `Orders Management`

**Country dropdown (top right):**
Saudi Arabia (KSA) | United Arab Emirates (UAE) | Kuwait | Qatar | Pakistan | Oman | Bahrain | Iraq

**Status tabs (confirmed exact text, left → right):**
```
All Orders | Confirmation Pending | Approved | Dispatching In Process |
Shipped | Undelivered | Delivered | Return in Transit | Return | Cancelled
```
> ⚠️ Tab 5 is **Shipped** — NOT 'In Delivery'. Updated from previous documentation.
> ⚠️ Tab 4 is **Dispatching In Process** (capital I in 'In').

**Search:** `input[placeholder='Search orders']`

**Buttons:** `Filter` | `Actions`

> ⚠️ CRITICAL — Actions button pattern (applies to ALL tables with row checkboxes):
> The Actions button/dropdown is DISABLED by default.
> It only becomes ENABLED after at least one table row checkbox is selected.
> ALWAYS follow this exact sequence for any test that uses Actions:
> ```
> SELECT_ROW: nth=0          ← click first row checkbox
> WAIT: 500                  ← wait for Actions to enable
> CLICK: button:has-text('Actions')   ← now clickable
> CLICK_OPTION: Revert       ← click the option inside Actions dropdown
> ```
> Never skip SELECT_ROW and WAIT — Actions will be disabled and the test will fail.

> CRITICAL — Actions button pattern:
> - Actions button is disabled by default
> - Must select at least one row checkbox first (SELECT_ROW: nth=0)
> - Only then does Actions become clickable
> - Applies to ALL order table pages: Confirmation Pending, Dispatching in Process, etc.

**Table columns (confirmed):**
ORDER ID | TICKET | STORE INFO | ORDER DATE | CUSTOMER NAME | PHONE NUMBER | AMOUNT | TAG | TRUSTED | STATUS | SUB-STATUS | COURIER | BATCH ID | TRACKING ID

---

### Orders Filter Modal

**Modal title:** `Filters`

**Filter fields (exact placeholders confirmed):**
- `Order ID (comma-separated for multiple)`
- `Order # (comma-separated for multiple)`
- `Tracking #`
- `Customer Name`
- `Phone Number`
- `Store URL`
- `Activity Counter`
- Date range: `dd/mm/yyyy` (two inputs)

**Dropdown filter labels:**
Select Tags | Select Sub-Status | Select Remarks | Select Platform | Select Store | Assigned Agent | Select Bifurcation | Select City | Select Courier | Select Batch ID

**Buttons:** `Clear all filters` | `Apply filter`

---

### Order Details Modal

**Modal title:** `Order Details`
**Subtitle format:** `Order #NNNN` (e.g. `Order #2223`)

**Tabs:** Overview | Timeline | Conversation

**Overview tab — sections:**

| Section | Fields |
|---------|--------|
| Header fields | Store Name, Customer Name, Order#, Order Date, Payment Method |
| Order Items | PRODUCT, SKU, QUANTITY, PRICE |
| Delivery Address | Address, Phone Number, Country, City, Area Name, Building/Society, National Address Short Code |
| Financial Summary | Subtotal, Discount, Tax, Shipping, Total, Website Price |
| Bottom controls | Update Tag, Activity Counter |

**Action buttons:** `Edit Order` | `Approve Order` | `Cancel Order` | `Save`

---

### Dispatch Batches (`/orders-management/dispatch-batches`)
**h1:** `Dispatch Batches`
**Subtitle:** `Generate tracking IDs and download combined courier documents.`

**Filters:** Country dropdown | Status dropdown | Vendor dropdown | Courier dropdown | Date range (dd/mm/yyyy)

**Search:** `input[placeholder='Search orders...']` (note: three dots, not zero)

**Table columns (confirmed):**
BATCH ID | CREATED BY | CREATED DATE/TIME | VENDOR ID | COURIER NAME | COURIER REQUEST ID | TOTAL ORDERS | TRACKING STATUS | GENERATE TRACKING ID | DOWNLOAD DOCUMENT

**Tracking status badges:** `Generated` (green) | `Partial` (orange) | `New` | `Generating` | `Failed`

**Per-row buttons:** `Generate Tracking ID` | `Generate & Download` | `Download Combined Doc`

---

### Agents (`/orders-management/agents`)
**h1:** `Agents`

**Controls:**
- Search: `input[placeholder='Search by Name, Email or Country']`
- Button: `+ Create Agent` (purple, top right)

**Table columns (confirmed):** Name | Email | Phone | Country | Status | Team

**Status badges:** `Active` (green)

**Create Agent modal fields:** Full Name (placeholder: `John Doe`) | Email | Phone Number | Country | Team

---

### Stores Settings (`/orders-management/stores-settings`)
**h1:** `Integrated Stores`
> ⚠️ Page title is **Integrated Stores**, NOT 'Stores Settings'

**Controls:**
- Checkbox: `Show untrusted Manual stores only`
- Search: `input[placeholder='Search by Store Name or URL']`

**Table columns (confirmed):**
STORE URL | STORE ID | STORE NAME | PLATFORM | BIFURCATION | USER ID | CONFIRMATION SETTINGS | TRUSTED

**Badges:** `Dropshipper` (blue pill, with dropdown arrow for bifurcation) | `Trusted` (green)

---

### Ticketing (`/orders-management/ticketing`)
**h1:** `Ticketing Management`
> ⚠️ OMS ticketing title is **Ticketing Management** — differs from Seller portal's 'Ticketing System'

**Stats cards (confirmed labels):**
Total Tickets | Pending | In Progress | Awaiting Seller Action | Resolved

**Tabs:** `Tickets Assigned to Zambeel` | `Tickets Assigned by Zambeel`

**Filter:** Store Name dropdown | `input[placeholder='Search by store name...']` | `Search` button

**Primary button:** `+ Create New Ticket` (purple)

**Table columns (confirmed):**
TICKET ID | CATEGORY | SUB-CATEGORY | ORDER ID | DATE | STATUS | ACTIONS

**Status badges:** `Pending` (yellow) | `Resolved` (green) | `In Progress` (blue) | `Awaiting Seller Action`

**Row action:** `View` button

---

### Gold Subscription Management (`/orders-management/gold-subscriptions`)
**h1:** `Gold Subscription Management`
**Subtitle:** `View all users, search in the database, and manage Gold access from OMS.`
> ⚠️ Page title is **Gold Subscription Management** (singular), NOT 'Gold Subscriptions'

**Search controls:**
- Search-by dropdown (confirmed options): `Email` | `Phone` | `User ID`
- Search input placeholder: `Enter user email` (when Email is selected)
- Buttons: `Search` | `Clear`

**Tabs:** `All users` | `Gold users`

**Table columns (confirmed):**
USER ID | EMAIL | TOTAL STORES | SUBSCRIPTION STATUS | EXPIRY DATE | ACTIONS

**Status badges:** `Free` (gray) | `Gold` (gold/amber)

**Row action:** `View Details` button

---

### Inventory Movements (`/orders-management/inventory-movements`)
**h1:** `Inventory Movements`

**Primary button:** `+ Add Inventory Movement` (purple, top right)
> ⚠️ Button text is **'+ Add Inventory Movement'**, not 'Create Inventory Movement'

**Search controls:**
- Search-by dropdown (default: `Movement ID`)
- Search input: `input[placeholder='Search Movement ID']`
- Search submit: icon button (magnifying glass)

**Filter buttons:** `Date` | `Filters`

**Table columns (confirmed):**
MOVEMENT ID | TYPE | WAREHOUSE | STATUS | MOVED BY | DATE

**Movement type badges (confirmed colors):**
`Warehouse → Warehouse` (purple) | `SKU → SKU` (blue) | `To Damaged Bin` (red)

**Status badges:** `In Transit` (yellow) | `Received` (green)

---

### Ticker Config (`/orders-management/ticker-config`)
**h1:** `Global Ticker Configuration`
**Subtitle:** `This is where the Admin will manage the banner.`
> ⚠️ Page title is **Global Ticker Configuration**, NOT 'Ticker Config'

**Form fields (confirmed labels):**
- `Ticker Config` — toggle on/off
- `Ticker Message` — text input
- `Ticker Background Color` — color picker
- `Ticker Text Color` — color picker

**Submit button:** `Update Global Ticker`
> ⚠️ Button text is **'Update Global Ticker'**, NOT 'Save'

---

### Agency Registrations (`/orders-management/agency-registrations`)
**h1:** `Agency Registrations`
**Subtitle:** `Review and manage agency applications.`

**Status tabs (confirmed):** All | Pending | Approved | OnHold | Rejected

**Table columns (confirmed):** Name | Country | POC | Status | License | Submitted | (action column)

**Status badges:** `Pending` (yellow) | `Approved` (green) | `OnHold` (orange) | `Rejected` (red)

**License values (confirmed):** `Active` | `Inactive`

**Row action:** `Review` (blue link-style button)

---

### Commission Models (`/orders-management/commission-models`)
**h1:** `Commission Models`
**Subtitle:** `Define per-country commission rates for agencies.`

**Primary button:** `+ New Model` (purple, top right)

**Model card elements (confirmed):**
- Model name (dynamic heading)
- Agencies assigned count (e.g. "2 agencies assigned")
- `✏ Edit` button (top right of each card — includes pencil emoji)

**Table inside each model card (confirmed columns):**
Country | Commission Type | Value | Currency

**Commission type values (confirmed from live UI):**
`Flat per Order` | `% of Revenue`

**Create/Edit drawer fields:**
- `input[placeholder='Enter model name']` — Model Name*
- Country* — Flowbite dropdown (trigger: `button:has-text('Select')`)
- Type* — `% of Revenue` or `Flat per Order`
- Value* — `input[type='number']` (no placeholder)
- Currency* — `input[placeholder='AED']` (auto-fills, disabled)

**Drawer buttons:** `+ Add Rule` | `Remove rule` | `Save Model` | `Cancel`

**Empty state button:** `Create First Model`

**Validation alert:** `Each country can only appear once inside the same model.`

---

### Contracts (`/orders-management/contracts`)

**h1:** "Contracts"
**Sub-text:** "Manage contract templates and seller contracts"

**Two-tab layout:**

| Tab | Purpose |
|-----|---------|
| **Templates** | Create, edit, delete reusable contract bodies |
| **Contracts** | Create, view, revoke, and track contracts sent to sellers |

**Templates tab UI:**
- Table columns: Name | Created By | Created Date | Actions (Edit | Delete)
- `+ New Template` button
- Create/Edit: modal with Name field + rich text content editor
- Delete: confirm modal "Delete this template?"

**Contracts tab UI:**
- Search input: placeholder "Search by seller or contract title..."
- Status filter: All / Draft / Pending / Approved / Revoked
- Table columns: Seller | Title | Status | Sent Date | Signed Date | Actions
- Status badges: Draft (gray) | Pending (amber) | Approved (green) | Revoked (red)
- Per-row actions: View (eye) | Edit (pencil, Draft only) | Revoke (Draft/Pending/Approved, confirm) | Delete (trash, Draft only)
- `New Contract` button → opens `CreateContractWizard` (3-step: pick template + seller → edit content → send/save as draft)
- Pagination: 10 per page; "Page N of N · total" + Previous/Next buttons

**Revoke confirm modal message:** "Revoking [title] cannot be undone. The seller will still see it with a Revoked status. To re-engage them you must create a new contract."

**Delete confirm modal message:** "Delete the draft [title]? This permanently removes it."

**API:** See `knowledge/contracts/business_logic.md` for all 16 endpoints.

---

### Broadcast Notifications (`/orders-management/broadcast-notifications`)

**h1:** "Broadcast Notifications"
**Sub-text:** "Send FYI communications to sellers via the platform. Compose individually, upload via CSV, or review delivery analytics in the sent log."

**Three-tab layout:**

| Tab | Icon | Purpose |
|-----|------|---------|
| **Compose** (`compose`) | Send icon | Manual single or all-sellers notification compose form |
| **CSV** (`csv`) | FileSpreadsheet icon | Upload CSV to send personalised bulk notifications |
| **Sent Log** (`sent-log`) | History icon | Paginated sent log with read/unread analytics |

**Compose tab form fields:**
| Field | Type | Constraints |
|-------|------|-------------|
| Title | Text input | Max 100 chars |
| Message | Textarea | Max 500 chars |
| Category | Select | Pricing / Inventory / Zambeel Updates / Payments |
| Expiry Date | Date-time picker | Must be a future date (min: 1 minute from now) |
| Image | File upload / drag-drop | Optional; S3-hosted |
| Recipients | Toggle: "Select sellers" or "Send to all sellers" | All-sellers mode requires 6-digit PIN (shown in modal) |
| Seller search | Search by email / phone / user ID (when targeted mode) | Results from `/admin/broadcast-notifications/sellers/search` |

**Live preview:** Right panel shows `SellerNotificationPreview` as the compose form is filled.

**CSV tab:**
- Download CSV template button
- Upload / drag-drop CSV file
- `Validate CSV` button → shows per-row errors if invalid
- `Send Notifications` button (enabled only after successful validation)
- Error display: per-row errors with row number

**Sent Log tab:**
- Paginated table: Title | Category | Sent At | Recipients | Read | Unread | Expiry | Actions
- Click row → opens detail drawer with per-recipient list (Username | Email | Phone | Read At)
- Detail pagination: 10 recipients per page

**API:** See `knowledge/notifications/broadcast.md` for all 11 endpoints.

---

## ⚠️ Corrections to Previous Documentation

| Page | Previous (wrong) | Correct (verified) |
|------|-----------------|-------------------|
| `/orders-management/orders` | h1: 'Orders' | h1: **Orders Management** |
| `/orders-management/orders` | Tab: 'In Delivery' | Tab: **Shipped** |
| `/orders-management/orders` | Tab: 'Dispatching in Process' | Tab: **Dispatching In Process** |
| `/orders-management/stores-settings` | h1: 'Stores Settings' | h1: **Integrated Stores** |
| `/orders-management/ticketing` | h1: 'Ticketing System' | h1: **Ticketing Management** |
| `/orders-management/gold-subscriptions` | h1: 'Gold Subscriptions' | h1: **Gold Subscription Management** |
| `/orders-management/inventory-movements` | btn: 'Create Inventory Movement' | btn: **+ Add Inventory Movement** |
| `/orders-management/ticker-config` | h1: 'Ticker Config' | h1: **Global Ticker Configuration** |
| `/orders-management/ticker-config` | btn: 'Save' | btn: **Update Global Ticker** |
| `/orders-management/commission-models` | Edit btn: 'Edit' | Edit btn: **✏ Edit** |
| Filter modal | btn: 'Apply Filters' | btn: **Apply filter** |
| Filter modal | btn: 'Reset' | btn: **Clear all filters** |
| Filter modal | search: 'Search orders' | Dispatch search: **'Search orders...'** (with ellipsis) |
