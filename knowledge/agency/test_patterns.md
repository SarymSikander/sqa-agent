# Agency Portal — Test Patterns

## Pattern 1: Agency Dashboard Load (Approved)

```python
# Login as approved agency user
NAVIGATE /agency
ASSERT_TEXT Agency Dashboard
ASSERT_TEXT Performance across all your merchants
ASSERT_TEXT Active Merchants
ASSERT_TEXT Total Stores
ASSERT_TEXT Delivered Orders
ASSERT_TEXT Commission Earned
ASSERT_TEXT Commission Due
ASSERT_VISIBLE input[placeholder='Search merchants or stores...']
```

## Pattern 2: Commission Hub — Invoices Tab

```python
NAVIGATE /agency/portal/commission
ASSERT_TEXT Commission & Invoices
ASSERT_TEXT Track earnings and view invoices from Zambeel
ASSERT_TEXT Total Earned
ASSERT_TEXT Total Paid
ASSERT_TEXT Commission Due
CLICK button:has-text('Invoices')
# Invoice tab loads
ASSERT_VISIBLE text='Invoices'
# Check empty or populated state
```

## Pattern 3: Commission Hub — Store Breakdown Tab

```python
NAVIGATE /agency/portal/commission
CLICK button:has-text('Store Breakdown')
# Table may be empty or populated
# Verify column headers present
text='Store'
text='Merchant'
text='Type'
text='Revenue'
text='Commission'
```

## Pattern 4: Team Members Page

```python
NAVIGATE /agency/portal/team-members
ASSERT_TEXT Team Members
ASSERT_TEXT Manage who has access to the agency portal
# Add Member button is disabled
ASSERT_DISABLED button:has-text('Add Member')
# or: ASSERT_ATTRIBUTE button:has-text('Add Member') | title | Temporarily disabled
```

## Pattern 5: Merchants — Tab Navigation

```python
NAVIGATE /agency/portal/merchants
ASSERT_TEXT Merchants
ASSERT_TEXT Manage your merchant connections
ASSERT_VISIBLE button:has-text('Pending Requests')
ASSERT_VISIBLE button:has-text('Active')
ASSERT_VISIBLE button:has-text('Inactive')
CLICK button:has-text('Active')
CLICK button:has-text('Inactive')
CLICK button:has-text('Pending Requests')
```

## Pattern 6: Agency Settings — Copy ID

```python
NAVIGATE /agency/portal/settings
ASSERT_TEXT Agency Settings
ASSERT_TEXT Manage your agency profile
ASSERT_TEXT Agency ID
ASSERT_TEXT Share this ID with merchants to connect to your agency.
CLICK button:has-text('Copy')
ASSERT_TEXT Copied
# After 1500ms button reverts to 'Copy'
```

## Pattern 7: Agency Settings — Update Profile

```python
NAVIGATE /agency/portal/settings
# Form fields present
ASSERT_VISIBLE input[name='name']    # or by label Agency Name
ASSERT_VISIBLE input[name='city']
ASSERT_VISIBLE input[name='phone']
ASSERT_VISIBLE input[name='poc_name']
# Country NOT editable — only shown in meta text
ASSERT_TEXT Country:
# Save disabled initially (form not dirty)
ASSERT_DISABLED button:has-text('Save')
# Make a change
FILL input[name='city'] | Dubai
ASSERT_ENABLED button:has-text('Save')
CLICK button:has-text('Save')
ASSERT_TEXT Agency settings updated
```

## Pattern 8: Registration — Step 1 Validation

```python
# Open registration modal
# Try to continue without filling fields
CLICK button:has-text('Continue')
# Validation prevents proceeding
ASSERT_VISIBLE input[placeholder='Enter your agency name']   # still on step 1
# Fill required fields
FILL input[placeholder='Enter your agency name'] | Test Agency
# Select country
CLICK_OPTION select | United Arab Emirates
# City populates (dropdown or text)
FILL input[placeholder='+971 50 000 0000'] | +971501234567
FILL input[placeholder='Full name of main contact'] | John Doe
CLICK button:has-text('Continue')
# Moves to Step 2
ASSERT_TEXT Step 2 of 2
```

## Pattern 9: Registration — Step 2 with Terms

```python
# On step 2
ASSERT_TEXT Point of Contact Photo
ASSERT_TEXT Identity Proof
ASSERT_TEXT A clear face photo for verification.
ASSERT_TEXT National ID / Passport (front side).
# Terms checkbox must be checked to submit
ASSERT_DISABLED button:has-text('Submit')
CLICK input[type='checkbox']
# Without file uploads, still may be disabled
# Upload files then submit
```

## Pattern 10: Merchant Accept (Pending Request)

```python
NAVIGATE /agency/portal/merchants
CLICK button:has-text('Pending Requests')
# If there are pending requests
CLICK button:has-text('✓ Accept')
ASSERT_TEXT Request accepted
# Merchant moves to Active tab
CLICK button:has-text('Active')
ASSERT_TEXT Active
```

## Pattern 11: Range Filter on Dashboard

```python
NAVIGATE /agency
# Approved agency
CLICK button:has-text('7d')
# Data reloads for 7-day range
CLICK button:has-text('30d')
# Data reloads for 30-day range
CLICK button:has-text('all')
# Data reloads for all time
```

## Selector Quick Reference (Agency)

| Element | Selector |
|---------|----------|
| Agency tab | `button:has-text('Agency')` |
| Agency dashboard title | `h1:has-text('Agency Dashboard')` |
| Commission hub title | `h1:has-text('Commission & Invoices')` |
| Team members title | `h1:has-text('Team Members')` |
| Merchants title | `h1:has-text('Merchants')` |
| Settings title | `h1:has-text('Agency Settings')` |
| Agency ID copy | `button:has-text('Copy')` |
| Save settings | `button:has-text('Save')` |
| Pending requests tab | `button:has-text('Pending Requests')` |
| Accept merchant | `button:has-text('✓ Accept')` |
| Reject merchant | `button:has-text('✕ Reject')` |
| View merchant details | `button:has-text('View details →')` |
| Disconnect merchant | `button:has-text('Disconnect Merchant')` |
| Invoices tab | `button:has-text('Invoices')` |
| Store breakdown tab | `button:has-text('Store Breakdown')` |
| Add member | `button:has-text('Add Member')` |
| Remove member | `button[title='Remove']` |
| Merchant search | `input[placeholder='Search merchants or stores...']` |

## Error/Toast Messages Reference

| Message | Trigger |
|---------|---------|
| "Request accepted" | Merchant accept |
| "Request rejected" | Merchant reject |
| "Merchant disconnected" | Disconnect action |
| "Invitation accepted." | Team invite accept |
| "Invitation declined." | Team invite decline |
| "Invite sent successfully" | Team invite with email |
| "Member removed" | Remove team member |
| "Agency settings updated" | Save settings form |
| "Failed to load commission data" | API error on commission page |
| "Please login again to download invoice" | No auth token for invoice download |
| "Failed to download invoice PDF" | Invoice download API error |
| "Failed to load dashboard" | Dashboard API error |
