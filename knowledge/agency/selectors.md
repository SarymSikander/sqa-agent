# Agency Portal — UI Selectors Reference

> Source: Zambeel Agency Model PRD (Zambeel-Agency.pdf) + zambeel-fe source code.

## Selector Rules
- **Buttons:** `button:has-text('exact text')`
- **Inputs:** `input[placeholder='exact placeholder']`
- **Navigation:** `a:has-text('Menu Item')`
- **Modals/Drawers:** `div[role='dialog']`
- **NEVER use** `#id` selectors

---

## Sidebar — Agency Tab

```
# Switch to Agency portal
button:has-text('Agency')                     → sidebar tab

# Agency navigation (no registration / pending)
a:has-text('Dashboard')                       → /agency

# Agency navigation (approved only)
a:has-text('Dashboard')                       → /agency/portal/dashboard
a:has-text('Merchants')                       → /agency/portal/merchants
a:has-text('Commission')                      → /agency/portal/commission
a:has-text('Team Members')                    → /agency/portal/team-members
a:has-text('Settings')                        → /agency/portal/settings
```

---

## Agency Program Landing Page (`/agency` — no registration)

```
# Landing page CTA
button:has-text('Apply Now')                  → opens AgencyRegistrationModal

# Feature cards text
text='Manage Merchants'
text='Unified Dashboard'
text='Earn Commission'

# How It Works steps
text='How It Works'

# FAQ section
text='FAQ'                                    # or accordion trigger
```

---

## Agency Status Cards (`/agency` — post-application)

```
# Pending card
text='Application Under Review'

# Approved card
text='Approved!'
text='Agency ID'
button:has-text('Copy')                       # copies Agency ID
button:has-text('Open Agency Portal')         # → /agency/portal/dashboard

# OnHold card
text='hold_reason'                            # dynamic text from API

# Rejected card
text='cooloff_days_remaining'                 # dynamic

# Revoked card (overrides all)
text='Agency Access Revoked'
```

---

## Agency Registration Modal

```
# Modal
div[role='dialog']
h2:has-text('Apply to Become an Agency')

# Step indicators
text='Step 1 of 3'
text='Step 2 of 3'
text='Step 3 of 3'

# Step 1 — Details form
input[placeholder='Enter your agency name']
# Country select
select                                        → country dropdown (UAE, Saudi Arabia, etc.)
# City
button:has-text('Select city')                → SearchableDropdown trigger
input[placeholder='Type city']                → plain text input fallback
input[placeholder='Select country first']     → disabled state before country selected
# Phone
input[placeholder='+971 50 000 0000']
# POC name
input[placeholder='Full name of main contact']

# Step 1 navigation
button:has-text('Continue')

# Step 2 — Document Uploads
text='POC Photo'                              # or 'Point of Contact Photo'
text='A clear face photo for verification.'
input[accept='image/*']                       # first upload input (max 5MB)
text='Identity Proof'
text='Passport / National ID'
input[accept='image/*,application/pdf']       # second upload input (max 10MB)

# Step 2 navigation
button:has-text('Continue')

# Step 3 — Terms
input[type='checkbox']
text='I confirm that all information is accurate and I agree to Zambeel'    # partial match

# Step 3 submit
button:has-text('Submit')
button:has-text('Submitting...')              # loading state

# Universal cancel
button:has-text('Cancel')
```

---

## Agency Dashboard (`/agency/portal/dashboard`)

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

# Time filter buttons (exact labels)
button:has-text('7 Days')
button:has-text('30 Days')
button:has-text('All Time')

# Refresh
button[title='Refresh']                       # RefreshCcw icon button

# Merchants table section
text='Merchants & Stores'
input[placeholder='Search merchants or stores...']

# Table columns
text='MERCHANT'
text='STORE URL'
text='ORDERS / REVENUE'
text='COMMISSION'
text='INVOICE'

# Currency pills
span:has-text('AED')                          # blue pill
span:has-text('SAR')                          # amber pill
span:has-text('PKR')                          # green pill
span:has-text('USD')                          # gray pill

# Expand/collapse merchant row
button[aria-label='expand']                   # or chevron button

# "View" link in Invoice column
a:has-text('View')

# Empty / loading states
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
span:has-text('Paid')                         # green
span:has-text('Unpaid')                       # orange

# Invoice PDF download
button[aria-label='Download']                 # or download icon per row

# Empty states (exact text from PRD)
text='No invoices yet'                        # ⚠️ NOT 'No invoices available'
text='No commission records yet'              # ⚠️ NOT 'No commission records available'
```

---

## Team Members (`/agency/portal/team-members`)

```
# Header
h1:has-text('Team Members')
p:has-text('Manage who has access to the agency portal')

# Add member button (functional per PRD)
button:has-text('Add Member')

# Add member modal
div[role='dialog']
h2:has-text('Add Team Member')
input[placeholder="Team member's name"]
input[placeholder='email@example.com']
button:has-text('Send Invite')
button:has-text('Sending...')                 # loading state
button:has-text('Cancel')

# Team member list
text='Loading team members...'
text='No team members yet'

# Status badges
span:has-text('Active')
span:has-text('Invite Pending')

# Role display
text='Admin'                                  # Owner role shown as Admin

# Remove member (trash icon)
button[title='Remove']

# Remove confirmation modal (NOT window.confirm)
div[role='dialog']
text='Will lose access to the agency portal. This cannot be undone.'
button:has-text('Remove')
button:has-text('Cancel')

# Toast
text='Member removed'
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

# Pending tab — action buttons per card
button:has-text('Accept')                     # green (checkmark)
button:has-text('Reject')                     # red (X)

# Active/Inactive tabs
button:has-text('View details →')

# Merchant Detail Drawer
div[role='dialog']                            # or panel (420px wide)

# Drawer header
span:has-text('Active')                       # green dot badge
span:has-text('Inactive')                     # gray dot badge
text='Connected since'
text='Disconnected on'

# Drawer — STORES section
text='STORES'
button:has-text('Open →')                     # active stores only
text='No access'                              # inactive/grayed out stores ⚠️ NOT 'Locked'

# Drawer — Commission Summary
text='Commission Summary'
text='Total Earned'
text='Total Paid'
text='Commission Due'
text='Historical data only.'                  # inactive merchant note

# Disconnect button (Active merchants)
button:has-text('Disconnect Merchant')        # rose button

# Toast messages
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
text='Share this ID with merchants'
button:has-text('Copy')
button:has-text('Copied')                     # after copy (2 seconds per PRD, 1500ms in source)

# Profile section
text='Agency Profile'
text='Country:'
text='Member since:'

# Form fields (non-editable per PRD — shown for reference)
input[name='name']
input[name='city']
input[name='phone']
input[name='poc_name']

# Save
button:has-text('Save')                       # or 'Save Changes'; disabled until form isDirty

# Ownership transfer footer
text='Need to transfer ownership?'
text='support@zambeel.com'                    # or ilqa@myzambeel.com in source

# Toast
text='Agency settings updated'
```

---

## Merchant Agency Connection Section (Seller Profile Page)

```
# Not Connected state
input[placeholder='ZMB-AG-XXXXXX']           # Agency ID input
# Inline validation error (invalid format)
text='Please enter a valid Agency ID (format: ZMB-AG-XXXXXX).'

# Pending state
text='Request Sent'
button:has-text('Cancel')                     # cancel pending request

# Active (Connected) state
text='Connected to Agency'
button:has-text('Disconnect')                 # opens Disconnect Modal

# Disconnect Modal
div[role='dialog']
text='The agency will lose access to your store data immediately upon disconnection.'
# Reason dropdown options:
text='No longer need agency services'
text='Switching to a different agency'
text='Unsatisfied with service'
text='Business closure'
text='Other'
# If 'Other' selected:
textarea                                       # optional free-text

# Revoked agency warning
text='Agency Access Revoked'                  # warning when connected agency is revoked
```

---

## Agency Invite Accept Page (`/agency/invite`)

```
# Team invitation modal
h2:has-text('Agency Team Invitation')
text='You have been invited by'
text='to join their agency team.'
text='You already accepted this invitation.'  # if already done

button:has-text('Accept')                     # blue
button:has-text('Decline')                    # gray

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
span:has-text('Revoked')                      # license_status override

# Merchant connection statuses
span:has-text('Active')
span:has-text('Inactive')                     # shown for Disconnected
span:has-text('Pending')

# Invoice statuses
span:has-text('Paid')
span:has-text('Unpaid')

# Team member statuses
span:has-text('Active')
span:has-text('Invite Pending')
```

---

## Agency Context Banner (Proxy Mode — Seller Portal)

```
# Shown on every page while in agency proxy mode
# Format: "Agency Name · Merchant Name · Store Name"
text='·'                                      # separator dots in banner
# Exit context
button:has-text('Agency')                     # sidebar nav back to agency portal
# or navigate to /agency/portal/* — context is cleared automatically
```
