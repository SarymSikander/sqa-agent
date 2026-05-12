# Seller Portal — Step-by-Step User Flows

## Flow 1: Seller Login

1. Navigate to `/login`
2. Enter email + password
3. Firebase `signInWithEmailAndPassword` → get ID token
4. `POST /login` with `{idToken}` → receives JWT
5. Zustand `useAuthStore` saves token and role
6. `RootRedirect`: Seller/Agency → `/get-started` (first time) or `/dashboard`

**Expected URL after login:** `/get-started` or `/dashboard`

---

## Flow 2: Seller Registration

1. Navigate to `/register`
2. Fill form:
   - Username (required)
   - Email (required)
   - Password (required, Firebase-validated)
   - Confirm Password (must match)
   - Phone + Country Code
   - Country (from COUNTRIES list)
   - Promo Code (optional)
3. OR: click Google/Apple social sign-in
4. Firebase `createUserWithEmailAndPassword` → sends verification email
5. `POST /signUp` with `{username, email, firebase_uid, phone_number, country, provider: 'Email', role: 'Seller'}`
6. User sees message to verify email
7. User clicks verification link → `/verify-email` → `GET /verify-email`
8. Redirected to `/login`

---

## Flow 3: Send Order to Zambeel

1. Navigate to `/orders`
2. Unprocessed orders appear in "Your Store Orders" section
3. Select one or more orders via checkbox
4. Click `Send To Zambeel`
5. System validates each order:
   - Country must be one of: Saudi Arabia, Qatar, Kuwait, UAE, Pakistan, Oman, Bahrain, Iraq
   - Phone number must be present and numeric
   - Order items must have valid SKUs
   - Gold subscription required if applicable
6. Success: "{{count}} order processed successfully to Zambeel."
7. Orders move to "Orders with Zambeel" section with status `Confirmation Pending`

---

## Flow 4: Delete Unprocessed Order

1. Navigate to `/orders`
2. Select order(s) in "Your Store Orders"
3. Click `Delete` / `Delete Order` / `Delete Orders`
4. Confirm deletion (window.confirm or modal)
5. API: `DELETE /orders/delete/:orderId`
6. Success: "{{count}} order deleted successfully"
7. Order removed from table

---

## Flow 5: Create Support Ticket

**Step 1 — Select Store:**
1. Navigate to `/ticketing`
2. Click `Create New Ticket`
3. Modal/wizard opens at "Select Store" step
4. Choose store from dropdown or search

**Step 2 — Category & Type:**
5. Select category (6 options)
6. Sub-category list populates based on category
7. Select sub-category
8. If category `requiresOrderId=true` → must search and select an order

**Step 3 — Details & Files:**
9. Enter description (min 10, max 2000 chars)
10. Optionally upload image (max 3 files, max 5MB each, images only)
    - `POST /s3/generate-presigned-url` → upload to S3 → save URL

**Step 4 — Review:**
11. Review all selections
12. Click `Submit` → `POST /tickets`
13. Success screen: "Ticket Created Successfully!"
14. Ticket appears in list with status `Pending`

---

## Flow 6: View Ticket Detail and Reply

1. Navigate to `/ticketing`
2. Find ticket in table (status: Pending/In Progress/Awaiting Seller Action)
3. Click on ticket row or View button
4. Ticket detail opens: category, sub-category, description, attachment, status timeline
5. Add comment: type in comment input → submit → `POST /comments`
6. If status is `Awaiting Seller Action`, seller reply moves ticket back to `In Progress`

---

## Flow 7: Connect Shopify Store

1. Navigate to `/stores/integration`
2. Click `Connect Shopify`
3. Enter Shopify shop URL
4. System validates: `GET /shopify/shop?shop=X`
5. Check if already connected: `GET /shopify/check-store-exists`
6. `GET /shopify/auth?shop=X` → redirected to Shopify OAuth
7. Shopify redirects back with OAuth code
8. Backend exchanges code → `POST /shopify/bind-store`
9. Store appears in store list

---

## Flow 8: Create Manual Store

1. Navigate to `/stores/integration`
2. Click `Create Manual Store`
3. Select platform sub-type (Facebook Marketplace, Amazon, etc.)
4. Enter store nick name (must be unique — `GET /store/check-name`)
   - Error: "Store Nick name already exists. Please choose a different name."
5. Submit → `POST /store/create/storeManually`
6. Store appears in store list

---

## Flow 9: Add Bank Account

1. Navigate to `/settings`
2. Click `Add Account` or payment type button
3. Select payment type: `Bank Account` | `USDT` | `PayPal`

**For Bank Account:**
- Account Title, Bank Name, IBAN (country-specific length)
- Swift code (optional for some countries), FedWire (US only)
- Submit → `POST /accounts`

**For USDT:**
- Exchange Name (required), Exchange ID (min 3), Wallet Address
- First Name, Last Name, Country
- Submit → `POST /accounts`

4. Account appears in list
5. Click `Set as Primary` to set as default withdrawal account

---

## Flow 10: View Invoice

1. Navigate to `/my-invoices`
2. List of invoices from Zambeel
3. Green pulse badge in sidebar indicates new invoices
4. Click download button → `GET /invoices/invoices/download/:id`
5. PDF opens/downloads

---

## Flow 11: Bulk CSV Order Upload

1. Navigate to `/orders`
2. Click `Bulk Upload` button (or similar)
3. Download CSV template
4. Fill CSV rows with required fields:
   - order_reference_id, customer_name, Address, delivery_city, delivery_country,
   - customer_phone_number, product_sku, Quantity, price, shipping_charges,
   - Discount, total_amount, currency, payment_mode
5. Upload CSV → `POST /orders/bulk-order-upload`
6. Response: `successCount`, `skippedOrders`, `totalProcessed`

---

## Flow 12: View Orders Analytics

1. Navigate to `/orders-analytics`
2. Charts load showing order performance over time
3. Status breakdown and trend analysis
4. API: `GET /orders/order-analytics`

---

## Flow 13: Update Profile

1. Navigate to `/profile`
2. Edit username, phone (format: +XXXXXXXXXX), country, promo code
3. Optionally set sidebar_color or button_color (hex format: #RRGGBB)
4. Submit → `PUT /user/profile`
5. Profile updates reflected in UI

---

## Ticket Status Lifecycle

```
Pending
    ↓ (admin picks up)
In Progress
    ↓ (admin asks seller)
Awaiting Seller Action
    ↓ (seller replies)
In Progress
    ↓ (admin resolves)
Resolved
```
