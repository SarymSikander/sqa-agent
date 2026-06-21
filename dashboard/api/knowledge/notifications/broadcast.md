# Broadcast Notifications — Business Logic

## Overview

Broadcast Notifications is a distinct admin-to-seller messaging subsystem. It is **separate from the standard notification system** (which fires on system events like order status changes, ticket updates, or invoice generation via Customer.io/Firebase/Socket.IO). Broadcast notifications are admin-initiated FYI messages — no system event triggers them.

---

## How Broadcast Differs from Standard Notifications

| Dimension | Standard Notifications | Broadcast Notifications |
|-----------|----------------------|------------------------|
| Trigger | System event (order placed, ticket opened, invoice generated) | Admin manually sends |
| Recipients | Pre-determined by event | Admin selects: specific sellers, all sellers, or CSV |
| Channels | Customer.io email + Firebase push + Socket.IO `notifications` room | Socket.IO `broadcast_notification_received` only |
| Categories | Typed by event source | `pricing`, `inventory`, `zambeel_updates`, `payments` |
| Read tracking | Not tracked | Per-recipient `read_at` timestamp in DB |
| Expiry | No expiry | Admin sets a future expiry date per notification |
| Images | No | Optional image URL (`BROADCAST_S3_BUCKET_NAME`) |
| Seller UI | Varies by notification type | Dedicated `/notifications` page + bell unread count |

---

## Database Tables

The model is `BroadcastNotification` in `models/BroadcastNotification.js` (inferred from service usage). Two tables:

### `broadcast_notifications` — the message

| Column | Notes |
|--------|-------|
| `id` | PK |
| `title` | Max 100 chars |
| `message` | Max 500 chars (manual), 1000 chars (CSV rows) |
| `category` | ENUM: `pricing`, `inventory`, `zambeel_updates`, `payments` |
| `image_url` | Optional; images stored in S3 (`BROADCAST_S3_BUCKET_NAME`) |
| `expiry_at` | Must be a future date when creating; can be updated later |
| `send_mode` | `manual_selected`, `manual_all`, or `csv` |
| `fk_created_by` | Admin user who sent it |
| `sent_at` | Timestamp when the notification was dispatched |

### `broadcast_notification_recipients` — per-user delivery

| Column | Notes |
|--------|-------|
| `id` | PK |
| `fk_notification_id` | FK → `broadcast_notifications.id` |
| `fk_user_id` | FK → `users.id` — the seller/recipient |
| `read_at` | NULL until the seller opens/marks read; set to timestamp on read |

Both tables are created atomically in `BroadcastNotification.createWithRecipients()`.

---

## API Endpoints

### Admin Endpoints

Mounted at `/api/admin/broadcast-notifications/`. Requires either `verifyAdminOnly` or `verifyUser` (noted per route).

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/admin/broadcast-notifications/sellers/search` | `verifyAdminOnly` | Search active sellers by username/email for targeting |
| `POST` | `/admin/broadcast-notifications/manual` | `verifyAdminOnly` | Send a manually composed notification |
| `POST` | `/admin/broadcast-notifications/csv/validate` | `verifyAdminOnly` | Validate CSV rows without sending |
| `POST` | `/admin/broadcast-notifications/csv` | `verifyAdminOnly` | Validate and send all CSV rows |
| `GET` | `/admin/broadcast-notifications` | `verifyUser` | Get paginated sent log (all notifications) |
| `GET` | `/admin/broadcast-notifications/:id` | `verifyUser` | Get notification detail with per-recipient read status |
| `PATCH` | `/admin/broadcast-notifications/:id/expiry` | `verifyAdminOnly` | Update expiry date of an existing notification |

**Note**: `GET /` and `GET /:id` use `verifyUser` (not `verifyAdminOnly`) — agents can view the sent log without admin role.

### Seller Endpoints

Mounted at `/api/broadcast-notifications/`. All routes require `verifySeller`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/broadcast-notifications/unread-count` | Get count of unread notifications for the bell badge |
| `GET` | `/broadcast-notifications` | List all notifications for this seller; optional `?category=X` filter |
| `PATCH` | `/broadcast-notifications/read-all` | Mark all unread notifications as read |
| `PATCH` | `/broadcast-notifications/:recipientId/read` | Mark a single notification as read by its recipient row ID |

---

## Admin Send Flows

### Manual Send (`POST /admin/broadcast-notifications/manual`)

**Request body**:
- `title` — string (max 100 chars)
- `message` — string (max 500 chars)
- `category` — one of `pricing`, `inventory`, `zambeel_updates`, `payments`
- `image_url` — optional string (S3 URL)
- `expiry_at` — ISO date string; must be in the future
- Targeting (mutually exclusive — cannot send both):
  - `recipient_user_ids: number[]` — specific seller IDs (validated against active sellers)
  - `send_to_all: true` + `pin: string` — send to ALL active sellers; requires 6-digit PIN from `config.get("broadcast.allSellersPin")`

**What happens**:
1. Validates category is valid.
2. Validates `expiry_at` is a future date.
3. Validates targeting is not ambiguous (cannot combine `send_to_all` + `recipient_user_ids`).
4. For `send_to_all`: verifies PIN; fetches all active seller IDs via `BroadcastNotification.getActiveSellerIds()`.
5. For targeted: validates all provided IDs are active sellers (returns 400 if any invalid).
6. Creates notification + recipient rows in a single DB transaction via `BroadcastNotification.createWithRecipients()`.
7. Emits `broadcast_notification_received` socket event to each recipient's `user_<id>` Socket.IO room.
8. Returns `{notification_id, recipient_count}`.

### CSV Send (`POST /admin/broadcast-notifications/csv`)

Each CSV row is a **separate notification** targeting one seller — useful for personalised messages (e.g. price change specific to that seller's product).

**CSV row structure** (passed as `rows[]` in the request body, pre-parsed by frontend):

| Field | Type | Constraints |
|-------|------|-------------|
| `user_id` | integer | Active seller ID |
| `title` | string | Max 100 chars |
| `message` | string | Max 1000 chars (higher limit than manual) |
| `category` | string | `pricing`, `inventory`, `zambeel_updates`, or `payments` |
| `expiry_date` | ISO date | Must be future |

**Two-step approach**:
- `POST /csv/validate` — validates all rows, returns `{valid, errors[], row_count}`. If any row fails, the entire CSV is rejected (`valid: false`) with per-row error details. Frontend should always call this first.
- `POST /csv` — validates again internally, then creates + emits all notifications in a single transaction.

**send_mode**: all CSV notifications record `send_mode = "csv"`.

### Sent Log (`GET /admin/broadcast-notifications`)

Paginated (default 20, max 100 per page). Each entry includes:
- `recipient_count` — total recipients
- `read_count` — recipients who have read
- `unread_count` — derived

Detail view (`GET /admin/broadcast-notifications/:id`) shows per-recipient list with `username`, `email`, `phone_number`, `read_at`, `is_read`. Paginated (default 10 per page).

### Update Expiry (`PATCH /admin/broadcast-notifications/:id/expiry`)

Updates `expiry_at` on an existing notification. No constraint requiring the new date to be in the future (unlike creation). Useful to extend a promotion window.

---

## Seller-Side Flow

### Notifications Page (`/notifications`)

**Component**: `NotificationsPage` (`src/pages/notifications/index.tsx`)

- Calls `GET /broadcast-notifications?category=X` — returns all non-expired notifications for the seller.
- **Sort**: unread first; within each group, newest `sent_at` first.
- **Category filter tabs**: All / Pricing / Inventory / Zambeel Updates / Payments.
- **Expand to read**: clicking a notification card marks it read via `PATCH /broadcast-notifications/:recipientId/read`.
- **Mark all as read**: confirmation modal → `PATCH /broadcast-notifications/read-all`.
- Unread count synced to the global Zustand store (`useBroadcastNotificationStore`) which drives the bell badge.

### Notification Bell (Header)

- `GET /broadcast-notifications/unread-count` → `{count}`.
- Count stored in `useBroadcastNotificationStore`.
- Real-time update: socket event `broadcast_notification_received` increments the count immediately without a polling cycle.

### Real-Time Socket Delivery

When admin sends a notification, the backend calls:
```js
io.to(`user_${userId}`).emit("broadcast_notification_received", payload)
```
Payload: `{notification_id, title, message, category, image_url, expiry_at, sent_at}`.

The seller's socket connection joins `user_<id>` room on login. The frontend (`useBroadcastNotificationStore` + socket listener) increments unread count and appends the notification to the list if the seller is on `/notifications`.

---

## Validation Rules (Enforced in Service)

| Rule | Error |
|------|-------|
| Category not in `["pricing","inventory","zambeel_updates","payments"]` | 400 `Invalid category` |
| `expiry_at` is not a valid future date | 400 `Expiry date must be in the future when sending` |
| Both `send_to_all` and `recipient_user_ids` provided | 400 `Cannot send to both...` |
| `recipient_user_ids` empty (not send_to_all) | 400 `At least one recipient is required` |
| PIN invalid for `send_to_all` | 403 `Incorrect PIN` |
| Any `recipient_user_ids` not active sellers | 400 `User not found or is not an active seller` |
| CSV row validation: any row fails | 400 whole file rejected; per-row errors in response |

---

## Frontend Admin Page — `/orders-management/broadcast-notifications`

**Component**: `BroadcastNotificationsPage` (`src/pages/orders-management/broadcast-notifications/index.tsx`)

Three-tab layout:

| Tab | Component | Purpose |
|-----|-----------|---------|
| **Compose** (`compose`) | `ComposeTab` | Manual send: select sellers via search autocomplete, fill title/message/category/expiry, optional image |
| **CSV** (`csv`) | `CsvTab` | Download CSV template, upload filled CSV, validate, then send |
| **Sent Log** (`sent-log`) | `SentLogTab` | Paginated sent log; click row to view per-recipient read status |

**"All Sellers" flow in Compose**:
- Toggle to "Send to all sellers" mode.
- Seller search is hidden; PIN input appears.
- 6-digit PIN required (set in backend config as `broadcast.allSellersPin`).

---

## Key Files

| File | Purpose |
|------|---------|
| `routes/broadcastNotificationAdminRoutes.js` | 7 admin routes |
| `routes/broadcastNotificationRoutes.js` | 4 seller routes |
| `controllers/broadcastNotificationController.js` | `adminController` + `sellerController` |
| `helpers/broadcastNotificationService.js` | All business logic (send, validate, query) |
| `constants/broadcastNotification.constants.js` | Categories, send modes, socket event name, limits |
| `models/BroadcastNotification.js` | Model with static helpers (`createWithRecipients`, `getActiveSellerIds`, etc.) |
| `src/pages/orders-management/broadcast-notifications/` | Admin page + 3 tab components |
| `src/pages/notifications/index.tsx` | Seller notifications page |
| `src/hooks/useNotifications.ts` | Data fetching + read/mark logic for seller page |
| `src/store/useBroadcastNotificationStore.ts` | Zustand store: global unread count + socket sync |
| `src/api/broadcastNotifications.ts` | Axios calls for all 11 endpoints |
| `src/constants/broadcastNotification.constants.ts` | FE category labels + tab config |
