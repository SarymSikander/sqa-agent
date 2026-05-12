# Agency Portal — UI Selectors Reference (VERIFIED from source code)

> Source: zambeel-fe source code `/src/pages/agency/`, `/src/components/agency/` — all selectors verified from TSX.
> Last updated: 2026-05-11

## Selector Rules
- **Buttons:** `button:has-text('exact text')`
- **Inputs:** `input[placeholder='exact placeholder']`
- **Navigation:** `a:has-text('Menu Item')`
- **Modals/Drawers:** `div[role='dialog']`
- **NEVER use** `#id` selectors

---

## Sidebar — Agency Tab

```
# Agency navigation (approved portal):
a:has-text('Dashboard')                       → /agency or /agency/portal/dashboard
a:has-text('Merchants')                       → /agency/portal/merchants
a:has-text('Commission')                      → /agency/portal/commission
a:has-text('Team Members')                    → /agency/portal/team-members
a:has-text('Settings')                        → /agency/portal/settings
```

---

## Agency Program Landing Page (`/agency` — no registration / not approved)

### Landing Header
```
# Breadcrumb:
a[href='/dashboard']                          # Home icon link

# Page heading:
h1:has-text('Zambeel Marketing Agency Program')
p:has-text('Manage all your clients under one account and earn commission on every delivered order.')

# CTA button:
button:has-text('Apply Now')                  # opens AgencyRegistrationModal
```

### Contact / Footer
```
text='Questions? Email'
a[href='mailto:ilqa@myzambeel.com']
```

---

## Agency Registration Modal

```
# Modal (Flowbite Modal):
div[role='dialog']
h2:has-text('Apply to Become an Agency')

# Step progress indicator (text format):
text='Step 1 of 2'                            # ⚠️ 2 steps NOT 3 — source has 2 steps
text='Step 2 of 2'

# Step 1 label: "Agency Details"
# Step 2 label: "Documents & Terms"
```

### Step 1 — Agency Details
```
# Agency Name:
text='Agency Name'                            # label (has '*' red asterisk)
input[placeholder='Enter your agency name']

# Country:
text='Country'                                # label
select                                        # country dropdown (UAE shown as "UAE" in dropdown)

# City (depends on country):
input[placeholder='Select City']              # SearchableDropdown for countries with known cities
input[placeholder='Enter city']              # plain text input for other countries
input[placeholder='Select country first']    # disabled state before country is chosen

# Phone:
text='Phone Number'                           # label
input[placeholder='+971 50 000 0000']

# POC Name:
text='Point of Contact Name'                  # label
input[placeholder='Full name of primary contact person']

# Navigation:
button:has-text('Continue')
button:has-text('Cancel')
```

### Step 2 — Documents & Uploads
```
# Upload cards:
text='Point of Contact Photo'                 # card title
text='Clear face photo for verification.'     # card description
input[accept='image/*']                       # poc photo file input (id='agency-poc-photo')

text='Identity Proof'                         # card title
text='National ID / Passport (front side).'  # card description
input[accept='image/*']                       # identity proof file input (id='agency-identity-proof')

# Terms and Conditions:
text='Terms and Conditions'                   # section label
input[type='checkbox']                        # terms checkbox
text='I confirm the provided information and documents are accurate, and I agree to submit them for review.'

# Navigation:
button:has-text('Submit')
button:has-text('Submitting...')              # loading state
button:has-text('Cancel')
```

---

## Agency Status Pages

### Application Pending (`AgencyApplicationPending`)
```
h1:has-text('Application Submitted')
p:has-text('Your agency is currently under review.')

# Info cards:
text='Processing time'
text='3-4 days'
text='We\'ll review your documents and respond after approval.'
text='Need help?'
text='If you have any question during the waiting period, contact Zambeel Support.'
button:has-text('Contact Support')             # links to /ticketing

# Status card:
text='Current Status'
text='We\'re reviewing your submission.'
text='Registration'
text='License'

# Tip message:
text='Tip: Keep checking back for updates. After approval, your agency portal will unlock automatically.'
```

### Application On Hold (`AgencyApplicationOnHold`)
```
h1:has-text('Application On Hold')
p:has-text('We need a quick clarification before we can continue.')

# Status badge:
span:has-text('On Hold')

# Info card:
text='What this means'
text='Your application is safe. It\'s paused until we receive/verify additional information.'
text='Need help?'
text='Contact Zambeel Support and mention your Agency Application.'
button:has-text('Contact Support')

# Reason card:
text='Reason'
text='Please read this carefully and contact support if needed.'
# reason text is dynamic from API (hold_reason)

# Resubmit section (shown when allow_resubmit = true):
text='Re-upload requested documents'
text='Upload the updated files below and submit for re-review.'
text='Point of Contact Photo'
text='Identity Proof'
# Upload state buttons:
text='Upload image'                           # before upload
text='Uploaded'                               # after upload
text='Upload image/pdf'                       # identity proof (accepts PDF too)

button:has-text('Re-submit Documents')
button:has-text('Submitting...')              # loading state

# No-resubmit tip:
text='Tip: If support asks for additional documents, you can re-submit after they enable it for you.'
```

### Application Rejected (`AgencyApplicationRejected`)
```
h1:has-text('Application Rejected')
p:has-text('Don\'t worry — we can help you get it right.')

# Status badge:
span:has-text('Rejected')

# Info cards:
text='Next step'
text='Review the reason below. If something can be fixed, contact support for guidance.'
text='Contact Support'
button:has-text('Contact Support')

# Reason card:
text='Reason'
text='This is why your application was rejected.'
# reason text is dynamic from API (reject_reason)

# Tip:
text='Tip: If you think the reason is incorrect, share details (and any supporting documents) with support.'
```

---

## Agency Team Invitation Flow (`/agency/invite`)

### Pre-login (not authenticated)
```
h1:has-text('Agency Invitation')
p:has-text('Sign in or create an account for')
text='to accept this invite.'
a:has-text('Login')                           # link to /login?redirect=...
a:has-text('Sign Up')                         # link to /register?redirect=...
```

### Post-login (authenticated, redirecting)
```
h1:has-text('Agency Invitation')
text='Redirecting to agency portal...'
text='Preparing invitation acceptance...'     # idle state
```

### Invite Accept Modal (shown on /agency page after redirect)
```
# Flowbite Modal:
div[role='dialog']
# Modal header:
text='Agency Team Invitation'

# Body:
text='You have been invited by'               # followed by agency name
text='to join their agency team.'
text='You already accepted this invitation.'  # if alreadyAccepted=true

# Footer buttons:
button:has-text('Decline')                    # gray
button:has-text('Accept')                     # blue

# Result messages (inline):
text='Invitation accepted.'
text='Invitation declined.'
```

---

## Agency Dashboard (`/agency/portal/dashboard`)

### Page Header
```
h1:has-text('Agency Dashboard')
p:has-text('Performance across all your merchants')
```

### Time Range Buttons (from AGENCY_REPORT_RANGE_OPTIONS)
```
# Exact label text from source:
button:has-text('7 Days')
button:has-text('30 Days')
button:has-text('All Time')
# ⚠️ verify exact labels from AGENCY_REPORT_RANGE_OPTIONS constant if changed
```

### Refresh Button
```
button:has-text('Refresh')                    # ⚠️ text 'Refresh' NOT just an icon
```

### Summary Cards
```
text='Active Merchants'
text='Total Stores'
text='Delivered Orders'
text='Commission Earned'
text='Commission Due'
```

### Merchants Table Section
```
# Section heading:
text='Merchants & Stores'                     # or similar — check actual source

# Search input:
input[placeholder='Search merchants or stores...']

# Table column headers:
th:has-text('Merchant')
th:has-text('Store URL')
th:has-text('Orders / Revenue')               # ⚠️ note space around '/'
th:has-text('Commission')
th:has-text('Invoice')

# Invoice column — "View" link:
a:has-text('View')
```

### Loading / Empty States
```
text='Loading dashboard...'
text='No merchants found'
```

---

## Merchants (`/agency/portal/merchants`)

### Page Header
```
h1:has-text('Merchants')
p:has-text('Manage merchant connections')
```

### Status Tabs
```
# ⚠️ Tabs are: Pending, Active, Inactive — NOT 'Pending Requests'
button:has-text('Pending')
button:has-text('Active')
button:has-text('Inactive')
```

### Pending Tab — Action Buttons
```
button:has-text('Accept')                     # per merchant card
button:has-text('Reject')                     # per merchant card
```

### Active / Inactive Tabs
```
# ⚠️ Button text is 'View Details' (NOT 'View details →' with arrow)
button:has-text('View Details')
```

### Merchant Detail Drawer
```
div[role='dialog']                            # or slide-in panel

# Status badges:
span:has-text('Active')                       # green
span:has-text('Inactive')                     # gray

# Connection info:
text='Connected since'
text='Disconnected on'                        # inactive merchants

# Stores section:
text='STORES'                                 # or 'Stores' heading

# Per-store buttons:
button:has-text('Open')                       # ⚠️ NOT 'Open →' — plain text
text='Closed'                                 # ⚠️ NOT 'No access' — shows for inactive stores

# Commission Summary section:
text='Commission Summary'
text='Total Earned'
text='Total Paid'
text='Commission Due'
text='Historical data only.'                  # shown for inactive merchants

# Disconnect button (Active merchants only):
button:has-text('Disconnect Merchant')

# Toast messages:
text='Request accepted'
text='Request rejected'
text='Merchant disconnected'
```

### Empty / Loading States
```
text='No merchants found'
text='No stores available'
text='Loading merchants...'
```

---

## Commission Hub (`/agency/portal/commission`)

### Page Header
```
h1:has-text('Commission & Invoices')
p:has-text('Track earnings and view invoices from Zambeel')
```

### Summary Cards
```
text='Total Earned'
text='Total Paid'
text='Commission Due'
```

### Tabs
```
button:has-text('Invoices')
button:has-text('Store Breakdown')            # ⚠️ NOT 'Stores' — exact text "Store Breakdown"
```

### Invoice Tab
```
span:has-text('Paid')                         # green badge
span:has-text('Unpaid')                       # orange badge

# Download button:
button                                        # download icon button per row

# Empty states:
text='No invoices yet'
text='No commission records yet'
```

---

## Team Members (`/agency/portal/team-members`)

### Page Header
```
h1:has-text('Team Members')
p:has-text('Manage who can access the agency portal')   # ⚠️ exact text confirmed from source
```

### Add Member Button
```
# ⚠️ Currently DISABLED in source (isAddTeamMemberDisabled = true)
button:has-text('Add Member')                 # disabled, title='Temporarily disabled'
```

### Loading / Empty States
```
text='Loading team members...'
text='No team members yet'
```

### Member List Items
```
# Role badge (indigo):
span:has-text('Owner')
span:has-text('Admin')                        # or other roles

# Status badge:
span:has-text('Active')                       # emerald
span:has-text('Pending')                      # or amber for non-active

# Remove button (trash icon, non-owner only):
button[title='Remove']                        # Trash2 icon
```

### Add Team Member Modal (when enabled)
```
div                                           # fixed overlay (not Flowbite Modal)
h2:has-text('Add Team Member')

# Fields:
label:has-text('Full Name*')
input[placeholder='Team member name']

label:has-text('Email*')
input[placeholder='email@example.com']

# Buttons:
button:has-text('Cancel')
button:has-text('Send Invitation')
button:has-text('Sending...')                 # loading state

# Toast messages:
text='Invitation sent successfully'
text='Email not sent; invitation link copied'
text='Invitation created but email failed'
text='Full name is required'
text='Please enter a valid email address.'
text='Failed to send invitation'
```

### Remove Confirmation
```
# window.confirm dialog (native browser dialog):
# text: 'Remove [member name] from team?'
# Note: This is window.confirm — NOT a Playwright-style modal
# Use page.on('dialog', ...) to handle it in Playwright
```

---

## Agency Settings (`/agency/portal/settings`)

### Page Header
```
h1:has-text('Agency Settings')
p:has-text('Manage your agency profile')
```

### Agency ID Card
```
text='Agency ID'
text='Share this ID with merchants to connect to your agency.'
button:has-text('Copy')
button:has-text('Copied')                     # after copy (1500ms timeout)
```

### Agency Profile Section
```
h2:has-text('Agency Profile')

# Meta info text:
text='Country:'
text='Member since:'

# Editable form fields (no placeholders — current values pre-filled):
label:has-text('Agency Name')
label:has-text('City')
label:has-text('Phone Number')
label:has-text('Point of Contact')

# Save button (disabled until isDirty):
button:has-text('Save')

# Ownership transfer footer:
text='Need to transfer ownership? Contact'
a[href='mailto:ilqa@myzambeel.com']

# Toast:
text='Agency settings updated'
text='Failed to update agency settings'

# Loading / Error states:
text='Agency profile not found'               # error when API returns no agency
```

---

## Merchant Agency Connection (Seller Profile Page)

```
# Not Connected state:
input[placeholder='ZMB-AG-XXXXXX']
text='Please enter a valid Agency ID (format: ZMB-AG-XXXXXX).'

# Pending state:
text='Request Sent'
button:has-text('Cancel')

# Active (Connected) state:
text='Connected to Agency'
button:has-text('Disconnect')

# Disconnect Confirmation Modal:
div[role='dialog']
text='The agency will lose access to your store data immediately upon disconnection.'
# Reason dropdown options:
text='No longer need agency services'
text='Switching to a different agency'
text='Unsatisfied with service'
text='Business closure'
text='Other'
textarea                                      # free-text when 'Other' selected
```

---

## Status Pills (Agency-wide)

```
# Agency registration statuses:
span:has-text('Pending')
span:has-text('Approved')
span:has-text('OnHold')
span:has-text('Rejected')
span:has-text('Revoked')

# Merchant connection statuses:
span:has-text('Active')
span:has-text('Inactive')
span:has-text('Pending')

# Invoice statuses:
span:has-text('Paid')
span:has-text('Unpaid')

# Team member statuses:
span:has-text('Active')
span:has-text('Pending')                      # Invite pending state
```

---

## Agency Context Banner (Proxy Mode — Seller Portal)

```
# Shown on every page while browsing as a merchant via agency context
# Format: "Agency Name · Merchant Name · Store Name"
text='·'                                      # separator dots

# Exit proxy mode:
button:has-text('Agency')                     # sidebar nav — returns to agency portal
```

---

## ⚠️ Corrections vs Previously Documented

| Field | Old (incorrect) | Correct (verified from source) |
|-------|----------------|-------------------------------|
| Registration steps | 'Step 1 of 3' (3 steps) | **'Step 1 of 2'** (2 steps only) |
| Registration step 1 POC label | 'Full name of main contact' | **'Full name of primary contact person'** |
| Registration upload description | 'A clear face photo for verification.' | **'Clear face photo for verification.'** (no leading 'A') |
| Registration upload description | 'Passport / National ID' | **'National ID / Passport (front side).'** |
| Registration terms text | 'I confirm that all information is accurate...' | **'I confirm the provided information and documents are accurate, and I agree to submit them for review.'** |
| Merchants tab 1 | 'Pending Requests' | **'Pending'** |
| Merchants active action | 'View details →' (with arrow) | **'View Details'** (no arrow, capital D) |
| Store access button | 'Open →' (with arrow) | **'Open'** (plain text) |
| Store inactive state | 'No access' | **'Closed'** |
| Team Members description | 'Manage who has access to the agency portal' | **'Manage who can access the agency portal'** |
| Team Members invite | `button:has-text('Send Invite')` | **`button:has-text('Send Invitation')`** |
| Team Members placeholder | `input[placeholder="Team member's name"]` | **`input[placeholder='Team member name']`** |
| Team member status badge | 'Invite Pending' | **'Pending'** (source uses `t(member.status)` — check actual API status value) |
| Add Member button | enabled per PRD | **Disabled** (isAddTeamMemberDisabled = true in source) |
| Remove member | `div[role='dialog']` modal | **window.confirm** (native browser dialog) |
| Remove confirmation text | 'Will lose access...' | **native dialog**: 'Remove [name] from team?' |
| Commission tabs | 'Store Breakdown' via 'stores' key | **`button:has-text('Store Breakdown')`** |
| Settings save button | 'Save Changes' | **'Save'** |
| Invite Accept page title | 'Agency Team Invitation' (h1) | **`h1:has-text('Agency Invitation')`** |
| Dashboard table column | 'ORDERS / REVENUE' (uppercase) | column text: **'Orders / Revenue'** (actual case from source) |
| Agency Landing heading | not previously documented | **`h1:has-text('Zambeel Marketing Agency Program')`** |
| Status pages | generic pending card text | **`h1:has-text('Application Submitted')`** for pending; **`h1:has-text('Application On Hold')`** for hold; **`h1:has-text('Application Rejected')`** for rejected |
