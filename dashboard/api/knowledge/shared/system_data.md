# Zambeel System Data — Live Production Database
_Queried from production (zambeel-production.c2knh0obsufa.eu-west-3.rds.amazonaws.com) on 2026-06-01_

---

## Live Counts
<!-- LIVE_COUNTS_START -->
_Last updated: 2026-06-18 09:04_

| Metric | Count |
|--------|-------|
| Total Orders | 779,515 |
| Total Tickets | 24,150 |
| Total Stores | 22,884 |
| Total Users | 61,228 |
| Supported Countries | 9 |
<!-- LIVE_COUNTS_END -->

---

## Supported Countries
Source: `SELECT * FROM countries ORDER BY id`

| ID | Country | Currency Code |
|----|---------|---------------|
| 1  | UAE | AED |
| 2  | Qatar | QAR |
| 3  | Kuwait | KWD |
| 4  | Saudi Arabia | SAR |
| 5  | Pakistan | PKR |
| 6  | Oman | OMR |
| 7  | Bahrain | BHD |
| 8  | Iraq | IQD (no commission model yet) |
| 9  | United States | USD (no commission model yet) |

Iraq and United States are in the countries table but have no commission model rules configured yet.

---

## Store Platforms
Source: `SELECT DISTINCT platform FROM stores`
Total stores in production: **21,611**

| Platform |
|----------|
| Amazon |
| easyorders |
| Ebay |
| Facebook Marketplace |
| lightfunnels |
| Salla |
| shopify |
| Shopify Manual |
| Whatsapp Marketplace |
| WooCommerce |
| youcan |
| Zid |

---

## Courier Partners
Source: `SELECT DISTINCT name FROM courier_partners ORDER BY name`
Table: `courier_partners` (not `dispatch_batches` — courier is linked via `fk_courier_id`)

| Courier Name |
|--------------|
| ahl |
| ARA DOM |
| Aramex |
| Arrtx |
| barq_raftar |
| c3x |
| Dalilee |
| dex |
| Do Deliver |
| ECO |
| fast_ex |
| Flow Express |
| imile - KSA |
| imile - UAE |
| IW Express |
| JnT |
| Labaih |
| leopards |
| Live Tracking N/A |
| Logistiq |
| M&P |
| next_step |
| Porter |
| Postex Pakistan |
| qwqer |
| SaudiPost |
| SLS |
| Smartlane |
| stallion |
| TAM Logistics |
| Tamex |
| Tawseel |
| tcs |
| trax |
| trazno |
| Velox |
| Wareone |
| Zajel |

---

## Order Status Structure
The `orders.status` column stores a **JSON object** with three keys: `status`, `substatus`, `tag`.

### Main Statuses (top-level)
| Status |
|--------|
| Received |
| Confirmation Pending |
| Approved |
| Dispatching in Process |
| Shipped |
| Delivered |
| Undelivered |
| Return in Transit |
| Return |
| Cancelled |

### Full Status → Substatus → Tag Matrix
Source: `SELECT DISTINCT status FROM orders`

**Received**
- Pending Reseller Submission → Awaiting Push To Zambeel
- Pending Reseller Submission → Awaiting Push
- Pending Reseller Submission → Send Message

**Confirmation Pending**
- Confirmation in Process → 2/4/6 Calls Done (No Response)
- Confirmation in Process → Customer Replied
- Confirmation in Process → Details Requested from Reseller
- Confirmation in Process → Message Sent
- Confirmation in Process → Order on Hold- Contact Support
- Confirmation in Process → Ready to Pack
- Confirmation in Process → Send Message
- On Hold by Customer → Contact Again Address/Variant/Call Back
- On Hold by Customer → Schedule Before Delivery
- On Hold by Customer → SKU Required
- Address Verification in Process → Address Verification in Process / Send Message

**Approved**
- Checking Inventory For Dispatching → Checking Inventory
- Inventory In Transit → Dispatch in 1-2 Days / Dispatch in 2-3 Days

**Dispatching in Process**
- Awaiting Courier Pickup → (empty) / Ready to Dispatch

**Shipped**
- In Transit → Delivery Attempt in 1-2 Days / In Transit To Customer City / Order needs Attention
- In Delivery → Rider on the Way / Order needs Attention / Delivery Attempt Failed → Customer Unreachable
- Scheduled by Customer → Customer Requested Future Delivery / Scheduled by Customer

**Delivered**
- Delivered → Delivered

**Undelivered**
- Customer Refused - Assigned to CS Team → Cancelled by Customer / No Cash / Open package request / Duplicate Order / FA tags
- Customer Uncontactable - Assigned to CS Team → Incomplete/Bad Address / Uncontactable and Unreachable
- Request to Re-Scheduled → Customer Requested Future Delivery / FA variants
- Request to Return → FA - various cancellation reasons

**Return in Transit**
- Returning → Cancelled by Customer / Item Lost / Long Reschedule / No Cash / Open package request / Package Discrepancy / Uncontactable (No Response)

**Return**
- Returned → Customer cancelled the Order / Did not Order / Long Reschedule / No Cash / Package Discrepancy / Uncontactable (No Response) / Duplicate Order

**Cancelled**
- Customer Refused → Change of Mind / Price Issue / Did not Order / Customer Not Reachable / Not Available/Travelling / Open Package Request / No Response By Reseller
- Invalid Order → Duplicate Order / Fraud Orders / Invalid Number / Invalid Order Details / No Service Area / Test/Fake Order / Wrong Number / On Sellers Request / On Internal Team Request
- Product Not Available → Out of Stock / Not Available on Zambeel

---

## Commission Types
Source: `agency_commission_model_rules.commission_type` (enum column)

| DB Value | Meaning |
|----------|---------|
| `flat_per_delivered_order` | Fixed amount per delivered order |
| `percentage_of_delivered_revenue` | Percentage of revenue from delivered orders |

Commission rules are in table `agency_commission_model_rules`, linked to `agency_commission_models`.
There is **no** `commission_rules` table — the correct table is `agency_commission_model_rules`.

---

## Key Table Names (corrected)
| Concept | Actual Table |
|---------|-------------|
| Couriers | `courier_partners` |
| Countries | `countries` |
| Commission models | `agency_commission_models` |
| Commission rules | `agency_commission_model_rules` |
| Commission records | `agency_commission_records` |
| Dispatch batches | `dispatch_batches` (links courier via `fk_courier_id`) |

---

## Dispatch Batch Statuses (from enum columns)
- **tracking_status**: New, Generating, Partial, Generated, Failed
- **document_status**: Not Ready, Preparing, Ready, Invalidated
