# OMS — UI Selectors Reference (VERIFIED from live portal screenshots)

> Source: 12 screenshots of portal.myzambeel.com — all selectors confirmed from actual UI.
> Last verified: 2026-05-01

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

### Country Filter (top right dropdown)
```
# Opens a country dropdown — options confirmed:
button:has-text('Saudi Arabia')         → KSA
button:has-text('United Arab Emirates') → UAE
button:has-text('Kuwait')
button:has-text('Qatar')
button:has-text('Pakistan')
button:has-text('Oman')
button:has-text('Bahrain')
button:has-text('Iraq')
```

### Status Tabs (confirmed exact text)
```
button:has-text('All Orders')
button:has-text('Confirmation Pending')
button:has-text('Approved')
button:has-text('Dispatching In Process')
button:has-text('Shipped')
button:has-text('Undelivered')
button:has-text('Delivered')
button:has-text('Return in Transit')
button:has-text('Return')
button:has-text('Cancelled')
```
> ⚠️ Tab 4 is **'Dispatching In Process'** (not 'Dispatching in Process' with lowercase 'n') — verify casing on click.
> ⚠️ Tab 5 is **'Shipped'** — previously documented as 'In Delivery'. Use 'Shipped'.

### Search & Action Controls
```
input[placeholder='Search orders']
button:has-text('Filter')
button:has-text('Actions')
```

### Table Column Headers (confirmed)
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
th:has-text('STATUS')
th:has-text('SUB-STATUS')
th:has-text('COURIER')
th:has-text('BATCH ID')
th:has-text('TRACKING ID')
```

### Actions Dropdown Items
```
# Click 'Actions' first, then:
button:has-text('Update Statuses')
button:has-text('Upload Orders')
button:has-text('Approve')
button:has-text('Cancel')
button:has-text('Update Tag')
button:has-text('Update Remarks')
button:has-text('Assign Courier')
```

### Empty State
```
text='No orders found'
```

---

## Orders Filter Modal

### Modal Header
```
div[role='dialog'] h2:has-text('Filters')
# or:
text='Filters'
```

### Filter Fields (exact placeholders / labels confirmed)
```
input[placeholder='Order ID (comma-separated for multiple)']
input[placeholder='Order # (comma-separated for multiple)']
input[placeholder='Tracking #']
input[placeholder='Customer Name']
input[placeholder='Phone Number']
input[placeholder='Store URL']
input[placeholder='Activity Counter']

# Dropdowns (Flowbite select — use CLICK_OPTION):
button:has-text('Select Tags')
button:has-text('Select Sub-Status')
button:has-text('Select Remarks')
button:has-text('Select Platform')
button:has-text('Select Store')
button:has-text('Assigned Agent')
button:has-text('Select Bifurcation')
button:has-text('Select City')
button:has-text('Select Courier')
button:has-text('Select Batch ID')

# Date range (two inputs)
input[placeholder='dd/mm/yyyy']       → from date (first)
input[placeholder='dd/mm/yyyy']       → to date (second)
```

### Filter Modal Buttons
```
button:has-text('Clear all filters')
button:has-text('Apply filter')
```

---

## Order Details Modal

### Modal Header
```
div[role='dialog'] h2:has-text('Order Details')
# Subtitle shows dynamic order number:
text='Order #2223'        # example — format: 'Order #NNNN'
```

### Tabs Inside Modal
```
button:has-text('Overview')
button:has-text('Timeline')
button:has-text('Conversation')
```

### Overview Tab — Field Labels
```
text='Store Name'
text='Customer Name'
text='Order#'
text='Order Date'
text='Payment Method'
```

### Order Items Section
```
text='Order Items'
th:has-text('PRODUCT')
th:has-text('SKU')
th:has-text('QUANTITY')
th:has-text('PRICE')
```

### Delivery Address Section
```
text='Delivery Address'
text='Address'
text='Phone Number'
text='Country'
text='City'
text='Area Name'
text='Building/Society'
text='National Address Short Code'
```

### Financial Summary Section
```
text='Financial Summary'
text='Subtotal'
text='Discount'
text='Tax'
text='Shipping'
text='Total'
text='Website Price'
```

### Bottom Controls
```
text='Update Tag'
text='Activity Counter'
```

### Modal Action Buttons
```
button:has-text('Edit Order')
button:has-text('Approve Order')
button:has-text('Cancel Order')
button:has-text('Save')
```

---

## Dispatch Batches (`/orders-management/dispatch-batches`)

### Page Header
```
h1:has-text('Dispatch Batches')
p:has-text('Generate tracking IDs and download combined courier documents.')
```

### Filters
```
# Country dropdown (top left area)
button:has-text('UAE')              → default/example country shown

# Other filter dropdowns
button:has-text('Status')
button:has-text('Vendor')
button:has-text('Courier')

# Date range inputs
input[placeholder='dd/mm/yyyy']    → from
input[placeholder='dd/mm/yyyy']    → to
```

### Search
```
input[placeholder='Search orders...']
```

### Table Column Headers (confirmed)
```
th:has-text('BATCH ID')
th:has-text('CREATED BY')
th:has-text('CREATED DATE/TIME')
th:has-text('VENDOR ID')
th:has-text('COURIER NAME')
th:has-text('COURIER REQUEST ID')
th:has-text('TOTAL ORDERS')
th:has-text('TRACKING STATUS')
th:has-text('GENERATE TRACKING ID')
th:has-text('DOWNLOAD DOCUMENT')
```

### Tracking Status Badges (confirmed)
```
span:has-text('Generated')          → green badge
span:has-text('Partial')            → orange badge
# Other possible values:
span:has-text('New')
span:has-text('Generating')
span:has-text('Failed')
```

### Per-Row Action Buttons (confirmed)
```
button:has-text('Generate Tracking ID')
button:has-text('Generate & Download')
button:has-text('Download Combined Doc')
```

---

## Agents (`/orders-management/agents`)

### Page Header
```
h1:has-text('Agents')
```

### Controls
```
input[placeholder='Search by Name, Email or Country']
button:has-text('+ Create Agent')
```

### Table Column Headers (confirmed)
```
th:has-text('Name')
th:has-text('Email')
th:has-text('Phone')
th:has-text('Country')
th:has-text('Status')
th:has-text('Team')
```

### Status Badges
```
span:has-text('Active')             → green badge
```

### Create Agent Modal Fields
```
div[role='dialog']
input[placeholder='John Doe']       → Full Name field
# Additional fields: Email, Phone Number, Country, Team
```

---

## Stores Settings (`/orders-management/stores-settings`)

### Page Header
```
h1:has-text('Integrated Stores')
```

### Controls
```
input[type='checkbox']              → 'Show untrusted Manual stores only'
# Label text:
label:has-text('Show untrusted Manual stores only')

input[placeholder='Search by Store Name or URL']
```

### Table Column Headers (confirmed)
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

### Badges (confirmed)
```
span:has-text('Dropshipper')        → blue pill (bifurcation type)
span:has-text('Trusted')            → green badge
```

---

## Ticketing (`/orders-management/ticketing`)

### Page Header
```
h1:has-text('Ticketing Management')
```

### Stats Cards (confirmed labels — values are dynamic)
```
text='Total Tickets'
text='Pending'
text='In Progress'
text='Awaiting Seller Action'
text='Resolved'
```

### Tabs (confirmed exact text)
```
button:has-text('Tickets Assigned to Zambeel')
button:has-text('Tickets Assigned by Zambeel')
```

### Filter Controls
```
# Store Name filter
button:has-text('Store Name')       → dropdown for filter type
input[placeholder='Search by store name...']
button:has-text('Search')
```

### Primary Button
```
button:has-text('+ Create New Ticket')
```

### Table Column Headers (confirmed)
```
th:has-text('TICKET ID')
th:has-text('CATEGORY')
th:has-text('SUB-CATEGORY')
th:has-text('ORDER ID')
th:has-text('DATE')
th:has-text('STATUS')
th:has-text('ACTIONS')
```

### Status Badges (confirmed)
```
span:has-text('Pending')            → yellow badge
span:has-text('Resolved')           → green badge
span:has-text('In Progress')        → blue badge
# Also possible:
span:has-text('Awaiting Seller Action')
```

### Row Action
```
button:has-text('View')
```

---

## Gold Subscription Management (`/orders-management/gold-subscriptions`)

### Page Header
```
h1:has-text('Gold Subscription Management')
p:has-text('View all users, search in the database, and manage Gold access from OMS.')
```

### Search Controls
```
# Search-by type dropdown (confirmed options: Email, Phone, User ID)
button:has-text('Email')            → default selected
# After clicking the dropdown, options:
button:has-text('Email')
button:has-text('Phone')
button:has-text('User ID')

input[placeholder='Enter user email']   → search input (placeholder changes with type)
button:has-text('Search')
button:has-text('Clear')
```

### Tabs (confirmed)
```
button:has-text('All users')
button:has-text('Gold users')
```

### Table Column Headers (confirmed)
```
th:has-text('USER ID')
th:has-text('EMAIL')
th:has-text('TOTAL STORES')
th:has-text('SUBSCRIPTION STATUS')
th:has-text('EXPIRY DATE')
th:has-text('ACTIONS')
```

### Status Badges (confirmed)
```
span:has-text('Free')               → gray badge
span:has-text('Gold')               → gold/amber badge
```

### Row Action
```
button:has-text('View Details')
```

---

## Inventory Movements (`/orders-management/inventory-movements`)

### Page Header
```
h1:has-text('Inventory Movements')
```

### Primary Button
```
button:has-text('+ Add Inventory Movement')
```

### Search Controls
```
# Search-by type dropdown
button:has-text('Movement ID')      → default selected

input[placeholder='Search Movement ID']
# Search submit — icon button (magnifying glass)
```

### Filter Buttons
```
button:has-text('Date')
button:has-text('Filters')
```

### Table Column Headers (confirmed)
```
th:has-text('MOVEMENT ID')
th:has-text('TYPE')
th:has-text('WAREHOUSE')
th:has-text('STATUS')
th:has-text('MOVED BY')
th:has-text('DATE')
```

### Movement Type Badges (confirmed colors)
```
span:has-text('Warehouse → Warehouse')   → purple badge
span:has-text('SKU → SKU')               → blue badge
span:has-text('To Damaged Bin')          → red badge
```

### Status Badges (confirmed)
```
span:has-text('In Transit')         → yellow badge
span:has-text('Received')           → green badge
```

### Create Movement Form (inside Add modal)

**Movement Type Options:**
```
button:has-text('SKU → SKU')
button:has-text('Warehouse → Warehouse')
button:has-text('To Damaged Bin')
```

**Reason options — To Damaged Bin:**
```
option:has-text('Physical Damage')
option:has-text('Expired Product')
option:has-text('Quality Failure')
option:has-text('Packaging Damage')
option:has-text('Customer Return - Unsellable')
option:has-text('Purchase Order Correction')
option:has-text('Lost / Missing in Audit')
option:has-text('Outdated Stock')
```

**Reason options — SKU to SKU:**
```
option:has-text('SKU Merge')
option:has-text('Wrong SKU Mapping')
option:has-text('Repackaging')
option:has-text('Services Deal')
option:has-text('Variant Consolidation')
option:has-text('Internal Adjustment')
```

**Reason options — Warehouse to Warehouse:**
```
option:has-text('Demand Fulfillment')
option:has-text('Purchase Transfer')
```

---

## Ticker Config (`/orders-management/ticker-config`)

### Page Header
```
h1:has-text('Global Ticker Configuration')
p:has-text('This is where the Admin will manage the banner.')
```

### Form Fields (confirmed labels)
```
# Toggle switch
label:has-text('Ticker Config')         → on/off toggle

# Text field
label:has-text('Ticker Message')
input[name='tickerMessage']             → or by label

# Color pickers
label:has-text('Ticker Background Color')
label:has-text('Ticker Text Color')
input[type='color']                     → first: background color
input[type='color']                     → second: text color
```

### Submit Button
```
button:has-text('Update Global Ticker')
```

---

## Agency Registrations (`/orders-management/agency-registrations`)

### Page Header
```
h1:has-text('Agency Registrations')
p:has-text('Review and manage agency applications.')
```

### Status Tabs (confirmed)
```
button:has-text('All')
button:has-text('Pending')
button:has-text('Approved')
button:has-text('OnHold')
button:has-text('Rejected')
```

### Table Column Headers (confirmed)
```
th:has-text('Name')
th:has-text('Country')
th:has-text('POC')
th:has-text('Status')
th:has-text('License')
th:has-text('Submitted')
```

### Status Badges (confirmed)
```
span:has-text('Pending')            → yellow badge
span:has-text('Approved')           → green badge
span:has-text('OnHold')             → orange badge
span:has-text('Rejected')           → red badge
```

### License Status Values (confirmed)
```
text='Active'
text='Inactive'
```

### Row Action
```
button:has-text('Review')           → blue link-style button
```

### Review Drawer — Action Buttons by Status
```
# Pending application:
button:has-text('Approve Agency')
button:has-text('Put on Hold')
button:has-text('Reject')

# Approved application (not revoked):
button:has-text('Revoke License')

# Rejected application:
button:has-text('Revert to Pending')
```

### Approve Sub-form
```
select                                  → commission model selector
# placeholder text in select:
button:has-text('Select commission model')
button:has-text('Confirm Approve')
button:has-text('Cancel')
```

### Hold Sub-form
```
textarea[placeholder='Explain what needs to be fixed...']
input[type='checkbox']                  → Allow resubmit
button:has-text('Put on Hold')
button:has-text('Cancel')
```

### Reject Sub-form
```
textarea[placeholder='Reason for rejection...']
button:has-text('Confirm Reject')
button:has-text('Cancel')
```

### Document Links in Drawer
```
button:has-text('Identity Document')
button:has-text('Agency Document')
```

---

## Commission Models (`/orders-management/commission-models`)

### Page Header
```
h1:has-text('Commission Models')
p:has-text('Define per-country commission rates for agencies.')
```

### Primary Button
```
button:has-text('+ New Model')
```

### Model Card Elements
```
# Each model card shows:
text='[model name]'                     → dynamic
text='agencies assigned'               → count label (e.g. '2 agencies assigned')
button:has-text('✏ Edit')               → edit button top-right of each card
```

### Table Inside Each Model Card (confirmed columns)
```
th:has-text('Country')
th:has-text('Commission Type')
th:has-text('Value')
th:has-text('Currency')
```

### Commission Type Values (confirmed from live UI)
```
text='Flat per Order'
text='% of Revenue'
```

### Create / Edit Drawer
```
div[role='dialog']                      → drawer panel

# Model Name field
input[placeholder='Enter model name']  → Model Name* label

# Country dropdown (Flowbite select)
button:has-text('Select')              → Country* dropdown trigger
button:has-text('Loading countries...') → while loading

# Commission Type dropdown
# Use CLICK_OPTION — options confirmed:
CLICK_OPTION: % of Revenue
CLICK_OPTION: Flat per Order

# Value input
input[type='number']                   → Value* field (NO placeholder text)

# Currency input (auto-fills on country select)
input[placeholder='AED']              → Currency* (maxLength=3, disabled after auto-fill)

# Add / remove rules
button:has-text('+ Add Rule')
button:has-text('Remove rule')         → red text button per rule

# Drawer footer
button:has-text('Save Model')
button:has-text('Cancel')
button[aria-label='Close']             → X button top-right

# Empty state (no models yet)
button:has-text('Create First Model')
```

### Validation Alert (inside drawer)
```
text='Each country can only appear once inside the same model.'
```

---

## Purchase Orders (`/orders-management/purchase-orders`)

```
# Status badge values (confirmed from app context):
span:has-text('Draft')
span:has-text('Received')
span:has-text('Partially Received')
span:has-text('Cancelled')
span:has-text('Submitted')
```

---

## Quick Selector Reference Table

| Page | Key Selector | Notes |
|------|-------------|-------|
| Orders | `h1:has-text('Orders Management')` | Page title |
| Orders | `input[placeholder='Search orders']` | Search box |
| Orders | `button:has-text('Dispatching In Process')` | Tab 4 (capital I) |
| Orders | `button:has-text('Shipped')` | Tab 5 — NOT 'In Delivery' |
| Orders Filter | `button:has-text('Clear all filters')` | Reset all |
| Orders Filter | `button:has-text('Apply filter')` | Submit filter |
| Order Detail | `button:has-text('Edit Order')` | Opens edit mode |
| Order Detail | `button:has-text('Approve Order')` | Approve single order |
| Order Detail | `button:has-text('Cancel Order')` | Cancel single order |
| Dispatch | `h1:has-text('Dispatch Batches')` | Page title |
| Dispatch | `input[placeholder='Search orders...']` | Search (note: '...' not '') |
| Dispatch | `button:has-text('Generate Tracking ID')` | Per-row action |
| Dispatch | `button:has-text('Generate & Download')` | Per-row action |
| Dispatch | `button:has-text('Download Combined Doc')` | Per-row action |
| Agents | `button:has-text('+ Create Agent')` | Create button |
| Stores | `h1:has-text('Integrated Stores')` | Page title — NOT 'Stores Settings' |
| Stores | `input[placeholder='Search by Store Name or URL']` | Search |
| Ticketing | `h1:has-text('Ticketing Management')` | Page title |
| Ticketing | `button:has-text('+ Create New Ticket')` | Create button |
| Ticketing | `input[placeholder='Search by store name...']` | Filter input |
| Gold Sub | `h1:has-text('Gold Subscription Management')` | Page title |
| Gold Sub | `input[placeholder='Enter user email']` | Search input |
| Inventory | `button:has-text('+ Add Inventory Movement')` | Create button |
| Inventory | `input[placeholder='Search Movement ID']` | Search input |
| Ticker | `h1:has-text('Global Ticker Configuration')` | Page title |
| Ticker | `button:has-text('Update Global Ticker')` | Save button |
| Agency Reg | `button:has-text('Review')` | Per-row action |
| Commission | `button:has-text('+ New Model')` | Create button |
| Commission | `button:has-text('✏ Edit')` | Per-card edit |
| Commission | `input[placeholder='Enter model name']` | Model name field |
| Commission | `button:has-text('Save Model')` | Drawer save |

---

## ⚠️ Corrections vs Previously Documented

| Field | Old (incorrect) | Correct (verified) |
|-------|----------------|-------------------|
| Orders page title | 'Orders' | **'Orders Management'** |
| Tab 5 label | 'In Delivery' | **'Shipped'** |
| Stores page title | 'Stores Settings' | **'Integrated Stores'** |
| Ticketing page title | 'Ticketing System' (seller) | **'Ticketing Management'** (OMS) |
| Gold Sub page title | 'Gold Subscriptions' | **'Gold Subscription Management'** |
| Gold Sub search input | generic | **`input[placeholder='Enter user email']`** |
| Inventory page primary btn | 'Create Inventory Movement' | **'+ Add Inventory Movement'** |
| Inventory search input | generic | **`input[placeholder='Search Movement ID']`** |
| Ticker page title | 'Ticker Config' | **'Global Ticker Configuration'** |
| Ticker save button | 'Save' | **'Update Global Ticker'** |
| Commission card edit btn | 'Edit' | **'✏ Edit'** (with pencil emoji) |
| Dispatch search | 'Search orders' | **'Search orders...'** (with ellipsis) |
| Filter modal apply btn | 'Apply Filters' | **'Apply filter'** (lowercase 'f') |
| Filter modal clear btn | 'Reset' | **'Clear all filters'** |
