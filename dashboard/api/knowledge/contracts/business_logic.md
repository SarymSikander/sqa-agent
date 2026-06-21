# Contract Management — Business Logic

## Overview

The Contracts system allows Zambeel admins to create, send, and track legal contracts with sellers. Sellers receive contracts on their Profile page and can sign pending ones in-portal. Signed contracts can be downloaded as PDFs.

There are two database tables: `contract_templates` (reusable bodies) and `contracts` (individual instances sent to specific sellers).

---

## Database Models

### `contract_templates`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `name` | STRING | Template display name |
| `content` | LONGTEXT | Full contract body (HTML/rich text) |
| `fk_created_by` | INTEGER FK → `users.id` | Admin who created it |
| `created_at` / `updated_at` | TIMESTAMP | Auto-managed |

No soft-delete — templates are permanently deleted via `destroy()`.

### `contracts`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `title` | STRING | Contract display name |
| `content` | LONGTEXT | Copied/customized from template at creation time |
| `fk_template_id` | INTEGER FK → `contract_templates.id` | Template used; nullable (stored for reference, not enforced) |
| `template_name` | STRING | Snapshot of template name at creation time |
| `fk_seller_id` | INTEGER FK → `users.id` | Seller this contract is assigned to |
| `fk_created_by` | INTEGER FK → `users.id` | Admin who created it |
| `status` | ENUM | `Draft`, `Pending`, `Approved`, `Revoked` |
| `sent_at` | DATE | When status moved to Pending |
| `signed_at` | DATE | When seller signed |
| `signed_name` | STRING | Typed signature from seller (min 2 chars) |
| `revoked_at` | DATE | When admin revoked |
| `fk_revoked_by` | INTEGER FK → `users.id` | Admin who revoked |
| `archived` | BOOLEAN | Soft-delete flag; default `false` |
| `created_at` / `updated_at` | TIMESTAMP | Auto-managed |

**Default scope**: `where: { archived: false }` — archived contracts never appear in any query.

---

## Contract Status Machine

```
Draft ──(send)──► Pending ──(seller signs)──► Approved
  │                  │                           │
  │           (admin revokes)             (admin revokes)
  │                  ▼                           ▼
(delete/archive)  Revoked                    Revoked
```

| Status | Admin can edit? | Admin can delete? | Admin can revoke? | Seller can sign? | PDF available? |
|--------|----------------|-------------------|-------------------|-----------------|----------------|
| Draft | Yes | Yes (soft-delete) | No | No | No |
| Pending | No | No | Yes | Yes | No |
| Approved | No | No | Yes | No | Yes |
| Revoked | No | No | No | No | No |

- Sellers **never see Draft** contracts — `getMyContracts` filters `status != 'Draft'`.
- A seller can only sign a **Pending** contract.
- PDF download is only available for **Approved** (signed) contracts.
- Delete sets `archived = true` (soft-delete); all reads use the default scope.

---

## API Endpoints

All routes mounted at `/api/contracts/`.

### Admin Endpoints (role: `Admin` via `verifyJWTWithRoles(["Admin"])`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/contracts/templates` | List all templates (ordered by `created_at DESC`), including `createdBy` user |
| `POST` | `/contracts/templates` | Create a new template — body: `{name, content}` |
| `GET` | `/contracts/templates/:id` | Get single template by ID |
| `PUT` | `/contracts/templates/:id` | Update template `name` and/or `content` |
| `DELETE` | `/contracts/templates/:id` | Permanently delete template (`destroy()`) |
| `GET` | `/contracts/sellers/search?q=X&limit=N` | Search sellers by username or email (for contract creation); returns `{sellers[]}` |
| `GET` | `/contracts?status=X&search=Y&page=N&limit=N` | Paginated contract list; filterable by status and by seller username/email/contract title |
| `POST` | `/contracts` | Create contract — body: `{fk_template_id, title, content, fk_seller_id, send, force}` |
| `GET` | `/contracts/:id` | Get single contract with seller, createdBy, revokedBy |
| `PUT` | `/contracts/:id` | Update contract — only allowed on `Draft` status; same body fields as create |
| `DELETE` | `/contracts/:id` | Soft-delete — only allowed on `Draft` status; sets `archived = true` |
| `POST` | `/contracts/:id/revoke` | Revoke contract — only `Pending` or `Approved` contracts can be revoked |

### Seller/Agency Endpoints (role: `Seller` or `Agency` via `verifyJWTWithRoles(["Seller","Agency"])`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/contracts/my` | List all non-Draft contracts for the authenticated seller (ordered by `sent_at DESC`) |
| `GET` | `/contracts/my/:id` | Get single contract for the seller (non-Draft only) |
| `POST` | `/contracts/my/:id/sign` | Sign a Pending contract — body: `{signed_name}` (min 2 chars) |
| `GET` | `/contracts/my/:id/pdf` | Download signed (Approved) contract as PDF — returns binary `application/pdf` |

**Route ordering note**: `/my` and `/my/:id` are declared **before** `/:id` in the router so the string "my" is not matched as an integer contract ID.

---

## Admin Workflow

### Creating and Sending a Contract

1. **Create templates** — admin creates reusable bodies in the Templates tab. Templates are pure text/HTML; content is copied into each contract at creation time (a contract is not linked live to its template's future edits).

2. **Create contract** (`POST /contracts`):
   - `fk_template_id`: the template to base on (validated to exist)
   - `title`: display name — must be unique per seller (across all statuses)
   - `content`: can be edited from the template's body before sending
   - `fk_seller_id`: the seller to assign to (must exist and have role `Seller`)
   - `send: true` → status becomes `Pending`, `sent_at` is set, `sendContractSentNotification()` is called
   - `send: false` (default) → status stays `Draft` (saved for later)
   - `force: true` → skip the duplicate-title check (used when admin explicitly wants to allow a duplicate)

3. **Update and send** — a Draft contract can be edited and/or sent later via `PUT /contracts/:id` with `send: true`. Once sent (Pending/Approved/Revoked), the contract is locked — PUT returns 422 `Only draft contracts can be edited`.

4. **Duplicate title detection** — if `send: true` and the seller already has a contract with the same title (any status), the API returns HTTP 409 with `code: "DUPLICATE_TITLE"`. The frontend can surface a warning and let the admin retry with `force: true`.

5. **Revoke** — admin can revoke any `Pending` or `Approved` contract. Sets `status = "Revoked"`, `revoked_at`, and `fk_revoked_by`.

6. **Track** — the Contracts tab on the admin page shows a paginated, searchable, filterable table with status badges. Columns: seller name, contract title, status, sent date, signed date.

---

## Seller Workflow

Seller contracts surface on the **seller Profile page** (`/profile`) — there is **no separate `/contracts` seller route**. The `SellerContractsSection` component renders as a card within Profile.

1. Seller visits `/profile` → `SellerContractsSection` mounts.
2. Calls `GET /contracts/my` → receives all non-Draft contracts assigned to them (Pending, Approved, Revoked).
3. **Pending contract** → seller sees a "Sign" button → opens `SignContractModal` → seller types their name → `POST /contracts/my/:id/sign`.
4. **Approved contract** → seller sees a "Download PDF" button → `GET /contracts/my/:id/pdf` → browser triggers file download as `<title>.pdf`.
5. **Revoked contract** → shown with a Revoked badge; no actions available.

### Signing Requirements
- Contract must be in `Pending` status (422 otherwise).
- `signed_name` must be at least 2 characters.
- On success: `status → Approved`, `signed_name` and `signed_at` are set.

### PDF Download Requirements
- Contract must be in `Approved` status (422 `PDF_ONLY_APPROVED` otherwise).
- PDF is generated on demand by `generateContractPdf(contract)` in `helpers/contractPdf.js`.
- Response: `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="<safe_title>.pdf"`.

---

## Frontend Pages

### OMS Admin Page — `/orders-management/contracts`

**Component**: `OMSContractsPage` (`src/pages/orders-management/contracts/index.tsx`)

Two-tab layout:

| Tab | Component | Purpose |
|-----|-----------|---------|
| **Templates** | `TemplatesTab` | List, create, edit, delete contract templates |
| **Contracts** | `ContractsTab` | List, create, view, revoke contracts; search by seller/title; filter by status |

**Contracts tab UI elements**:
- Search input: searches by seller username, email, or contract title
- Status filter dropdown: All / Draft / Pending / Approved / Revoked
- Pagination (10 per page)
- Per-row actions: View (eye icon), Edit (only for Draft), Revoke (confirm modal), Delete (only for Draft, confirm modal)
- "New Contract" button → opens `CreateContractWizard`

**CreateContractWizard flow**:
- Step 1: Pick a template + select a seller (via seller search autocomplete) + enter title
- Step 2: Edit/review contract content
- Step 3: Send immediately or save as draft

### Seller Profile Page — `/profile` (embedded)

**Component**: `SellerContractsSection` (inside `Profile.tsx`)

Renders a card listing all contracts for the logged-in seller. Per contract:
- Status badge (color-coded: Pending = amber, Approved = green, Revoked = rose)
- Sent date and signed date (if applicable)
- "Sign" button for Pending contracts
- "Download PDF" button for Approved contracts
- `SignContractModal`: type-to-sign dialog with name input

---

## Notifications

`sendContractSentNotification(contract, req)` is called in `helpers/contractNotifications.js` when a contract is sent to a seller (status → Pending). The exact notification channel (email/push/socket) is implemented in that helper — check `helpers/contractNotifications.js` for the delivery method.

---

## Key Files

| File | Purpose |
|------|---------|
| `routes/contractRoutes.js` | All 16 route definitions |
| `controllers/contracts.js` | Seller + admin contract endpoints |
| `controllers/contractTemplates.js` | Template CRUD |
| `models/contract.js` | `contracts` table + associations + `sellerHasDuplicateTitle()` |
| `models/contractTemplate.js` | `contract_templates` table |
| `constants/contract.constants.js` | Status enum, error/success messages, revocable statuses |
| `validations/contract.validations.js` | Joi/Zod schemas for all endpoints |
| `helpers/contractPdf.js` | PDF generation |
| `helpers/contractNotifications.js` | Notification on send |
| `src/pages/orders-management/contracts/index.tsx` | OMS admin page |
| `src/components/oms-contracts/` | Admin-side contract UI components |
| `src/components/seller-contracts/SellerContractsSection.tsx` | Seller profile card |
| `src/api/contracts.ts` | Axios API calls for all contract endpoints |
| `src/types/contract.types.ts` | TypeScript contract + template type definitions |
