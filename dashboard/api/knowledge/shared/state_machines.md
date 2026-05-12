# Shared — State Machines & Lifecycle Flows

---

## Order Status Lifecycle

```
[External source creates order]
           ↓
       "Received"
           ↓ (auto or manual push)
  "Confirmation Pending"
    substatus: "Pending Reseller Submission"  |  tag: "Awaiting Push To Zambeel"
    substatus: "Confirmation in Process"      |  tag: "Message Sent" / "Send Message"
           ↓ (approve action)
        "Approved"
    substatus: "Checking Inventory For Dispatching"  |  tag: "Checking Inventory"
    substatus: "Inventory In Transit"                |  tag: "Calculating Dispatching Time"
           ↓
  "Dispatching in Process"
           ↓
      "In Delivery"  (displayed as "Shipped" in UI)
           ↓              ↓
      "Delivered"    "Undelivered"
                          ↓
                   "Return in Transit"
                          ↓
                       "Return"
```

**Cancelled** can be reached from: Confirmation Pending, Approved (via cancel action).

**Revert to Confirmation Pending** is possible from Approved (via `PUT /orders/revert-to-confirmation-pending`).

---

## Dispatch Batch / Tracking Status Machine

```
[Batch created]
      ↓
    "New"
      ↓ (generate-tracking-ids triggered)
 "Generating"
      ↓           ↓
 "Generated"   "Partial"  (some tracking IDs failed)
      ↓           ↓
   "Failed"    retry possible
```

Documents can only be downloaded when status is `"Generated"`.

---

## Agency Application Lifecycle

```
[Seller submits agency application]
              ↓
           "Pending"
         ↙     ↓     ↘
  "Approved"  "On Hold"  "Rejected"
      ↓
  "Licensed" (active agency — can invite merchants)
      ↓
  "Revoked"  ← admin action
```

Admin transitions:
- `approve` — Pending → Approved
- `hold` — Pending → On Hold
- `reject` — Pending → Rejected
- `revoke` — Approved → Revoked
- `revert_to_pending` — On Hold → Pending

Agency IDs (`ZMB-AG-XXXXXX`) are assigned at approval time.

---

## Agency Merchant Connection States

```
[Agency invites or merchant connects]
              ↓
          "pending"
         ↙     ↘
  "accepted"  "rejected"
      ↓
  "disconnected" ← disconnect action
      ↓
  "reconnected" ← reconnect action
```

---

## Agency Team Member States

```
[Team invite sent]
       ↓
   "invited"
    ↙    ↘
"accepted" "declined"
```

---

## Purchase Order (IMS) Lifecycle

```
[Create PO]
    ↓
 "Draft" / "Pending"
    ↓ (submit to warehouse)
 "Submitted"
    ↓ (items arrive)
 "Received"
```

Actions:
- `PUT /purchase-orders/:poId/mark-as-submitted` — Draft → Submitted
- `PUT /purchase-orders/:poId/mark-as-received` — Submitted → Received

---

## Return Order Lifecycle

```
[Seller creates return order]
         ↓
      "Created"
         ↓
    "Processing"
         ↓
     "Completed"
```

---

## User Subscription Plan

```
[New user]
     ↓
  "Free"
     ↓ (payment via PayTabs or Shopify billing)
  "Gold"
     ↓ (expiry)
  "Free"
```

Plan state: `useGoldPlanStore.isGoldPlanActive` + `planExpiryTime`.

---

## Store Integration / Webhook States

Integrations are connected once and then receive webhooks. The connection can be:
- **Connected** — active, receiving webhooks
- **Disconnected** — manually unlinked by seller

Platforms: Shopify, EasyOrder, LightFunnels, Salla, YouCan, Smartlane, Wati, iMile, Tawseel

---

## Session / Auth State

```
[No session]
     ↓ (Google/email login via Firebase)
[Firebase authenticated]
     ↓ (POST /login with idToken)
[JWT issued, user record fetched]
     ↓
[Logged in — role-based redirect]
 Admin/Agent → /orders-management/dashboard
 Seller → /get-started
 Agency → /get-started
     ↓ (401 response / expiry)
[Session expired → handleSessionExpiration() → /login]
```

Session persistence: `useAuthStore` with key `"auth-storage"` in localStorage.

---

## Inventory Movement Transaction States

Inventory movements created via `POST /inventory-movements/transactions` go through:
```
[Created]
    ↓ (PUT /inventory-movements/transactions/:id/receive)
[Received]
```
