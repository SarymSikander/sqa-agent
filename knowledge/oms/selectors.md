# OMS — UI Selectors Reference

This file contains exact Playwright selectors for every interactive element in the OMS portal.

## Selector Rules (React + Tailwind — No IDs)
- **Buttons:** `button:has-text('exact text')` or `role=button[name='text']`
- **Inputs by placeholder:** `input[placeholder='exact placeholder']`
- **Inputs by label:** `label:has-text('Label') >> input` or `label:has-text('Label') + input`
- **Navigation links:** `a:has-text('Menu Item')`
- **Modals/drawers:** `div[role='dialog']` or the containing drawer div
- **Tables:** `table` or `[role='grid']`
- **Select dropdowns:** `select` or Flowbite `Dropdown` component — `button:has-text('option')`
- **NEVER use** `#id` selectors — this app has no element IDs

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

## Commission Models Page (`/orders-management/commission-models`)

```
# Page header
h1:has-text('Commission Models')
p:has-text('Define per-country commission rates for agencies.')

# Primary action
button:has-text('+ New Model')

# Empty state action
button:has-text('Create First Model')

# Drawer (after clicking New Model or Edit)
div[role='dialog']                        → or the drawer panel

# Drawer form fields
input[placeholder='Enter model name']    → Model Name field
# Country select — Flowbite Select/Dropdown
button:has-text('Select')                → Country dropdown trigger
button:has-text('Loading countries...')  → while loading
# Type select
# After opening Type dropdown, options are:
button:has-text('% of Revenue')          → percentage_of_delivered_revenue
button:has-text('Flat per Order')        → flat_per_delivered_order
# Value input (number)
input[type='number']                     → Value field (first match in rule)
# Currency input
input[placeholder='AED']                 → Currency field (maxLength=3)

# Add rule
button:has-text('+ Add Rule')

# Remove a rule
button:has-text('Remove rule')

# Drawer footer
button:has-text('Cancel')
button:has-text('Save Model')

# Close drawer
button[aria-label='Close']

# Per-row edit button
button:has-text('Edit')

# Alert message
text='Each country can only appear once inside the same model.'
```

---

## Orders Page (`/orders-management/orders`)

```
# Search
input[placeholder='Search orders']

# Tab bar (order tabs)
button:has-text('All Orders')
button:has-text('Confirmation Pending')
button:has-text('Approved')
button:has-text('Dispatching in Process')
button:has-text('In Delivery')
button:has-text('Undelivered')
button:has-text('Delivered')
button:has-text('Return in Transit')
button:has-text('Return')
button:has-text('Cancelled')

# Filter & Actions
button:has-text('Filter')
button:has-text('Actions')

# Actions dropdown items (visible after clicking Actions)
button:has-text('Update Statuses')
button:has-text('Upload Orders')
button:has-text('Approve')
button:has-text('Cancel')
button:has-text('Update Tag')
button:has-text('Update Remarks')
button:has-text('Assign Courier')

# Empty state
text='No orders found'
```

---

## Agency Registrations Page (`/orders-management/agency-registrations`)

```
# Page header
h1:has-text('Agency Registrations')
p:has-text('Review and manage agency applications.')

# Status tabs
button:has-text('All')
button:has-text('Pending')
button:has-text('Approved')
button:has-text('OnHold')
button:has-text('Rejected')

# Row action
button:has-text('Review')

# Drawer — Approve flow
button:has-text('Approve Agency')
# Commission model select
select:has-text('Select commission model')    # or Flowbite select
button:has-text('Confirm Approve')
button:has-text('Cancel')

# Drawer — Hold flow
button:has-text('Put on Hold')
textarea[placeholder='Explain what needs to be fixed...']
input[type='checkbox']                       → Allow resubmit checkbox
button:has-text('Put on Hold')               → Submit hold

# Drawer — Reject flow
button:has-text('Reject')
textarea[placeholder='Reason for rejection...']
button:has-text('Confirm Reject')

# Drawer — Revoke
button:has-text('Revoke License')

# Drawer — Revert
button:has-text('Revert to Pending')

# Document links
button:has-text('Identity Document')
button:has-text('Agency Document')

# Status pills (visual verification)
span:has-text('Approved')
span:has-text('Pending')
span:has-text('OnHold')
span:has-text('Rejected')

# License pills
span:has-text('Active')
span:has-text('Revoked')
```

---

## Gold Subscriptions Page (`/orders-management/gold-subscriptions`)

```
# Search controls
button:has-text('Email')
button:has-text('Phone')
button:has-text('User ID')
button:has-text('Search')
button:has-text('Clear')

# Tabs
button:has-text('All users')
button:has-text('Gold users')

# Row actions
button:has-text('View Details')
button:has-text('Give Gold Access')
button:has-text('Extend Gold Access')
button:has-text('Remove Gold Access')
```

---

## Agents Page (`/orders-management/agents`)

```
input[placeholder='Search by Name, Email or Country']
button:has-text('Create Agent')

# Create Agent modal fields
input[placeholder='John Doe']          → Full Name
# Email, Phone Number, Country, Team inputs
```

---

## Ticketing Page — OMS View (`/orders-management/ticketing`)

```
# Search
input[placeholder='Search tickets, stores, orders...']

# Status filter options
button:has-text('All Statuses')
button:has-text('Pending')
button:has-text('In Progress')
button:has-text('Resolved')

# Category filter options
button:has-text('All Categories')
button:has-text('Order Delivery')
button:has-text('Change Order Details')
button:has-text('Contact Customer Request')
button:has-text('Customer Complaint')
button:has-text('Invoice Related')
button:has-text('Payment Issues')

# SLA filter
button:has-text('All SLA Status')
button:has-text('Within SLA')
button:has-text('SLA Breached')

# Table columns (verify headers exist)
th:has-text('Ticket ID')
th:has-text('Store')
th:has-text('Category')
th:has-text('Order ID')
th:has-text('Status')
th:has-text('Assigned To')
th:has-text('SLA')
th:has-text('Created')

# Row action
button:has-text('View')

# Ticket detail modal
button:has-text('Close')
button:has-text('Update Ticket')
button:has-text('Updating...')              → loading state
textarea[placeholder='Add notes about the resolution...']

# Status dropdown inside modal
select                                     → pick Pending / In Progress / Resolved
```

---

## Purchase Orders Page (`/orders-management/purchase-orders`)

```
button:has-text('Create PO')

# Status badge values (in table)
span:has-text('Draft')
span:has-text('Received')
span:has-text('Partially Received')
span:has-text('Cancelled')
span:has-text('Submitted')

# Create PO form fields
select                                     → Country selector
select                                     → Warehouse selector
input                                      → SKU search
button:has-text('Submit')
button:has-text('Save as Draft')
```

---

## Inventory Movements (`/orders-management/inventory-movements`)

```
# Movement type selections (tabs/radio)
button:has-text('SKU → SKU')
button:has-text('Warehouse → Warehouse')
button:has-text('To Damaged Bin')

# Damaged bin reason dropdown values
option:has-text('Physical Damage')
option:has-text('Expired Product')
option:has-text('Quality Failure')
option:has-text('Packaging Damage')
option:has-text('Customer Return - Unsellable')
option:has-text('Purchase Order Correction')
option:has-text('Lost / Missing in Audit')
option:has-text('Outdated Stock')

# SKU to SKU reason values
option:has-text('SKU Merge')
option:has-text('Wrong SKU Mapping')
option:has-text('Repackaging')
option:has-text('Services Deal')
option:has-text('Variant Consolidation')
option:has-text('Internal Adjustment')

# Warehouse to Warehouse reason values
option:has-text('Demand Fulfillment')
option:has-text('Purchase Transfer')
```
