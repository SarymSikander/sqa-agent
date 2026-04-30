# Agency Portal — Pages Reference

## Route Map

| Route | Component | Guard | Purpose |
|-------|-----------|-------|---------|
| `/agency` | `AgencyPage` (router) | SellerProtected | Routing hub — shows correct state component |
| `/agency/application-submitted` | `ApplicationSubmittedPage` | SellerProtected | Confirmation after registration submission |
| `/agency/portal/commission` | `AgencyCommissionHub` | SellerProtected + ApprovedAgency | Commission overview and invoices |
| `/agency/portal/team-members` | `AgencyTeamMembers` | SellerProtected + ApprovedAgency | Manage agency team |
| `/agency/portal/merchants` | `AgencyMerchants` | SellerProtected + ApprovedAgency | Manage connected merchants |
| `/agency/portal/settings` | `AgencySettingsPage` | SellerProtected + ApprovedAgency | Agency profile settings |
| `/agency/invite` | `AgencyInviteAccept` | Public | Accept team invitation (token-based) |

---

## `/agency` — Routing Hub

This page checks `registration_status` and renders the correct sub-component:

| Status Value | Component Shown |
|-------------|-----------------|
| `"Pending"` | `AgencyApplicationPending` |
| `"OnHold"` | `AgencyApplicationOnHold` |
| `"Rejected"` | `AgencyApplicationRejected` |
| `"Approved"` | `AgencyDashboard` |
| null/none | `AgencyLanding` (start registration) |

### Pending Invite Modal (if `pendingAgencyInvite` in localStorage)
- **Modal Title:** "Agency Team Invitation"
- **Body:** "You have been invited by [agencyName] to join their agency team."
- **Info (already accepted):** "You already accepted this invitation."
- **Buttons:** `Decline` (gray) | `Accept` (blue)
- **Toast on decline:** "Invitation declined."
- **Toast on accept:** "Invitation accepted."

---

## `/agency` — AgencyDashboard (Approved state)

**Page Title:** "Agency Dashboard"
**Subtitle:** "Performance across all your merchants"

### Summary Cards (5 cards)
| Card | Border Color |
|------|-------------|
| Active Merchants | violet-500 |
| Total Stores | purple-500 |
| Delivered Orders | emerald-500 |
| Commission Earned | blue-500 |
| Commission Due | orange-500 |

### Range Filter Options
From `AGENCY_REPORT_RANGE_OPTIONS` — includes: `7d` | `30d` | `all` | custom date range
- **Refresh button:** RefreshCcw icon

### Merchants & Stores Table
- **Section title:** "Merchants & Stores" + "{count} merchants" badge
- **Search input placeholder:** "Search merchants or stores..."
- **Columns:** Merchant | Store URL | Orders / Revenue | Commission | Invoice

### Row Interactions
- Click merchant row → expand/collapse stores
- Store row: name, URL (external link), orders/revenue, commission, invoice (View link or "—")

### Empty/Loading States
- "No merchants found"
- "Loading dashboard..."

---

## `/agency/portal/commission` — Commission Hub

**Page Title:** "Commission & Invoices"
**Subtitle:** "Track earnings and view invoices from Zambeel"

### Summary Cards
| Card | Color |
|------|-------|
| Total Earned | emerald-700 |
| Total Paid | blue-700 |
| Commission Due | amber-700 |

### Tabs
| Tab | Icon | Key |
|-----|------|-----|
| Invoices | FileText | `"invoices"` |
| Store Breakdown | DollarSign | `"stores"` |

### Invoices Table Columns
- Period | Amount | Status | Date | (download PDF button)

### Invoice Status Display
- `"Paid"` → green badge "Paid"
- anything else → amber badge "Unpaid"

### Store Breakdown Table Columns
- Store | Merchant | Type | Revenue | Commission | Date

### Commission Type Display
- `percentage_of_delivered_revenue` → "% Revenue"
- any other → "Flat / Order"

### Empty States
- "No invoices available"
- "No commission records available"

### Error Messages
- `e?.response?.data?.message || e?.message || "Failed to load commission data"`
- `toast.error("Please login again to download invoice")`
- `toast.error("Failed to download invoice PDF")`

---

## `/agency/portal/team-members` — Team Members

**Page Title:** "Team Members"
**Subtitle:** "Manage who has access to the agency portal"

### Invite Member Button
- **Button:** `Add Member` (⚠️ DISABLED — `isAddTeamMemberDisabled = true`, title="Temporarily disabled")

### Invite Modal Title
- "Add Team Member"

### Form Fields
| Label | Type | Placeholder |
|-------|------|-------------|
| Full Name* | text | "Team member's name" |
| Email Address* | text | "email@example.com" |

### Modal Buttons
- `Cancel` | `Send Invite` / `Sending...`

### Role Display
- `Owner` role → displayed as `"Admin"`
- Other roles → shown as-is

### Toast Messages
- "Invite sent successfully" (emailSent=true)
- "Email not sent; invite link copied to clipboard" (link exists, no email)
- "Invite created, but email sending failed" (no link)
- "Member removed"
- Error: `e?.response?.data?.message || e?.message || "Failed to send invite"` / "Failed to remove member"

### Confirmation Dialog
- `window.confirm("Remove {memberName} from team?")`

### Empty/Loading States
- "Loading team members..."
- "No team members yet"

### Remove Button
- Trash2 icon button — title="Remove"

---

## `/agency/portal/merchants` — Merchants

**Page Title:** "Merchants"
**Subtitle:** "Manage your merchant connections"

### Tabs
| Tab Label | Status Value |
|-----------|-------------|
| "Pending Requests" | `"Pending"` |
| "Active" | `"Active"` |
| "Inactive" | `"Inactive"` |

### Merchant Card Actions (by tab)
- **Pending tab:** `✓ Accept` (emerald) | `✕ Reject` (rose)
- **Active/Inactive tab:** `View details →` (blue)

### Merchant Drawer Sections
- Merchant name + email (header)
- Status pill + "Connected since {date}"
- **"STORES"** section (uppercase, tracking-wide label)
  - Per store: name, `(country) storeUrl`, `Open →` button (active) or `Locked` badge (inactive)
- **"Commission Summary"** section
  - Total Earned | Total Paid (shows "—") | Commission Due
- **For Active merchants:** `Disconnect Merchant` button (rose)

### Toast Messages
- "Request accepted" | "Request rejected"
- "Merchant disconnected"
- Errors: `e?.message || "Failed to update request"` / "Failed to disconnect merchant"

### Empty States
- "No merchants found"
- "No stores available"
- "Loading merchants..."

### Navigation from Drawer
- `Open →` → `enterAgencyView(...)` then navigate to `/orders`

---

## `/agency/portal/settings` — Agency Settings

**Page Title:** "Agency Settings"
**Subtitle:** "Manage your agency profile"

### Agency ID Card
- Label: "Agency ID"
- Sub-text: "Share this ID with merchants to connect to your agency."
- Button: `Copy` / `Copied` (1500ms toggle)

### Agency Profile Form
- **Section Title:** "Agency Profile"
- **Meta text:** "Country: {country} • Member since: {date}"
- **Save button:** `Save` (disabled until form `isDirty`)

### Form Fields
| Label | Field Name |
|-------|-----------|
| Agency Name | `name` |
| City | `city` |
| Phone Number | `phone` |
| Point of Contact | `poc_name` |

Note: `Country` is **NOT editable** in this form (read-only, shown in meta text).

### Footer
- "Need to transfer ownership? Contact ilqa@myzambeel.com."

### Toast Messages
- "Agency settings updated" (success)
- `toast.error(e?.message || "Failed to update agency settings")`

---

## Agency Registration Flow (via AgencyRegistrationModal)

**Modal Title:** "Apply to Become an Agency"
**Step indicator:** "Step {N} of 2 - {stepLabel}"
**Progress bar:** 2 segments — active = emerald-600, inactive = gray-200

### Step 1 — Details (`RegistrationStepDetails`)
| Field | Required | Type | Placeholder |
|-------|----------|------|-------------|
| Agency Name | * | text | "Enter your agency name" |
| Country | * | select | COUNTRIES list |
| City | * | dropdown/text | "Select city" or "Type city" |
| Phone Number | * | text | "+971 50 000 0000" |
| Point of Contact Name | * | text | "Full name of main contact" |

Countries shown: Kuwait | Qatar | Saudi Arabia | UAE (shown as "UAE") | Pakistan | Oman | Bahrain | Iraq

City behavior:
- If country has cities API: `SearchableDropdown` with placeholder "Select city"
- Otherwise: text input, placeholder "Type city" or "Select country first" (disabled)

### Step 2 — Uploads (`RegistrationStepUploads`)
| Upload Card | Required | Description | Accept |
|-------------|----------|-------------|--------|
| Point of Contact Photo | * | "A clear face photo for verification." | image/* |
| Identity Proof | * | "National ID / Passport (front side)." | image/* |

**Terms Checkbox:** "I agree that the information and documents provided are accurate and I consent to upload documents for review."

### Modal Buttons
- **Step 1:** `Continue` (success) | `Cancel` (gray)
- **Step 2:** `Submit` / `Submitting...` (success) | `Cancel` (gray)
