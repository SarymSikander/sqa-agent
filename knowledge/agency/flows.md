# Agency Portal — Step-by-Step User Flows

> Source: Zambeel Agency Model PRD (Zambeel-Agency.pdf) + zambeel-fe source code.

---

## Flow 1: Agency Registration (New User — 3-Step Wizard)

**Prerequisites:** User is logged in as Seller. No existing agency registration.

1. Navigate to `/agency` (click "Agency" tab in seller sidebar)
2. `AgencyLanding` component shown — page has "Apply Now" CTA, feature cards, How It Works section, commission slider, FAQ
3. Click `Apply Now` → `AgencyRegistrationModal` opens: "Apply to Become an Agency"

**Step 1 of 3 — Agency Details:**
4. Fill Agency Name: `input[placeholder='Enter your agency name']`
5. Select Country from dropdown (UAE / Saudi Arabia / Pakistan / Kuwait / Bahrain / Oman / Jordan / Egypt / Iraq)
6. Select/Enter City:
   - If country has cities API: `SearchableDropdown` → "Select city"
   - Otherwise: text input → "Type city"
7. Enter Phone: `input[placeholder='+971 50 000 0000']`
8. Enter Point of Contact Name: `input[placeholder='Full name of main contact']`
9. Click `Continue` — validates all fields; empty fields show red inline errors
10. API: `POST /api/agency/register` → response includes S3 signed upload URLs

**Step 2 of 3 — Document Upload:**
11. Upload POC Photo (image — JPG/PNG/WebP, max 5MB) — `input[accept='image/*']` first zone
12. Upload Identity Proof (image or PDF — JPG/PNG/WebP/PDF, max 10MB) — second zone
    - Zones turn red if user tries to proceed without uploading
    - After upload: shows thumbnail/file-icon, filename, file size, trash to remove
13. Click `Continue` — validates both uploads are present

**Step 3 of 3 — Terms:**
14. Upload summary shown (files from Step 2)
15. Check terms checkbox: "I confirm that all information is accurate and I agree to Zambeel's Agency Terms."
16. Click `Submit` / shows `Submitting...`
17. Files uploaded to S3 signed URLs
18. API: `POST /api/agency/register/complete`
19. **Toast:** "Application submitted! We'll review within 3–5 business days. In the meantime, our team might call you on your provided number."
20. Modal closes; page re-renders to show **Pending status card**
21. Agency `registration_status` = `Pending`

---

## Flow 2: Agency Registration — Resubmit (After OnHold)

**Prerequisites:** Agency `registration_status = 'OnHold'` and `allow_resubmit = true`

1. Navigate to `/agency` → sees `AgencyApplicationOnHold` component
2. `hold_reason` text from admin is displayed (explains what needs to be fixed)
3. `allow_resubmit = true` → resubmit CTA is visible
4. Click resubmit → shows URL fields only (no new document upload required)
5. API: `POST /api/agency/resubmit`
6. Status returns to `Pending`

---

## Flow 3: Merchant Connects to an Agency (Seller Side)

**Prerequisites:** Seller has the Agency's `ZMB-AG-XXXXXX` ID.

1. Seller navigates to Profile page → `AgencyConnectionSection`
2. Sees **Not Connected** state with `input[placeholder='ZMB-AG-XXXXXX']`
3. Types the Agency ID into the field
   - Frontend validates: must start with `ZMB-AG-`
   - If invalid format: inline error "Please enter a valid Agency ID (format: ZMB-AG-XXXXXX)."
4. Submit → `POST /api/merchant/agency/connect`
   - Backend validates agency exists, is approved, not revoked
   - Connection created with `status = Pending`
5. Page shows **Pending state**: animated clock, "Request Sent", agency name, `Cancel` button
6. If merchant cancels: `DELETE /api/merchant/agency/request` → back to Not Connected state

**After agency accepts:**
7. Page shows **Active state**: green checkmark, "Connected to Agency", agency name + Agency ID
8. `Disconnect` button appears

**Merchant Disconnect Flow:**
9. Click `Disconnect` → Disconnect Modal opens
10. Warning: "The agency will lose access to your store data immediately upon disconnection."
11. Select reason from dropdown:
    - "No longer need agency services" | "Switching to a different agency" | "Unsatisfied with service" | "Business closure" | "Other"
    - If "Other": optional free-text textarea appears
12. Confirm → `POST /api/merchant/agency/disconnect`
13. Connection `status = Disconnected`

---

## Flow 4: View Agency Dashboard (Approved Agency)

1. Navigate to `/agency/portal/dashboard` (click Agency tab → Dashboard)
2. Page: "Agency Dashboard" — "Performance across all your merchants"
3. Summary cards load (Active Merchants, Total Stores, Delivered Orders, Commission Earned, Commission Due)
4. Merchants & Stores table loads grouped by merchant
5. Change date range: click `7 Days` / `30 Days` / `All Time` buttons
6. Refresh: click RefreshCcw icon button
7. Search merchants/stores: `input[placeholder='Search merchants or stores...']`
8. Click merchant row chevron → expands to show store sub-rows
9. Click `Open →` on active store → enters agency proxy view (see Flow 8)

---

## Flow 5: View Commission and Download Invoice

1. Navigate to `/agency/portal/commission`
2. Summary cards: Total Earned, Total Paid, Commission Due (per currency, color-coded pills)
3. Default tab: `Invoices`
   - Table: Period | Amount | Status (Paid/Unpaid) | Payment Date | PDF download
   - Empty state: "No invoices yet"
4. Click download icon → API: `GET /api/agency/invoices/:invoiceId/download` (Bearer token)
5. Click `Store Breakdown` tab
   - Filter: 7 days / 30 days / custom date range
   - Table: Store | Merchant | Commission Type | Delivered Revenue | Delivered Orders | Commission
   - Commission type badges: "% Revenue" | "Flat / Order"
   - Empty state: "No commission records yet"

---

## Flow 6: Accept Merchant Connection Request

1. Navigate to `/agency/portal/merchants`
2. Default tab: "Pending Requests"
3. Pending cards show: merchant avatar/initial, name, email, store count
4. Click `Accept` → `POST /api/agency/merchants/{connectionId}/accept`
5. Toast: "Request accepted"
6. Merchant moves from "Pending Requests" tab to "Active" tab

---

## Flow 7: Reject Merchant Connection Request

1. Navigate to `/agency/portal/merchants` → "Pending Requests" tab
2. Find pending merchant card
3. Click `Reject` → `POST /api/agency/merchants/{connectionId}/reject`
4. Toast: "Request rejected"
5. Merchant removed from Pending list (status = Rejected on merchant side)

---

## Flow 8: View Merchant Stores (Agency Proxy / Contextual Switching)

1. Go to `/agency/portal/merchants` → "Active" tab
2. Click `View details →` on an active merchant
3. Merchant Detail Drawer opens (420px wide, slides from right)
   - Header: merchant name, email, status badge, "Connected since {date}"
   - STORES section: store name, country, URL per store
4. Click `Open →` on an active store
5. System writes to `useAgencyViewStore` Zustand store: merchantId, merchantName, merchantEmail, storeId, storeName, storeCountry, agencyName
6. Drawer closes
7. Navigate to `/dashboard` (merchant's seller dashboard)
8. **Agency Context Banner** appears at top: "Agency Name · Merchant Name · Store Name"
9. Dashboard shows merchant's store data (scoped to that storeId)
10. Agency can navigate: Dashboard, Analytics, Orders, Ticketing, Invoices, My Inventory (all scoped)

**Exit Proxy Mode:**
11. Click Agency in sidebar or navigate to `/agency/portal/*`
12. Context (`useAgencyViewStore`) is cleared automatically
13. Agency Context Banner disappears; seller dashboard reverts to own data

**Edge case:** If merchant disconnects during agency proxy session, next API call returns 403 → UI redirects agency back to their portal.

---

## Flow 9: Disconnect Active Merchant (Agency Side)

1. Navigate to `/agency/portal/merchants` → "Active" tab
2. Click `View details →` on an active merchant
3. Merchant Detail Drawer opens
4. Click `Disconnect Merchant` (rose button)
5. API: disconnect endpoint (PATCH/POST)
6. Toast: "Merchant disconnected"
7. Merchant moves to "Inactive" tab; drawer shows "Disconnected on {date}"

---

## Flow 10: Invite Team Member

**Prerequisites:** User is agency owner.

1. Navigate to `/agency/portal/team-members`
2. Click `Add Member` button (top right)
3. Modal opens: "Add Team Member"
4. Fill Full Name*: `input[placeholder="Team member's name"]`
5. Fill Email Address*: `input[placeholder='email@example.com']`
   - Email validated for valid format before submission
6. Click `Send Invite`
7. API: `POST /api/agency/team` (or `/agency/team-members/invite`)
8. Toast outcomes:
   - `emailSent=true`: "Invite sent successfully"
   - No email but link: "Email not sent; invite link copied to clipboard"
   - Failure: "Invite created, but email sending failed"
9. Invited member appears with "Invite Pending" badge until they accept

---

## Flow 11: Remove Team Member

**Prerequisites:** User is agency owner (cannot remove self).

1. Navigate to `/agency/portal/team-members`
2. Find member row → click Trash2 icon (title="Remove")
3. **Confirmation modal** opens:
   - Text: "Will lose access to the agency portal. This cannot be undone."
   - Buttons: `Cancel` | `Remove`
4. Click `Remove` → `DELETE /api/agency/team/{memberId}` (soft-delete: `archived = true`)
5. Toast: "Member removed"
6. Member disappears from list

---

## Flow 12: Accept Team Invite (Invitee Flow)

1. Invitee receives email with link: `/agency/invite?token=XXXXXX`
2. `AgencyInviteAccept` page loads
3. Token read from URL → `POST /api/agency/team-members/invite/preview` → agency name returned
4. Modal: "Agency Team Invitation" — "You have been invited by [agencyName] to join their agency team."
5. Click `Accept` → `POST /api/agency/team-members/accept` with `{ token }`
6. Toast: "Invitation accepted."
7. Already accepted case: "You already accepted this invitation." — buttons hidden

---

## Flow 13: Update Agency Settings

1. Navigate to `/agency/portal/settings`
2. "Agency ID" card shows unique ID (monospace font, blue card)
3. Click `Copy` → ID copied to clipboard → button shows "Copied" for ~2 seconds
4. Edit Agency Profile form: Agency Name, City, Phone Number, Point of Contact Name
   - ⚠️ Per PRD: fields are non-editable after registration (source code may still render input fields)
   - Country field is NOT editable (read-only, shown in meta text)
5. Click `Save` / `Save Changes` (only enabled when form `isDirty`)
6. API: `PUT /api/agency/settings`
7. Toast: "Agency settings updated"

---

## Flow 14: Admin Reviews Agency Application (OMS Side)

1. OMS Admin navigates to `/orders-management/agency-registrations`
2. Default tab: "All" — all applications listed
3. Click `Pending` tab → see pending applications
4. Click `Review` button on a row
5. Drawer opens with application details (name, country, POC, documents)
6. Admin actions:
   - `Approve Agency` → select commission model → `Confirm Approve`
   - `Put on Hold` → enter hold reason in textarea → submit (sets allow_resubmit)
   - `Confirm Reject` → enter rejection reason in textarea → submit
7. Agency `registration_status` changes; agency is notified

---

## State Machine Summary

```
registration_status:
  null → [Apply Now] → Pending
  Pending → [Admin approve] → Approved
  Pending → [Admin reject]  → Rejected (cooloff_days_remaining set)
  Pending → [Admin hold]    → OnHold   (hold_reason set, allow_resubmit optional)
  OnHold  → [Resubmit]      → Pending
  OnHold  → [Admin approve] → Approved
  OnHold  → [Admin reject]  → Rejected
  Approved→ license_status='Revoked' → Shows Revoked card (approval overridden)

merchant_connection status:
  Pending → [Agency accept]      → Active
  Pending → [Agency reject]      → Rejected (merchant can connect to another)
  Pending → [Merchant cancel]    → (deleted)
  Active  → [Merchant disconnect]→ Disconnected
  Active  → [Agency license revoked] → Disconnected (automatic)
```
