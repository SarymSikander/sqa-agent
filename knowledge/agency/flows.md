# Agency Portal — Step-by-Step User Flows

## Flow 1: Agency Registration (New)

**Prerequisites:** User is logged in as Seller. No existing agency registration.

1. Navigate to `/agency` (click "Agency" tab in seller sidebar)
2. `AgencyLanding` component shown — click "Register as Agency" or equivalent CTA
3. `AgencyRegistrationModal` opens: "Apply to Become an Agency"

**Step 1 — Details:**
4. Fill Agency Name: `input[placeholder='Enter your agency name']`
5. Select Country from dropdown (Kuwait/Qatar/Saudi Arabia/UAE/Pakistan/Oman/Bahrain/Iraq)
6. Select/Enter City:
   - If country has cities: `SearchableDropdown` with "Select city"
   - Otherwise: text input with "Type city"
7. Enter Phone: `input[placeholder='+971 50 000 0000']`
8. Enter Point of Contact Name: `input[placeholder='Full name of main contact']`
9. Click `Continue`
10. API: `POST /agency/register` → response includes S3 signed upload URLs

**Step 2 — Uploads:**
11. Upload POC Photo (image file) — `input[accept='image/*']` first card
12. Upload Identity Proof (image file) — `input[accept='image/*']` second card
13. Check Terms checkbox: "I agree that the information and documents provided are accurate..."
14. Click `Submit` / shows `Submitting...`
15. Files uploaded to S3 signed URLs
16. API: `POST /agency/register/complete`
17. Redirect to `/agency/application-submitted`
18. Agency status: `Pending`

---

## Flow 2: Agency Registration — Resubmit (After Hold)

1. Navigate to `/agency` → sees `AgencyApplicationOnHold` component
2. Hold reason is displayed (text from `hold_reason`)
3. If `allow_resubmit` is true → sees resubmit CTA
4. Click resubmit → same registration flow as Flow 1

---

## Flow 3: View Agency Dashboard (Approved Agency)

1. Navigate to `/agency` (or click Agency tab)
2. `registration_status === "Approved"` → renders `AgencyDashboard`
3. Summary cards load: Active Merchants, Total Stores, Delivered Orders, Commission Earned, Commission Due
4. Merchants & Stores table loads with merchant + store breakdown
5. Change date range by clicking range buttons (7d / 30d / all)
6. Search merchants/stores via `input[placeholder='Search merchants or stores...']`
7. Click merchant row → expands to show store details
8. Click `Open →` on active store → enters agency proxy view → navigate to `/orders`

---

## Flow 4: View Commission and Download Invoice

1. Navigate to `/agency/portal/commission`
2. Summary cards: Total Earned, Total Paid, Commission Due (per currency)
3. Click `Invoices` tab → invoice list loads
4. Invoice statuses: `Paid` (green) or `Unpaid` (amber)
5. Click download icon for an invoice
   - API: `GET /agency/invoices/:invoiceId/download` (Bearer token)
   - PDF opens/downloads
6. Click `Store Breakdown` tab → store-level commission table loads
   - Commission type shown as "% Revenue" or "Flat / Order"

---

## Flow 5: Accept Merchant Connection Request

1. Navigate to `/agency/portal/merchants`
2. Default tab: "Pending Requests"
3. Pending merchant cards show agency connection requests from sellers
4. Click `✓ Accept` → `PATCH /agency/merchants/:id/status` with `{action: "accept"}`
5. Toast: "Request accepted"
6. Merchant moves to "Active" tab

---

## Flow 6: Reject Merchant Connection Request

1. Navigate to `/agency/portal/merchants` → "Pending Requests" tab
2. Click `✕ Reject` on a pending request
3. API: `PATCH /agency/merchants/:id/status` with `{action: "reject"}`
4. Toast: "Request rejected"
5. Merchant is removed from Pending list

---

## Flow 7: Disconnect Active Merchant

1. Navigate to `/agency/portal/merchants` → "Active" tab
2. Click `View details →` on an active merchant
3. Merchant drawer opens with store list and commission summary
4. Click `Disconnect Merchant` (rose button)
5. API: `PATCH /agency/merchants/:id/status` with `{action: "disconnect"}`
6. Toast: "Merchant disconnected"
7. Merchant moves to "Inactive" tab

---

## Flow 8: View Merchant Stores (Agency Proxy Mode)

1. In Merchants drawer — Active tab
2. Find a store in "STORES" section
3. Click `Open →` button on an active store
4. System calls `enterAgencyView(...)` to set agency context header `x-agency-context-store-id`
5. Navigate to `/orders` — shows only that store's orders
6. Agency banner appears in header indicating proxy mode

---

## Flow 9: Invite Team Member

1. Navigate to `/agency/portal/team-members`
2. Click `Add Member` button (⚠️ Currently disabled — title: "Temporarily disabled")
3. If/when enabled: Modal opens: "Add Team Member"
4. Fill Full Name*: `input[placeholder="Team member's name"]`
5. Fill Email Address*: `input[placeholder='email@example.com']`
6. Click `Send Invite`
7. API: `POST /agency/team-members/invite`
8. Toast outcomes:
   - emailSent=true: "Invite sent successfully"
   - no email but link: "Email not sent; invite link copied to clipboard"
   - fail: "Invite created, but email sending failed"

---

## Flow 10: Remove Team Member

1. Navigate to `/agency/portal/team-members`
2. Find member in list
3. Click Trash2 icon (title="Remove")
4. `window.confirm("Remove {memberName} from team?")` dialog appears
5. Confirm → `DELETE /agency/team-members/:id`
6. Toast: "Member removed"
7. Member disappears from list

---

## Flow 11: Accept Team Invite (Invitee Flow)

1. Invitee receives email with link: `/agency/invite?token=XXXXXX`
2. `AgencyInviteAccept` page loads
3. Token read from URL → `POST /agency/team-members/invite/preview` → agency name returned
4. Modal appears: "Agency Team Invitation" — "You have been invited by [agencyName]..."
5. Click `Accept` → `POST /agency/team-members/accept` with `{token}`
6. Toast: "Invitation accepted."
7. OR: already accepted → "You already accepted this invitation." → buttons hidden

---

## Flow 12: Update Agency Settings

1. Navigate to `/agency/portal/settings`
2. "Agency ID" card shows unique ID with `Copy` button
3. Click `Copy` → ID copied to clipboard → button shows "Copied" for 1500ms
4. Edit Agency Profile form: name, city, phone, poc_name
   - Note: Country field is NOT editable here
5. Click `Save` (only enabled when form `isDirty`)
6. API: `PUT /agency/settings`
7. Toast: "Agency settings updated"

---

## Merchant Connect to Agency Flow (Seller side)

1. Seller navigates to settings or connection page
2. Enters agency unique ID (format: `ZMB-AG-XXXXXX`)
3. Selects access scope:
   - `all` — agency sees all stores
   - `specific` — select specific store IDs
4. Submit → `POST /agency/connect`
5. Connection created with status `Pending`
6. Agency owner sees it in Merchants → "Pending Requests" tab
7. Agency accepts → status `Active`
