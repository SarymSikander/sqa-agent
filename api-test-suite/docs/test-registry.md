# Zambeel API — Test Registry

> Auto-generated on 2026-04-19 09:10:23 UTC
> Source: `api-inventory.json` (148 routes)

## Summary

| Priority | Total | Passed | Failed | Pending | Not Run |
|----------|------:|------:|------:|------:|------:|
| **P0** | 4 | 0 | 0 | 0 | 4 |
| **P1** | 12 | 0 | 0 | 0 | 12 |
| **P2** | 132 | 0 | 0 | 0 | 132 |

## SLA Breach Report

_No SLA breaches recorded in last run._

## Route Inventory by Category

### Auth

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_001 | `POST` | `/api/login` | 🌐 | — | P0 | 297ms | ⬜ |
| TC_002 | `POST` | `/api/signUp` | 🌐 | — | P2 | — | ⬜ |
| TC_003 | `GET` | `/api/auth/check-email` | 🌐 | — | P2 | — | ⬜ |
| TC_004 | `GET` | `/api/verify-email` | 🌐 | — | P2 | — | ⬜ |
| TC_036 | `GET` | `/api/shopify/auth` | 🌐 | — | P2 | — | ⬜ |
| TC_039 | `POST` | `/api/lightfunnels/auth` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_053 | `GET` | `/api/youcan/auth` | 🌐 | — | P2 | — | ⬜ |
| TC_059 | `GET` | `/api/salla/auth` | 🌐 | — | P2 | — | ⬜ |

### Misc

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_005 | `PUT` | `/api/user/profile` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_006 | `POST` | `/api/user/accept-terms` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_012 | `GET` | `/api/sub-statuses` | 🌐 | — | P2 | — | ⬜ |
| TC_018 | `POST` | `/api/payments/create` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_019 | `POST` | `/api/payments/callback` | 🌐 | — | P2 | — | ⬜ |
| TC_020 | `POST` | `/api/payments/redirect` | 🌐 | — | P2 | — | ⬜ |
| TC_021 | `POST` | `/api/payments/verify` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_022 | `GET` | `/api/payments/checkUserSubscription` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_023 | `POST` | `/api/accounts/` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_024 | `GET` | `/api/accounts/:userId` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_025 | `GET` | `/api/accounts/:userId/all` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_026 | `PUT` | `/api/accounts/:id` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_027 | `DELETE` | `/api/accounts/:id` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_028 | `PATCH` | `/api/accounts/:id/set-primary` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_029 | `GET` | `/api/accounts/myaccount/:id` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_050 | `POST` | `/api/easyOrders/install-link` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_051 | `POST` | `/api/easyOrders/callback` | 🌐 | — | P2 | — | ⬜ |
| TC_052 | `DELETE` | `/api/easyOrders/disconnect` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_113 | `PUT` | `/api/orderTags/:tagId` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_120 | `GET` | `/api/billing/status` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_141 | `GET` | `/api/imile/token` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_142 | `POST` | `/api/imile/create-order` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_143 | `POST` | `/api/imile/track` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_144 | `POST` | `/api/imile/cancel` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_145 | `POST` | `/api/imile/reprint-awb` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_146 | `POST` | `/api/imile/pod` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_147 | `POST` | `/api/imile/webhook` | 🌐 | — | P2 | — | ⬜ |
| TC_148 | `POST` | `/api/tawseel/webhook` | 🌐 | — | P2 | — | ⬜ |

### Teams

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_007 | `GET` | `/api/teams` | 🌐 | — | P1 | 192ms | ⬜ |
| TC_008 | `GET` | `/api/agents` | 🌐 | — | P1 | 285ms | ⬜ |

### Dashboard

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_009 | `GET` | `/api/dashboard/data` | 🔒 | Seller, Agency | P0 | 298ms | ⬜ |

### Orders

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_010 | `POST` | `/api/remarks` | 🌐 | — | P1 | 230ms | ⬜ |
| TC_011 | `POST` | `/api/tags` | 🌐 | — | P2 | 210ms | ⬜ |
| TC_016 | `GET` | `/api/inventory/purchase-order/orders/:variantId` | 🔒 | Seller, Agency | P1 | — | ⬜ |
| TC_063 | `PUT` | `/api/orders/bulk-csv-update` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_064 | `PUT` | `/api/orders/revert-to-confirmation-pending` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_065 | `POST` | `/api/orders/bulk-order-upload` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_066 | `POST` | `/api/orders/bulk-vendor-courier-upload` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_067 | `GET` | `/api/orders/duplicates/:orderId` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_068 | `POST` | `/api/orders/` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_069 | `GET` | `/api/orders/status-counts` | 🔒 | Admin, Agent | P0 | 1.3s | ⬜ |
| TC_070 | `GET` | `/api/orders/order-analytics` | 🔒 | Seller, Agency | P1 | 206ms | ⬜ |
| TC_071 | `GET` | `/api/orders/substatusOrders` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_072 | `GET` | `/api/orders/seller-orders` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_073 | `POST` | `/api/orders/add-product` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_074 | `GET` | `/api/orders/couriers` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_075 | `GET` | `/api/orders/batch-ids` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_076 | `POST` | `/api/orders/courier-assignment/report` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_077 | `POST` | `/api/orders/assign-courier` | 🔒 | Admin, Agent | P1 | 1.2s | ⬜ |
| TC_078 | `POST` | `/api/orders/check-availability` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_079 | `POST` | `/api/orders/variants/price` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_080 | `GET` | `/api/orders/proccessedOrders` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_081 | `GET` | `/api/orders/tags` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_082 | `GET` | `/api/orders/remarks` | 🔒 | Admin, Agent | P1 | — | ⬜ |
| TC_083 | `POST` | `/api/orders/ndr-remarks` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_084 | `GET` | `/api/orders/batches/dip` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_085 | `POST` | `/api/orders/download-awbs` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_086 | `POST` | `/api/orders/download-packing-list` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_087 | `PUT` | `/api/orders/approve-status/bulk` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_088 | `POST` | `/api/orders/sub-statuses/bulk-update` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_089 | `PUT` | `/api/orders/:orderId` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_090 | `PUT` | `/api/orders/:orderId/order-product-variants/:orderProductVariantId` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_091 | `DELETE` | `/api/orders/:orderId/delete-product/:orderProductVariantId` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_092 | `POST` | `/api/orders/variants/search` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_093 | `GET` | `/api/orders/store/:storeId` | 🌐 | — | P2 | — | ⬜ |
| TC_094 | `GET` | `/api/orders/orderDetails/:orderId` | 🔒 | Admin, Agent, Seller | P0 | 182ms | ⬜ |
| TC_095 | `GET` | `/api/orders/:orderId/conversation` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_096 | `PUT` | `/api/orders/customers/:customerId` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_097 | `PUT` | `/api/orders/:orderId/status` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_098 | `PUT` | `/api/orders/:orderId/approve-status` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_099 | `DELETE` | `/api/orders/:orderId/delete-product/:variantId` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_100 | `POST` | `/api/orders/uploadOrderCSV` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_101 | `GET` | `/api/orders/:orderId/logs` | 🔒 | Admin, Agent, Seller | P1 | 193ms | ⬜ |
| TC_102 | `PUT` | `/api/orders/address/:orderId` | 🔒 | Admin, Seller | P2 | — | ⬜ |
| TC_103 | `PUT` | `/api/orders/:orderId/edit` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_104 | `POST` | `/api/orders/clear-courier-assignment` | 🔒 | Admin, Agent, Seller | P2 | — | ⬜ |
| TC_105 | `GET` | `/api/orders/dispatch-batches` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_106 | `POST` | `/api/orders/generate-batches` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_107 | `POST` | `/api/orders/generate-tracking-ids` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_108 | `GET` | `/api/orders/tracking-generation-report` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_109 | `GET` | `/api/orders/vendors` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_110 | `POST` | `/api/orders/generate-documents` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_111 | `DELETE` | `/api/orders/delete/:orderId` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_112 | `GET` | `/api/orders/substatus-orders-for-csv` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_114 | `POST` | `/api/tags/createTag` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_115 | `GET` | `/api/tags/` | 🔒 | Admin, Seller | P2 | — | ⬜ |
| TC_116 | `DELETE` | `/api/tags/:id` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_117 | `PUT` | `/api/tags/:id` | 🔒 | Admin, Agent | P2 | — | ⬜ |
| TC_118 | `GET` | `/api/tags/statuses` | 🔒 | Admin, Seller | P2 | — | ⬜ |
| TC_119 | `GET` | `/api/tags/substatuses/:statusId` | 🔒 | Admin, Seller | P2 | — | ⬜ |

### Inventory

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_013 | `GET` | `/api/inventory/seller-inventory` | 🔒 | Seller, Agency | P1 | 205ms | ⬜ |
| TC_014 | `GET` | `/api/inventory/seller-inventory/export` | 🔒 | Seller, Agency | P1 | 18.0s | ⬜ |
| TC_015 | `GET` | `/api/inventory/purchase-order/:variantId` | 🔒 | Seller, Agency | P1 | — | ⬜ |
| TC_017 | `GET` | `/api/inventory/inventory-movements/:variantId` | 🔒 | Seller, Agency | P1 | — | ⬜ |

### Store

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_030 | `GET` | `/api/accounts/store/:storeId` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_041 | `GET` | `/api/store/` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_042 | `GET` | `/api/store/:id` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_043 | `PUT` | `/api/store/:id` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_044 | `GET` | `/api/store/user/:userId` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_045 | `GET` | `/api/store/user/stores/:userId` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_046 | `DELETE` | `/api/store/:id` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_047 | `POST` | `/api/store/check-name` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_048 | `POST` | `/api/store/create/storeManually` | 🔒 | Admin, Seller, Agency | P2 | — | ⬜ |
| TC_049 | `GET` | `/api/store-names` | 🌐 | — | P2 | — | ⬜ |
| TC_055 | `GET` | `/api/youcan/store-info` | 🌐 | — | P2 | — | ⬜ |
| TC_123 | `GET` | `/api/billing/shopify/stores` | 🔒 | Seller, Agency | P2 | — | ⬜ |

### Integrations

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_031 | `GET` | `/api/notion/notion_data` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_032 | `GET` | `/api/shopify/checkUser` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_033 | `GET` | `/api/shopify/shop` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_034 | `GET` | `/api/shopify/check-store-exists` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_035 | `POST` | `/api/shopify/bind-store` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_037 | `DELETE` | `/api/shopify/webhooks/delete` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_038 | `POST` | `/api/shopify/app/installation-status` | 🌐 | — | P2 | — | ⬜ |
| TC_040 | `DELETE` | `/api/lightfunnels/webhooks/delete` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_054 | `GET` | `/api/youcan/callback` | 🌐 | — | P2 | — | ⬜ |
| TC_056 | `POST` | `/api/youcan/disconnect` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_057 | `POST` | `/api/youcan/webhooks` | 🌐 | — | P2 | — | ⬜ |
| TC_058 | `DELETE` | `/api/youcan/webhooks/delete` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_060 | `GET` | `/api/salla/callback` | 🌐 | — | P2 | — | ⬜ |
| TC_061 | `DELETE` | `/api/salla/disconnect` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_062 | `POST` | `/api/salla/order/created` | 🌐 | — | P2 | — | ⬜ |
| TC_121 | `POST` | `/api/billing/shopify/create` | 🔒 | Seller, Agency | P2 | — | ⬜ |
| TC_122 | `GET` | `/api/billing/shopify/callback` | 🌐 | — | P2 | — | ⬜ |

### Admin

| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |
|-------|--------|------|------|-------|----------|----------|--------|
| TC_124 | `GET` | `/api/admin/gold-subscriptions/users/gold` | 🔒 | Admin | P2 | — | ⬜ |
| TC_125 | `GET` | `/api/admin/gold-subscriptions/users` | 🔒 | Admin | P2 | — | ⬜ |
| TC_126 | `GET` | `/api/admin/gold-subscriptions/users/:userId` | 🔒 | Admin | P2 | — | ⬜ |
| TC_127 | `POST` | `/api/admin/gold-subscriptions/give` | 🔒 | Admin | P2 | — | ⬜ |
| TC_128 | `POST` | `/api/admin/gold-subscriptions/extend` | 🔒 | Admin | P2 | — | ⬜ |
| TC_129 | `POST` | `/api/admin/gold-subscriptions/remove` | 🔒 | Admin | P2 | — | ⬜ |
| TC_130 | `GET` | `/api/admin/agency-registrations/applications` | 🔒 | Admin | P2 | — | ⬜ |
| TC_131 | `GET` | `/api/admin/agency-registrations/applications/:id` | 🔒 | Admin | P2 | — | ⬜ |
| TC_132 | `GET` | `/api/admin/agency-registrations/commission-models` | 🔒 | Admin | P2 | — | ⬜ |
| TC_133 | `GET` | `/api/admin/agency-registrations/commission-models/manage` | 🔒 | Admin | P2 | — | ⬜ |
| TC_134 | `POST` | `/api/admin/agency-registrations/commission-models` | 🔒 | Admin | P2 | — | ⬜ |
| TC_135 | `PUT` | `/api/admin/agency-registrations/commission-models/:id` | 🔒 | Admin | P2 | — | ⬜ |
| TC_136 | `POST` | `/api/admin/agency-registrations/applications/:id/approve` | 🔒 | Admin | P2 | — | ⬜ |
| TC_137 | `POST` | `/api/admin/agency-registrations/applications/:id/hold` | 🔒 | Admin | P2 | — | ⬜ |
| TC_138 | `POST` | `/api/admin/agency-registrations/applications/:id/reject` | 🔒 | Admin | P2 | — | ⬜ |
| TC_139 | `POST` | `/api/admin/agency-registrations/applications/:id/revert-to-pending` | 🔒 | Admin | P2 | — | ⬜ |
| TC_140 | `POST` | `/api/admin/agency-registrations/applications/:id/revoke` | 🔒 | Admin | P2 | — | ⬜ |

---
_Regenerate with: `node scripts/generate-registry.js`_

---

## Production Smoke Tests

> This section is hand-authored. It is **not** overwritten by `generate-registry.js`.

### What are smoke tests?

The smoke layer is a separate, **read-only** test suite that runs against the live production API after every deployment. It verifies that the most critical read paths are reachable and performant — without touching any data.

**Config file:** `jest.smoke.js`  
**Test file:** `tests/smoke/smoke.test.js`  
**Workflow:** `.github/workflows/smoke-prod.yml` (manual trigger only)

---

### @readonly contract

Every file inside `tests/smoke/` carries the JSDoc annotation:

```js
/**
 * @readonly
 * ...
 */
```

This tag signals that the file **must not** contain:

| Forbidden | Why |
|-----------|-----|
| `POST` (except `/api/login`) | Could create real orders/tickets in production |
| `PUT` / `PATCH` / `DELETE` | Would mutate live data |
| CSV upload endpoints | Triggers actual ingestion pipeline |
| Bulk status updates | Could change thousands of orders |
| `assignCourier`, `bulkRemarks` | Irreversible logistics mutations |

Any PR that adds a mutation to a `@readonly` file should be blocked at review.

---

### Smoke test coverage

| Smoke TC | Method | Endpoint | Token needed | SLA goal | Dimensions |
|----------|--------|----------|--------------|----------|------------|
| SMOKE-TC_001 | `POST` | `/api/login` | — (public) | 297 ms | perf / auth / validation / security |
| SMOKE-TC_002 | `GET` | `/api/orders/seller-orders` | PROD_SELLER_TOKEN | 1 500 ms | perf / auth / validation / security |
| SMOKE-TC_003 | `GET` | `/api/orders/status-counts` | PROD_TOKEN | 1 300 ms | perf / auth / validation / security |
| SMOKE-TC_004 | `GET` | `/api/orders/orderDetails/:orderId` | PROD_TOKEN or PROD_SELLER_TOKEN | 182 ms | perf / auth / validation / security |
| SMOKE-TC_005 | `GET` | `/api/orders/order-analytics` | PROD_SELLER_TOKEN | 206 ms | perf / auth / validation / security |
| SMOKE-TC_006 | `GET` | `/api/inventory-movements/movements` | PROD_TOKEN | 515 ms | perf / auth / validation / security |
| SMOKE-TC_007 | `GET` | `/api/dashboard/data` | PROD_SELLER_TOKEN | 298 ms | perf / auth / validation / security |
| SMOKE-TC_008 | `GET` | `/api/tickets` | PROD_TOKEN or PROD_SELLER_TOKEN | 372 ms | perf / auth / validation / security |
| SMOKE-TC_009 | `GET` | `/api/comments/ticket/:ticketId` | PROD_TOKEN or PROD_SELLER_TOKEN | 190 ms | perf / auth / validation / security |
| SMOKE-TC_010 | `GET` | `/api/teams` | PROD_TOKEN | 192 ms | perf / auth / validation / security |
| SMOKE-TC_011 | `GET` | `/api/auth/check-email` | — (public) | < 1 000 ms | perf / auth / validation / security |
| SMOKE-TC_012 | `GET` | `/api/orders/substatus-orders-for-csv` | PROD_SELLER_TOKEN | 18 000 ms | perf / auth / validation / security |

> **Note on SMOKE-TC_002:** The main test suite uses `POST /api/orders` (admin-only).  
> Smoke tests are GET-only, so TC_002 maps to `GET /api/orders/seller-orders` — the seller-scoped equivalent.

---

### How to trigger the workflow

1. Go to **GitHub → Actions → Production Smoke Tests**.
2. Click **Run workflow**.
3. Fill in the **"deployed_by"** field — your name or the ticket that triggered the deployment (e.g. `sarim / OMS-142`). This appears in the Slack alert.
4. Click **Run workflow** (green button).

The workflow runs `jest --config jest.smoke.js --ci` against `PROD_BASE_URL`, then always posts a Slack notification regardless of pass/fail.

> **The job never exits with code 1.** Production stays live. Failures are communicated via Slack, not by blocking anything.

---

### Read-only token setup

You need two production JWTs — obtain them by calling `POST /api/login` with a real production account.

**PROD_TOKEN (Admin or Agent role)**
```
POST https://api.myzambeel.com/api/login
{ "email": "sqa-readonly-admin@myzambeel.com", "password": "..." }
```
Copy the `token` field from the response.  
Used for: TC_003, TC_006, TC_008, TC_009, TC_010.

**PROD_SELLER_TOKEN (Seller or Agency role)**
```
POST https://api.myzambeel.com/api/login
{ "email": "sqa-readonly-seller@myzambeel.com", "password": "..." }
```
Copy the `token` field from the response.  
Used for: TC_002, TC_005, TC_007, TC_012.

Add both to GitHub Secrets:
- `PROD_TOKEN`
- `PROD_SELLER_TOKEN`
- `PROD_JWT_SECRET` — the JWT signing secret (for expired-token auth tests only)
- `PROD_BASE_URL` — e.g. `https://api.myzambeel.com`
- `PROD_SAMPLE_ORDER_ID` — a stable archived order ID safe to query at any time
- `PROD_SAMPLE_TICKET_ID` — a stable ticket ID safe to query at any time
- `SLACK_WEBHOOK_URL` — from the SQA Agent Slack app > Incoming Webhooks

> 🔐 Rotate both tokens after every engineer departure. The tokens need read access only — if the API ever supports scoped tokens, restrict them accordingly.

---

### What the Slack alert looks like

**On full pass:**
```
✅ Zambeel Production — All Clear
Time: 2026-04-19 09:30 UTC   Triggered by: sarim / OMS-142
Results: 87/87 passed         Duration: 34s

📄 Full report on GitHub Actions
```

**On failure:**
```
🚨 Zambeel Production — Smoke Test Failed
Time: 2026-04-19 09:30 UTC   Triggered by: sarim / OMS-142
Results: 84/87 passed         Duration: 36s

Failed Tests
• TC_003 [perf]  GET /api/orders/status-counts
  Expected: <= 1300 | Received: 2140
• TC_007 [auth]  GET /api/dashboard/data
  Expected value: 401 | Received: 502

⏱ SLA Breaches
• TC_003  GET /api/orders/status-counts — avg 2140ms (threshold: 1300ms)

📄 Full report on GitHub Actions
```

**What to do when the alert fires:**

| Failure type | Likely cause | First action |
|---|---|---|
| `[perf]` SLA breach | DB slow query, cold cache, high traffic | Check Grafana latency dashboard, recent deploys |
| `[auth]` 502 / 503 | Server crashed or unreachable | Check Render/server logs, restart if needed |
| `[auth]` token expired | PROD_TOKEN / PROD_SELLER_TOKEN expired | Re-login, update GitHub Secrets |
| `[security]` 500 | Unhandled injection path in new code | Open a P0 bug in Jira OMS |
| `[validation]` 500 | New endpoint missing input guards | Open a P1 bug in Jira OMS |

