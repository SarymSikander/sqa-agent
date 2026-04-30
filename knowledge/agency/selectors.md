# Agency Portal — UI Selectors Reference

## Selector Rules
- **Buttons:** `button:has-text('exact text')`
- **Inputs:** `input[placeholder='exact placeholder']`
- **Navigation:** `a:has-text('Menu Item')`
- **Modals:** `div[role='dialog']`
- **NEVER use** `#id` selectors

---

## Sidebar — Agency Tab

```
# Switch to Agency portal
button:has-text('Agency')        → sidebar tab

# Agency navigation (approved only)
a:has-text('Dashboard')          → /agency
a:has-text('Merchants')          → /agency/portal/merchants
a:has-text('Commission')         → /agency/portal/commission
a:has-text('Team Members')       → /agency/portal/team-members
a:has-text('Settings')           → /agency/portal/settings
```

---

## Agency Dashboard (`/agency` — approved state)

```
# Page header
h1:has-text('Agency Dashboard')
p:has-text('Performance across all your merchants')

# Summary cards
text='Active Merchants'
text='Total Stores'
text='Delivered Orders'
text='Commission Earned'
text='Commission Due'

# Range filter buttons (from AGENCY_REPORT_RANGE_OPTIONS)
button:has-text('7d')           # or
button:has-text('30d')
button:has-text('all')

# Refresh
button[title='Refresh']         # or RefreshCcw icon button

# Merchants table search
input[placeholder='Search merchants or stores...']

# Section title
text='Merchants & Stores'

# Empty / loading
text='No merchants found'
text='Loading dashboard...'
```

---

## Commission Hub (`/agency/portal/commission`)

```
# Header
h1:has-text('Commission & Invoices')
p:has-text('Track earnings and view invoices from Zambeel')

# Summary cards
text='Total Earned'
text='Total Paid'
text='Commission Due'

# Tabs
button:has-text('Invoices')
button:has-text('Store Breakdown')

# Invoice tab — status badges
span:has-text('Paid')
span:has-text('Unpaid')

# Invoice download
button[aria-label='Download']   # or download icon button per row

# Empty states
text='No invoices available'
text='No commission records available'
```

---

## Team Members (`/agency/portal/team-members`)

```
# Header
h1:has-text('Team Members')
p:has-text('Manage who has access to the agency portal')

# Add member (currently disabled)
button:has-text('Add Member')
button[title='Temporarily disabled']

# Modal (if enabled)
div[role='dialog']
h2:has-text('Add Team Member')
input[placeholder="Team member's name"]
input[placeholder='email@example.com']
button:has-text('Send Invite')
button:has-text('Sending...')
button:has-text('Cancel')

# Team member list
text='Loading team members...'
text='No team members yet'

# Remove member
button[title='Remove']           # Trash2 icon

# Role display
text='Admin'                     # Owner role shown as Admin
```

---

## Merchants (`/agency/portal/merchants`)

```
# Header
h1:has-text('Merchants')
p:has-text('Manage your merchant connections')

# Status tabs
button:has-text('Pending Requests')
button:has-text('Active')
button:has-text('Inactive')

# Pending request actions (per card)
button:has-text('✓ Accept')     # or just button with Accept text
button:has-text('✕ Reject')     # or just button with Reject text

# Active/Inactive actions
button:has-text('View details →')

# Merchant drawer
div[role='dialog']              # or drawer panel
# Sections
text='STORES'
text='Commission Summary'

# Store items in drawer
button:has-text('Open →')
span:has-text('Locked')         # inactive stores

# Disconnect button (Active merchants)
button:has-text('Disconnect Merchant')

# Toast confirmations
text='Request accepted'
text='Request rejected'
text='Merchant disconnected'

# Empty states
text='No merchants found'
text='No stores available'
text='Loading merchants...'
```

---

## Agency Settings (`/agency/portal/settings`)

```
# Header
h1:has-text('Agency Settings')
p:has-text('Manage your agency profile')

# Agency ID card
text='Agency ID'
text='Share this ID with merchants to connect to your agency.'
button:has-text('Copy')
button:has-text('Copied')       # after copy (1500ms)

# Profile section
text='Agency Profile'
# Meta text
text='Country:'
text='Member since:'

# Form fields
input[name='name']              # or by label: Agency Name
input[name='city']
input[name='phone']
input[name='poc_name']          # Point of Contact

# Save
button:has-text('Save')

# Footer note
text='Need to transfer ownership? Contact ilqa@myzambeel.com.'

# Toast
text='Agency settings updated'
```

---

## Agency Registration Modal

```
# Modal
div[role='dialog']
h2:has-text('Apply to Become an Agency')

# Progress indicator
text='Step 1 of 2'
text='Step 2 of 2'

# Step 1 — Details form
input[placeholder='Enter your agency name']
# Country select
select                              → country dropdown
# City (if dropdown available)
button:has-text('Select city')      → SearchableDropdown
# or plain text input
input[placeholder='Type city']
input[placeholder='Select country first']   # disabled state
# Phone
input[placeholder='+971 50 000 0000']
# POC name
input[placeholder='Full name of main contact']

# Step 1 button
button:has-text('Continue')

# Step 2 — Uploads
text='Point of Contact Photo'
text='A clear face photo for verification.'
input[accept='image/*']             # first upload input
text='Identity Proof'
text='National ID / Passport (front side).'
input[accept='image/*']             # second upload input

# Terms checkbox
input[type='checkbox']
text='I agree that the information and documents provided are accurate'

# Step 2 buttons
button:has-text('Submit')
button:has-text('Submitting...')    # loading state

# Universal cancel
button:has-text('Cancel')
```

---

## Agency Invite Accept Page (`/agency/invite`)

```
# Page context (team invitation modal)
h2:has-text('Agency Team Invitation')
text='You have been invited by'
text='to join their agency team.'
text='You already accepted this invitation.'   # if already done

button:has-text('Accept')
button:has-text('Decline')

# Toast messages
text='Invitation accepted.'
text='Invitation declined.'
```

---

## Status Pills (Agency-wide)

```
# Agency registration statuses
span:has-text('Pending')
span:has-text('Approved')
span:has-text('OnHold')
span:has-text('Rejected')

# Merchant connection statuses
span:has-text('Active')
span:has-text('Inactive')
span:has-text('Pending')

# Invoice statuses
span:has-text('Paid')
span:has-text('Unpaid')

# Team member statuses
span:has-text('Active')
span:has-text('Invite Pending')
```
