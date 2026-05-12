# Agency Portal — Test Patterns

> Source: Zambeel Agency Model PRD (Zambeel-Agency.pdf) + zambeel-fe source code.

## Pattern 1: Agency Dashboard Load (Approved)

```python
NAVIGATE /agency/portal/dashboard
ASSERT_TEXT Agency Dashboard
ASSERT_TEXT Performance across all your merchants
ASSERT_TEXT Active Merchants
ASSERT_TEXT Total Stores
ASSERT_TEXT Delivered Orders
ASSERT_TEXT Commission Earned
ASSERT_TEXT Commission Due
ASSERT_VISIBLE input[placeholder='Search merchants or stores...']
```

## Pattern 2: Dashboard Time Filter

```python
NAVIGATE /agency/portal/dashboard
# Time filter buttons — exact labels per PRD
CLICK button:has-text('7 Days')
CLICK button:has-text('30 Days')
CLICK button:has-text('All Time')
# Refresh
CLICK button[title='Refresh']
```

## Pattern 3: Commission Hub — Invoices Tab

```python
NAVIGATE /agency/portal/commission
ASSERT_TEXT Commission & Invoices
ASSERT_TEXT Track earnings and view invoices from Zambeel
ASSERT_TEXT Total Earned
ASSERT_TEXT Total Paid
ASSERT_TEXT Commission Due
CLICK button:has-text('Invoices')
# Empty state text (when no invoices)
# text='No invoices yet'   ⚠️ NOT 'No invoices available'
```

## Pattern 4: Commission Hub — Store Breakdown Tab

```python
NAVIGATE /agency/portal/commission
CLICK button:has-text('Store Breakdown')
# Empty state text (when no records)
# text='No commission records yet'   ⚠️ NOT 'No commission records available'
```

## Pattern 5: Team Members Page — Add Member (Functional)

```python
NAVIGATE /agency/portal/team-members
ASSERT_TEXT Team Members
ASSERT_TEXT Manage who has access to the agency portal
# Add Member is functional per PRD
CLICK button:has-text('Add Member')
ASSERT_VISIBLE div[role='dialog']
ASSERT_TEXT Add Team Member
FILL input[placeholder="Team member's name"] | Jane Smith
FILL input[placeholder='email@example.com'] | jane@example.com
CLICK button:has-text('Send Invite')
ASSERT_TEXT Invite sent successfully
```

## Pattern 6: Team Members — Remove Member

```python
NAVIGATE /agency/portal/team-members
# Click trash icon for a member
CLICK button[title='Remove']
# Confirmation modal opens (NOT window.confirm)
ASSERT_VISIBLE div[role='dialog']
ASSERT_TEXT Will lose access to the agency portal. This cannot be undone.
CLICK button:has-text('Remove')
ASSERT_TEXT Member removed
```

## Pattern 7: Merchants — Tab Navigation and Accept Request

```python
NAVIGATE /agency/portal/merchants
ASSERT_TEXT Merchants
ASSERT_TEXT Manage your merchant connections
ASSERT_VISIBLE button:has-text('Pending Requests')
ASSERT_VISIBLE button:has-text('Active')
ASSERT_VISIBLE button:has-text('Inactive')
# Accept a pending request
CLICK button:has-text('Pending Requests')
CLICK button:has-text('Accept')
ASSERT_TEXT Request accepted
CLICK button:has-text('Active')
```

## Pattern 8: Merchant Detail Drawer — Open and View

```python
NAVIGATE /agency/portal/merchants
CLICK button:has-text('Active')
CLICK button:has-text('View details →')
ASSERT_VISIBLE div[role='dialog']
ASSERT_TEXT STORES
ASSERT_TEXT Commission Summary
ASSERT_TEXT Total Earned
ASSERT_TEXT Total Paid
ASSERT_TEXT Commission Due
```

## Pattern 9: Agency Settings — Copy ID

```python
NAVIGATE /agency/portal/settings
ASSERT_TEXT Agency Settings
ASSERT_TEXT Manage your agency profile
ASSERT_TEXT Agency ID
ASSERT_TEXT Share this ID with merchants
CLICK button:has-text('Copy')
ASSERT_TEXT Copied
# After ~2 seconds button reverts to 'Copy'
```

## Pattern 10: Agency Settings — Update Profile

```python
NAVIGATE /agency/portal/settings
# Form fields present
ASSERT_VISIBLE input[name='name']
ASSERT_VISIBLE input[name='city']
ASSERT_VISIBLE input[name='phone']
ASSERT_VISIBLE input[name='poc_name']
# Country NOT editable — only shown in meta text
ASSERT_TEXT Country:
# Save disabled initially (form not dirty)
ASSERT_DISABLED button:has-text('Save')
FILL input[name='city'] | Dubai
ASSERT_ENABLED button:has-text('Save')
CLICK button:has-text('Save')
ASSERT_TEXT Agency settings updated
```

## Pattern 11: Registration — Full 3-Step Flow

```python
# Prerequisites: user has no agency registration
NAVIGATE /agency
# Landing page shown
ASSERT_TEXT Apply Now
CLICK button:has-text('Apply Now')
ASSERT_VISIBLE div[role='dialog']
ASSERT_TEXT Apply to Become an Agency
ASSERT_TEXT Step 1 of 3

# Step 1 — Details
FILL input[placeholder='Enter your agency name'] | Test Agency LLC
CLICK_OPTION select | United Arab Emirates
FILL input[placeholder='+971 50 000 0000'] | +971501234567
FILL input[placeholder='Full name of main contact'] | John Doe
CLICK button:has-text('Continue')
ASSERT_TEXT Step 2 of 3

# Step 2 — Documents
ASSERT_TEXT POC Photo
ASSERT_TEXT Identity Proof
# Upload files (handled by file input interaction)
CLICK button:has-text('Continue')
ASSERT_TEXT Step 3 of 3

# Step 3 — Terms
CLICK input[type='checkbox']
CLICK button:has-text('Submit')
ASSERT_TEXT Application submitted!
# Modal closes; page shows Pending status card
ASSERT_TEXT Application Under Review
```

## Pattern 12: Registration — Step 1 Validation (Empty Fields)

```python
NAVIGATE /agency
CLICK button:has-text('Apply Now')
ASSERT_VISIBLE div[role='dialog']
# Try to proceed without filling fields
CLICK button:has-text('Continue')
# Should still be on Step 1 (validation blocked)
ASSERT_TEXT Step 1 of 3
ASSERT_VISIBLE input[placeholder='Enter your agency name']
```

## Pattern 13: Merchant Connect to Agency (Seller Side)

```python
# On seller profile page — AgencyConnectionSection
# Not Connected state
ASSERT_VISIBLE input[placeholder='ZMB-AG-XXXXXX']

# Test invalid format
FILL input[placeholder='ZMB-AG-XXXXXX'] | INVALID-123
# Inline error should appear
ASSERT_TEXT Please enter a valid Agency ID (format: ZMB-AG-XXXXXX).

# Submit valid ID
FILL input[placeholder='ZMB-AG-XXXXXX'] | ZMB-AG-ABC123
# Submits → Pending state
ASSERT_TEXT Request Sent
ASSERT_VISIBLE button:has-text('Cancel')
```

## Pattern 14: Team Invite Accept (`/agency/invite?token=XXX`)

```python
NAVIGATE /agency/invite?token=TESTTOKEN123
ASSERT_VISIBLE div[role='dialog']
ASSERT_TEXT Agency Team Invitation
ASSERT_TEXT You have been invited by
CLICK button:has-text('Accept')
ASSERT_TEXT Invitation accepted.
```

---

## Selector Quick Reference (Agency — Updated from PRD)

| Element | Selector | Notes |
|---------|----------|-------|
| Agency tab | `button:has-text('Agency')` | |
| Landing page CTA | `button:has-text('Apply Now')` | ⚠️ NOT 'Register as Agency' |
| Open Agency Portal | `button:has-text('Open Agency Portal')` | Approved status card |
| Dashboard (approved nav) | `a:has-text('Dashboard')` → `/agency/portal/dashboard` | |
| Agency dashboard title | `h1:has-text('Agency Dashboard')` | |
| Time filter — 7 days | `button:has-text('7 Days')` | ⚠️ NOT '7d' |
| Time filter — 30 days | `button:has-text('30 Days')` | ⚠️ NOT '30d' |
| Time filter — all time | `button:has-text('All Time')` | ⚠️ NOT 'all' |
| Commission hub title | `h1:has-text('Commission & Invoices')` | |
| Invoices empty state | `text='No invoices yet'` | ⚠️ NOT 'No invoices available' |
| Commission empty state | `text='No commission records yet'` | ⚠️ NOT 'No commission records available' |
| Team members title | `h1:has-text('Team Members')` | |
| Add member | `button:has-text('Add Member')` | Functional per PRD |
| Remove member confirm | `text='Will lose access to the agency portal. This cannot be undone.'` | In modal, not window.confirm |
| Merchants title | `h1:has-text('Merchants')` | |
| Accept merchant | `button:has-text('Accept')` | ⚠️ May NOT have '✓' prefix |
| Reject merchant | `button:has-text('Reject')` | ⚠️ May NOT have '✕' prefix |
| View merchant details | `button:has-text('View details →')` | |
| Store open (proxy) | `button:has-text('Open →')` | Active stores in drawer |
| Inactive store | `text='No access'` | ⚠️ NOT 'Locked' |
| Disconnect merchant | `button:has-text('Disconnect Merchant')` | |
| Settings title | `h1:has-text('Agency Settings')` | |
| Agency ID copy | `button:has-text('Copy')` | |
| Save settings | `button:has-text('Save')` | |
| Agency ID input (seller) | `input[placeholder='ZMB-AG-XXXXXX']` | On seller Profile page |
| Agency ID format error | `text='Please enter a valid Agency ID (format: ZMB-AG-XXXXXX).'` | Inline validation |
| Cancel pending request | `button:has-text('Cancel')` | Seller pending state |
| Disconnect (seller) | `button:has-text('Disconnect')` | Seller active state |
| Registration step 1 | `text='Step 1 of 3'` | ⚠️ 3-step wizard, not 2-step |
| Registration step 2 | `text='Step 2 of 3'` | |
| Registration step 3 | `text='Step 3 of 3'` | |
| Context banner | `text='·'` | "Agency · Merchant · Store" format |

## Error/Toast Messages Reference (PRD-Verified)

| Message | Trigger |
|---------|---------|
| "Application submitted! We'll review within 3–5 business days. In the meantime, our team might call you on your provided number." | Registration submit |
| "Request accepted" | Merchant accept |
| "Request rejected" | Merchant reject |
| "Merchant disconnected" | Disconnect action |
| "Invitation accepted." | Team invite accept |
| "Invitation declined." | Team invite decline |
| "Invite sent successfully" | Team invite with email |
| "Invite sent" | Team invite (short form) |
| "Member removed" | Remove team member |
| "Agency settings updated" | Save settings form |
| "Please login again to download invoice" | No auth token for invoice download |
| "Failed to download invoice PDF" | Invoice download API error |
| "Please enter a valid Agency ID (format: ZMB-AG-XXXXXX)." | Invalid Agency ID format on merchant connect |
