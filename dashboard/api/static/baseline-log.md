# Zambeel API — Baseline Performance Log

Auto-appended by `scripts/generate-registry.js` after each CI run.
Never edit manually — add corrections by running a new baseline measurement.

| Run | Timestamp | SLA Key | Endpoint Label | Avg | p95 | Pass ≤ | p95 Baseline | Status |
|-----|-----------|---------|----------------|-----|-----|--------|--------------|--------|

## Run #001

_Date: 2026-05-04 07:52:57 UTC | Environment: Production | Iterations: 10 (9 effective) | Triggered by: manual_

| TC ID | API Endpoint | Method | Min | Max | Avg | p95 | SLA Goal | Result |
|-------|-------------|--------|-----|-----|-----|-----|----------|--------|
| TC_001 | `/api/login` | `POST` | 162ms | 169ms | 165ms | 169ms | ≤ 1312ms | ✅ PASS |
| TC_009 | `/api/dashboard/data` | `GET` | 166ms | 176ms | 168ms | 176ms | ≤ 311ms | ✅ PASS |
| TC_070 | `/api/orders/status-counts` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_095 | `/api/orders/orderDetails/:orderId` | `GET` | 255ms | 5492ms | 1137ms | 5492ms | ≤ 1278ms | ✅ PASS |
| TC_007 | `/api/teams` | `GET` | 229ms | 2552ms | 905ms | 2552ms | ≤ 2358ms | ✅ PASS |
| TC_008 | `/api/agents` | `GET` | 155ms | 6476ms | 1093ms | 6476ms | ≤ 306ms | ❌ FAIL |
| TC_013 | `/api/inventory/seller-inventory` | `GET` | 157ms | 197ms | 169ms | 197ms | ≤ 1461ms | ✅ PASS |
| TC_014 | `/api/inventory/seller-inventory/export` | `GET` | 166ms | 171ms | 168ms | 171ms | ≤ 2685ms | ✅ PASS |
| TC_015 | `/api/inventory/purchase-order/:variantId` | `GET` | 169ms | 1827ms | 401ms | 1827ms | — | ⬜ NO SLA |
| TC_016 | `/api/inventory/purchase-order/orders/:variantId` | `GET` | 161ms | 2142ms | 544ms | 2142ms | — | ⬜ NO SLA |
| TC_017 | `/api/inventory/inventory-movements/:variantId` | `GET` | 163ms | 199ms | 173ms | 199ms | — | ⬜ NO SLA |
| TC_071 | `/api/orders/order-analytics` | `GET` | 161ms | 344ms | 184ms | 344ms | ≤ 1145ms | ✅ PASS |
| TC_083 | `/api/orders/remarks` | `GET` | 166ms | 183ms | 170ms | 183ms | — | ⬜ NO SLA |
| TC_103 | `/api/orders/:orderId/logs` | `GET` | 172ms | 4147ms | 718ms | 4147ms | ≤ 240ms | ❌ FAIL |
| TC_003 | `/api/auth/check-email` | `GET` | 157ms | 1205ms | 307ms | 1205ms | — | ⬜ NO SLA |
| TC_004 | `/api/verify-email` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_012 | `/api/sub-statuses` | `GET` | 160ms | 1981ms | 364ms | 1981ms | — | ⬜ NO SLA |
| TC_022 | `/api/payments/checkUserSubscription` | `GET` | 163ms | 202ms | 173ms | 202ms | — | ⬜ NO SLA |
| TC_030 | `/api/accounts/store/:storeId` | `GET` | 162ms | 299ms | 178ms | 299ms | — | ⬜ NO SLA |
| TC_031 | `/api/notion/notion_data` | `GET` | 441ms | 1536ms | 585ms | 1536ms | — | ⬜ NO SLA |
| TC_032 | `/api/shopify/checkUser` | `GET` | 164ms | 261ms | 177ms | 261ms | — | ⬜ NO SLA |
| TC_033 | `/api/shopify/shop` | `GET` | 162ms | 203ms | 170ms | 203ms | — | ⬜ NO SLA |
| TC_034 | `/api/shopify/check-store-exists` | `GET` | 162ms | 4051ms | 674ms | 4051ms | — | ⬜ NO SLA |
| TC_036 | `/api/shopify/auth` | `GET` | 159ms | 246ms | 170ms | 246ms | — | ⬜ NO SLA |
| TC_041 | `/api/store/` | `GET` | 1285ms | 5564ms | 2407ms | 5564ms | — | ⬜ NO SLA |
| TC_042 | `/api/store/trust/confirmation-pending-tags` | `GET` | 166ms | 3844ms | 582ms | 3844ms | — | ⬜ NO SLA |
| TC_050 | `/api/store-names` | `GET` | 462ms | 3972ms | 1024ms | 3972ms | — | ⬜ NO SLA |
| TC_054 | `/api/youcan/auth` | `GET` | 159ms | 1207ms | 363ms | 1207ms | — | ⬜ NO SLA |
| TC_055 | `/api/youcan/callback` | `GET` | 159ms | 211ms | 166ms | 211ms | — | ⬜ NO SLA |
| TC_056 | `/api/youcan/store-info` | `GET` | 159ms | 380ms | 191ms | 380ms | — | ⬜ NO SLA |
| TC_060 | `/api/salla/auth` | `GET` | 158ms | 2597ms | 611ms | 2597ms | — | ⬜ NO SLA |
| TC_061 | `/api/salla/callback` | `GET` | 159ms | 2102ms | 583ms | 2102ms | — | ⬜ NO SLA |
| TC_068 | `/api/orders/duplicates/:orderId` | `GET` | 203ms | 2262ms | 687ms | 2262ms | — | ⬜ NO SLA |
| TC_072 | `/api/orders/substatusOrders` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_073 | `/api/orders/seller-orders` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_075 | `/api/orders/couriers` | `GET` | 184ms | 1296ms | 679ms | 1296ms | — | ⬜ NO SLA |
| TC_076 | `/api/orders/batch-ids` | `GET` | 182ms | 4609ms | 2560ms | 4609ms | — | ⬜ NO SLA |
| TC_081 | `/api/orders/proccessedOrders` | `GET` | 185ms | 5905ms | 1746ms | 5905ms | — | ⬜ NO SLA |
| TC_082 | `/api/orders/tags` | `GET` | 194ms | 647ms | 398ms | 647ms | — | ⬜ NO SLA |
| TC_085 | `/api/orders/batches/dip` | `GET` | 180ms | 2037ms | 637ms | 2037ms | — | ⬜ NO SLA |
| TC_094 | `/api/orders/store/:storeId` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_096 | `/api/orders/:orderId/conversation/media` | `GET` | 162ms | 462ms | 200ms | 462ms | — | ⬜ NO SLA |
| TC_097 | `/api/orders/:orderId/conversation` | `GET` | 592ms | 1009ms | 808ms | 1009ms | — | ⬜ NO SLA |
| TC_107 | `/api/orders/dispatch-batches` | `GET` | 165ms | 2106ms | 801ms | 2106ms | — | ⬜ NO SLA |
| TC_110 | `/api/orders/tracking-generation-report` | `GET` | 163ms | 592ms | 345ms | 592ms | — | ⬜ NO SLA |
| TC_111 | `/api/orders/vendors` | `GET` | 166ms | 313ms | 185ms | 313ms | — | ⬜ NO SLA |
| TC_114 | `/api/orders/substatus-orders-for-csv` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_117 | `/api/tags/` | `GET` | 171ms | 201ms | 182ms | 201ms | — | ⬜ NO SLA |
| TC_120 | `/api/tags/statuses` | `GET` | 165ms | 210ms | 173ms | 210ms | — | ⬜ NO SLA |
| TC_122 | `/api/billing/status` | `GET` | 171ms | 198ms | 177ms | 198ms | — | ⬜ NO SLA |
| TC_124 | `/api/billing/shopify/callback` | `GET` | 159ms | 405ms | 190ms | 405ms | — | ⬜ NO SLA |
| TC_125 | `/api/billing/shopify/stores` | `GET` | 165ms | 3823ms | 671ms | 3823ms | — | ⬜ NO SLA |
| TC_126 | `/api/admin/gold-subscriptions/users/gold` | `GET` | 162ms | 444ms | 199ms | 444ms | — | ⬜ NO SLA |
| TC_127 | `/api/admin/gold-subscriptions/users` | `GET` | 163ms | 306ms | 184ms | 306ms | — | ⬜ NO SLA |
| TC_132 | `/api/admin/agency-registrations/applications` | `GET` | 179ms | 244ms | 188ms | 244ms | — | ⬜ NO SLA |
| TC_134 | `/api/admin/agency-registrations/commission-models` | `GET` | 165ms | 449ms | 204ms | 449ms | — | ⬜ NO SLA |
| TC_135 | `/api/admin/agency-registrations/commission-models/manage` | `GET` | 169ms | 330ms | 200ms | 330ms | — | ⬜ NO SLA |
| TC_143 | `/api/imile/token` | `GET` | 162ms | 407ms | 191ms | 407ms | — | ⬜ NO SLA |

**Summary:** 7 passed · 0 warning · 2 failed · 49 skipped
**Regressions vs previous run:** none

## Run #002

_Date: 2026-05-04 09:16:49 UTC | Environment: Production | Iterations: 10 (9 effective) | Triggered by: manual_

| TC ID | API Endpoint | Method | Min | Max | Avg | p95 | SLA Goal | Result |
|-------|-------------|--------|-----|-----|-----|-----|----------|--------|
| TC_001 | `/api/login` | `POST` | 165ms | 4708ms | 681ms | 4708ms | ≤ 1514ms | ✅ PASS |
| TC_009 | `/api/dashboard/data` | `GET` | 169ms | 2059ms | 410ms | 2059ms | ≤ 225ms | ❌ FAIL |
| TC_070 | `/api/orders/status-counts` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_095 | `/api/orders/orderDetails/:orderId` | `GET` | 310ms | 862ms | 470ms | 862ms | ≤ 3329ms | ✅ PASS |
| TC_007 | `/api/teams` | `GET` | 162ms | 6855ms | 1062ms | 6855ms | ≤ 281ms | ❌ FAIL |
| TC_008 | `/api/agents` | `GET` | 163ms | 275ms | 206ms | 275ms | ≤ 298ms | ✅ PASS |
| TC_013 | `/api/inventory/seller-inventory` | `GET` | 173ms | 318ms | 193ms | 318ms | ≤ 248ms | ✅ PASS |
| TC_014 | `/api/inventory/seller-inventory/export` | `GET` | 172ms | 361ms | 194ms | 361ms | ≤ 2772ms | ✅ PASS |
| TC_015 | `/api/inventory/purchase-order/:variantId` | `GET` | 174ms | 264ms | 187ms | 264ms | ≤ 768ms | ✅ PASS |
| TC_016 | `/api/inventory/purchase-order/orders/:variantId` | `GET` | 169ms | 277ms | 183ms | 277ms | ≤ 333ms | ✅ PASS |
| TC_017 | `/api/inventory/inventory-movements/:variantId` | `GET` | 171ms | 364ms | 193ms | 364ms | ≤ 4586ms | ✅ PASS |
| TC_071 | `/api/orders/order-analytics` | `GET` | 170ms | 371ms | 193ms | 371ms | ≤ 564ms | ✅ PASS |
| TC_083 | `/api/orders/remarks` | `GET` | 175ms | 295ms | 194ms | 295ms | ≤ 218ms | ✅ PASS |
| TC_103 | `/api/orders/:orderId/logs` | `GET` | 172ms | 296ms | 187ms | 296ms | ≤ 232ms | ✅ PASS |
| TC_003 | `/api/auth/check-email` | `GET` | 165ms | 224ms | 172ms | 224ms | ≤ 234ms | ✅ PASS |
| TC_004 | `/api/verify-email` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_012 | `/api/sub-statuses` | `GET` | 164ms | 1951ms | 483ms | 1951ms | ≤ 278ms | ❌ FAIL |
| TC_022 | `/api/payments/checkUserSubscription` | `GET` | 169ms | 284ms | 182ms | 284ms | ≤ 406ms | ✅ PASS |
| TC_030 | `/api/accounts/store/:storeId` | `GET` | 167ms | 282ms | 181ms | 282ms | ≤ 1314ms | ✅ PASS |
| TC_031 | `/api/notion/notion_data` | `GET` | 478ms | 709ms | 522ms | 709ms | ≤ 2841ms | ✅ PASS |
| TC_032 | `/api/shopify/checkUser` | `GET` | 169ms | 283ms | 182ms | 283ms | ≤ 4500ms | ✅ PASS |
| TC_033 | `/api/shopify/shop` | `GET` | 166ms | 359ms | 189ms | 359ms | ≤ 3021ms | ✅ PASS |
| TC_034 | `/api/shopify/check-store-exists` | `GET` | 166ms | 330ms | 186ms | 330ms | ≤ 568ms | ✅ PASS |
| TC_036 | `/api/shopify/auth` | `GET` | 164ms | 361ms | 187ms | 361ms | ≤ 2459ms | ✅ PASS |
| TC_041 | `/api/store/` | `GET` | 1268ms | 1376ms | 1305ms | 1376ms | ≤ 6308ms | ✅ PASS |
| TC_042 | `/api/store/trust/confirmation-pending-tags` | `GET` | 171ms | 2204ms | 654ms | 2204ms | ≤ 2439ms | ✅ PASS |
| TC_050 | `/api/store-names` | `GET` | 462ms | 493ms | 476ms | 493ms | ≤ 2570ms | ✅ PASS |
| TC_054 | `/api/youcan/auth` | `GET` | 164ms | 1971ms | 366ms | 1971ms | ≤ 390ms | ✅ PASS |
| TC_055 | `/api/youcan/callback` | `GET` | 163ms | 1961ms | 378ms | 1961ms | ≤ 412ms | ✅ PASS |
| TC_056 | `/api/youcan/store-info` | `GET` | 163ms | 291ms | 179ms | 291ms | ≤ 232ms | ✅ PASS |
| TC_060 | `/api/salla/auth` | `GET` | 163ms | 342ms | 184ms | 342ms | ≤ 1064ms | ✅ PASS |
| TC_061 | `/api/salla/callback` | `GET` | 163ms | 385ms | 189ms | 385ms | ≤ 376ms | ✅ PASS |
| TC_068 | `/api/orders/duplicates/:orderId` | `GET` | 206ms | 1926ms | 421ms | 1926ms | ≤ 442ms | ✅ PASS |
| TC_072 | `/api/orders/substatusOrders` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_073 | `/api/orders/seller-orders` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_075 | `/api/orders/couriers` | `GET` | 616ms | 1599ms | 1028ms | 1599ms | — | ⬜ NO SLA |
| TC_076 | `/api/orders/batch-ids` | `GET` | 174ms | 3391ms | 1177ms | 3391ms | — | ⬜ NO SLA |
| TC_081 | `/api/orders/proccessedOrders` | `GET` | 187ms | 564ms | 252ms | 564ms | ≤ 3195ms | ✅ PASS |
| TC_082 | `/api/orders/tags` | `GET` | 182ms | 2028ms | 589ms | 2028ms | ≤ 357ms | ❌ FAIL |
| TC_085 | `/api/orders/batches/dip` | `GET` | 165ms | 217ms | 185ms | 217ms | ≤ 356ms | ✅ PASS |
| TC_094 | `/api/orders/store/:storeId` | `GET` | 267ms | 4250ms | 1221ms | 4250ms | ≤ 590ms | ❌ FAIL |
| TC_096 | `/api/orders/:orderId/conversation/media` | `GET` | 260ms | 3692ms | 1076ms | 3692ms | ≤ 322ms | ❌ FAIL |
| TC_097 | `/api/orders/:orderId/conversation` | `GET` | 794ms | 3277ms | 1524ms | 3277ms | ≤ 2580ms | ✅ PASS |
| TC_107 | `/api/orders/dispatch-batches` | `GET` | 624ms | 5117ms | 2425ms | 5117ms | ≤ 238ms | ❌ FAIL |
| TC_110 | `/api/orders/tracking-generation-report` | `GET` | 166ms | 3379ms | 787ms | 3379ms | ≤ 315ms | ❌ FAIL |
| TC_111 | `/api/orders/vendors` | `GET` | 165ms | 1105ms | 385ms | 1105ms | ≤ 863ms | ✅ PASS |
| TC_114 | `/api/orders/substatus-orders-for-csv` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_117 | `/api/tags/` | `GET` | 169ms | 4568ms | 1272ms | 4568ms | — | ⬜ NO SLA |
| TC_120 | `/api/tags/statuses` | `GET` | 165ms | 2020ms | 413ms | 2020ms | — | ⬜ NO SLA |
| TC_122 | `/api/billing/status` | `GET` | 171ms | 204ms | 176ms | 204ms | — | ⬜ NO SLA |
| TC_124 | `/api/billing/shopify/callback` | `GET` | 160ms | 167ms | 162ms | 167ms | ≤ 196ms | ✅ PASS |
| TC_125 | `/api/billing/shopify/stores` | `GET` | 165ms | 258ms | 179ms | 258ms | ≤ 9184ms | ✅ PASS |
| TC_126 | `/api/admin/gold-subscriptions/users/gold` | `GET` | 163ms | 166ms | 164ms | 166ms | ≤ 215ms | ✅ PASS |
| TC_127 | `/api/admin/gold-subscriptions/users` | `GET` | 163ms | 213ms | 178ms | 213ms | ≤ 216ms | ✅ PASS |
| TC_132 | `/api/admin/agency-registrations/applications` | `GET` | 179ms | 2980ms | 602ms | 2980ms | ≤ 238ms | ❌ FAIL |
| TC_134 | `/api/admin/agency-registrations/commission-models` | `GET` | 166ms | 2427ms | 418ms | 2427ms | ≤ 226ms | ❌ FAIL |
| TC_135 | `/api/admin/agency-registrations/commission-models/manage` | `GET` | 170ms | 181ms | 173ms | 181ms | ≤ 250ms | ✅ PASS |
| TC_143 | `/api/imile/token` | `GET` | 163ms | 2082ms | 398ms | 2082ms | ≤ 491ms | ✅ PASS |

**Summary:** 38 passed · 0 warning · 10 failed · 10 skipped
**Regressions vs Run #001:** 18 endpoint(s) degraded by >15%
  - `POST /api/login` — avg 165ms → 681ms (+313%)
  - `GET /api/dashboard/data` — avg 168ms → 410ms (+144%)
  - `GET /api/teams` — avg 905ms → 1062ms (+17%)
  - `GET /api/inventory/seller-inventory/export` — avg 168ms → 194ms (+15%)
  - `GET /api/sub-statuses` — avg 364ms → 483ms (+33%)
  - `GET /api/youcan/callback` — avg 166ms → 378ms (+128%)
  - `GET /api/orders/couriers` — avg 679ms → 1028ms (+51%)
  - `GET /api/orders/tags` — avg 398ms → 589ms (+48%)
  - `GET /api/orders/:orderId/conversation/media` — avg 200ms → 1076ms (+438%)
  - `GET /api/orders/:orderId/conversation` — avg 808ms → 1524ms (+89%)
  - `GET /api/orders/dispatch-batches` — avg 801ms → 2425ms (+203%)
  - `GET /api/orders/tracking-generation-report` — avg 345ms → 787ms (+128%)
  - `GET /api/orders/vendors` — avg 185ms → 385ms (+108%)
  - `GET /api/tags/` — avg 182ms → 1272ms (+599%)
  - `GET /api/tags/statuses` — avg 173ms → 413ms (+139%)
  - `GET /api/admin/agency-registrations/applications` — avg 188ms → 602ms (+220%)
  - `GET /api/admin/agency-registrations/commission-models` — avg 204ms → 418ms (+105%)
  - `GET /api/imile/token` — avg 191ms → 398ms (+108%)

## Run #003

_Date: 2026-05-05 13:28:16 UTC | Environment: Production | Iterations: 10 (9 effective) | Triggered by: manual_

| TC ID | API Endpoint | Method | Min | Max | Avg | p95 | SLA Goal | Result |
|-------|-------------|--------|-----|-----|-----|-----|----------|--------|
| TC_001 | `/api/login` | `POST` | 150ms | 154ms | 151ms | 154ms | ≤ 1514ms | ✅ PASS |
| TC_009 | `/api/dashboard/data` | `GET` | 154ms | 159ms | 156ms | 159ms | ≤ 225ms | ✅ PASS |
| TC_070 | `/api/orders/status-counts` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_095 | `/api/orders/orderDetails/:orderId` | `GET` | 294ms | 3444ms | 2242ms | 3444ms | ≤ 3329ms | ✅ PASS |
| TC_007 | `/api/teams` | `GET` | 149ms | 8603ms | 2720ms | 8603ms | ≤ 281ms | ❌ FAIL |
| TC_008 | `/api/agents` | `GET` | 144ms | 250ms | 158ms | 250ms | ≤ 298ms | ✅ PASS |
| TC_013 | `/api/inventory/seller-inventory` | `GET` | 156ms | 177ms | 163ms | 177ms | ≤ 248ms | ✅ PASS |
| TC_014 | `/api/inventory/seller-inventory/export` | `GET` | 154ms | 1258ms | 299ms | 1258ms | ≤ 2772ms | ✅ PASS |
| TC_015 | `/api/inventory/purchase-order/:variantId` | `GET` | 156ms | 168ms | 159ms | 168ms | ≤ 768ms | ✅ PASS |
| TC_016 | `/api/inventory/purchase-order/orders/:variantId` | `GET` | 151ms | 188ms | 161ms | 188ms | ≤ 333ms | ✅ PASS |
| TC_017 | `/api/inventory/inventory-movements/:variantId` | `GET` | 151ms | 158ms | 153ms | 158ms | ≤ 4586ms | ✅ PASS |
| TC_071 | `/api/orders/order-analytics` | `GET` | 150ms | 154ms | 152ms | 154ms | ≤ 564ms | ✅ PASS |
| TC_083 | `/api/orders/remarks` | `GET` | 153ms | 162ms | 157ms | 162ms | ≤ 218ms | ✅ PASS |
| TC_103 | `/api/orders/:orderId/logs` | `GET` | 153ms | 158ms | 156ms | 158ms | ≤ 232ms | ✅ PASS |
| TC_003 | `/api/auth/check-email` | `GET` | 146ms | 150ms | 148ms | 150ms | ≤ 234ms | ✅ PASS |
| TC_004 | `/api/verify-email` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_012 | `/api/sub-statuses` | `GET` | 146ms | 2945ms | 698ms | 2945ms | ≤ 278ms | ❌ FAIL |
| TC_022 | `/api/payments/checkUserSubscription` | `GET` | 150ms | 240ms | 163ms | 240ms | ≤ 406ms | ✅ PASS |
| TC_030 | `/api/accounts/store/:storeId` | `GET` | 148ms | 2152ms | 375ms | 2152ms | ≤ 1314ms | ✅ PASS |
| TC_031 | `/api/notion/notion_data` | `GET` | 426ms | 3833ms | 873ms | 3833ms | ≤ 2841ms | ✅ PASS |
| TC_032 | `/api/shopify/checkUser` | `GET` | 150ms | 159ms | 153ms | 159ms | ≤ 4500ms | ✅ PASS |
| TC_033 | `/api/shopify/shop` | `GET` | 148ms | 184ms | 153ms | 184ms | ≤ 3021ms | ✅ PASS |
| TC_034 | `/api/shopify/check-store-exists` | `GET` | 148ms | 173ms | 152ms | 173ms | ≤ 568ms | ✅ PASS |
| TC_036 | `/api/shopify/auth` | `GET` | 145ms | 151ms | 147ms | 151ms | ≤ 2459ms | ✅ PASS |
| TC_041 | `/api/store/` | `GET` | 1096ms | 7205ms | 4369ms | 7205ms | ≤ 6308ms | ✅ PASS |
| TC_042 | `/api/store/trust/confirmation-pending-tags` | `GET` | 153ms | 6375ms | 1219ms | 6375ms | ≤ 2439ms | ✅ PASS |
| TC_050 | `/api/store-names` | `GET` | 1421ms | 5092ms | 2919ms | 5092ms | ≤ 2570ms | ⚠️  WARN |
| TC_054 | `/api/youcan/auth` | `GET` | 144ms | 147ms | 145ms | 147ms | ≤ 390ms | ✅ PASS |
| TC_055 | `/api/youcan/callback` | `GET` | 145ms | 150ms | 146ms | 150ms | ≤ 412ms | ✅ PASS |
| TC_056 | `/api/youcan/store-info` | `GET` | 145ms | 149ms | 146ms | 149ms | ≤ 232ms | ✅ PASS |
| TC_060 | `/api/salla/auth` | `GET` | 145ms | 147ms | 146ms | 147ms | ≤ 1064ms | ✅ PASS |
| TC_061 | `/api/salla/callback` | `GET` | 144ms | 1004ms | 241ms | 1004ms | ≤ 376ms | ✅ PASS |
| TC_068 | `/api/orders/duplicates/:orderId` | `GET` | 167ms | 3885ms | 865ms | 3885ms | ≤ 442ms | ❌ FAIL |
| TC_072 | `/api/orders/substatusOrders` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_073 | `/api/orders/seller-orders` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_075 | `/api/orders/couriers` | `GET` | 149ms | 173ms | 154ms | 173ms | — | ⬜ NO SLA |
| TC_076 | `/api/orders/batch-ids` | `GET` | 150ms | 160ms | 153ms | 160ms | — | ⬜ NO SLA |
| TC_081 | `/api/orders/proccessedOrders` | `GET` | 150ms | 5001ms | 1247ms | 5001ms | ≤ 3195ms | ✅ PASS |
| TC_082 | `/api/orders/tags` | `GET` | 154ms | 3310ms | 506ms | 3310ms | ≤ 357ms | ❌ FAIL |
| TC_085 | `/api/orders/batches/dip` | `GET` | 149ms | 200ms | 156ms | 200ms | ≤ 356ms | ✅ PASS |
| TC_094 | `/api/orders/store/:storeId` | `GET` | 307ms | 3670ms | 1065ms | 3670ms | ≤ 590ms | ❌ FAIL |
| TC_096 | `/api/orders/:orderId/conversation/media` | `GET` | 148ms | 172ms | 153ms | 172ms | ≤ 322ms | ✅ PASS |
| TC_097 | `/api/orders/:orderId/conversation` | `GET` | 576ms | 2448ms | 1040ms | 2448ms | ≤ 2580ms | ✅ PASS |
| TC_107 | `/api/orders/dispatch-batches` | `GET` | 148ms | 2566ms | 580ms | 2566ms | ≤ 238ms | ❌ FAIL |
| TC_110 | `/api/orders/tracking-generation-report` | `GET` | 147ms | 4974ms | 1779ms | 4974ms | ≤ 315ms | ❌ FAIL |
| TC_111 | `/api/orders/vendors` | `GET` | 149ms | 3946ms | 572ms | 3946ms | ≤ 863ms | ✅ PASS |
| TC_114 | `/api/orders/substatus-orders-for-csv` | `GET` | — | — | — | — | — | ⏭️ SKIPPED |
| TC_117 | `/api/tags/` | `GET` | 152ms | 1843ms | 506ms | 1843ms | — | ⬜ NO SLA |
| TC_120 | `/api/tags/statuses` | `GET` | 148ms | 156ms | 150ms | 156ms | — | ⬜ NO SLA |
| TC_122 | `/api/billing/status` | `GET` | 154ms | 166ms | 159ms | 166ms | — | ⬜ NO SLA |
| TC_124 | `/api/billing/shopify/callback` | `GET` | 143ms | 147ms | 145ms | 147ms | ≤ 196ms | ✅ PASS |
| TC_125 | `/api/billing/shopify/stores` | `GET` | 148ms | 160ms | 150ms | 160ms | ≤ 9184ms | ✅ PASS |
| TC_126 | `/api/admin/gold-subscriptions/users/gold` | `GET` | 146ms | 2964ms | 548ms | 2964ms | ≤ 215ms | ❌ FAIL |
| TC_127 | `/api/admin/gold-subscriptions/users` | `GET` | 147ms | 154ms | 150ms | 154ms | ≤ 216ms | ✅ PASS |
| TC_132 | `/api/admin/agency-registrations/applications` | `GET` | 151ms | 155ms | 152ms | 155ms | ≤ 238ms | ✅ PASS |
| TC_134 | `/api/admin/agency-registrations/commission-models` | `GET` | 283ms | 2392ms | 686ms | 2392ms | ≤ 226ms | ❌ FAIL |
| TC_135 | `/api/admin/agency-registrations/commission-models/manage` | `GET` | 254ms | 2116ms | 990ms | 2116ms | ≤ 250ms | ❌ FAIL |
| TC_143 | `/api/imile/token` | `GET` | 223ms | 562ms | 322ms | 562ms | ≤ 491ms | ✅ PASS |

**Summary:** 37 passed · 1 warning · 10 failed · 10 skipped
**Regressions vs Run #002:** 17 endpoint(s) degraded by >15%
  - `GET /api/orders/orderDetails/:orderId` — avg 470ms → 2242ms (+377%)
  - `GET /api/teams` — avg 1062ms → 2720ms (+156%)
  - `GET /api/inventory/seller-inventory/export` — avg 194ms → 299ms (+54%)
  - `GET /api/sub-statuses` — avg 483ms → 698ms (+45%)
  - `GET /api/accounts/store/:storeId` — avg 181ms → 375ms (+107%)
  - `GET /api/notion/notion_data` — avg 522ms → 873ms (+67%)
  - `GET /api/store/` — avg 1305ms → 4369ms (+235%)
  - `GET /api/store/trust/confirmation-pending-tags` — avg 654ms → 1219ms (+86%)
  - `GET /api/store-names` — avg 476ms → 2919ms (+513%)
  - `GET /api/salla/callback` — avg 189ms → 241ms (+28%)
  - `GET /api/orders/duplicates/:orderId` — avg 421ms → 865ms (+105%)
  - `GET /api/orders/proccessedOrders` — avg 252ms → 1247ms (+395%)
  - `GET /api/orders/tracking-generation-report` — avg 787ms → 1779ms (+126%)
  - `GET /api/orders/vendors` — avg 385ms → 572ms (+49%)
  - `GET /api/admin/gold-subscriptions/users/gold` — avg 164ms → 548ms (+234%)
  - `GET /api/admin/agency-registrations/commission-models` — avg 418ms → 686ms (+64%)
  - `GET /api/admin/agency-registrations/commission-models/manage` — avg 173ms → 990ms (+472%)
