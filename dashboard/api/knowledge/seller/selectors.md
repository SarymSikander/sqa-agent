# Seller Portal — UI Selectors Reference (VERIFIED from source code)

> Source: zambeel-fe source code `/src/components/`, `/src/pages/` — all selectors verified from TSX.
> Last updated: 2026-05-11

## Selector Rules (React + Tailwind — No IDs)
- **Buttons:** `button:has-text('exact text')`
- **Inputs:** `input[placeholder='exact placeholder']`
- **Labels → inputs:** `label:has-text('Label') >> input`
- **Navigation:** `a:has-text('Menu Item')`
- **Modals:** `div[role='dialog']`
- **NEVER use** `#id` selectors

---

## Sidebar Navigation

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

## Auth Pages

### Login (`/login`)

```
# Labels and inputs:
label:has-text('Email Address')
input[placeholder='Enter your email']         # type='email'

label:has-text('Password')
input[placeholder='Enter your password']      # type='password'

# Forgot Password link:
a:has-text('Forgot Password ?')               # ⚠️ includes space before '?'

# Submit button:
button:has-text('Sign In')
button:has-text('Signing In...')              # loading state

# Validation / error messages:
text='Please enter a valid email address.'
text='This email account either not valid or not registered with us'
text='Invalid email. Please enter a valid email address.'
text='This account has been disabled. Please contact support.'
text='Network error. Please check your internet connection.'
text='Too many attempts. Please try again later.'
```

### Register (`/register`)

```
# Labels:
label:has-text('Name')
input[placeholder='Enter your name']

label:has-text('Email')
input[placeholder='Enter your email']         # type='email'

label:has-text('Password')
input[placeholder='Enter your password']

label:has-text('Confirm Password')
input[placeholder='Confirm your password']

label:has-text('Where do you live?')          # Country field label
input[placeholder='Select your country']      # searchable country dropdown

# Phone number (PhoneInput component):
input[placeholder='Enter phone number']

# Optional promo/affiliate field:
label:has-text('Affiliate Code (optional)')
input[placeholder='Enter affiliate code (optional)']

# Submit:
button:has-text('Sign Up')
button:has-text('Signing Up...')              # loading state

# Validation messages:
text='Name is required'
text='Name cannot be just spaces'
text='Email is required'
text='Please enter a valid email address.'
text='Password is required'
text='Password must be at least 8 characters long.'
text='Confirm Password is required'
text='Passwords do not match'
text='Country is required'
text='Phone number is required'
text='No countries found'

# Firebase error messages:
text='This email is already registered. Try logging in.'
text='Password should be at least 6 characters long.'
text='Registration is currently disabled. Try again later.'
```

### Forgot Password (`/forgot-password`)

```
label:has-text('Email Address')
input[placeholder='Enter your email']

# Submit button (acts as both label and button):
button:has-text('Forgot Password ?')          # ⚠️ button text, not just a label

button:has-text('Sending Email...')           # loading state

# Success message:
text='Password reset email sent! Check your inbox.'
text='Please check your spam folder in case it doesn\'t land in your Inbox.'

# Error messages:
text='Please enter your email.'
text='This email account either not valid or not registered with us'
text='Invalid email. Please enter a valid email address.'
```

---

## Orders Page (`/orders`)

```
# Page heading:
h1:has-text('Orders Dashboard')

# Section headings:
text='Your Store Orders'                      # Collapsible section title
text='Orders which are not yet processed to Zambeel.'   # section description
text='Orders with Zambeel'                    # Collapsible section title
text='Orders that have been processed to Zambeel'       # section description

# Unprocessed orders action buttons:
button:has-text('Send To Zambeel')
button:has-text('Delete Order')               # singular — when exactly 1 selected
button:has-text('Delete Orders')              # plural — when 2+ selected
button:has-text('Deleting...')                # loading state (replaces Delete button text)

# Processing overlay (shown while connecting):
text='Connecting to Zambeel...'

# CSV Upload (in the header area):
# CsvOrderUploader component — trigger button text varies
```

### Processed Orders Table Filter Controls
```
input[placeholder='Search by Order ID']
input[placeholder='Search by Phone']
button:has-text('Filter')
button:has-text('Reset')
button:has-text('Apply Filters')

# Filter dropdowns:
select                               # Select Status dropdown
select                               # Select Sub-Status dropdown
```

### Processing Modal
```
div[role='dialog']
# Shows progress of sending orders to Zambeel
```

### Delete Confirmation Modal
```
div[role='dialog']
# Confirms deletion of selected orders
button:has-text('Delete')           # confirm
button:has-text('Cancel')
button:has-text('Deleting...')      # in-progress
```

### Empty States
```
text='No Orders Found'
text='No orders found'
```

---

## Ticketing Page (`/ticketing`)

### Page Header
```
# ⚠️ Seller ticketing uses h2, NOT h1
h2:has-text('Ticketing Management')
```

### Loading / Error States
```
text='Loading tickets...'
text='Failed to load tickets'
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

### Tabs (Seller view — seller sees "to Zambeel" first)
```
button:has-text('Tickets Assigned to Zambeel')
button:has-text('Tickets Assigned by Zambeel')
```

### Filter Controls
```
# Filter type selector — options:
option:has-text('Store Name')        # default
option:has-text('Store ID')
option:has-text('Status')
option:has-text('Team ID')

# Placeholder changes by selected type:
input[placeholder='Search by store name...']
input[placeholder='Search by store ID...']
input[placeholder='Select status...']
input[placeholder='Select team...']

button:has-text('Search')
```

### Primary Button
```
button:has-text('Create New Ticket')      # ⚠️ NO '+' prefix
```

### Table Column Headers (Seller view)
```
th:has-text('TICKET ID')
th:has-text('CATEGORY')
th:has-text('SUB-CATEGORY')
th:has-text('ORDER NUMBER')           # ⚠️ Seller uses 'ORDER NUMBER' (not 'ORDER ID')
th:has-text('DATE')
th:has-text('STATUS')
th:has-text('ACTIONS')
```

### Status Badges
```
span:has-text('Pending')              # yellow
span:has-text('In Progress')          # blue
span:has-text('Awaiting Seller Action')  # orange
span:has-text('Resolved')             # green
```

### Empty States
```
text='No tickets assigned to Zambeel'
text='No tickets assigned by Zambeel'
```

---

## Create Ticket Wizard (Modal)

```
# Wizard steps (shown in progress bar):
text='Select Store'
text='Category & Type'
text='Details & Files'
text='Review'

# Step 2 — Category options:
text='Onboarding & Integration'
text='Order Sending & Inventory Issue'
text='Order Changes & Updates'
text='Product Complaint'
text='Delivery Complaint'
text='Payments & Invoices'

# Sub-category options (examples):
text='Request to Cancel the order'
text='Change Price'
text='Change Quantity'
text='Damaged/defective item delivered'
text='Wrong item/SKU delivered'
text='Invoice not received'
text='Payment not received'

# Step 3 — file upload:
input[type='file']
text='Maximum 3 files allowed'

# Wizard navigation:
button:has-text('Next')
button:has-text('Back')
button:has-text('Submit')
button:has-text('Cancel')

# Success screen:
h3:has-text('Ticket Created Successfully!')
```

---

## Payment Methods / Bank Accounts (`/settings`)

### Page Header
```
h1:has-text('Payment Methods')              # ⚠️ NOT 'Bank Accounts'
input[placeholder='Search accounts']        # search bar
h2:has-text('Connected Accounts')           # section heading
```

### Table Column Headers (confirmed from source)
```
th:has-text('Account Name')
th:has-text('Type')
th:has-text('IBAN/BIC/IFSC/Email')
th:has-text('Country')
th:has-text('Primary')
th:has-text('Date Added')
th:has-text('Status')
```

### Add Account Form — Bank Account fields
```
# Payment type selection buttons:
button:has-text('Bank Account')
button:has-text('USDT')
button:has-text('PayPal')

# Bank Account form labels (confirmed from bankForm.tsx):
label:has-text('Account Title')
label:has-text('Account Nickname')
label:has-text('Bank Account Country')      # select dropdown
label:has-text('Bank Name')
# Also: IBAN field (label varies by country)

# USDT form:
# Exchange Name, Exchange ID, Wallet Address, First Name, Last Name fields

# Actions:
button:has-text('Add Account')
button:has-text('Set as Primary')
button:has-text('Delete')
button:has-text('Save')
button:has-text('Cancel')
```

---

## Stores Integration (`/stores/integration`)

```
# Platform connect buttons:
button:has-text('Connect Shopify')
button:has-text('Connect EasyOrder')
button:has-text('Connect Light Funnels')
button:has-text('Connect YouCan')
button:has-text('Create Manual Store')

# Disconnect:
button:has-text('Disconnect')

# Manual store sub-platform options:
text='Facebook Marketplace'
text='Amazon'
text='Whatsapp Marketplace'
text='Salla'
text='Zid'
text='Ebay'

# Errors:
text='Store Nick name already exists. Please choose a different name.'
text='Unsupported integration type'
text='Failed to connect store'
```

---

## Profile (`/profile`)

### Page Header
```
h1:has-text('Profile Settings')
p:has-text('Manage your account information and preferences')
```

### Profile Card (left side)
```
# Avatar card shows user name and email
button:has-text('Go to Dashboard')
```

### Personal Information Form (right side)
```
h3:has-text('Personal Information')

# Fields:
label:has-text('Full Name')
input[placeholder='Enter your full name']

label:has-text('Email Address')
# Email field is disabled (read-only)
text='Email cannot be changed'

label:has-text('Country')
input[placeholder='Select your country']      # searchable dropdown

label:has-text('Phone Number')
input[placeholder='+1']                       # country code (disabled)
input[placeholder='Enter phone number']       # number input

# Submit buttons:
button:has-text('Cancel')
button:has-text('Update Profile')
button:has-text('Updating...')                # loading state

# Errors:
text='Name is required'
text='Country is required'
text='Phone number is required'
text='No countries found'
```

### Terms & Conditions Card
```
h3:has-text('Terms & Conditions')
text='Status:'
text='Accepted'                               # when accepted
text='Not Accepted'                           # when not accepted
text='Accepted Date:'
text='Version:'
a:has-text('View Full Terms & Conditions')
```

### Agency Connection Card
```
# Not Connected state:
input[placeholder='ZMB-AG-XXXXXX']
text='Please enter a valid Agency ID (format: ZMB-AG-XXXXXX).'  # validation error

# Pending state:
text='Request Sent'
button:has-text('Cancel')

# Connected state:
text='Connected to Agency'
button:has-text('Disconnect')

# Disconnect Modal:
div[role='dialog']
text='The agency will lose access to your store data immediately upon disconnection.'
# Reason options:
text='No longer need agency services'
text='Switching to a different agency'
text='Unsatisfied with service'
text='Business closure'
text='Other'
textarea                                      # if 'Other' selected
```

---

## Gold Subscription (`/gold-subscription`)

### Loading State
```
text='Loading...'                             # index page while checking and redirecting
```

### Subscription Page (`/gold-subscription/subscription`)
```
# The GoldSubscriptionComponents are rendered here.
# Key page loading state:
text='Checking subscription status...'        # products page while checking
```

### Products Page (`/gold-subscription/products`)
```
# No-access state:
h2:has-text('You don\'t have access')
p:has-text('Please unlock the Gold plan to access products.')
a:has-text('Unlock Gold Plan')

# Active state: ProductCatalog component rendered
```

---

## Seller Inventory (`/seller/inventory`)

### Page Header
```
h1:has-text('Inventory Management')
p:has-text('View and manage your inventory across all countries')
h2:has-text('Product Inventory')            # section heading inside
```

### Controls
```
input[placeholder='Search product name or SKU...']
button:has-text('Export Inventory')
button:has-text('Exporting...')             # loading state
```

### Table Column Headers (confirmed from inventoryTable.tsx)
```
th:has-text('Product Name')
th:has-text('SKU Code')
th:has-text('Country')
th:has-text('Total Received')
th:has-text('Stock in Warehouse')
th:has-text('Shipped')
th:has-text('Undelivered')
th:has-text('Returning in Transit')
th:has-text('Delivered Stock')
th:has-text('Inventory Owner')
th:has-text('Inventory Movement')
th:has-text('Logs')
```

### Empty State
```
text='No Data Available'
```

---

## Invoices (`/my-invoices`)

### Section Header
```
h2:has-text('Invoices')
```

### Loading / Error States
```
text='Loading invoices...'
```

### Table Column Headers
```
th:has-text('Invoice Name')
th:has-text('Store Name')
th:has-text('Payment Status')
th:has-text('Payment Reason')
th:has-text('Date of Invoice')
th:has-text('Download')
```

### Pagination Controls
```
label:has-text('Per page:')
select                                        # items per page (10, 25, 50, 100)
label:has-text('Go to:')
select                                        # go to page
# Previous/Next page buttons (icon buttons)
```

### Download Button Per Row
```
button:has-text('Download')
button:has-text('Downloading')               # loading state
```

### Empty States
```
h3:has-text('No Invoices Found')
text='Try selecting another store from the dropdown above.'   # store selected, no invoices
text='Select a store to view available invoices.'             # no store selected
```

---

## Dashboard (`/dashboard`)

```
# KPI cards (verify text present after load):
text='Total Orders'
text='Delivered'
text='Pending'
text='Cancelled'

# Date range inputs:
input[type='date']                            # from date
input[type='date']                            # to date
button:has-text('Apply')
```

---

## Get Started (`/get-started`)

```
# The GetStarted page renders different components by path:
# /get-started           → GetStartedComponents
# /get-started/dropshipping → DropshippingComponents
# /get-started/zambeel-360  → Zambeel360Components
# /get-started/3pl-services → ThreePLServicesComponents

# Common landing page CTA patterns:
button:has-text('Get Started')
button:has-text('Learn More')
```

---

## ⚠️ Corrections vs Previously Documented

| Field | Old (incorrect) | Correct (verified from source) |
|-------|----------------|-------------------------------|
| Ticketing heading | `h1:has-text('Ticketing System')` | **`h2:has-text('Ticketing Management')`** |
| Ticketing "Create" | `button:has-text('Create New Ticket')` (had '+' in old docs) | **`button:has-text('Create New Ticket')`** (no '+') |
| Ticket table column | `th:has-text('ORDER ID')` | **`th:has-text('ORDER NUMBER')`** (seller view) |
| Delete button | single label "Delete" | **'Delete Order'** (singular) / **'Delete Orders'** (plural) |
| Settings page title | implied 'Bank Accounts' | **`h1:has-text('Payment Methods')`** |
| Settings table | old column list | **Account Name, Type, IBAN/BIC/IFSC/Email, Country, Primary, Date Added, Status** |
| Inventory columns | SKU, Stock, Warehouse | **12-column table** (full list above) |
| Profile page title | generic | **`h1:has-text('Profile Settings')`** |
| Profile form section | generic | **`h3:has-text('Personal Information')`** |
| Profile form fields | `input[name='username']` etc | **`input[placeholder='Enter your full name']`** etc |
| Gold subscription | 'Subscribe'/'Renew' buttons | **redirects to PayTabs; check `a:has-text('Unlock Gold Plan')`** for no-access state |
