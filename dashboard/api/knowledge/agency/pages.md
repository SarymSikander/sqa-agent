# Agency Portal — Pages Reference

> Source: Zambeel Agency Model PRD (Zambeel-Agency.pdf) + zambeel-fe source code.

## Route Map

| Route | Component | Guard | Purpose |
|-------|-----------|-------|---------|
| `/agency` | `AgencyPage` (router) | SellerProtected | Routing hub — shows landing or status card |
| `/agency/portal/dashboard` | `AgencyDashboard` | SellerProtected + ApprovedAgency | Agency dashboard with merchants + KPIs |
| `/agency/portal/commission` | `AgencyCommissionHub` | SellerProtected + ApprovedAgency | Commission overview and invoices |
| `/agency/portal/team-members` | `AgencyTeamMembers` | SellerProtected + ApprovedAgency | Manage agency team |
| `/agency/portal/merchants` | `AgencyMerchants` | SellerProtected + ApprovedAgency | Manage connected merchants |
| `/agency/portal/settings` | `AgencySettingsPage` | SellerProtected + ApprovedAgency | Agency profile settings |
| `/agency/invite` | `AgencyInviteAccept` | Public | Accept team invitation (token-based) |

---

## `/agency` — Routing Hub

Checks `registration_status` + `license_status` and renders:

| Condition | Component Shown |
|-----------|----------------|
| `license_status = 'Revoked'` (overrides all) | Revoked card |
| `registration_status = 'Pending'` | `AgencyApplicationPending` |
| `registration_status = 'OnHold'` | `AgencyApplicationOnHold` |
| `registration_status = 'Rejected'` | `AgencyApplicationRejected` |
| `registration_status = 'Approved'` | (redirects to `/agency/portal/dashboard`) |
| null/none | `AgencyLanding` (program landing page) |

### Pending Invite Modal (if `pendingAgencyInvite` in localStorage)
- **Modal Title:** "Agency Team Invitation"
- **Body:** "You have been invited by [agencyName] to join their agency team."
- **Info (already accepted):** "You already accepted this invitation."
- **Buttons:** `Decline` (gray) | `Accept` (blue)
- **Toast on decline:** "Invitation declined."
- **Toast on accept:** "Invitation accepted."

---

## `/agency` — AgencyLanding (No Registration)

**Purpose:** Agency Program promotional page to recruit new agency applicants.

### Sections (in order)
1. **Hero section** — headline + "Apply Now" CTA button
2. **3 feature cards** — "Manage Merchants" | "Unified Dashboard" | "Earn Commission"
3. **"How It Works"** — 4 numbered steps: Apply → Review → Approve → Start Earning
4. **Commission Estimation Slider** — interactive slider showing estimated monthly earnings based on merchant count/volume
5. **FAQ accordion** — collapsible FAQ questions and answers

**CTA button text:** `Apply Now` (purple) — opens `AgencyRegistrationModal`

---

## `/agency` — Status Cards (Post-Application)

### Pending Card
- Animated pulsing clock icon
- Text: "Application Under Review"
- Shows: agency name + submission date

### Approved Card
- Green checkmark icon
- Text: "Approved!"
- Shows: Agency ID with `Copy` button
- **Action button:** `Open Agency Portal` → navigates to `/agency/portal/dashboard`

### OnHold Card
- Amber alert icon
- Shows: `hold_reason` text from admin
- If `allow_resubmit = true`: shows resubmit CTA (URL fields only, no new document upload)

### Rejected Card
- Red X icon
- Shows: `reject_reason`, `cooloff_days_remaining`
- Shows: contact support link
- After cooloff expires (cooloff_days_remaining = 0): reapply CTA appears

### Revoked Card
- Red X icon
- Text: "Agency Access Revoked"
- Shows: contact support link
> ⚠️ Shown even if registration_status = Approved — license_status = Revoked always wins.

---

## Agency Registration Flow (via AgencyRegistrationModal)

**Triggered by:** "Apply Now" CTA on the landing page
**Modal Title:** "Apply to Become an Agency"
**Step indicator:** "Step {N} of 3"
**Progress bar:** 3 segments — active = emerald-600, inactive = gray-200

### Step 1 — Agency Details (`RegistrationStepDetails`)
| Field | Required | Type | Notes |
|-------|----------|------|-------|
| Agency Name | * | text | placeholder: "Enter your agency name" |
| Country | * | select | UAE, Saudi Arabia, Pakistan, Kuwait, Bahrain, Oman, Jordan, Egypt, Iraq |
| City | * | dropdown or text | "Select city" (if cities API) or "Type city" (otherwise) |
| Phone Number | * | text | placeholder: "+971 50 000 0000" |
| Point of Contact Name | * | text | placeholder: "Full name of main contact" |

- Validation: empty fields show red inline errors on "Continue"
- Only proceeds to Step 2 if all fields pass

API on Continue: `POST /api/agency/register` (or `/agency/register` in source)

### Step 2 — Document Upload (`RegistrationStepUploads`)
| Upload Zone | Required | Accept | Max Size | Notes |
|-------------|----------|--------|---------|-------|
| POC Photo | * | JPG, PNG, WebP | 5 MB | "A clear face photo for verification." |
| Identity Proof | * | JPG, PNG, WebP, PDF | 10 MB | "Passport / National ID (required)" |

- Drag-and-drop supported
- Zones turn red if user tries to proceed without uploading
- After upload: shows thumbnail (images) or file icon (PDF), filename, file size, trash icon to remove
- "Continue" validates both uploads are present

### Step 3 — Terms (`RegistrationStepTerms`)
- Upload summary shown for files uploaded in Step 2
- **Terms checkbox:** "I confirm that all information is accurate and I agree to Zambeel's Agency Terms." (required to submit)
- **Submit button:** `Submit` / `Submitting...`
- API on Submit: `POST /api/agency/register/complete` — files uploaded to S3 signed URLs

### Post-Submit
- **Success toast:** "Application submitted! We'll review within 3–5 business days. In the meantime, our team might call you on your provided number."
- Modal closes; page re-renders to show the Pending status card.
- Registration status set to `Pending`

### Modal Buttons
- **Steps 1 & 2:** `Continue` (success) | `Cancel` (gray)
- **Step 3:** `Submit` / `Submitting...` | `Cancel` (gray)

---

## `/agency/portal/dashboard` — Agency Dashboard

**Page Title:** "Agency Dashboard"
**Subtitle:** "Performance across all your merchants"

### Time Filter (global — applies to all cards + table)
| Button Label | Period |
|-------------|--------|
| `7 Days` | Last 7 days |
| `30 Days` | Last 30 days |
| `All Time` | All history |
Custom date range also available.
- **Refresh button:** RefreshCcw icon — manually re-fetches data

### Summary Cards (5 cards, top row)
| Card | Value | Icon Color | Highlight |
|------|-------|-----------|-----------|
| Active Merchants | Count of active connections | Purple | — |
| Total Stores | Count of unique stores across active merchants | Teal | — |
| Delivered Orders | Sum of delivered orders in period | Green | — |
| Commission Earned | Multi-currency map (currency badge pills) | Blue | — |
| Commission Due | If > 0, highlighted in amber | Orange | amber bg if > 0 |

**Currency badge pills:** AED=blue | SAR=amber | PKR=green | USD=gray

### Merchants & Stores Table
- **Section title:** "Merchants & Stores" + `{count} merchants` badge
- **Search input placeholder:** "Search merchants or stores..." (case-insensitive, real-time)
  - Also matches store sub-rows; parent merchant row is shown if store matches

**Grouped by Merchant** — each merchant is a header row:
- Expand/collapse chevron
- Merchant avatar (initials-based)
- Merchant name + email below
- Inline store count badge (e.g. "3")
- Aggregated Delivered ORDERS / Delivered REVENUE (sum of all stores in period)
- Commission earned across all stores (currency pills)
- Empty cell for Invoice (no invoice at merchant level)

**Expanded store sub-rows** (per store):
- Indented store name + country flag + country name
- Store URL (clickable link, opens in new tab)
- Store-level Delivered ORDERS / Delivered REVENUE (currency pills)
- Store-level Commission (currency pills)
- Last invoice date + "View" link to PDF

### Table Columns (5 sortable)
| Column | Sortable | Content |
|--------|----------|---------|
| MERCHANT | Yes (by name) | Merchant name / store name (indented) |
| STORE URL | No | Store URL link |
| ORDERS / REVENUE | Yes (by delivered orders) | Count + revenue pills |
| COMMISSION | Yes (by primary currency) | Commission pills |
| INVOICE | No | Last invoice date + View link |

Active sort column highlighted in indigo; sort icon changes direction.

### Empty/Loading States
- "No merchants found"
- "Loading dashboard..."

API: `GET /api/agency/dashboard?date_from=...&date_to=...`

---

## `/agency/portal/commission` — Commission Hub

**Page Title:** "Commission & Invoices"
**Subtitle:** "Track earnings and view invoices from Zambeel"

### Summary Cards
| Card | Color |
|------|-------|
| Total Earned | Green (emerald-700) |
| Total Paid | Blue (blue-700) |
| Commission Due | Orange (amber-700) |

### Tabs
| Tab | Icon | Key |
|-----|------|-----|
| Invoices | FileText | `"invoices"` |
| Store Breakdown | DollarSign | `"stores"` |

### Invoices Tab
**Table columns:** Period (from–to dates) | Amount | Status | Payment Date | (PDF Download)

**Status badges:**
- `"Paid"` → green badge "Paid"
- anything else → orange badge "Unpaid"

**Empty state:** "No invoices yet" (with file icon)

### Store Breakdown Tab
**Filter:** 7 days / 30 days / custom date range (top of tab)

**Table columns:** Store | Merchant | Commission Type (badge) | Delivered Revenue | Delivered Orders | Commission

**Commission type badges:**
- `percentage_of_delivered_revenue` → "% Revenue"
- `flat_per_delivered_order` → "Flat / Order"

Commission amounts highlighted in green.

**Empty state:** "No commission records yet."

### Error Messages
- `toast.error("Please login again to download invoice")`
- `toast.error("Failed to download invoice PDF")`

---

## `/agency/portal/team-members` — Team Members

**Page Title:** "Team Members"
**Subtitle:** "Manage who has access to the agency portal"

### Add Member
- **Button:** `Add Member` (top right)
- **Modal Title:** "Add Team Member"
- **Fields:** Full Name* (placeholder: "Team member's name") | Email Address* (placeholder: "email@example.com")
- Email validated for valid format before submission
- **Modal Buttons:** `Cancel` | `Send Invite` / `Sending...`
- **On success:** "Invite sent" toast; member appears with "Invite Pending" badge

### Team Member List
Each row: avatar (gradient), name, email, status badge (Active / Invite Pending)
- Remove button (trash icon) per row

### Remove Member Confirmation
- **Confirmation modal** (NOT `window.confirm`):
  - Text: "Will lose access to the agency portal. This cannot be undone."
  - Buttons: `Cancel` | `Remove`
- On confirm: `DELETE /api/agency/team/:id` (or `/agency/team-members/:id`)
- **Toast:** "Member removed"
- Note: Owner cannot be removed; soft-delete (`archived = true`)

### Toast Messages
- "Invite sent successfully" (emailSent=true)
- "Email not sent; invite link copied to clipboard" (link exists, no email)
- "Invite created, but email sending failed" (no link, no email)
- "Member removed"
- Error: `e?.response?.data?.message || e?.message || "Failed to send invite"`

### Role Display
- `owner` role → displayed as `"Admin"`
- `member` → shown as-is

### Empty/Loading States
- "Loading team members..."
- "No team members yet"

---

## `/agency/portal/merchants` — Merchants

**Page Title:** "Merchants"
**Subtitle:** "Manage your merchant connections"

### Tabs
| Tab Label | Status Filter |
|-----------|--------------|
| `Pending Requests` | `status = Pending` |
| `Active` | `status = Active` |
| `Inactive` | `status = Disconnected` |

### Per-Card Info
Each card/row: merchant avatar (initial), merchant username, email, store count

**Pending tab — action buttons per card:**
- `Accept` (green) → `POST /api/agency/merchants/{connectionId}/accept`
- `Reject` (red) → `POST /api/agency/merchants/{connectionId}/reject`

**Inactive tab** — also shows disconnection date next to store count.

**Active/Inactive tabs:**
- `View details →` (blue) → opens Merchant Detail Drawer

### Merchant Detail Drawer
- **Width:** 420px (desktop), full width (mobile)
- Slides in from the right

**Header:**
- Merchant avatar (gradient if active, gray if inactive)
- Merchant name + email
- Status badge: Active (green dot) | Inactive (gray dot)
- "Connected since {date}" (Active) or "Disconnected on {date}" (Inactive)
- If `disconnect_reason` recorded: shown below status badge

**Body — STORES section (uppercase, tracking-wide label):**
- Per store: name, country code, store URL
- **Active merchants:** each store has `Open →` button → contextual store switching → navigate to `/dashboard`
- **Inactive merchants:** stores grayed out (opacity-50); show "No access" instead of "Open →"

**Body — Commission Summary section:**
- Total Earned | Total Paid | Commission Due (per currency)
- If Commission Due > 0: amber background, left border, alert icon
- **Inactive merchants:** italic note "Historical data only. No new commission is being earned from this merchant."

**Disconnect Merchant (Active merchants only):**
- Button: `Disconnect Merchant` (rose)
- API: `POST /api/agency/merchants/{connectionId}/reject` or disconnect endpoint

### Toast Messages
- "Request accepted" | "Request rejected"
- "Merchant disconnected"
- Errors: `e?.message || "Failed to update request"` | "Failed to disconnect merchant"

### Empty States
- "No merchants found"
- "No stores available"
- "Loading merchants..."

Commission summary API: `GET /api/agency/merchants/{merchantId}/summary` (60s stale time)

---

## `/agency/portal/settings` — Agency Settings

**Page Title:** "Agency Settings"
**Subtitle:** "Manage your agency profile"

### Agency ID Card
- Agency ID displayed in large monospace font on a blue-tinted card
- Label: "Agency ID"
- Hint: "Share this ID with merchants so they can connect to your agency."
- **Button:** `Copy` → changes to checkmark / "Copied" for 2 seconds
- API: none (read-only display)

### Agency Profile Form
> ⚠️ Per PRD: All profile fields are **Non-Editable** after registration.

- **Section Title:** "Agency Profile"
- **Meta text (read-only):** "Country: {country} • Member since: {date}"
- Fields: Agency Name | City | Phone Number | Point of Contact Name
- **Save Changes** button: disabled until a field is changed (`isDirty`)
- API on save: `PUT /api/agency/settings`

### Footer / Ownership Transfer
- Amber info card: "Need to transfer ownership? Contact support@zambeel.com"
- (Source code shows `ilqa@myzambeel.com` — may differ between envs)

### Toast Messages
- "Agency settings updated" (success)
- `toast.error(e?.message || "Failed to update agency settings")`

---

## Merchant Agency Connection Section (Seller Profile Page)

**Location:** Seller portal → Profile page → `AgencyConnectionSection` component

This section has 4 distinct states based on connection status:

### State 1: Not Connected
- **Input:** `input[placeholder='ZMB-AG-XXXXXX']`
- User types the Agency ID shared by their agency
- Frontend validates: must start with `ZMB-AG-` prefix
  - If invalid: inline error "Please enter a valid Agency ID (format: ZMB-AG-XXXXXX)."
- On submit: `POST /api/merchant/agency/connect`
- Connection created with `status = Pending`

### State 2: Pending
- Animated clock icon
- Text: "Request Sent"
- Shows: agency name
- **Cancel button** → `DELETE /api/merchant/agency/request`

### State 3: Active (Connected)
- Green checkmark icon
- Text: "Connected to Agency"
- Shows: agency name + Agency ID
- **Disconnect button** → opens Disconnect Modal

**Disconnect Modal:**
- Warning: "The agency will lose access to your store data immediately upon disconnection."
- **Reason dropdown** (required):
  - "No longer need agency services"
  - "Switching to a different agency"
  - "Unsatisfied with service"
  - "Business closure"
  - "Other"
- If "Other" selected: optional free-text textarea appears
- **Confirm** → `POST /api/merchant/agency/disconnect`

### State 4: Disconnected / Rejected
- Shows previous connection was disconnected
- Can connect to a new agency

### Revoked Agency Warning (Special State)
- If connected agency's `license_status = 'Revoked'`: red warning mentioning the revoked agency by name
- Connection auto-moves to `Disconnected`

---

## `/agency/invite` — Team Invite Accept Page

**Component:** `AgencyInviteAccept`
**Guard:** Public (no auth required to view)

- Token read from URL query: `/agency/invite?token=XXXXXX`
- On load: `POST /api/agency/team-members/invite/preview` → returns agency name

**Modal Title:** "Agency Team Invitation"
**Body:** "You have been invited by [agencyName] to join their agency team."
**Already accepted:** "You already accepted this invitation." — buttons hidden

**Buttons:** `Decline` (gray) | `Accept` (blue)
- Accept: `POST /api/agency/team-members/accept` with `{ token }`
- **Toast on accept:** "Invitation accepted."
- **Toast on decline:** "Invitation declined."
