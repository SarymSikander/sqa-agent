# Shared — Backend API Endpoints

## Base
- All routes mounted at `/api` prefix
- Backend runs on: `http://localhost:3000` (local)
- Staging: `https://staging.myzambeel.com/api` (approximately)

## Authentication Headers
- `Authorization: Bearer <JWT>` on all protected routes
- `x-agency-context-store-id: <storeId>` for agency proxy mode

## Middleware Reference
| Middleware | Allowed Roles |
|-----------|--------------|
| `verifySeller` | Seller, Agency |
| `verifyUser` | Any authenticated user |
| `verifyAdminOnly` | Admin only |
| `verifyAdminAndSeller` | Admin, Seller, Agency |
| `verifyAdminAndAgent` | Admin, Agent |
| `verifyAgentAdminAndSeller` | Agent, Admin, Seller, Agency |
| `verifyJWTWithRoles(['Seller','Agency'])` | Seller, Agency (agency endpoints) |

---

## Authentication & User

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/signUp` | None | Create new user |
| POST | `/login` | None | Login with Firebase ID token → returns JWT |
| GET | `/auth/check-email` | None | Check if email exists |
| GET | `/verify-email` | None | Mark email as verified |
| PUT | `/user/profile` | verifySeller | Update user profile |
| POST | `/user/accept-terms` | verifySeller | Accept terms |
| GET | `/agents` | None | Get all agents |
| GET | `/teams` | None | Get all teams |
| GET | `/dashboard/data` | verifySeller | Seller dashboard KPIs |

---

## Orders

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/orders` | verifyUser | Get orders (with filters) |
| GET | `/orders/status-counts` | verifyUser | Get order counts by status |
| GET | `/orders/order-analytics` | verifySeller | Order analytics data |
| GET | `/orders/seller-orders` | verifySeller | Seller's own orders (paginated) |
| GET | `/orders/proccessedOrders` | verifySeller | Processed orders list |
| GET | `/orders/orderDetails/:orderId` | verifyAgentAdminAndSeller | Full order modal details |
| GET | `/orders/:orderId/logs` | verifyAgentAdminAndSeller | Order activity logs |
| GET | `/orders/:orderId/conversation` | verifyAgentAdminAndSeller | WhatsApp conversation |
| GET | `/orders/duplicates/:orderId` | verifyUser | Duplicate orders |
| GET | `/orders/couriers` | verifyUser | Available couriers |
| GET | `/orders/vendors` | verifyUser | Available vendors |
| GET | `/orders/batch-ids` | verifyUser | Batch IDs for filters |
| GET | `/orders/tags` | verifyUser | Order tags |
| GET | `/orders/remarks` | verifyUser | All NDR remarks |
| GET | `/orders/batches/dip` | verifyUser | DIP batches |
| GET | `/orders/dispatch-batches` | verifyUser | Dispatch batches (with filters) |
| GET | `/orders/tracking-generation-report` | verifyUser | Tracking generation CSV report |
| GET | `/orders/sub-statuses` | None | Sub-statuses by status name |
| POST | `/orders/bulk-order-upload` | verifyUser | Bulk CSV order upload |
| POST | `/orders/bulk-vendor-courier-upload` | verifyUser | Bulk vendor/courier CSV upload |
| POST | `/orders/add-product` | verifyAgentAdminAndSeller | Add product to order |
| POST | `/orders/assign-courier` | verifyUser | Assign courier to orders |
| POST | `/orders/check-availability` | verifyUser | Check order availability |
| POST | `/orders/variants/search` | verifyAgentAdminAndSeller | Search variant by SKU |
| POST | `/orders/variants/price` | verifyAgentAdminAndSeller | Get variant price |
| POST | `/orders/sub-statuses/bulk-update` | verifyAgentAdminAndSeller | Bulk update sub-statuses |
| POST | `/orders/ndr-remarks` | verifyUser | Bulk update NDR remarks |
| POST | `/orders/download-awbs` | verifyUser | Download AWB files |
| POST | `/orders/download-packing-list` | verifyUser | Download packing list |
| POST | `/orders/generate-batches` | verifyUser | Generate dispatch batches |
| POST | `/orders/generate-tracking-ids` | verifyUser | Generate tracking IDs |
| POST | `/orders/generate-documents` | verifyUser | Generate batch documents |
| POST | `/orders/courier-assignment/report` | verifyUser | Download courier assignment report |
| POST | `/orders/clear-courier-assignment` | verifyAgentAdminAndSeller | Clear courier assignment |
| POST | `/orders/uploadOrderCSV` | verifySeller | Single order CSV upload |
| PUT | `/orders/bulk-csv-update` | verifyUser | Bulk CSV update orders |
| PUT | `/orders/revert-to-confirmation-pending` | verifyUser | Revert orders to Confirmation Pending |
| PUT | `/orders/approve-status/bulk` | verifyAgentAdminAndSeller | Bulk approve/cancel orders |
| PUT | `/orders/:orderId` | verifyAgentAdminAndSeller | Update order metadata |
| PUT | `/orders/:orderId/approve-status` | verifyAgentAdminAndSeller | Update single order status |
| PUT | `/orders/:orderId/status` | verifyAdminAndSellerWithAgencyContext | Update order status (from Received) |
| PUT | `/orders/:orderId/edit` | verifyAgentAdminAndSeller | Edit order fields |
| PUT | `/orders/:orderId/order-product-variants/:opvId` | verifyAgentAdminAndSeller | Update variant quantity/price |
| PUT | `/orders/customers/:customerId` | verifyAgentAdminAndSeller | Update customer info |
| PUT | `/orders/address/:orderId` | verifyAdminAndSeller | Update order address |
| DELETE | `/orders/delete/:orderId` | verifySeller | Delete unprocessed order |
| DELETE | `/orders/:orderId/delete-product/:variantId` | verifyAgentAdminAndSeller | Remove product from order |

---

## Tags

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/tags/createTag` | verifyUser | Create tag |
| GET | `/tags` | verifyAdminAndSeller | Get all tags |
| PUT | `/tags/:id` | verifyUser | Update tag |
| DELETE | `/tags/:id` | verifyUser | Soft delete tag |
| GET | `/tags/statuses` | verifyAdminAndSeller | Get all order statuses |
| GET | `/tags/substatuses/:statusId` | verifyAdminAndSeller | Get sub-statuses by status ID |

---

## Products

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/products` | None | Get all products |
| GET | `/products/gold-products` | verifySeller | Get gold products (Gold plan required) |
| GET | `/products/gold-product/:id` | None | Get single gold product |
| GET | `/products/featured` | None | Get featured products |
| POST | `/products/featured` | verifySeller | Update featured products |

---

## Purchase Orders

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/purchase-orders` | verifyUser | List purchase orders |
| POST | `/purchase-orders` | verifyUser | Create purchase order |
| GET | `/purchase-orders/:poId` | verifyUser | Get single PO |
| PUT | `/purchase-orders/:poId` | verifyUser | Update PO |
| GET | `/purchase-orders/countries` | verifyAgentAdminAndSeller | Get countries |
| GET | `/purchase-orders/warehouses/country/:countryId` | verifyUser | Get warehouses by country |
| GET | `/purchase-orders/warehouses/:warehouseId/search` | verifyUser | Search SKU in warehouse |
| PUT | `/purchase-orders/:poId/mark-as-received` | verifyUser | Mark PO as received |
| PUT | `/purchase-orders/:poId/mark-as-submitted` | verifyUser | Submit PO to warehouse |
| POST | `/purchase-orders/warehouses/:warehouseId/validate-variants` | verifyUser | Validate CSV variants |

---

## Return Orders

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/return-orders` | verifyUser | List return orders |
| GET | `/return-orders/:returnId` | verifyUser | Get single return order |
| POST | `/return-orders` | verifyUser | Create return order |

---

## Inventory (Seller)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/inventory/seller-inventory` | verifySeller | Get seller inventory |
| GET | `/inventory/seller-inventory/export` | verifySeller | Export inventory |
| GET | `/inventory/purchase-order/:variantId` | verifySeller | Get POs for variant |
| GET | `/inventory/purchase-order/orders/:variantId` | verifySeller | Get orders for variant |
| GET | `/inventory/inventory-movements/:variantId` | verifySeller | Get movements for variant |

---

## Inventory Movements (Admin)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/inventory-movements/transactions` | verifyAdminOnly | Create inventory transaction |
| POST | `/inventory-movements/damaged-bin` | verifyAdminOnly | Create damaged bin movement |
| POST | `/inventory-movements/find-variant` | verifyAdminOnly | Find variant by SKU in warehouse |
| GET | `/inventory-movements/warehouses` | verifyAdminOnly | Get all warehouses |
| GET | `/inventory-movements/movements` | verifyAdminOnly | List inventory movements |
| PUT | `/inventory-movements/transactions/:id/receive` | verifyAdminOnly | Receive movement quantity |

---

## Payments

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/payments/create` | verifySeller | Create PayTabs payment |
| POST | `/payments/callback` | None | PayTabs webhook callback |
| POST | `/payments/verify` | verifySeller | Verify payment |
| GET | `/payments/checkUserSubscription` | verifySeller | Check gold subscription status |

---

## Bank Accounts

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/accounts` | verifySeller | Create bank account |
| GET | `/accounts/:userId` | verifySeller | Get user accounts |
| GET | `/accounts/:userId/all` | verifySeller | Get all user accounts |
| PUT | `/accounts/:id` | verifySeller | Update account |
| DELETE | `/accounts/:id` | verifySeller | Delete account |
| PATCH | `/accounts/:id/set-primary` | verifySeller | Set primary account |
| GET | `/accounts/myaccount/:id` | verifySeller | Get account by ID |
| GET | `/accounts/store/:storeId` | verifySeller | Get store bank accounts |

---

## Stores

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/store` | verifyAdminAndSellerWithAgencyContext | Get all stores |
| GET | `/store/:id` | verifyAdminAndSellerWithAgencyContext | Get store by ID |
| PUT | `/store/:id` | verifyAdminAndSellerWithAgencyContext | Update store |
| DELETE | `/store/:id` | verifyAdminAndSellerWithAgencyContext | Delete store |
| GET | `/store/user/:userId` | verifyAdminAndSellerWithAgencyContext | Get stores by user |
| POST | `/store/check-name` | verifyAdminAndSellerWithAgencyContext | Check store name availability |
| POST | `/store/create/storeManually` | verifyAdminAndSellerWithAgencyContext | Create manual store |
| GET | `/store-names` | None | Get all store names |

---

## Tickets

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/tickets` | verifyJWT | Get seller tickets |
| POST | `/tickets` | verifyJWT | Create seller ticket |
| POST | `/tickets/admin` | verifyJWT | Create admin ticket |
| GET | `/tickets/admin` | verifyJWT | Get admin tickets |
| GET | `/tickets/search-orders` | verifyJWT | Search orders for ticket |
| GET | `/tickets/user-stores` | verifyJWT | Get user's stores |
| GET | `/tickets/find-store-order` | verifyJWT | Find order in store |
| GET | `/tickets/search/stores` | verifyJWT | Search stores |
| GET | `/tickets/:ticket_id` | verifyJWT | Get ticket by ID |
| PUT | `/tickets/:ticket_id` | verifyJWT | Update ticket |
| GET | `/tickets/:ticket_id/logs` | verifyJWT | Get ticket audit logs |

---

## Comments

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/comments` | verifyJWT | Create comment on ticket |
| GET | `/comments/ticket/:ticketId` | verifyJWT | Get all comments for ticket |

---

## Invoices

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/invoices` | verifyUser | Create invoices |
| PUT | `/invoices` | verifyUser | Update invoices |
| POST | `/invoices/check-stores` | verifyUser | Check stores exist (pre-upload) |
| GET | `/invoices/:storeId` | verifySeller | Get invoices for store |
| GET | `/invoices/invoices/download/:id` | None | Download invoice PDF |

---

## Agency — Agency-Side Routes (`/api/agency/*`)

> Source: source code (`/agency/*`) + PRD spec (`/api/agency/*`). Both path forms may appear depending on API base prefix.

| Method | Path (source) | PRD Path | Purpose |
|--------|--------------|----------|---------|
| POST | `/agency/register` | `/api/agency/register` | Step 1: Submit agency application |
| POST | `/agency/register/complete` | — | Step 2: Complete registration (upload confirm) |
| POST | — | `/api/agency/resubmit` | Resubmit documents after OnHold |
| GET | `/agency/cities` | — | Get cities list for a country |
| GET | `/agency/me` | `/api/agency/status` | Get current user's agency status |
| PUT | `/agency/settings` | `/api/agency/settings` | Update agency profile |
| GET | `/agency/dashboard` | `/api/agency/dashboard?date_from&date_to` | Dashboard summary + store rows |
| GET | `/agency/merchants` | `/api/agency/merchants?status&page&limit` | List merchant connections |
| PATCH | `/agency/merchants/:id/status` | — | Accept/reject/disconnect (combined, source) |
| POST | — | `/api/agency/merchants/:connectionId/accept` | Accept merchant request (PRD) |
| POST | — | `/api/agency/merchants/:connectionId/reject` | Reject merchant request (PRD) |
| GET | — | `/api/agency/merchants/:merchantId/summary` | Merchant drawer commission data (60s stale) |
| GET | `/agency/commission` | `/api/agency/commission?date_from&date_to` | Commission records + summary |
| GET | `/agency/invoices` | `/api/agency/invoices?status` | Agency invoices list |
| GET | `/agency/invoices/:id/download` | — | Download agency invoice PDF (Bearer token) |
| GET | `/agency/team-members` | `/api/agency/team` | List team members |
| POST | `/agency/team-members/invite` | `/api/agency/team` | Invite (add) team member |
| DELETE | `/agency/team-members/:id` | `/api/agency/team/:id` | Remove team member (soft-delete) |
| POST | `/agency/team-members/invite/preview` | — | Preview invite token (get agency name) |
| POST | `/agency/team-members/accept` | — | Accept team invite |
| POST | `/agency/team-members/decline` | — | Decline team invite |

## Agency — Merchant-Side Routes (`/api/merchant/agency/*`)

> These routes are used by the seller (merchant) to manage their agency connection from their Profile page.

| Method | Path (source) | PRD Path | Purpose |
|--------|--------------|----------|---------|
| POST | `/agency/connect` | `/api/merchant/agency/connect` | Send connection request to agency |
| GET | `/agency/my-connection` | `/api/merchant/agency/status` | Get merchant's agency connection status |
| DELETE | — | `/api/merchant/agency/request` | Cancel pending connection request |
| POST | `/agency/my-connection/disconnect` | `/api/merchant/agency/disconnect` | Disconnect from agency (with reason) |

---

## Agency Admin (Admin Only)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/agency-registrations/applications` | List all agency applications |
| GET | `/admin/agency-registrations/applications/:id` | Get single application |
| GET | `/admin/agency-registrations/commission-models` | List commission models (simple) |
| GET | `/admin/agency-registrations/commission-models/manage` | List models with rules |
| POST | `/admin/agency-registrations/commission-models` | Create commission model |
| PUT | `/admin/agency-registrations/commission-models/:id` | Update commission model |
| POST | `/admin/agency-registrations/applications/:id/approve` | Approve application |
| POST | `/admin/agency-registrations/applications/:id/hold` | Put on hold |
| POST | `/admin/agency-registrations/applications/:id/reject` | Reject application |
| POST | `/admin/agency-registrations/applications/:id/revert-to-pending` | Revert to pending |
| POST | `/admin/agency-registrations/applications/:id/revoke` | Revoke agency license |

---

## Gold Subscription Admin

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/gold-subscriptions/users/gold` | List gold users |
| GET | `/admin/gold-subscriptions/users` | Search all users |
| GET | `/admin/gold-subscriptions/users/:userId` | Get user details |
| POST | `/admin/gold-subscriptions/give` | Give gold access |
| POST | `/admin/gold-subscriptions/extend` | Extend gold access |
| POST | `/admin/gold-subscriptions/remove` | Remove gold access |

---

## Store Platform Integrations

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/shopify/auth` | Shopify OAuth initiation |
| GET | `/shopify/check-store-exists` | Check if Shopify store already connected |
| POST | `/shopify/bind-store` | Bind Shopify store |
| GET | `/shopify/checkUser` | Check Shopify user login |
| DELETE | `/shopify/webhooks/delete` | Remove Shopify webhooks |
| GET | `/salla/auth` | Salla OAuth |
| DELETE | `/salla/disconnect` | Disconnect Salla |
| GET | `/youcan/auth` | YouCan OAuth |
| GET | `/youcan/store-info` | YouCan store info |
| POST | `/youcan/disconnect` | Disconnect YouCan |
| DELETE | `/youcan/webhooks/delete` | Remove YouCan webhooks |
| GET | `/easyorders/install-link` | EasyOrder install link |
| POST | `/easyorders/disconnect` | Disconnect EasyOrder |
| GET | `/lightfunnels/auth` | LightFunnels OAuth |
| DELETE | `/lightfunnels/webhooks/delete` | Remove LightFunnels webhooks |

---

## S3

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/s3/generate-presigned-url` | Get S3 presigned upload URL |

---

## Ticker Config

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/ticker-config` | None | Get current ticker settings |
| PUT | `/ticker-config/admin` | verifyUser | Update ticker settings |

---

## Data / Thresholds

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/data/thresholds` | Add or update seller rating threshold |
| GET | `/data/thresholds` | Get thresholds |

---

## Billing (Shopify App)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/billing/status` | verifySeller | Check billing status |
| POST | `/billing/shopify/create` | verifySeller | Create Shopify subscription |
| GET | `/billing/shopify/callback` | None | Shopify subscription callback |
| GET | `/billing/shopify/stores` | verifySeller | Get user's Shopify stores |
