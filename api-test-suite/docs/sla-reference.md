# Zambeel API — SLA Reference

_Calibrated: 2026-05-04 07:45:22 UTC | Environment: Production | Base URL: https://portal.myzambeel.com_
_Iterations: 30 total · 3 warm-up discarded · 27 effective readings per endpoint_

---

## Methodology

Thresholds are derived using an **Apdex-aligned p95 baseline method**:

1. Run each endpoint **30 times** against the production environment.
2. Discard the first **3 iterations** as warm-up (cold TCP connections, DNS,
   connection-pool establishment artificially inflate initial response times).
3. Compute the **95th percentile** of the remaining effective readings as the calibrated baseline.
4. Apply buffer factors to produce three alert levels:

| Level | Formula | Meaning |
|-------|---------|---------|
| ✅ **Pass**    | p95 × 1.20 | 20% headroom — normal operation          |
| ⚠️ **Warning** | p95 × 1.50 | 50% above p95 — degraded, investigate    |
| ❌ **Fail**    | p95 × 2.00 | Double p95 — SLA breach, escalate        |

> **Phase 2 ongoing testing** (`npm run baseline`) runs **10 iterations**, discards the first 1,
> and compares the **average of the remaining 9** against these thresholds.
> Historical run data lives in `docs/baseline-log.md`.

---

## SLA Thresholds by Category

### P0 — Critical _(SLA breach blocks merge)_

| TC ID | Endpoint | Method | Avg | p50 | p95 | Pass ≤ | Warn ≤ | Fail > |
|-------|----------|--------|-----|-----|-----|--------|--------|--------|
| TC_001 | `/api/login` | `POST` | 307ms | 164ms | 1261ms | 1514ms | 1892ms | 2522ms |
| TC_009 | `/api/dashboard/data` | `GET` | 172ms | 168ms | 187ms | 225ms | 281ms | 374ms |
| TC_070 | `/api/orders/status-counts` | `GET` | 187ms | 159ms | 188ms | 226ms | 282ms | 376ms |
| TC_095 | `/api/orders/orderDetails/:orderId` | `GET` | 456ms | 191ms | 2774ms | 3329ms | 4161ms | 5548ms |

### P1 — High

| TC ID | Endpoint | Method | Avg | p50 | p95 | Pass ≤ | Warn ≤ | Fail > |
|-------|----------|--------|-----|-----|-----|--------|--------|--------|
| TC_007 | `/api/teams` | `GET` | 197ms | 192ms | 234ms | 281ms | 351ms | 468ms |
| TC_008 | `/api/agents` | `GET` | 216ms | 208ms | 248ms | 298ms | 372ms | 496ms |
| TC_013 | `/api/inventory/seller-inventory` | `GET` | 174ms | 168ms | 206ms | 248ms | 309ms | 412ms |
| TC_014 | `/api/inventory/seller-inventory/export` | `GET` | 352ms | 172ms | 2310ms | 2772ms | 3465ms | 4620ms |
| TC_015 | `/api/inventory/purchase-order/:variantId` | `GET` | 286ms | 168ms | 640ms | 768ms | 960ms | 1280ms |
| TC_016 | `/api/inventory/purchase-order/orders/:variantId` | `GET` | 181ms | 164ms | 277ms | 333ms | 416ms | 554ms |
| TC_017 | `/api/inventory/inventory-movements/:variantId` | `GET` | 516ms | 167ms | 3821ms | 4586ms | 5732ms | 7642ms |
| TC_071 | `/api/orders/order-analytics` | `GET` | 244ms | 200ms | 470ms | 564ms | 705ms | 940ms |
| TC_083 | `/api/orders/remarks` | `GET` | 244ms | 169ms | 181ms | 218ms | 272ms | 362ms |
| TC_103 | `/api/orders/:orderId/logs` | `GET` | 172ms | 168ms | 193ms | 232ms | 290ms | 386ms |

### P2 — Medium

| TC ID | Endpoint | Method | Avg | p50 | p95 | Pass ≤ | Warn ≤ | Fail > |
|-------|----------|--------|-----|-----|-----|--------|--------|--------|
| TC_003 | `/api/auth/check-email` | `GET` | 172ms | 162ms | 195ms | 234ms | 293ms | 390ms |
| TC_012 | `/api/sub-statuses` | `GET` | 243ms | 179ms | 231ms | 278ms | 347ms | 462ms |
| TC_022 | `/api/payments/checkUserSubscription` | `GET` | 226ms | 183ms | 338ms | 406ms | 507ms | 676ms |
| TC_030 | `/api/accounts/store/:storeId` | `GET` | 409ms | 200ms | 1095ms | 1314ms | 1643ms | 2190ms |
| TC_031 | `/api/notion/notion_data` | `GET` | 817ms | 521ms | 2367ms | 2841ms | 3551ms | 4734ms |
| TC_032 | `/api/shopify/checkUser` | `GET` | 661ms | 204ms | 3750ms | 4500ms | 5625ms | 7500ms |
| TC_033 | `/api/shopify/shop` | `GET` | 867ms | 438ms | 2517ms | 3021ms | 3776ms | 5034ms |
| TC_034 | `/api/shopify/check-store-exists` | `GET` | 281ms | 181ms | 473ms | 568ms | 710ms | 946ms |
| TC_036 | `/api/shopify/auth` | `GET` | 611ms | 178ms | 2049ms | 2459ms | 3074ms | 4098ms |
| TC_041 | `/api/store/` | `GET` | 2592ms | 1650ms | 5256ms | 6308ms | 7884ms | 10512ms |
| TC_042 | `/api/store/trust/confirmation-pending-tags` | `GET` | 435ms | 209ms | 2032ms | 2439ms | 3048ms | 4064ms |
| TC_050 | `/api/store-names` | `GET` | 648ms | 480ms | 2141ms | 2570ms | 3212ms | 4282ms |
| TC_054 | `/api/youcan/auth` | `GET` | 180ms | 163ms | 325ms | 390ms | 488ms | 650ms |
| TC_055 | `/api/youcan/callback` | `GET` | 188ms | 163ms | 343ms | 412ms | 515ms | 686ms |
| TC_056 | `/api/youcan/store-info` | `GET` | 171ms | 165ms | 193ms | 232ms | 290ms | 386ms |
| TC_060 | `/api/salla/auth` | `GET` | 301ms | 162ms | 886ms | 1064ms | 1329ms | 1772ms |
| TC_061 | `/api/salla/callback` | `GET` | 177ms | 163ms | 313ms | 376ms | 470ms | 626ms |
| TC_068 | `/api/orders/duplicates/:orderId` | `GET` | 229ms | 204ms | 368ms | 442ms | 552ms | 736ms |
| TC_081 | `/api/orders/proccessedOrders` | `GET` | 525ms | 185ms | 2662ms | 3195ms | 3993ms | 5324ms |
| TC_082 | `/api/orders/tags` | `GET` | 210ms | 197ms | 297ms | 357ms | 446ms | 594ms |
| TC_085 | `/api/orders/batches/dip` | `GET` | 202ms | 186ms | 296ms | 356ms | 444ms | 592ms |
| TC_094 | `/api/orders/store/:storeId` | `GET` | 330ms | 279ms | 491ms | 590ms | 737ms | 982ms |
| TC_096 | `/api/orders/:orderId/conversation/media` | `GET` | 187ms | 178ms | 268ms | 322ms | 402ms | 536ms |
| TC_097 | `/api/orders/:orderId/conversation` | `GET` | 789ms | 643ms | 2150ms | 2580ms | 3225ms | 4300ms |
| TC_107 | `/api/orders/dispatch-batches` | `GET` | 180ms | 178ms | 198ms | 238ms | 297ms | 396ms |
| TC_110 | `/api/orders/tracking-generation-report` | `GET` | 229ms | 178ms | 262ms | 315ms | 393ms | 524ms |
| TC_111 | `/api/orders/vendors` | `GET` | 270ms | 181ms | 719ms | 863ms | 1079ms | 1438ms |
| TC_124 | `/api/billing/shopify/callback` | `GET` | 161ms | 161ms | 163ms | 196ms | 245ms | 326ms |
| TC_125 | `/api/billing/shopify/stores` | `GET` | 790ms | 176ms | 7653ms | 9184ms | 11480ms | 15306ms |
| TC_126 | `/api/admin/gold-subscriptions/users/gold` | `GET` | 175ms | 174ms | 179ms | 215ms | 269ms | 358ms |
| TC_127 | `/api/admin/gold-subscriptions/users` | `GET` | 175ms | 174ms | 180ms | 216ms | 270ms | 360ms |
| TC_132 | `/api/admin/agency-registrations/applications` | `GET` | 192ms | 191ms | 198ms | 238ms | 297ms | 396ms |
| TC_134 | `/api/admin/agency-registrations/commission-models` | `GET` | 179ms | 178ms | 188ms | 226ms | 282ms | 376ms |
| TC_135 | `/api/admin/agency-registrations/commission-models/manage` | `GET` | 194ms | 202ms | 208ms | 250ms | 312ms | 416ms |
| TC_143 | `/api/imile/token` | `GET` | 232ms | 179ms | 409ms | 491ms | 614ms | 818ms |

### Skipped / Not Calibrated

| TC ID | Endpoint | Reason |
|-------|----------|--------|
| TC_004 | `/api/verify-email` | only 4/27 effective readings |
| TC_072 | `/api/orders/substatusOrders` | only 0/27 effective readings |
| TC_073 | `/api/orders/seller-orders` | only 0/27 effective readings |
| TC_075 | `/api/orders/couriers` | only 0/27 effective readings |
| TC_076 | `/api/orders/batch-ids` | only 0/27 effective readings |
| TC_114 | `/api/orders/substatus-orders-for-csv` | only 0/27 effective readings |
| TC_117 | `/api/tags/` | only 0/27 effective readings |
| TC_120 | `/api/tags/statuses` | only 0/27 effective readings |
| TC_122 | `/api/billing/status` | only 0/27 effective readings |
| TC_024 | `/api/accounts/:userId` | no substitution rule for :userId |
| TC_025 | `/api/accounts/:userId/all` | no substitution rule for :userId |
| TC_029 | `/api/accounts/myaccount/:id` | no substitution rule for :id |
| TC_043 | `/api/store/:id` | no substitution rule for :id |
| TC_045 | `/api/store/user/:userId` | no substitution rule for :userId |
| TC_046 | `/api/store/user/stores/:userId` | no substitution rule for :userId |
| TC_121 | `/api/tags/substatuses/:statusId` | no substitution rule for :statusId |
| TC_128 | `/api/admin/gold-subscriptions/users/:userId` | no substitution rule for :userId |
| TC_133 | `/api/admin/agency-registrations/applications/:id` | no substitution rule for :id |

---

## Calibration Raw Data

All 30 readings per endpoint. First 3 are warm-up and excluded from threshold computation.

### TC_001 — `POST /api/login`
**Warm-up (3 discarded):** 485ms, 166ms, 165ms  
**Effective readings (27):** 164ms, 165ms, 167ms, 164ms, 165ms, 164ms, 163ms, 161ms, 163ms, 1261ms, 982ms, 164ms, 162ms, 163ms, 224ms, 2055ms, 162ms, 162ms, 164ms, 169ms, 164ms, 164ms, 162ms, 164ms, 162ms, 162ms, 164ms  
**Stats —** min: 161ms · avg: 307ms · p50: 164ms · p95: 1261ms · max: 2055ms

### TC_009 — `GET /api/dashboard/data`
**Warm-up (3 discarded):** 169ms, 172ms, 166ms  
**Effective readings (27):** 165ms, 168ms, 167ms, 167ms, 167ms, 177ms, 168ms, 167ms, 168ms, 171ms, 169ms, 169ms, 167ms, 180ms, 168ms, 166ms, 206ms, 170ms, 166ms, 176ms, 180ms, 169ms, 167ms, 168ms, 170ms, 187ms, 178ms  
**Stats —** min: 165ms · avg: 172ms · p50: 168ms · p95: 187ms · max: 206ms

### TC_070 — `GET /api/orders/status-counts`
> ⚠️ 6 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, 8674ms  
**Effective readings (27):** 160ms, 157ms, 159ms, 158ms, 159ms, 158ms, 160ms, 157ms, 188ms, 158ms, 159ms, TIMEOUT, TIMEOUT, TIMEOUT, 778ms, 160ms, 161ms, 159ms, 159ms, 164ms, 160ms, 161ms, 158ms, 159ms, 159ms, 158ms, TIMEOUT  
**Stats —** min: 157ms · avg: 187ms · p50: 159ms · p95: 188ms · max: 778ms

### TC_095 — `GET /api/orders/orderDetails/:orderId`
> ⚠️ 1 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** 635ms, 606ms, 297ms  
**Effective readings (27):** 304ms, 3288ms, TIMEOUT, 2774ms, 232ms, 179ms, 175ms, 172ms, 199ms, 267ms, 176ms, 168ms, 171ms, 200ms, 184ms, 216ms, 193ms, 188ms, 189ms, 191ms, 187ms, 179ms, 178ms, 211ms, 211ms, 1225ms, 202ms  
**Stats —** min: 168ms · avg: 456ms · p50: 191ms · p95: 2774ms · max: 3288ms

### TC_007 — `GET /api/teams`
**Warm-up (3 discarded):** 197ms, 183ms, 177ms  
**Effective readings (27):** 187ms, 194ms, 186ms, 191ms, 197ms, 176ms, 206ms, 192ms, 190ms, 227ms, 203ms, 186ms, 192ms, 187ms, 195ms, 228ms, 181ms, 185ms, 185ms, 175ms, 168ms, 198ms, 186ms, 198ms, 197ms, 234ms, 265ms  
**Stats —** min: 168ms · avg: 197ms · p50: 192ms · p95: 234ms · max: 265ms

### TC_008 — `GET /api/agents`
**Warm-up (3 discarded):** 636ms, 231ms, 258ms  
**Effective readings (27):** 241ms, 241ms, 248ms, 250ms, 246ms, 205ms, 223ms, 218ms, 206ms, 238ms, 210ms, 224ms, 208ms, 202ms, 212ms, 208ms, 202ms, 205ms, 203ms, 203ms, 204ms, 203ms, 212ms, 199ms, 199ms, 202ms, 209ms  
**Stats —** min: 199ms · avg: 216ms · p50: 208ms · p95: 248ms · max: 250ms

### TC_013 — `GET /api/inventory/seller-inventory`
**Warm-up (3 discarded):** 170ms, 166ms, 169ms  
**Effective readings (27):** 166ms, 168ms, 165ms, 166ms, 164ms, 164ms, 168ms, 166ms, 175ms, 165ms, 168ms, 167ms, 163ms, 197ms, 166ms, 170ms, 173ms, 167ms, 166ms, 177ms, 206ms, 169ms, 169ms, 162ms, 257ms, 176ms, 168ms  
**Stats —** min: 162ms · avg: 174ms · p50: 168ms · p95: 206ms · max: 257ms

### TC_014 — `GET /api/inventory/seller-inventory/export`
**Warm-up (3 discarded):** 167ms, 176ms, 209ms  
**Effective readings (27):** 186ms, 165ms, 291ms, 173ms, 179ms, 172ms, 168ms, 175ms, 167ms, 172ms, 211ms, 170ms, 171ms, 176ms, 168ms, 171ms, 180ms, 170ms, 164ms, 2691ms, 190ms, 185ms, 178ms, 172ms, 2310ms, 170ms, 169ms  
**Stats —** min: 164ms · avg: 352ms · p50: 172ms · p95: 2310ms · max: 2691ms

### TC_015 — `GET /api/inventory/purchase-order/:variantId`
**Warm-up (3 discarded):** 210ms, 212ms, 570ms  
**Effective readings (27):** 640ms, 614ms, 482ms, 520ms, 373ms, 167ms, 180ms, 165ms, 1510ms, 166ms, 166ms, 167ms, 175ms, 166ms, 165ms, 187ms, 167ms, 168ms, 167ms, 166ms, 167ms, 168ms, 165ms, 164ms, 195ms, 170ms, 175ms  
**Stats —** min: 164ms · avg: 286ms · p50: 168ms · p95: 640ms · max: 1510ms

### TC_016 — `GET /api/inventory/purchase-order/orders/:variantId`
**Warm-up (3 discarded):** 161ms, 160ms, 202ms  
**Effective readings (27):** 161ms, 384ms, 163ms, 176ms, 164ms, 160ms, 163ms, 165ms, 277ms, 163ms, 170ms, 179ms, 179ms, 185ms, 189ms, 188ms, 174ms, 189ms, 174ms, 161ms, 161ms, 162ms, 161ms, 161ms, 162ms, 160ms, 160ms  
**Stats —** min: 160ms · avg: 181ms · p50: 164ms · p95: 277ms · max: 384ms

### TC_017 — `GET /api/inventory/inventory-movements/:variantId`
> ⚠️ 3 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** 164ms, 168ms, 164ms  
**Effective readings (27):** 163ms, 161ms, 165ms, 162ms, 162ms, 165ms, 164ms, 4255ms, TIMEOUT, TIMEOUT, TIMEOUT, 3821ms, 421ms, 291ms, 233ms, 231ms, 169ms, 165ms, 165ms, 166ms, 181ms, 195ms, 175ms, 216ms, 232ms, 167ms, 167ms  
**Stats —** min: 161ms · avg: 516ms · p50: 167ms · p95: 3821ms · max: 4255ms

### TC_071 — `GET /api/orders/order-analytics`
**Warm-up (3 discarded):** 173ms, 170ms, 370ms  
**Effective readings (27):** 339ms, 206ms, 200ms, 279ms, 380ms, 470ms, 479ms, 385ms, 263ms, 247ms, 331ms, 317ms, 218ms, 272ms, 190ms, 170ms, 165ms, 169ms, 167ms, 166ms, 165ms, 171ms, 167ms, 166ms, 167ms, 164ms, 163ms  
**Stats —** min: 163ms · avg: 244ms · p50: 200ms · p95: 470ms · max: 479ms

### TC_083 — `GET /api/orders/remarks`
**Warm-up (3 discarded):** 171ms, 170ms, 171ms  
**Effective readings (27):** 170ms, 168ms, 181ms, 169ms, 2154ms, 178ms, 169ms, 169ms, 169ms, 172ms, 170ms, 168ms, 178ms, 175ms, 169ms, 169ms, 168ms, 175ms, 171ms, 169ms, 170ms, 169ms, 169ms, 170ms, 169ms, 172ms, 169ms  
**Stats —** min: 168ms · avg: 244ms · p50: 169ms · p95: 181ms · max: 2154ms

### TC_103 — `GET /api/orders/:orderId/logs`
**Warm-up (3 discarded):** 169ms, 166ms, 166ms  
**Effective readings (27):** 166ms, 171ms, 168ms, 169ms, 167ms, 167ms, 168ms, 170ms, 170ms, 167ms, 169ms, 167ms, 168ms, 168ms, 167ms, 172ms, 180ms, 166ms, 225ms, 193ms, 168ms, 168ms, 169ms, 166ms, 167ms, 167ms, 168ms  
**Stats —** min: 166ms · avg: 172ms · p50: 168ms · p95: 193ms · max: 225ms

### TC_003 — `GET /api/auth/check-email`
**Warm-up (3 discarded):** 165ms, 167ms, 161ms  
**Effective readings (27):** 161ms, 163ms, 159ms, 160ms, 159ms, 160ms, 160ms, 161ms, 157ms, 159ms, 162ms, 160ms, 162ms, 160ms, 162ms, 173ms, 170ms, 180ms, 171ms, 173ms, 195ms, 193ms, 195ms, 227ms, 194ms, 177ms, 193ms  
**Stats —** min: 157ms · avg: 172ms · p50: 162ms · p95: 195ms · max: 227ms

### TC_004 — `GET /api/verify-email`
> ⚠️ 26 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, 577ms, 179ms, 177ms, 190ms  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_012 — `GET /api/sub-statuses`
**Warm-up (3 discarded):** 188ms, 179ms, 251ms  
**Effective readings (27):** 175ms, 175ms, 176ms, 231ms, 179ms, 179ms, 184ms, 185ms, 179ms, 182ms, 177ms, 178ms, 177ms, 181ms, 179ms, 178ms, 183ms, 180ms, 178ms, 179ms, 177ms, 1875ms, 178ms, 179ms, 177ms, 176ms, 175ms  
**Stats —** min: 175ms · avg: 243ms · p50: 179ms · p95: 231ms · max: 1875ms

### TC_022 — `GET /api/payments/checkUserSubscription`
**Warm-up (3 discarded):** 594ms, 2592ms, 2115ms  
**Effective readings (27):** 183ms, 180ms, 967ms, 180ms, 183ms, 264ms, 179ms, 189ms, 302ms, 181ms, 185ms, 182ms, 183ms, 185ms, 195ms, 183ms, 191ms, 180ms, 181ms, 182ms, 338ms, 181ms, 183ms, 181ms, 182ms, 187ms, 183ms  
**Stats —** min: 179ms · avg: 226ms · p50: 183ms · p95: 338ms · max: 967ms

### TC_030 — `GET /api/accounts/store/:storeId`
**Warm-up (3 discarded):** 181ms, 187ms, 184ms  
**Effective readings (27):** 187ms, 180ms, 181ms, 195ms, 204ms, 392ms, 272ms, 188ms, 3154ms, 1090ms, 494ms, 459ms, 181ms, 201ms, 185ms, 295ms, 241ms, 293ms, 276ms, 1095ms, 200ms, 181ms, 184ms, 180ms, 182ms, 181ms, 181ms  
**Stats —** min: 180ms · avg: 409ms · p50: 200ms · p95: 1095ms · max: 3154ms

### TC_031 — `GET /api/notion/notion_data`
**Warm-up (3 discarded):** 488ms, 537ms, 4208ms  
**Effective readings (27):** 1239ms, 1264ms, 518ms, 519ms, 505ms, 510ms, 496ms, 524ms, 2236ms, 450ms, 513ms, 528ms, 556ms, 600ms, 469ms, 519ms, 521ms, 534ms, 3541ms, 525ms, 472ms, 2367ms, 479ms, 497ms, 533ms, 650ms, 494ms  
**Stats —** min: 450ms · avg: 817ms · p50: 521ms · p95: 2367ms · max: 3541ms

### TC_032 — `GET /api/shopify/checkUser`
**Warm-up (3 discarded):** 182ms, 330ms, 182ms  
**Effective readings (27):** 182ms, 199ms, 183ms, 181ms, 4124ms, 640ms, 182ms, 314ms, 183ms, 234ms, 184ms, 186ms, 181ms, 182ms, 183ms, 3750ms, 1568ms, 183ms, 232ms, 1891ms, 204ms, 542ms, 465ms, 184ms, 713ms, 445ms, 325ms  
**Stats —** min: 181ms · avg: 661ms · p50: 204ms · p95: 3750ms · max: 4124ms

### TC_033 — `GET /api/shopify/shop`
**Warm-up (3 discarded):** 705ms, 378ms, 184ms  
**Effective readings (27):** 835ms, 2517ms, 2072ms, 1055ms, 1168ms, 495ms, 4098ms, 1090ms, 438ms, 970ms, 210ms, 219ms, 927ms, 188ms, 183ms, 260ms, 179ms, 181ms, 181ms, 182ms, 180ms, 2227ms, 1726ms, 1113ms, 338ms, 191ms, 186ms  
**Stats —** min: 179ms · avg: 867ms · p50: 438ms · p95: 2517ms · max: 4098ms

### TC_034 — `GET /api/shopify/check-store-exists`
**Warm-up (3 discarded):** 375ms, 2370ms, 3433ms  
**Effective readings (27):** 473ms, 433ms, 179ms, 304ms, 193ms, 279ms, 181ms, 284ms, 182ms, 182ms, 182ms, 181ms, 180ms, 180ms, 181ms, 1996ms, 181ms, 180ms, 183ms, 179ms, 181ms, 179ms, 184ms, 180ms, 179ms, 180ms, 182ms  
**Stats —** min: 179ms · avg: 281ms · p50: 181ms · p95: 473ms · max: 1996ms

### TC_036 — `GET /api/shopify/auth`
**Warm-up (3 discarded):** 196ms, 188ms, 199ms  
**Effective readings (27):** 178ms, 177ms, 177ms, 177ms, 392ms, 185ms, 177ms, 177ms, 176ms, 178ms, 175ms, 3478ms, 817ms, 177ms, 178ms, 177ms, 324ms, 176ms, 2014ms, 2049ms, 176ms, 176ms, 267ms, 1830ms, 279ms, 178ms, 2032ms  
**Stats —** min: 175ms · avg: 611ms · p50: 178ms · p95: 2049ms · max: 3478ms

### TC_041 — `GET /api/store/`
**Warm-up (3 discarded):** 1969ms, 2684ms, 1499ms  
**Effective readings (27):** 1402ms, 1445ms, 1831ms, 4954ms, 2630ms, 1592ms, 1670ms, 1509ms, 1503ms, 1408ms, 1451ms, 1484ms, 1650ms, 1427ms, 1302ms, 5040ms, 3238ms, 5256ms, 4106ms, 4071ms, 1353ms, 4557ms, 1442ms, 5683ms, 1623ms, 3381ms, 2979ms  
**Stats —** min: 1302ms · avg: 2592ms · p50: 1650ms · p95: 5256ms · max: 5683ms

### TC_042 — `GET /api/store/trust/confirmation-pending-tags`
> ⚠️ 1 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** 564ms, 401ms, 683ms  
**Effective readings (27):** 656ms, 628ms, 577ms, 594ms, 286ms, 211ms, 202ms, 206ms, 221ms, 187ms, 185ms, 223ms, 393ms, 182ms, 2032ms, 308ms, 2049ms, 184ms, 185ms, 188ms, 209ms, 184ms, TIMEOUT, 714ms, 182ms, 167ms, 168ms  
**Stats —** min: 167ms · avg: 435ms · p50: 209ms · p95: 2032ms · max: 2049ms

### TC_050 — `GET /api/store-names`
**Warm-up (3 discarded):** 1209ms, 499ms, 493ms  
**Effective readings (27):** 476ms, 630ms, 481ms, 482ms, 461ms, 461ms, 513ms, 468ms, 461ms, 466ms, 456ms, 465ms, 464ms, 472ms, 480ms, 464ms, 463ms, 2141ms, 589ms, 2364ms, 777ms, 555ms, 615ms, 625ms, 684ms, 464ms, 526ms  
**Stats —** min: 456ms · avg: 648ms · p50: 480ms · p95: 2141ms · max: 2364ms

### TC_054 — `GET /api/youcan/auth`
**Warm-up (3 discarded):** 208ms, 162ms, 189ms  
**Effective readings (27):** 163ms, 175ms, 168ms, 161ms, 165ms, 166ms, 161ms, 337ms, 162ms, 162ms, 162ms, 165ms, 164ms, 177ms, 163ms, 163ms, 325ms, 172ms, 161ms, 170ms, 163ms, 162ms, 162ms, 163ms, 163ms, 231ms, 162ms  
**Stats —** min: 161ms · avg: 180ms · p50: 163ms · p95: 325ms · max: 337ms

### TC_055 — `GET /api/youcan/callback`
**Warm-up (3 discarded):** 163ms, 160ms, 221ms  
**Effective readings (27):** 163ms, 170ms, 164ms, 161ms, 160ms, 160ms, 162ms, 159ms, 343ms, 163ms, 163ms, 165ms, 161ms, 162ms, 160ms, 162ms, 163ms, 161ms, 168ms, 352ms, 176ms, 170ms, 162ms, 162ms, 186ms, 300ms, 301ms  
**Stats —** min: 159ms · avg: 188ms · p50: 163ms · p95: 343ms · max: 352ms

### TC_056 — `GET /api/youcan/store-info`
**Warm-up (3 discarded):** 176ms, 337ms, 167ms  
**Effective readings (27):** 162ms, 159ms, 273ms, 167ms, 170ms, 180ms, 180ms, 167ms, 173ms, 186ms, 165ms, 168ms, 160ms, 165ms, 160ms, 161ms, 164ms, 161ms, 170ms, 162ms, 161ms, 160ms, 160ms, 162ms, 167ms, 193ms, 166ms  
**Stats —** min: 159ms · avg: 171ms · p50: 165ms · p95: 193ms · max: 273ms

### TC_060 — `GET /api/salla/auth`
**Warm-up (3 discarded):** 163ms, 167ms, 162ms  
**Effective readings (27):** 160ms, 169ms, 161ms, 160ms, 163ms, 162ms, 162ms, 164ms, 160ms, 168ms, 386ms, 161ms, 161ms, 159ms, 162ms, 162ms, 170ms, 161ms, 180ms, 169ms, 2938ms, 886ms, 161ms, 163ms, 160ms, 159ms, 161ms  
**Stats —** min: 159ms · avg: 301ms · p50: 162ms · p95: 886ms · max: 2938ms

### TC_061 — `GET /api/salla/callback`
**Warm-up (3 discarded):** 161ms, 159ms, 229ms  
**Effective readings (27):** 166ms, 163ms, 164ms, 159ms, 160ms, 161ms, 160ms, 163ms, 355ms, 162ms, 164ms, 163ms, 163ms, 163ms, 174ms, 160ms, 161ms, 168ms, 313ms, 178ms, 164ms, 164ms, 171ms, 173ms, 163ms, 161ms, 173ms  
**Stats —** min: 159ms · avg: 177ms · p50: 163ms · p95: 313ms · max: 355ms

### TC_068 — `GET /api/orders/duplicates/:orderId`
**Warm-up (3 discarded):** 259ms, 204ms, 203ms  
**Effective readings (27):** 215ms, 202ms, 203ms, 290ms, 203ms, 203ms, 204ms, 203ms, 202ms, 200ms, 205ms, 466ms, 206ms, 214ms, 217ms, 202ms, 200ms, 203ms, 368ms, 205ms, 204ms, 200ms, 202ms, 206ms, 203ms, 358ms, 204ms  
**Stats —** min: 200ms · avg: 229ms · p50: 204ms · p95: 368ms · max: 466ms

### TC_072 — `GET /api/orders/substatusOrders`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_073 — `GET /api/orders/seller-orders`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_075 — `GET /api/orders/couriers`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_076 — `GET /api/orders/batch-ids`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_081 — `GET /api/orders/proccessedOrders`
> ⚠️ 4 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, 5356ms, 2662ms, 1124ms, 277ms, 192ms, 182ms, 180ms, 192ms, 324ms, 196ms, 180ms, 216ms, 192ms, 186ms, 179ms, 186ms, 185ms, 180ms, 182ms, 180ms, 180ms, 180ms, 183ms, 181ms, 192ms, 179ms  
**Stats —** min: 179ms · avg: 525ms · p50: 185ms · p95: 2662ms · max: 5356ms

### TC_082 — `GET /api/orders/tags`
**Warm-up (3 discarded):** 357ms, 199ms, 194ms  
**Effective readings (27):** 196ms, 195ms, 197ms, 195ms, 198ms, 196ms, 203ms, 199ms, 197ms, 214ms, 246ms, 206ms, 213ms, 275ms, 306ms, 195ms, 200ms, 195ms, 297ms, 194ms, 195ms, 194ms, 194ms, 196ms, 197ms, 195ms, 194ms  
**Stats —** min: 194ms · avg: 210ms · p50: 197ms · p95: 297ms · max: 306ms

### TC_085 — `GET /api/orders/batches/dip`
**Warm-up (3 discarded):** 184ms, 186ms, 255ms  
**Effective readings (27):** 196ms, 180ms, 182ms, 186ms, 293ms, 180ms, 197ms, 180ms, 184ms, 190ms, 186ms, 180ms, 182ms, 180ms, 184ms, 184ms, 180ms, 181ms, 197ms, 184ms, 191ms, 193ms, 186ms, 196ms, 303ms, 284ms, 296ms  
**Stats —** min: 180ms · avg: 202ms · p50: 186ms · p95: 296ms · max: 303ms

### TC_094 — `GET /api/orders/store/:storeId`
**Warm-up (3 discarded):** 561ms, 398ms, 394ms  
**Effective readings (27):** 395ms, 382ms, 378ms, 375ms, 491ms, 803ms, 289ms, 273ms, 277ms, 275ms, 269ms, 272ms, 271ms, 354ms, 332ms, 274ms, 272ms, 279ms, 276ms, 285ms, 273ms, 274ms, 353ms, 335ms, 301ms, 271ms, 272ms  
**Stats —** min: 269ms · avg: 330ms · p50: 279ms · p95: 491ms · max: 803ms

### TC_096 — `GET /api/orders/:orderId/conversation/media`
**Warm-up (3 discarded):** 196ms, 193ms, 176ms  
**Effective readings (27):** 177ms, 177ms, 176ms, 177ms, 177ms, 179ms, 177ms, 178ms, 178ms, 181ms, 181ms, 176ms, 177ms, 191ms, 270ms, 193ms, 178ms, 178ms, 181ms, 179ms, 176ms, 178ms, 180ms, 183ms, 193ms, 268ms, 182ms  
**Stats —** min: 176ms · avg: 187ms · p50: 178ms · p95: 268ms · max: 270ms

### TC_097 — `GET /api/orders/:orderId/conversation`
**Warm-up (3 discarded):** 863ms, 721ms, 679ms  
**Effective readings (27):** 781ms, 718ms, 1780ms, 779ms, 923ms, 619ms, 609ms, 370ms, 376ms, 358ms, 371ms, 378ms, 375ms, 640ms, 712ms, 614ms, 2508ms, 1245ms, 649ms, 591ms, 740ms, 2150ms, 718ms, 360ms, 700ms, 599ms, 643ms  
**Stats —** min: 358ms · avg: 789ms · p50: 643ms · p95: 2150ms · max: 2508ms

### TC_107 — `GET /api/orders/dispatch-batches`
**Warm-up (3 discarded):** 179ms, 177ms, 178ms  
**Effective readings (27):** 178ms, 178ms, 186ms, 178ms, 177ms, 178ms, 189ms, 177ms, 177ms, 198ms, 177ms, 177ms, 177ms, 177ms, 179ms, 184ms, 176ms, 177ms, 176ms, 178ms, 178ms, 177ms, 177ms, 180ms, 202ms, 176ms, 181ms  
**Stats —** min: 176ms · avg: 180ms · p50: 178ms · p95: 198ms · max: 202ms

### TC_110 — `GET /api/orders/tracking-generation-report`
**Warm-up (3 discarded):** 178ms, 178ms, 3706ms  
**Effective readings (27):** 232ms, 175ms, 262ms, 240ms, 176ms, 178ms, 178ms, 177ms, 1343ms, 177ms, 178ms, 177ms, 177ms, 185ms, 177ms, 180ms, 187ms, 177ms, 180ms, 178ms, 178ms, 178ms, 177ms, 179ms, 178ms, 177ms, 178ms  
**Stats —** min: 175ms · avg: 229ms · p50: 178ms · p95: 262ms · max: 1343ms

### TC_111 — `GET /api/orders/vendors`
**Warm-up (3 discarded):** 187ms, 182ms, 180ms  
**Effective readings (27):** 181ms, 181ms, 182ms, 181ms, 180ms, 192ms, 182ms, 182ms, 188ms, 182ms, 180ms, 179ms, 179ms, 180ms, 181ms, 185ms, 2013ms, 719ms, 178ms, 180ms, 182ms, 181ms, 182ms, 186ms, 186ms, 181ms, 180ms  
**Stats —** min: 178ms · avg: 270ms · p50: 181ms · p95: 719ms · max: 2013ms

### TC_114 — `GET /api/orders/substatus-orders-for-csv`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_117 — `GET /api/tags/`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_120 — `GET /api/tags/statuses`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_122 — `GET /api/billing/status`
> ⚠️ 30 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT  
**Stats —** insufficient effective readings (all iterations timed out)

### TC_124 — `GET /api/billing/shopify/callback`
**Warm-up (3 discarded):** 491ms, 164ms, 162ms  
**Effective readings (27):** 162ms, 162ms, 162ms, 161ms, 161ms, 162ms, 159ms, 163ms, 169ms, 162ms, 161ms, 162ms, 162ms, 161ms, 161ms, 161ms, 162ms, 161ms, 161ms, 161ms, 159ms, 161ms, 160ms, 159ms, 161ms, 161ms, 161ms  
**Stats —** min: 159ms · avg: 161ms · p50: 161ms · p95: 163ms · max: 169ms

### TC_125 — `GET /api/billing/shopify/stores`
> ⚠️ 13 iteration(s) timed out and were excluded
**Warm-up (3 discarded):** TIMEOUT, TIMEOUT, TIMEOUT  
**Effective readings (27):** TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, TIMEOUT, 7653ms, 2717ms, 275ms, 176ms, 176ms, 176ms, 175ms, 187ms, 175ms, 175ms, 175ms, 175ms, 175ms, 174ms, 292ms, 174ms, 373ms  
**Stats —** min: 174ms · avg: 790ms · p50: 176ms · p95: 7653ms · max: 7653ms

### TC_126 — `GET /api/admin/gold-subscriptions/users/gold`
**Warm-up (3 discarded):** 174ms, 176ms, 177ms  
**Effective readings (27):** 174ms, 174ms, 174ms, 179ms, 173ms, 173ms, 174ms, 174ms, 175ms, 174ms, 175ms, 176ms, 175ms, 173ms, 173ms, 174ms, 178ms, 173ms, 172ms, 178ms, 175ms, 173ms, 174ms, 173ms, 173ms, 173ms, 183ms  
**Stats —** min: 172ms · avg: 175ms · p50: 174ms · p95: 179ms · max: 183ms

### TC_127 — `GET /api/admin/gold-subscriptions/users`
**Warm-up (3 discarded):** 175ms, 174ms, 173ms  
**Effective readings (27):** 173ms, 175ms, 173ms, 174ms, 173ms, 176ms, 174ms, 173ms, 177ms, 173ms, 176ms, 173ms, 172ms, 172ms, 174ms, 173ms, 173ms, 174ms, 198ms, 173ms, 173ms, 173ms, 179ms, 174ms, 180ms, 176ms, 174ms  
**Stats —** min: 172ms · avg: 175ms · p50: 174ms · p95: 180ms · max: 198ms

### TC_132 — `GET /api/admin/agency-registrations/applications`
**Warm-up (3 discarded):** 348ms, 188ms, 191ms  
**Effective readings (27):** 189ms, 191ms, 194ms, 190ms, 198ms, 193ms, 191ms, 190ms, 193ms, 193ms, 191ms, 190ms, 190ms, 194ms, 190ms, 189ms, 190ms, 191ms, 190ms, 190ms, 190ms, 219ms, 195ms, 190ms, 189ms, 191ms, 191ms  
**Stats —** min: 189ms · avg: 192ms · p50: 191ms · p95: 198ms · max: 219ms

### TC_134 — `GET /api/admin/agency-registrations/commission-models`
**Warm-up (3 discarded):** 182ms, 180ms, 194ms  
**Effective readings (27):** 180ms, 198ms, 178ms, 181ms, 179ms, 188ms, 178ms, 176ms, 177ms, 177ms, 177ms, 176ms, 178ms, 180ms, 177ms, 177ms, 177ms, 179ms, 182ms, 177ms, 178ms, 177ms, 178ms, 178ms, 176ms, 176ms, 179ms  
**Stats —** min: 176ms · avg: 179ms · p50: 178ms · p95: 188ms · max: 198ms

### TC_135 — `GET /api/admin/agency-registrations/commission-models/manage`
**Warm-up (3 discarded):** 181ms, 182ms, 187ms  
**Effective readings (27):** 181ms, 182ms, 179ms, 181ms, 180ms, 229ms, 206ms, 204ms, 208ms, 202ms, 205ms, 205ms, 204ms, 205ms, 202ms, 207ms, 204ms, 204ms, 204ms, 187ms, 180ms, 180ms, 180ms, 181ms, 185ms, 182ms, 180ms  
**Stats —** min: 179ms · avg: 194ms · p50: 202ms · p95: 208ms · max: 229ms

### TC_143 — `GET /api/imile/token`
**Warm-up (3 discarded):** 421ms, 174ms, 173ms  
**Effective readings (27):** 173ms, 198ms, 227ms, 212ms, 181ms, 268ms, 406ms, 409ms, 411ms, 303ms, 310ms, 408ms, 308ms, 187ms, 173ms, 179ms, 173ms, 174ms, 175ms, 173ms, 175ms, 176ms, 173ms, 175ms, 174ms, 178ms, 173ms  
**Stats —** min: 173ms · avg: 232ms · p50: 179ms · p95: 409ms · max: 411ms

---
_Generated by `scripts/calibrate-sla.js` on 2026-05-04 07:45:22 UTC_
