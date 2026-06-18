# Tickets Domain — Business Logic

## What This Domain Does

The tickets domain is a two-way support ticketing system between **sellers** (and agencies acting as sellers) and the **Zambeel operations/admin team**. Either side can open a ticket against a store; the system routes it to the right internal team, tracks status transitions through a defined workflow, logs every change, and fires real-time Socket.IO events to the relevant parties.

---

## Key Endpoints

### Seller-facing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tickets` | List tickets for the authenticated seller (or agency-proxied merchant). Supports status filter, free-text search, pagination, and `filter_type`. Returns tickets + per-status counts. |
| POST | `/tickets` | Create a ticket from seller → Zambeel. Assigned to Zambeel team based on category. |
| GET | `/tickets/search-orders` | Search orders belonging to a store (used when filling in a ticket that requires an order). |
| GET | `/tickets/user-stores` | List all stores owned by the authenticated (or proxied) user. |
| GET | `/tickets/find-store-order` | Find a single order by `order_id` or `order_number` within a store. |
| GET | `/tickets/:ticket_id` | Fetch a single ticket with full associations (store, order+customer, team, createdBy, seller, images, comments) plus all logs. |
| GET | `/tickets/:ticket_id/logs` | Fetch audit logs for a ticket (only for the ticket creator). |

### Admin/Agent-facing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tickets/admin` | List tickets from Zambeel's perspective. Admins see all; agents see their team's tickets. Supports filters: status (array), store_id, team_id, ticket_number, category, sub_category, store_protocol, subscription_plan. |
| POST | `/tickets/admin` | Create a ticket from Zambeel → Seller. Assigned to `Seller`; the seller identified from the store record. |
| PUT | `/tickets/:ticket_id` | Update a ticket: status, description, team assignment, or add resolution notes. Logs changes; fires Socket.IO on status change. |
| GET | `/tickets/search/stores` | Search stores by name, platform, or URL (admin use when creating a ticket). |

### Comments (via `/comments` router)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/comments` | Add a comment to a ticket. May trigger automatic status transitions. Supports `is_internal` flag. |
| GET | `/comments/ticket/:ticketId` | Fetch all comments for a ticket. Sellers never see internal comments. |

---

## Middleware & Auth

- `verifyJWT` — all ticket routes require a valid JWT.
- `verifyAgencyStoreContext` — seller-facing routes additionally verify that if the user is an `Agency` role, the request is scoped to a specific merchant (via `req.proxyContext`).
- `validateRequest` — Joi schema validation on all routes.

---

## Business Logic: Creating a Seller Ticket (POST /tickets)

1. Resolve effective `userId` — use `req.proxyContext.merchantUserId` if agency proxy, else `req.user.id`.
2. Verify the `fk_store_id` belongs to that user (403 if not).
3. Look up the team name from `CATEGORY_TEAM_MAPPING` by `category` (400 if category not in map).
4. Find the `Team` row by that name (404 if missing).
5. If `category` is in `CATEGORIES_REQUIRING_ORDER`, require and validate `fk_order_id` belongs to the store.
6. Create `Ticket` with `assigned_to: 'Zambeel'`, `status: 'Pending'`.
7. If an `image` URL is provided, create a `TicketImage` row with `linked_with: 'ticket'`.
8. Create a `TicketLog` with `action: 'SELLER_TICKET_CREATED'`.
9. Outside the transaction, emit Socket.IO event `seller_to_zambeel_ticket_created` to all agents in the assigned team and all admins.

## Business Logic: Creating an Admin/Agent Ticket (POST /tickets/admin)

1. Find the store; inner-join to confirm its user has `role: 'Seller'`.
2. Determine team assignment:
   - Agent: use `creator.team_id` directly.
   - Admin: use `CATEGORY_TEAM_MAPPING[category]` to look up the team.
3. If `category` requires an order, validate `fk_order_id`.
4. Create `Ticket` with `assigned_to: 'Seller'`, `status: 'Pending'`, `fk_seller_id: store.user.id`.
5. Optionally attach an image.
6. Create `TicketLog` with `action: 'ADMIN_TICKET_CREATED'`.
7. Emit Socket.IO `zambeel_to_seller_ticket_created` to the seller.

## Business Logic: Updating a Ticket (PUT /tickets/:ticket_id)

Updatable fields: `status`, `description`, `fk_team_id`. Additionally, `resolution_notes` is written as a `Comment` row with `notes_type: 'resolution_notes'`.

- Status change → log action `TICKET_STATUS_CHANGED`, fire `sendTicketStatusChangeNotification`.
- Description change → log action `TICKET_DESCRIPTION_UPDATED`.
- Team change → log action `TICKET_UPDATED`.
- Resolution notes → log action `TICKET_RESOLUTION_NOTES_UPDATED`.

## Business Logic: Automatic Status Transitions from Comments

When a comment is posted, the system checks whether the status should advance **automatically**:

| Ticket status | Who comments | `is_internal` | New status |
|---------------|-------------|---------------|------------|
| Pending | Zambeel (Admin/Agent) | false | Awaiting Seller Action |
| Pending | Zambeel (Admin/Agent) | true | (unchanged) |
| Pending | Seller | any | In Progress |
| Awaiting Seller Action | Seller | any | In Progress |
| In Progress | Zambeel (Admin/Agent) | false | Awaiting Seller Action |
| In Progress | Zambeel (Admin/Agent) | true | (unchanged) |
| In Progress | Seller | any | (unchanged) |

The logic uses `ticket.fk_seller_id === null` to determine whether the ticket was originally seller-created. If status changes, `sendTicketStatusChangeNotification` fires after the transaction commits.

## Business Logic: Socket.IO Notifications

`sendTicketStatusChangeNotification` in `helpers/ticketNotifications.js`:

- If `assigned_to === 'Zambeel'`: notify the ticket creator (seller) + all agents in `fk_team_id` + all admins.
- If `assigned_to === 'Seller'`: notify the `fk_seller_id` user + the ticket creator (admin/agent).
- Uses room pattern `user_<userId>`, event `ticket_status_changed`.

On ticket creation:
- Seller-created ticket → `seller_to_zambeel_ticket_created` to agents+admins.
- Admin-created ticket → `zambeel_to_seller_ticket_created` to the seller.

---

## Status Values

| Value | Meaning |
|-------|---------|
| `Pending` | Newly created; no one has acted yet |
| `In Progress` | Active dialogue; seller has responded |
| `Awaiting Seller Action` | Zambeel has replied; waiting on seller |
| `Resolved` | Closed (set manually via PUT) |

`assigned_to` values: `Zambeel` | `Seller`

---

## Category → Team Mapping

| Category | Team |
|----------|------|
| Onboarding & Integration | AM Team |
| Order Sending & Inventory Issue | AM Team |
| Payments & Invoices | AM Team |
| Catalog & Pricing Updates | AM Team |
| Payments & Payouts | AM Team |
| Order Changes & Updates | OP Team |
| Order Issue | OP Team |
| Product Complaint | NDR Team |
| Delivery Complaint | NDR Team |

## Categories Requiring an Order ID

`Order Changes & Updates`, `Product Complaint`, `Delivery Complaint`, `Order Issue`

---

## Key Models

### `tickets` table

| Field | Type | Notes |
|-------|------|-------|
| `id` | INT PK | Auto-increment |
| `fk_store_id` | INT | Required; FK → stores |
| `fk_order_id` | INT | Nullable; required for certain categories |
| `fk_team_id` | INT | Nullable; FK → teams |
| `fk_seller_id` | INT | Nullable; set when Zambeel creates ticket for seller |
| `fk_created_by` | INT | FK → users; always the user who hit the create endpoint |
| `category` | ENUM | See full list below |
| `sub_category` | ENUM | Must be valid for the chosen category |
| `status` | ENUM | Pending / In Progress / Awaiting Seller Action / Resolved |
| `assigned_to` | ENUM | Zambeel / Seller |
| `description` | TEXT | Required |

#### Full category ENUM
`Onboarding & Integration`, `Order Sending & Inventory Issue`, `Order Changes & Updates`, `Product Complaint`, `Delivery Complaint`, `Payments & Invoices`, `Order Issue`, `Catalog & Pricing Updates`, `Payments & Payouts` (plus legacy: `Order Processing`, `Other`)

### `comments` table

| Field | Type | Notes |
|-------|------|-------|
| `comment` | TEXT | Nullable |
| `fk_ticket_id` | INT | FK → tickets |
| `fk_user_id` | INT | FK → users |
| `notes_type` | ENUM | `comment` (default) / `resolution_notes` |
| `is_internal` | BOOLEAN | Default false; internal comments hidden from sellers |
| `fk_team_id` | INT | Nullable; set to user's team if `is_internal` is true |

### `ticket_logs` table

| Field | Type | Notes |
|-------|------|-------|
| `ticket_id` | INT | FK → tickets |
| `user_id` | INT | FK → users; actor |
| `action` | STRING | One of: `SELLER_TICKET_CREATED`, `ADMIN_TICKET_CREATED`, `TICKET_UPDATED`, `TICKET_STATUS_CHANGED`, `TICKET_DESCRIPTION_UPDATED`, `TICKET_RESOLUTION_NOTES_UPDATED` |
| `previous_value` | TEXT | JSON stringified previous state |
| `new_value` | TEXT | JSON stringified new state |

### `ticket_images` table

| Field | Type | Notes |
|-------|------|-------|
| `ticket_id` | INT | FK → tickets |
| `comment_id` | INT | Nullable; FK → comments |
| `linked_with` | ENUM | `ticket` / `comment` |
| `image_url` | STRING | S3 URL |

---

## Interactions with Other Domains

- **Stores** — every ticket must belong to a store; store ownership is verified on creation.
- **Orders** — certain ticket categories require a linked order that belongs to the store.
- **Users / Teams** — agents are scoped to teams; category determines team assignment; admin vs agent role gates query visibility.
- **Socket.IO** — real-time push to connected clients on ticket create and status change.
- **No email/external service calls** — all notifications are in-app via Socket.IO only.

---

## Important Constraints

- A seller can only create tickets for stores they own.
- `fk_seller_id` is `null` on seller-created tickets and populated only on admin-created tickets. This distinction drives the auto-status-transition logic in comments.
- Agents without a `team_id` can only see tickets they personally created.
- Internal comments (`is_internal: true`) are never visible to sellers.
- The `filter_type` query param on `GET /tickets` has three values: `all` (default), `created_by` (tickets the user created, assigned to Zambeel), `seller_id` (tickets assigned to the seller).
- `searchOrders` excludes orders with `status` containing `"Received"` to prevent assigning tickets to already-delivered orders.
