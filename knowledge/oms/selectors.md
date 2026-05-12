# OMS — UI Selectors Reference (VERIFIED from live staging portal)

> Source: Playwright live exploration of https://staging.myzambeel.com as admin
> Last updated: 2026-05-12

## Selector Rules (React + Tailwind — No IDs)
- **Buttons:** `button:has-text('exact text')`
- **Inputs:** `input[placeholder='exact placeholder']`
- **Navigation links:** `a:has-text('Menu Item')`
- **Modals/drawers:** `div[role='dialog']`
- **Labels → inputs:** `label:has-text('Label') >> input`
- **NEVER use** `#id` selectors — this app has none

---

## Sidebar Navigation

```
a:has-text('Dashboard')              → /orders-management/dashboard
a:has-text('Orders')                 → /orders-management/orders
a:has-text('Dispatch Batches')       → /orders-management/dispatch-batches
a:has-text('Agents')                 → /orders-management/agents
a:has-text('Ratings Settings')       → /orders-management/ratings-settings
a:has-text('Stores Settings')        → /orders-management/stores-settings
a:has-text('Tags Management')        → /orders-management/tags-management
a:has-text('Purchase Orders')        → /orders-management/purchase-orders
a:has-text('Return Orders')          → /orders-management/return-orders
a:has-text('Ticketing')              → /orders-management/ticketing
a:has-text('Gold Subscriptions')     → /orders-management/gold-subscriptions
a:has-text('Inventory Movements')    → /orders-management/inventory-movements
a:has-text('Ticker Config')          → /orders-management/ticker-config
a:has-text('Agency Registrations')   → /orders-management/agency-registrations
a:has-text('Commission Models')      → /orders-management/commission-models
a:has-text('Invoice Upload')         → /orders-management/invoice-upload
a:has-text('Update Invoice')         → /orders-management/invoice-update
```

---

## Orders Page (`/orders-management/orders`)

### Page Header
```
h1:has-text('Orders Management')
```

### Status Filter Buttons (top row — these are buttons, NOT tabs)
```
button:has-text('All Orders')
button:has-text('Confirmation Pending')
button:has-text('Approved')
button:has-text('Dispatching in Process')
button:has-text('Shipped')
button:has-text('Undelivered')
button:has-text('Delivered')
button:has-text('Return in Transit')
button:has-text('Return')
button:has-text('Cancelled')
```

### Filter Controls
```
input[placeholder='Search orders']          # text search
select                                       # Country filter — native <select>
# Country options (verified):
# Saudi Arabia (KSA), United Arab Emirates (UAE), Kuwait, Qatar,
# Pakistan, Oman, Bahrain, Iraq, United States (USA)

button:has-text('Filter')                   # opens advanced filter panel
button:has-text('Actions')                  # bulk actions dropdown
```

### Table Column Headers (verified live)
```
th:has-text('ORDER ID')
th:has-text('TICKET')
th:has-text('STORE INFO')
th:has-text('ORDER DATE')
th:has-text('CUSTOMER NAME')
th:has-text('PHONE NUMBER')
th:has-text('AMOUNT')
th:has-text('TAG')
th:has-text('TRUSTED')
th:has-text('Status')
th:has-text('SUB-STATUS')
th:has-text('COURIER')
th:has-text('BATCH ID')
th:has-text('TRACKING ID')
```

### Pagination
```
select                                       # per-page: 10, 15, 20, 25, 50, 100
```

---

## Inventory Movements (`/orders-management/inventory-movements`)

### Page Header
```
h2:has-text('Inventory Movements')
```

### Controls
```
input[placeholder='Search Movement ID']     # text search
button:has-text('Add Inventory Movement')   # opens Create modal
button:has-text('Date')                     # date range picker
button:has-text('Filters')                  # opens Filters panel
```

### Search Type Filter (native `<select>` left of search input)
```
select                                       # options: Movement ID, SKU Code, Warehouse
```

### Filters Panel (opens on button:has-text('Filters'))
```
# Movement Type native <select> — options:
# SKU → SKU, Warehouse → Warehouse, To Damaged Bin

# Warehouse native <select> — options:
# Bahrain, Iraq, Karachi, KSA, Kuwait, Oman, Qatar, UAE, United States

# Reason native <select> — options (SKU→SKU only):
# SKU Merge, Wrong SKU Mapping, Repackaging, Services Deal,
# Variant Consolidation, Internal Adjustment
```

### Table Column Headers (verified live)
```
th:has-text('MOVEMENT ID')
th:has-text('TYPE')
th:has-text('WAREHOUSE')
th:has-text('STATUS')
th:has-text('MOVED BY')
th:has-text('DATE')
```

### Pagination
```
page.locator('select').last()                # rows per page — last <select> on page
                                             # options: 10, 25, 50, 100
button:has-text('< Previous')               # previous page
button:has-text('Next >')                   # next page
button:has-text('1')                        # page number buttons
text='Page 1 of'                            # page info text
input                                        # go-to-page input (near text 'Go to page')
```

---

## Ticketing Page (`/orders-management/ticketing`)

### Page Header
```
h2:has-text('Ticketing Management')          # ⚠️ h2, NOT h1
```

### Tab Buttons
```
button:has-text('Tickets Assigned to Zambeel')
button:has-text('Tickets Assigned by Zambeel')
```

### Filter Controls
```
select                                       # filter type — native <select>
# Filter type options (verified live):
# Store Name, Store ID, Status, Team ID, Ticket Number

input[placeholder='Search by store name...']  # placeholder changes with filter type
button:has-text('Search')
```

### Primary Action Button
```
button:has-text('Create New Ticket')         # ⚠️ NO '+' prefix
```

### Table Column Headers (OMS admin view — verified live)
```
th:has-text('TICKET ID')
th:has-text('CATEGORY')
th:has-text('SUB-CATEGORY')
th:has-text('ORDER ID')                      # ⚠️ OMS uses 'ORDER ID', seller uses 'ORDER NUMBER'
th:has-text('DATE')
th:has-text('STATUS')
th:has-text('ACTIONS')
```

### Pagination
```
button:has-text('Previous')
button:has-text('Next')
```

---

## Commission Models (`/orders-management/commission-models`)

### Page Header
```
h1:has-text('Commission Models')
```

### List Actions
```
button:has-text('+ New Model')               # opens Create modal
button:has-text('Edit')                      # edit existing model (per-row)
```

### Table Column Headers (inside each model card)
```
th:has-text('Country')
th:has-text('Commission Type')
th:has-text('Value')
th:has-text('Currency')
```

### Create / Edit Model Modal
```
div[role='dialog']

# Close:
button:has-text('✕')

# Form fields:
label:has-text('Model Name*')
input[placeholder='Enter model name']

label:has-text('Commission Rules')
button:has-text('+ Add Rule')
button:has-text('Remove rule')

# Per-rule fields:
label:has-text('Country*')
select                     # options: Select, Bahrain, Iraq, Kuwait, Oman, Pakistan,
                           #          Qatar, Saudi Arabia, UAE, United States

label:has-text('Type*')
select                     # options: % of Revenue, Flat per Order

label:has-text('Value* (%)')
input[type='number']       # commission value

label:has-text('Currency*')
input[placeholder='AED']   # currency code text input (e.g. AED, SAR, KWD)

# Actions:
button:has-text('Cancel')
button:has-text('Save Model')
```

---

## Dispatch Batches (`/orders-management/dispatch-batches`)

### Page Header
```
h1:has-text('Dispatch Batches')
```

### Filter Controls (all native `<select>` elements)
```
input[placeholder='Search orders...']

select    # Country: Select Country, Bahrain, Iraq, Kuwait, Oman, Pakistan,
          #          Qatar, Saudi Arabia, UAE, United States

select    # Status: Status, New, Generating, Partial, Generated, Failed

select    # Vendor (e.g. Zambeel Bahrain Warehouse)

select    # Courier

input[placeholder='From']     # type='date'
input[placeholder='To']       # type='date'
```

### Table Column Headers (verified live)
```
th:has-text('BATCH ID')
th:has-text('CREATED BY')
th:has-text('CREATED DATE/TIME')
th:has-text('VENDOR ID')
th:has-text('COURIER NAME')
th:has-text('TOTAL ORDERS')
th:has-text('TRACKING STATUS')
th:has-text('GENERATE TRACKING ID')
th:has-text('DOWNLOAD DOCUMENT')    # only enabled when TRACKING STATUS = 'Generated'
```

### Status Values (Tracking Status)
```
# New, Generating, Partial, Generated, Failed
```

### Pagination
```
select    # per-page: 10, 15, 20, 25, 50, 100
```

---

## Purchase Orders (`/orders-management/purchase-orders`)

### Page Header
```
h2:has-text('Purchase Orders')
```

### Controls
```
input[placeholder='Search PO ID or Country']
button:has-text('Create Purchase Order')
button:has-text('Date')
button:has-text('Filters')
button:has-text('Export')
```

### Table Column Headers (verified live)
```
th:has-text('PO ID')
th:has-text('DATE')
th:has-text('COUNTRY')
th:has-text('CREATED BY')
th:has-text('STATUS')
th:has-text('ACTIONS')
```

### Create Purchase Order (opens full page, not dialog)
```
button:has-text('Back to Purchase Orders')

label:has-text('Country')
select    # options: 🇧🇭 Bahrain, 🇮🇶 Iraq, 🇰🇼 Kuwait, 🇴🇲 Oman, 🇵🇰 Pakistan,
          #          🇶🇦 Qatar, 🇸🇦 Saudi Arabia, 🇦🇪 UAE, 🇺🇸 United States

label:has-text('Date')
label:has-text('Target Location')
select    # warehouse options (country-dependent)

label:has-text('SKU')
input[placeholder='Search for SKU...']

label:has-text('Quantity')

button:has-text('Add')
button:has-text('Browse files')
button:has-text('Cancel')
button:has-text('Save a Draft')
button:has-text('Submit Purchase Order')
```

### Pagination
```
select    # per-page: 10, 15, 20, 25, 50, 100
```

---

## Return Orders (`/orders-management/return-orders`)

### Page Header
```
h2:has-text('Return Orders')
```

### Controls
```
input[placeholder='Search Return ID or Country']
button:has-text('Create Return Order')
button:has-text('Date')
button:has-text('Export')
```

### Table Column Headers (verified live)
```
th:has-text('RETURN ID')
th:has-text('DATE')
th:has-text('COUNTRY')
th:has-text('CREATED BY')
th:has-text('ACTIONS')
```

### Create Return Order (opens full page, not dialog)
```
button:has-text('Back to Return Orders')

label:has-text('Country')
select    # options: 🇧🇭 Bahrain, 🇮🇶 Iraq, 🇰🇼 Kuwait, 🇴🇲 Oman, 🇵🇰 Pakistan,
          #          🇶🇦 Qatar, 🇸🇦 Saudi Arabia, 🇦🇪 UAE, 🇺🇸 United States

label:has-text('Date')
label:has-text('Target Location')
label:has-text('SKU')
input[placeholder='Search for SKU...']
label:has-text('Quantity')

button:has-text('Add')
button:has-text('Browse files')
button:has-text('Cancel')
button:has-text('Submit Return Order')
```

### Pagination
```
select    # per-page: 10, 15, 20, 25, 50, 100
```

---

## Agency Registrations (`/orders-management/agency-registrations`)

### Page Header
```
h1:has-text('Agency Registrations')
```

### Status Filter Buttons
```
button:has-text('All')
button:has-text('Pending')
button:has-text('Approved')
button:has-text('OnHold')
button:has-text('Rejected')
button:has-text('Review')
```

### Table Column Headers (verified live)
```
th:has-text('Name')
th:has-text('Country')
th:has-text('POC')
th:has-text('Status')
th:has-text('License')
th:has-text('Submitted')
```

---

## Agents (`/orders-management/agents`)

### Controls
```
input[placeholder='Search by Name, Email or Country']
button:has-text('Create Agent')
```

### Table Column Headers (verified live)
```
th:has-text('Name')
th:has-text('Email')
th:has-text('Phone')
th:has-text('Country')
th:has-text('Status')
th:has-text('Team')
```

### Create Agent Modal
```
div[role='dialog']

label:has-text('Full Name')
input[placeholder='John Doe']

label:has-text('Email')
input[placeholder='johndoe@example.com']

label:has-text('Phone Number')
input[placeholder='+1234567890']

label:has-text('Country')
input[placeholder='Select Country']

label:has-text('Team')
select[name='team']
# Team options: Select a Team, Account Managers, AM Team, Call Center,
#   Development Team, Marketing Team, NDR Team, OP Team, Sales Team, Support Team

button:has-text('Create Agent')
button:has-text('Cancel')
```

### Pagination
```
select    # per-page: 10, 15, 20, 25, 50, 100
```

---

## Gold Subscriptions (`/orders-management/gold-subscriptions`)

### Page Header
```
h1:has-text('Gold Subscription Management')
```

### Filter Controls
```
select              # search type: Email, Phone, User ID
input[placeholder='Enter user email']
button:has-text('Search')
button:has-text('Clear')
```

### User Filter Tabs
```
button:has-text('All users')
button:has-text('Gold users')
```

### Table Column Headers (verified live)
```
th:has-text('USER ID')
th:has-text('EMAIL')
th:has-text('TOTAL STORES')
th:has-text('SUBSCRIPTION STATUS')
th:has-text('EXPIRY DATE')
th:has-text('ACTIONS')
```

### Per-Row Action
```
button:has-text('View Details')
```

---

## Ticker Config (`/orders-management/ticker-config`)

### Page Header
```
h1:has-text('Global Ticker Configuration')
```

### Form Fields
```
label:has-text('Ticker Message')
label:has-text('Ticker Background Color')
label:has-text('Ticker Text Color')
button:has-text('Update Global Ticker')
```

---

## Stores Settings (`/orders-management/stores-settings`)

### Page Header
```
h1:has-text('Integrated Stores')
```

### Filter Controls
```
input[placeholder='Search by Store Name or URL']
```

### Bifurcation Filter Buttons
```
button:has-text('Dropshipper')
button:has-text('Default')
button:has-text('3PL')
```

### Confirmation Settings Toggle
```
button:has-text('Off')     # toggles confirmation auto-approval
```

### Table Column Headers (verified live)
```
th:has-text('STORE URL')
th:has-text('STORE ID')
th:has-text('STORE NAME')
th:has-text('PLATFORM')
th:has-text('BIFURCATION')
th:has-text('USER ID')
th:has-text('CONFIRMATION SETTINGS')
th:has-text('TRUSTED')
```

### Pagination
```
select    # per-page: 5, 10, 20, 50
```

---

## Ratings Settings (`/orders-management/ratings-settings`)

### Page Header
```
h1:has-text('Maintain Country-wise Thresholds')
```

### Controls
```
input[placeholder='Search by country']
```

### Table Column Headers (verified live)
```
th:has-text('Country')
th:has-text('Product Threshold % (Delivery Ratio)')
th:has-text('Store Threshold % (Delivery Ratio)')
th:has-text('Actions')
```

---

## Tags Management (`/orders-management/tags-management`)

### Page Header
```
h1:has-text('Manage Tags')
h2:has-text('Tags List')
```

### Controls
```
button:has-text('Create New Tag')
```

### Table Column Headers (verified live)
```
th:has-text('TAG')
th:has-text('SUB STATUS')
th:has-text('STATUS')
th:has-text('ACTIVE')
th:has-text('ACTIONS')
```

### Create New Tag Modal
```
div[role='dialog']

label:has-text('Tag Name')
input[placeholder='Enter tag name']

label:has-text('Status')
select    # options: Select status, Received, Confirmation Pending, Cancelled,
          #   Approved, Dispatching in Process, Shipped, Delivered,
          #   Undelivered, Return in Transit, Return

label:has-text('Sub Status')
select    # sub-status options (depend on Status selection)

label:has-text('Active Status')
select    # options: Active, Inactive

label:has-text('Tag Color')
label:has-text('Custom Color')
input[placeholder='#RRGGBB']

button:has-text('Apply')
button:has-text('Cancel')
button:has-text('Create')
button:has-text('Close')
```

### Pagination
```
select    # per-page: 5, 10, 20, 50
```

---

## Invoice Upload (`/orders-management/invoice-upload`)

### Page Header
```
h1:has-text('Invoice PDF Upload')
h3:has-text('Upload PDF Invoice Files')
```

### Controls
```
label:has-text('Choose Files')
# File input — accepts PDF files
```

---

## Dashboard (`/orders-management/dashboard`)

### KPI Cards
```
# Cards show numeric values (h4) — no fixed text selectors
# Month selector (native <select>):
select    # options: Sep 2024, Oct 2024, Nov 2024 (historical months)
```

### Team Tasks Table
```
th:has-text('ASSIGNED')
th:has-text('PROGRESS')
th:has-text('PRIORITY')
th:has-text('BUDGET')
```

---

## ⚠️ Verified Corrections

| Field | Old (incorrect) | Correct (verified live) |
|-------|----------------|------------------------|
| Ticketing heading | `h1:has-text('Ticketing System')` | **`h2:has-text('Ticketing Management')`** |
| Ticketing "Create" button | had `+` prefix guessed | **`button:has-text('Create New Ticket')`** (no `+`) |
| Ticketing table: order column | `th:has-text('ORDER NUMBER')` | **`th:has-text('ORDER ID')`** (OMS view; seller uses ORDER NUMBER) |
| Ticketing filter type options | unknown | **Store Name, Store ID, Status, Team ID, Ticket Number** |
| Commission model "New" button | `button:has-text('Create Commission Model')` | **`button:has-text('+ New Model')`** |
| Commission model "Save" | `button:has-text('Save')` | **`button:has-text('Save Model')`** |
| Commission model name input | various guesses | **`input[placeholder='Enter model name']`** |
| Commission type values | unknown | **`% of Revenue`** / **`Flat per Order`** |
| Agency reg status filter | unknown | **All, Pending, Approved, OnHold, Rejected, Review** |
| Inventory movement types | unknown | **SKU → SKU, Warehouse → Warehouse, To Damaged Bin** |
| Inventory movement reasons | unknown | **SKU Merge, Wrong SKU Mapping, Repackaging, Services Deal, Variant Consolidation, Internal Adjustment** |
| Dispatch batch statuses | unknown | **New, Generating, Partial, Generated, Failed** |
| Tags modal status values | unknown | **Received, Confirmation Pending, Cancelled, Approved, Dispatching in Process, Shipped, Delivered, Undelivered, Return in Transit, Return** |
| Agents team options | unknown | **Account Managers, AM Team, Call Center, Development Team, Marketing Team, NDR Team, OP Team, Sales Team, Support Team** |
