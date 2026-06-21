# Notifications Domain — Business Logic

## What This Domain Does

The notifications domain covers two distinct systems:

1. **Broadcast Notifications** — admin-authored messages pushed to a targeted set of seller users. Admins can send to selected sellers, all sellers at once (PIN-protected), or via CSV upload. Sellers see their notification inbox, mark items read, and filter by category. **See also**: `knowledge/notifications/broadcast.md` for frontend page detail, comparison with standard notifications, and Socket.IO delivery specifics.

2. **Customer.io Integration** — server-side event tracking for user lifecycle events (signup, profile update). Fires silently in the background; never blocks the main request flow.

Both systems deliver messages in real-time via Socket.IO in addition to the persistent database records.

---

## Broadcast Notifications — Endpoints

### Admin Routes (`/admin/broadcast-notifications`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/broadcast-notifications/sellers/search` | Admin only | Search active sellers by `email`, `phone`, or `user_id` to build a recipient list. Paginated; max 25/page. |
| POST | `/admin/broadcast-notifications/manual` | Admin only | Send a notification to selected sellers OR all sellers (with PIN). |
| POST | `/admin/broadcast-notifications/csv/validate` | Admin only | Validate CSV rows before sending. Returns per-row errors. |
| POST | `/admin/broadcast-notifications/csv` | Admin only | Send individualized notifications from a CSV (one notification per row/user). |
| GET | `/admin/broadcast-notifications` | Admin/Agent (verifyUser) | Paginated log of all sent notifications with recipient count and read stats. |
| GET | `/admin/broadcast-notifications/:id` | Admin/Agent (verifyUser) | Detail view of one notification including paginated recipient list and read/unread counts. |
| PATCH | `/admin/broadcast-notifications/:id/expiry` | Admin only | Update expiry date of a notification (makes it visible longer or expire sooner). |

### Seller Routes (`/broadcast-notifications`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/broadcast-notifications/unread-count` | Seller (verifySeller) | Returns integer count of unread, non-expired notifications. |
| GET | `/broadcast-notifications` | Seller (verifySeller) | List all active (non-expired) notifications for the seller. Optional `?category=` filter. Sorted: unread first, then newest. |
| PATCH | `/broadcast-notifications/read-all` | Seller (verifySeller) | Mark all unread notifications as read. Returns `marked_count`. |
| PATCH | `/broadcast-notifications/:recipientId/read` | Seller (verifySeller) | Mark a single notification as read by `recipientId` (not notification id). |

---

## Business Logic: Sending a Manual Notification (POST /manual)

1. Validate `category` is one of: `pricing`, `inventory`, `zambeel_updates`, `payments`.
2. Validate `expiry_at` is a future date.
3. `send_to_all` and `recipient_user_ids` are mutually exclusive — passing both is a 400 error.
4. If `send_to_all: true`:
   - Verify the provided `pin` matches the configured `broadcast.allSellersPin` (403 if wrong).
   - Fetch IDs of all active sellers (`role` in SELLER_PORTAL_ROLES, `archived: false`, `status: 'Active'`).
   - `send_mode` set to `manual_all`.
5. If `send_to_all: false`:
   - Validate each `recipient_user_ids` entry is an active seller; return 400 with invalid IDs listed.
   - `send_mode` set to `manual_selected`.
6. In a single transaction: create `BroadcastNotification` row and bulk-insert `BroadcastNotificationRecipient` rows (one per recipient, `read_at: null`).
7. After commit: emit Socket.IO `broadcast_notification_received` event to each recipient's room (`user_<userId>`).

## Business Logic: Sending via CSV (POST /csv)

1. Validate all rows first (same rules: valid `user_id`, `title` ≤ `TITLE_MAX_LENGTH`, `message` ≤ `CSV_MESSAGE_MAX_LENGTH`, valid `category`, future `expiry_date`). All rows must pass; any failure aborts the whole batch.
2. Verify all `user_id` values are active sellers.
3. In a single transaction: for each row, create a separate `BroadcastNotification` + one `BroadcastNotificationRecipient`.
4. After commit: emit real-time event per notification per recipient.

Note: CSV sends create one notification record per row (not one shared notification), so each seller gets a uniquely crafted message.

## Business Logic: Seller Inbox

- Only notifications where `expiry_at > now` are visible.
- Optional `?category=` filter (pass `all` or omit to show every category).
- Sorting: unread first (`is_read: false`), then by `sent_at` descending.
- `read_at` is `null` when unread; set to a timestamp when marked read.
- Unread count ignores expired notifications.

## Business Logic: Marking Read

- `PATCH /:recipientId/read` — marks the specific `BroadcastNotificationRecipient` row read. Validates `fk_user_id === req.user.id` to prevent cross-user reads. Idempotent — already-read items are returned as-is.
- `PATCH /read-all` — fetches all `read_at: null` recipients for the user where the notification has not expired, sets `read_at` on each, returns the count.

---

## Customer.io Integration

File: `services/customerioService.js`

Uses `customerio-node` SDK in TrackClient mode (US region). Credentials from `config.customerio.CUSTOMERIO_SITE_ID` and `config.customerio.CUSTOMERIO_API_KEY`.

**Important**: all Customer.io calls are fire-and-forget — errors are caught and logged but never propagate to callers.

### Exported functions

| Function | Trigger | What it does |
|----------|---------|--------------|
| `trackUserSignup(user)` | Called at user registration | Calls `identify` with email, username, phone, country, provider, role, created_at, promo_code (if set); then tracks `user_signed_up` event |
| `updateUserProfile(user)` | Called on profile update | Calls `identify` with updated attributes; tracks `profile_updated` event |
| `identifyUser(userId, attributes)` | Internal | Creates/updates user in Customer.io using email as the identifier |
| `trackEvent(userId, eventName, data)` | Internal | Fires a named event against a user |

User identifier is always the user's `email` (or `firebase_uid` as fallback on signup). Dates are converted to Unix timestamps (seconds) before sending.

---

## Key Models

### `broadcast_notifications` table

| Field | Type | Notes |
|-------|------|-------|
| `id` | INT PK | Auto-increment |
| `title` | STRING(255) | Required |
| `message` | TEXT | Required |
| `category` | ENUM | `pricing` / `inventory` / `zambeel_updates` / `payments` |
| `image_url` | STRING(512) | Nullable; optional image attachment |
| `expiry_at` | DATE | Required; must be future; controls visibility |
| `send_mode` | ENUM | `manual_selected` / `manual_all` / `csv` |
| `fk_created_by` | INT | FK → users (admin who sent it) |
| `sent_at` | DATE | Timestamp of send |

### `broadcast_notification_recipients` table

| Field | Type | Notes |
|-------|------|-------|
| `id` | INT PK | Auto-increment |
| `fk_notification_id` | INT | FK → broadcast_notifications |
| `fk_user_id` | INT | FK → users (seller recipient) |
| `read_at` | DATE | Nullable; `null` = unread |

---

## Interactions with Other Domains

- **Users** — recipients are validated as active sellers (`SELLER_PORTAL_ROLES`, `archived: false`, `status: 'Active'`). Admin routes use `verifyAdminOnly`; seller routes use `verifySeller`.
- **Socket.IO** — real-time delivery via `broadcast_notification_received` event to room `user_<userId>` immediately after DB commit.
- **Customer.io** — external SaaS event tracking. Triggered by auth domain (signup) and user-profile domain (profile update). No inbound webhooks in this codebase.
- **Config** — `broadcast.allSellersPin` must be set to enable `send_to_all`. `customerio.CUSTOMERIO_SITE_ID` and `CUSTOMERIO_API_KEY` must be set for Customer.io to function; without them it silently no-ops.

---

## Important Constraints

- `send_to_all` requires a PIN (`broadcast.allSellersPin` from config). Sending without the correct PIN returns 403.
- `send_to_all` and `recipient_user_ids` cannot both be provided in one request.
- CSV send validates all rows atomically — one bad row blocks the entire batch.
- Expired notifications (`expiry_at <= now`) are invisible to sellers in their inbox and excluded from unread counts, but remain in the admin sent-log.
- `PATCH /:recipientId/read` uses the `BroadcastNotificationRecipient.id` (not the notification id) and verifies `fk_user_id` matches the authenticated seller.
- Pagination for admin sent-log: default 20/page, max 100/page. For notification detail (recipient list): default 10/page, max 100/page. For seller search: max 25/page.
