# Seller Portal — UI Selectors Reference

## Selector Rules (React + Tailwind — No IDs)
- **Buttons:** `button:has-text('exact text')`
- **Inputs:** `input[placeholder='exact placeholder']`
- **Labels → inputs:** `label:has-text('Label') >> input`
- **Navigation:** `a:has-text('Menu Item')`
- **Modals:** `div[role='dialog']`
- **NEVER use** `#id` selectors

---

## Sidebar Navigation (Merchant Tab)

```
a:has-text('Get Started')            → /get-started
a:has-text('Dropshipping')           → /get-started/dropshipping
a:has-text('Zambeel 360')            → /get-started/zambeel-360
a:has-text('3PL Services')           → /get-started/3pl-services
a:has-text('Dashboard')              → /dashboard
a:has-text('Zambeel Academy')        → /academy
a:has-text('Orders')                 → /orders
a:has-text('Orders Analytics')       → /orders-analytics
a:has-text('Gold Subscription')      → /gold-subscription
a:has-text('Bank Accounts')          → /settings
a:has-text('Stores Integration')     → /stores/integration
a:has-text('Ticketing')              → /ticketing
a:has-text('My Invoice')             → /my-invoices
a:has-text('My Inventory')           → /seller/inventory
```

---

## Orders Page (`/orders`)

```
# Page sections
h1:has-text('Orders Dashboard')
text='Your Store Orders'
text='Orders with Zambeel'

# Unprocessed orders actions
button:has-text('Send To Zambeel')
button:has-text('Delete')
button:has-text('Delete Order')
button:has-text('Delete Orders')
button:has-text('Deleting...')

# Filter controls (processed orders)
input[placeholder='Search by Order ID']
input[placeholder='Search by Phone']
button:has-text('Filter')            # Funnel icon toggle
button:has-text('Reset')
button:has-text('Apply Filters')

# Filter dropdowns
select:has-text('Select Status')     → status dropdown
select:has-text('Select Sub-Status') → sub-status dropdown

# Copy tracking ID
button[title='Copy tracking ID']
button[title='Copied!']

# Pagination
select                               → Show entries count (5/10/20/50)

# Empty state
text='No Orders Found'
text='No orders found'

# Processing overlay
text='Connecting to Zambeel...'
```

---

## Ticketing Page (`/ticketing`)

```
# Header
h1:has-text('Ticketing System')
p:has-text('Manage and track support tickets')
button:has-text('Create New Ticket')

# Tabs (Seller view)
button:has-text('Tickets Assigned by Zambeel')
button:has-text('Tickets Assigned to Zambeel')

# Filter controls
input[placeholder='Search by store name...']
input[placeholder='Search by store ID...']

# Stats cards text (verify after page load)
text='Total Tickets'
text='Pending'
text='In Progress'
text='Awaiting Seller Action'
text='Resolved'

# Table columns
th:has-text('TICKET ID')
th:has-text('CATEGORY')
th:has-text('SUB-CATEGORY')
th:has-text('ORDER NUMBER')
th:has-text('DATE')
th:has-text('STATUS')

# Empty states
text='No tickets assigned to Zambeel'
text='No tickets assigned by Zambeel'

# Error state
text='Failed to load tickets'
button:has-text('Try Again')
```

---

## Create Ticket Wizard (Modal)

```
# Wizard steps
text='Select Store'
text='Category & Type'
text='Details & Files'
text='Review'

# Step 1 — Store selection
# Dropdown or search for stores

# Step 2 — Category
# Category radio/select options:
text='Onboarding & Integration'
text='Order Sending & Inventory Issue'
text='Order Changes & Updates'
text='Product Complaint'
text='Delivery Complaint'
text='Payments & Invoices'

# Sub-category options (after category selected — examples):
text='Request to Cancel the order'
text='Change Price'
text='Change Quantity'
text='Damaged/defective item delivered'
text='Wrong item/SKU delivered'
text='Invoice not received'
text='Payment not received'

# Step 3 — Details & Files
textarea[placeholder]                → description field
# File upload
input[type='file']
text='Maximum 3 files allowed'       → error
text='File'                          → file too large / wrong type errors

# Wizard navigation
button:has-text('Next')
button:has-text('Back')
button:has-text('Submit')
button:has-text('Cancel')

# Success screen
h3:has-text('Ticket Created Successfully!')
```

---

## Bank Accounts / Settings (`/settings`)

```
# Payment type selection
button:has-text('Bank Account')
button:has-text('USDT')
button:has-text('PayPal')

# Bank Account form fields
input[placeholder]                   → Account Title
input[placeholder]                   → Bank Name
input[placeholder]                   → IBAN

# USDT form fields
input                               → Exchange Name
input                               → Exchange ID
input                               → Wallet Address
input                               → First Name
input                               → Last Name

# Actions
button:has-text('Add Account')
button:has-text('Set as Primary')
button:has-text('Delete')

# Update account form
input[placeholder]                   → Account title
select                               → Withdrawal day
input[type='number']                 → Withdrawal threshold
input[type='checkbox']               → Auto-withdrawal toggle

# Pagination / listing
button:has-text('Save')
button:has-text('Cancel')
```

---

## Stores Integration (`/stores/integration`)

```
# Platform connect buttons
button:has-text('Connect Shopify')
button:has-text('Connect EasyOrder')
button:has-text('Connect Light Funnels')
button:has-text('Connect YouCan')
button:has-text('Create Manual Store')

# Disconnect
button:has-text('Disconnect')

# Manual store sub-platform options
text='Facebook Marketplace'
text='Amazon'
text='Whatsapp Marketplace'
text='Salla'
text='Zid'
text='Ebay'

# Error messages
text='Store Nick name already exists. Please choose a different name.'
text='Unsupported integration type'
text='Failed to connect store'
```

---

## Profile (`/profile`)

```
# Editable fields
input[name='username']               → or by placeholder
input[name='phone_number']           → international format +XXXXXXXXXX
input[name='promo_code']
input[name='sidebar_color']          → hex color #RRGGBB
input[name='button_color']           → hex color #RRGGBB

# Country select
select                               → country dropdown

# Save
button:has-text('Save')
button:has-text('Update Profile')
```

---

## Gold Subscription (`/gold-subscription`)

```
# Status info
text='days remaining'
text='Gold Subscription'

# Subscribe
button:has-text('Subscribe')
button:has-text('Renew')

# PayTabs redirect happens on click — test should assert redirect
```

---

## Dashboard (`/dashboard`)

```
# KPI cards (verify text present)
text='Total Orders'           # or translated equivalent
text='Delivered'
text='Pending'
text='Cancelled'

# Date range selector
input[type='date']            # from date
input[type='date']            # to date
button:has-text('Apply')
```

---

## Seller Inventory (`/seller/inventory`)

```
button:has-text('Export')
# Table columns
th:has-text('SKU')
th:has-text('Stock')
th:has-text('Warehouse')
# Empty state
text='No inventory found'
```
