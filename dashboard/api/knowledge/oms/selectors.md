# OMS — UI Selectors Reference (VERIFIED from source code)

> Source: zambeel-fe source code `/src/pages/orders-management/` and related components.
> Last updated: 2026-05-11

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
# Opens a country dropdown — options confirmed from source:
button:has-text('Saudi Arabia')
button:has-text('United Arab Emirates')
button:has-text('Kuwait')
button:has-text('Qatar')
button:has-text('Pakistan')
button:has-text('Oman')
button:has-text('Bahrain')
button:has-text('Iraq')
button:has-text('United States (USA)')    # ⚠️ NEW — includes "(USA)" suffix
```

### Status Tabs (confirmed exact text from STATUS_DISPLAY_NAMES in source)
```
button:has-text('All Orders')
button:has-text('Confirmation Pending')
button:has-text('Approved')
button:has-text('Dispatching in Process')    # ⚠️ lowercase 'i' in "in"
button:has-text('Shipped')                   # ⚠️ NOT 'In Delivery' — source uses 'Shipped'
button:has-text('Undelivered')
button:has-text('Delivered')
button:has-text('Return in Transit')
button:has-text('Return')
button:has-text('Cancelled')
```
> ⚠️ Tab 4 exact text is **'Dispatching in Process'** (lowercase 'i') — source STATUS_DISPLAY_NAMES confirmed.
> ⚠️ Previous documentation said 'Dispatching In Process' (capital I) — that is WRONG.
> ⚠️ Tab 5 is **'Shipped'** — NOT 'In Delivery'. Source maps "In Delivery" → "Shipped".

### Search & Action Controls
```
input[placeholder='Search orders']
button:has-text('Filter')
button:has-text('Actions')
```

### Table Column Headers (All Orders tab)
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
th:has-text('STATUS')          # All Orders tab uses STATUS column (not SUB-STATUS)
th:has-text('COURIER')
th:has-text('BATCH ID')
th:has-text('TRACKING ID')
```

### Table Column Headers (Confirmation Pending / Undelivered tabs — additional columns)
```
th:has-text('WATI')            # ⚠️ Only shown on Confirmation Pending and Undelivered tabs
th:has-text('SUB-STATUS')      # shown on CP tab
```

### Table Column Headers (Dispatching in Process tab — additional columns)
```
th:has-text('EDIT')            # ⚠️ Only shown on Dispatching in Process tab
```

### Table Column Headers (Undelivered tab — additional columns)
```
th:has-text('SHIPPED DATE')    # ⚠️ Only shown on Undelivered tab
```

### Actions Dropdown — All Orders Tab
```
# Click 'Actions' first, then:
button:has-text('Update Statuses')
button:has-text('Upload Orders')
```
> ⚠️ All Orders tab has ONLY these 2 actions — previous docs listed more items incorrectly.

### Actions Dropdown — Confirmation Pending Tab
```
button:has-text('Update Tag')
button:has-text('Update Remarks')
button:has-text('Approve')
button:has-text('Cancel')
```

### Actions Dropdown — Cancelled Tab
```
button:has-text('Revert to Confirmation Pending')
```

### Actions Dropdown — Approved Tab
```
button:has-text('Update Tag')
button:has-text('Update Substatus')        # ⚠️ NOT 'Update Sub-status' — one word
button:has-text('Move Processable Orders') # ⚠️ NOT 'Assign Courier'
button:has-text('Cancel')
button:has-text('Revert to Confirmation Pending')
# Also conditionally:
button:has-text('Assign Courier')          # shown when showAssignCourier=true
```

### Actions Dropdown — Dispatching in Process Tab (DIP)
```
# DIP-specific standalone buttons (above the table, NOT in the dropdown):
button:has-text('Upload Courier + Vendor File')   # ⚠️ NEW button
button:has-text('Generate Batches')               # ⚠️ NEW button
button:has-text('Clear Courier Assignment')       # ⚠️ NEW button
```

### Actions Dropdown — Undelivered (NDR) Tab
```
button:has-text('Update Tag')
button:has-text('Update Remarks')
```

### Opening an Order
```
# Click the order ID link (plain text link in the ORDER ID column):
text='651501'               # example — use the actual order ID value
# The Order Details modal opens after the click.
```

### Empty State
```
text='No orders found'
```

### Loading State
```
text='Loading orders...'
```

---

## Orders Filter Modal

### Modal Header
```
div[role='dialog'] h2:has-text('Filters')
text='Filters'
```

### Filter Fields (exact placeholders confirmed from source)
```
input[placeholder='Order ID (comma-separated for multiple)']
input[placeholder='Order # (comma-separated for multiple)']
input[placeholder='Tracking #']
input[placeholder='Customer Name']
input[placeholder='Phone Number']
input[placeholder='Store URL']
input[placeholder='Activity Counter']
input[placeholder='Assigned Agent']

# Search inputs within dropdown filters:
input[placeholder='Search city']
input[placeholder='Search courier']
input[placeholder='Search batch id']

# Dropdown triggers (Flowbite select — click then select option):
button:has-text('Select Tags')
button:has-text('Select Sub-Status')
button:has-text('Select Remarks')
button:has-text('Select Platform')
button:has-text('Select Store')
button:has-text('Select Bifurcation')
button:has-text('Select City')
button:has-text('Select Courier')
button:has-text('Select Batch ID')

# Date range — ⚠️ use input[type='date'], NOT input[placeholder='dd/mm/yyyy']
input[type='date']            # from date
input[type='date']            # to date (second occurrence)
```

### Bifurcation Dropdown Options (confirmed from source)
```
option:has-text('360')
option:has-text('3PL')
option:has-text('Dropshipper')
option:has-text('Partner')
option:has-text('Seller-Lift')
```

### Filter Modal Buttons
```
button:has-text('Clear all filters')
button:has-text('Apply filter')          # ⚠️ lowercase 'f'
```

---

## Order Details Modal

### Modal Header
```
# ⚠️ Uses h3 NOT h2 (Flowbite Modal.Header)
div[role='dialog'] h3:has-text('Order Details')
text='Order #2223'        # format: 'Order #NNNN'
```

### Loading State
```
text='Loading order details...'
```

### Tabs Inside Modal
```
button:has-text('Overview')
button:has-text('Timeline')
button:has-text('Conversation')
```

### Warning Alert (non-editable orders)
```
text='This order can no longer be edited as it\'s not in Confirmation Pending or Undelivered status.'
```

### Edit Mode Banner
```
# Shown when Edit Mode is active:
text='Edit mode is active. You can now modify order details. Click "Save" to apply changes or "Cancel Edit" to discard changes.'
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
> ⚠️ These fields display as **read-only text** by default.
> They become editable inputs ONLY after clicking `button:has-text('Edit Order')`.

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

### Bottom Controls (MiscFields)
```
text='Update Tag'
text='Activity Counter'
```

### Modal Action Buttons
```
button:has-text('Edit Order')           # toggle — enter edit mode
button:has-text('Cancel Edit')          # toggle — exit edit mode
button:has-text('Approve Order')        # Confirmation Pending status only
button:has-text('Approving...')         # loading state
button:has-text('Process Order')        # ⚠️ Approved status (NOT 'Approve Order')
button:has-text('Assigning...')         # loading state for Process Order / Assign Courier
button:has-text('Assign Courier')       # when courier assignment shown
button:has-text('Cancel Order')
button:has-text('Cancelling...')        # loading state
button:has-text('Save')
button:has-text('Saving...')            # loading state
```

### Cancel Order Popup (inside modal)
```
h2:has-text('Against which tag do you want to Cancel the order?')
select                                  # cancel tag selector
option:has-text('Select a tag')         # placeholder
text='Loading cancellation tags...'    # while fetching
button:has-text('Back')                 # ⚠️ NOT 'Cancel' — returns without cancelling
button:has-text('Confirm Cancel')
button:has-text('Cancelling...')        # in-progress state
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
button:has-text('+ Create Agent')       # ⚠️ note the '+' prefix
```

### Table Column Headers (confirmed from source)
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
# Modal header:
text='Create Agent'

# Fields:
input[placeholder='John Doe']           → Full Name
input[placeholder='johndoe@example.com'] → Email
input[placeholder='+1234567890']        → Phone Number
# Country — Flowbite select:
text='Select Country'
# Team — Flowbite select:
text='Select a Team'

# Footer buttons:
button:has-text('Cancel')
button:has-text('Create Agent')

# Validation messages:
text='Name is required'
text='Name must be at least 2 characters long'
```

---

## Ratings Settings (`/orders-management/ratings-settings`)

### Page Header
```
# ⚠️ NEW PAGE — not previously documented
h1:has-text('Ratings Settings')
```

### Table Column Headers (confirmed from source)
```
th:has-text('Country')
th:has-text('Product Threshold % (Delivery Ratio)')
th:has-text('Store Threshold % (Delivery Ratio)')
th:has-text('Actions')
```

### Edit Threshold Modal
```
div[role='dialog']
# Title (dynamic with country name):
text='Edit Thresholds for Saudi Arabia'   # example

# Field labels:
text='Country'
text='Product Threshold % (Delivery Ratio)'
text='Store Threshold % (Delivery Ratio)'

# Buttons:
button:has-text('Cancel')
button:has-text('Save Changes')
```

---

## Stores Settings (`/orders-management/stores-settings`)

### Page Header
```
h1:has-text('Integrated Stores')
```

### Controls
```
label:has-text('Show untrusted Manual stores only')
input[type='checkbox']              → same checkbox

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

---

## Dispatch Batches (`/orders-management/dispatch-batches`)

### Page Header
```
h1:has-text('Dispatch Batches')
p:has-text('Generate tracking IDs and download combined courier documents.')
```

### Filters
```
button:has-text('Status')
button:has-text('Vendor')
button:has-text('Courier')
input[type='date']                  # from date
input[type='date']                  # to date
```

### Search
```
input[placeholder='Search orders...']    # ⚠️ with ellipsis
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

### Tracking Status Badges
```
span:has-text('Generated')          # green
span:has-text('Partial')            # orange
span:has-text('New')
span:has-text('Generating')
span:has-text('Failed')
```

### Per-Row Action Buttons
```
button:has-text('Generate Tracking ID')
button:has-text('Generate & Download')
button:has-text('Download Combined Doc')
```

---

## Ticketing (`/orders-management/ticketing`)

### Page Header
```
h2:has-text('Ticketing Management')    # ⚠️ h2 NOT h1 (source uses h2)
```

### Loading / Error States
```
text='Loading tickets...'
text='Failed to load tickets'
text='An error occurred while fetching tickets'
button:has-text('Try Again')
```

### Stats Cards
```
text='Total Tickets'
text='Pending'
text='In Progress'
text='Awaiting Seller Action'
text='Resolved'
```

### Tabs
```
button:has-text('Tickets Assigned to Zambeel')
button:has-text('Tickets Assigned by Zambeel')
```
> Note: Tab order depends on user role — admin sees "by Zambeel" first, seller sees "to Zambeel" first.

### Filter Controls
```
# Filter type selector — options:
select:has-text('Store Name')       # default
# Other options in the select:
option:has-text('Store Name')
option:has-text('Store ID')
option:has-text('Status')
option:has-text('Team ID')

# Input placeholder changes by type:
input[placeholder='Search by store name...']
input[placeholder='Search by store ID...']
input[placeholder='Select status...']
input[placeholder='Select team...']

button:has-text('Search')
```

### Primary Button
```
button:has-text('Create New Ticket')    # ⚠️ NO '+' prefix (unlike other pages)
```

### Table Column Headers
```
th:has-text('TICKET ID')
th:has-text('CATEGORY')
th:has-text('SUB-CATEGORY')
th:has-text('ORDER ID')             # ⚠️ admin view shows 'ORDER ID'
th:has-text('DATE')
th:has-text('STATUS')
th:has-text('ACTIONS')
```

### Status Badges
```
span:has-text('Pending')            # yellow
span:has-text('In Progress')        # blue
span:has-text('Awaiting Seller Action')  # orange
span:has-text('Resolved')           # green
```

### Row Action
```
# Eye icon button (gray):
button[title='View']                # or unlabeled button with Eye icon
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
# Search-by type selector (label: "Search by")
# Options confirmed from SEARCH_OPTIONS in source:
option:has-text('Email')
option:has-text('Phone')
option:has-text('User ID')

# Input placeholder changes by type:
input[placeholder='Enter user email']       # Email (default)
input[placeholder='Enter phone number']     # Phone
input[placeholder='Enter user ID']          # User ID

button:has-text('Search')
button:has-text('Searching...')             # loading state
button:has-text('Clear')
```

### Tabs
```
button:has-text('All users')
button:has-text('Gold users')
```

### Table Column Headers
```
th:has-text('USER ID')
th:has-text('EMAIL')
th:has-text('TOTAL STORES')
th:has-text('SUBSCRIPTION STATUS')
th:has-text('EXPIRY DATE')
th:has-text('ACTIONS')
```

### Row Action
```
button:has-text('View Details')
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
# Each card shows:
# Model name (dynamic text)
text='agencies assigned'            # e.g. '2 agencies assigned' or '1 agency assigned'
text='agency assigned'              # singular form when count = 1

# Edit button — has Pencil icon + "Edit" text (NOT emoji):
button:has-text('Edit')             # ⚠️ plain text 'Edit' with Pencil lucide icon
# Previous docs incorrectly documented as '✏ Edit' (unicode emoji) — that is WRONG
```

### Table Inside Each Model Card
```
th:has-text('Country')
th:has-text('Commission Type')
th:has-text('Value')
th:has-text('Currency')
```

### Commission Type Values
```
text='Flat per Order'
text='% of Revenue'
```

### Create / Edit Drawer
```
# Drawer title:
text='Create Commission Model'      # when creating
text='Edit Commission Model'        # when editing

# Model Name field:
input[placeholder='Enter model name']     # label: "Model Name*"

# Country dropdown (Flowbite select):
text='Loading countries...'         # while loading
text='Select'                       # when loaded (placeholder)

# Commission Type dropdown options:
option:has-text('% of Revenue')
option:has-text('Flat per Order')

# Value input (number):
input[type='number']                # no placeholder text

# Currency input:
input[placeholder='AED']            # label: "Currency*"

# Rule management buttons:
button:has-text('+ Add Rule')
button:has-text('Remove rule')      # red button per rule

# Drawer footer:
button:has-text('Save Model')
button:has-text('Cancel')

# Empty state (no models yet):
text='No commission models yet'
button:has-text('Create First Model')

# Validation alert inside drawer:
text='Each country can only appear once inside the same model.'
```

---

## Agency Registrations (`/orders-management/agency-registrations`)

### Page Header
```
h1:has-text('Agency Registrations')
p:has-text('Review and manage agency applications.')
```

### Status Tabs
```
button:has-text('All')
button:has-text('Pending')
button:has-text('Approved')
button:has-text('OnHold')
button:has-text('Rejected')
```

### Table Column Headers
```
th:has-text('Name')
th:has-text('Country')
th:has-text('POC')
th:has-text('Status')
th:has-text('License')
th:has-text('Submitted')
```

### Row Action
```
button:has-text('Review')
```

### Review Drawer — Action Buttons by Status
```
# Pending:
button:has-text('Approve Agency')
button:has-text('Put on Hold')
button:has-text('Reject')

# Approved:
button:has-text('Revoke License')

# Rejected:
button:has-text('Revert to Pending')
```

### Approve Sub-form
```
text='Assign Commission Model'          # section heading
label:has-text('Select commission model')
# select dropdown for commission model
button:has-text('Confirm Approve')
button:has-text('Cancel')
```

### Hold Sub-form
```
textarea[placeholder='Explain what needs to be fixed...']
label:has-text('Allow applicant to resubmit documents')
input[type='checkbox']                  # resubmit toggle
button:has-text('Put on Hold')
button:has-text('Cancel')
```

### Reject Sub-form
```
textarea[placeholder='Reason for rejection...']
button:has-text('Confirm Reject')
button:has-text('Cancel')
```

### Document Links
```
button:has-text('Identity Document')
button:has-text('Agency Document')
```

---

## Ticker Config (`/orders-management/ticker-config`)

### Page Header
```
h1:has-text('Global Ticker Configuration')
p:has-text('This is where the Admin will manage the banner.')
```

### Loading State
```
text='Loading configuration...'
```

### Form Fields
```
label:has-text('Ticker Config')         # toggle switch label
label:has-text('Ticker Message')
label:has-text('Ticker Background Color')
label:has-text('Ticker Text Color')
input[type='color']                     # first: background color
input[type='color']                     # second: text color
```

### Submit Button
```
button:has-text('Update Global Ticker')
button:has-text('Saving...')            # loading state
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
button:has-text('Movement ID')          # default search-by type
input[placeholder='Search Movement ID']
button:has-text('Date')
button:has-text('Filters')
```

### Table Column Headers
```
th:has-text('MOVEMENT ID')
th:has-text('TYPE')
th:has-text('WAREHOUSE')
th:has-text('STATUS')
th:has-text('MOVED BY')
th:has-text('DATE')
```

### Movement Type Badges
```
span:has-text('Warehouse → Warehouse')   # purple
span:has-text('SKU → SKU')               # blue
span:has-text('To Damaged Bin')          # red
```

### Status Badges
```
span:has-text('In Transit')         # yellow
span:has-text('Received')           # green
```

### Create Movement Form (inside Add modal)

**Movement Type Buttons:**
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

## Purchase Orders (`/orders-management/purchase-orders`)

```
# Status badge values:
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
| Orders | `button:has-text('Dispatching in Process')` | Tab 4 (lowercase 'i') |
| Orders | `button:has-text('Shipped')` | Tab 5 — NOT 'In Delivery' |
| Orders | `th:has-text('WATI')` | CP and Undelivered tabs only |
| Orders | `th:has-text('EDIT')` | DIP tab only |
| Orders | `th:has-text('SHIPPED DATE')` | Undelivered tab only |
| Orders DIP | `button:has-text('Upload Courier + Vendor File')` | DIP tab standalone |
| Orders DIP | `button:has-text('Generate Batches')` | DIP tab standalone |
| Orders DIP | `button:has-text('Clear Courier Assignment')` | DIP tab standalone |
| Orders Approved | `button:has-text('Update Substatus')` | NOT 'Update Sub-status' |
| Orders Approved | `button:has-text('Move Processable Orders')` | NOT 'Assign Courier' |
| Orders Cancel | `button:has-text('Back')` | NOT 'Cancel' — cancel popup back button |
| Orders Filter | `button:has-text('Clear all filters')` | Reset all |
| Orders Filter | `button:has-text('Apply filter')` | Submit — lowercase 'f' |
| Orders Filter | `input[type='date']` | NOT `input[placeholder='dd/mm/yyyy']` |
| Order Detail | `h3:has-text('Order Details')` | h3 NOT h2 |
| Order Detail | `button:has-text('Edit Order')` | Opens edit mode |
| Order Detail | `button:has-text('Process Order')` | Approved status (NOT 'Approve Order') |
| Order Detail | `button:has-text('Approve Order')` | CP status only |
| Order Detail | `button:has-text('Cancel Order')` | Cancel single order |
| Agents | `button:has-text('+ Create Agent')` | With '+' prefix |
| Ratings | `h1:has-text('Ratings Settings')` | NEW page |
| Stores | `h1:has-text('Integrated Stores')` | NOT 'Stores Settings' |
| Dispatch | `input[placeholder='Search orders...']` | With ellipsis '...' |
| Ticketing | `h2:has-text('Ticketing Management')` | h2 NOT h1 |
| Ticketing | `button:has-text('Create New Ticket')` | No '+' prefix |
| Gold Sub | `h1:has-text('Gold Subscription Management')` | Page title |
| Gold Sub | `input[placeholder='Enter user email']` | Default search |
| Commission | `button:has-text('Edit')` | NOT '✏ Edit' — plain text |
| Commission | `button:has-text('+ New Model')` | Create |
| Commission | `input[placeholder='Enter model name']` | Model name field |
| Commission | `button:has-text('Save Model')` | Drawer save |
| Inventory | `button:has-text('+ Add Inventory Movement')` | Create button |
| Inventory | `input[placeholder='Search Movement ID']` | Search input |
| Ticker | `h1:has-text('Global Ticker Configuration')` | Page title |
| Ticker | `button:has-text('Update Global Ticker')` | Save button |
| Agency Reg | `button:has-text('Review')` | Per-row action |

---

## ⚠️ Corrections vs Previously Documented

| Field | Old (incorrect) | Correct (verified from source) |
|-------|----------------|-------------------------------|
| Tab 4 label | 'Dispatching In Process' (capital I) | **'Dispatching in Process'** (lowercase i) |
| Tab 5 label | 'In Delivery' | **'Shipped'** |
| Country option | 'United States' | **'United States (USA)'** |
| Filter dates | `input[placeholder='dd/mm/yyyy']` | **`input[type='date']`** |
| All Orders dropdown | many items listed | **only 'Update Statuses' and 'Upload Orders'** |
| Approved dropdown | 'Update Sub-status' | **'Update Substatus'** (one word) |
| Approved dropdown | 'Assign Courier' | **'Move Processable Orders'** |
| Commission card edit | '✏ Edit' (unicode emoji) | **'Edit'** (Pencil lucide icon + text) |
| Order Details header | `h2:has-text('Order Details')` | **`h3:has-text('Order Details')`** |
| Modal action (Approved) | 'Approve Order' | **'Process Order'** for Approved-status orders |
| Cancel popup back btn | 'Cancel' | **'Back'** |
| Ticketing heading | `h1:has-text(...)` | **`h2:has-text('Ticketing Management')`** |
| Stores title | 'Stores Settings' | **'Integrated Stores'** |
