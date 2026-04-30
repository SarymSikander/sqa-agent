# OMS — Pages Reference

Every page under the Admin/Agent portal, with route, component name, and purpose.

## Route Map

| Route | Component | Role | Purpose |
|-------|-----------|------|---------|
| `/orders-management/dashboard` | `OrdersDashBoard` | Admin/Agent | KPI metrics, real-time order analytics |
| `/orders-management/orders` | `Orders` | Admin/Agent | All orders across all stores; filter, search, edit, approve, cancel |
| `/orders-management/dispatch-batches` | `DispatchBatches` | Admin only | Courier dispatch batch management; generate tracking IDs and documents |
| `/orders-management/agents` | `AgentsTable` | Admin only | View and create agent accounts |
| `/orders-management/ratings-settings` | `ThresholdManager` | Admin only | Configure seller performance rating thresholds by country |
| `/orders-management/stores-settings` | `OmsStoreSettingsPage` | Admin only | View and edit all seller stores |
| `/orders-management/tags-management` | `TagsManagementPage` | Admin only | CRUD on order tags linked to statuses/sub-statuses |
| `/orders-management/purchase-orders` | `PurchaseOrdersPage` | Admin only | IMS purchase order list and creation |
| `/orders-management/purchase-orders/create` | `CreatePurchaseOrderComponent` | Admin only | Create a new purchase order |
| `/orders-management/purchase-orders/:poId/receive` | `ReceiveItemsComponents` | Admin only | Mark quantities received for a PO |
| `/orders-management/purchase-orders/:poId/submit` | `SubmitPurchaseOrderComponent` | Admin only | Submit PO to warehouse |
| `/orders-management/return-orders` | `ReturnOrdersPage` | Admin only | IMS return order list |
| `/orders-management/return-orders/create` | `CreateReturnOrderComponent` | Admin only | Create a new return order |
| `/orders-management/ticketing` | `TicketingV2` | Admin/Agent | Admin ticket queue: view, update, create admin tickets |
| `/orders-management/inventory-movements` | `InventoryMovements` | Admin only | Warehouse inventory movement management |
| `/orders-management/gold-subscriptions` | `OMSGoldSubscriptionsPage` | Admin only | Grant/extend/remove seller gold subscriptions |
| `/orders-management/agency-registrations` | `AgencyRegistrationsPage` | Admin only | Review and action agency applications |
| `/orders-management/commission-models` | `CommissionModelsPage` | Admin only | CRUD on agency commission models |
| `/orders-management/invoice-upload` | `InvoiceUploadPage` | Admin only | Upload invoices for seller stores |
| `/orders-management/invoice-update` | `InvoiceUpdatePage` | Admin only | Update existing invoices |
| `/orders-management/ticker-config` | `TickerConfigPage` | Admin only | Configure marquee ticker bar content |
| `/orders-management/profile` | `Profile` | Admin/Agent | Admin user profile page |

## Page-by-Page Detail

### Dashboard (`/orders-management/dashboard`)
- Real-time KPI cards for order counts, revenue, status breakdowns
- API: `GET /dashboard/data`

### Orders (`/orders-management/orders`)
**Tabs (left → right):**
All Orders | Confirmation Pending | Approved | Dispatching in Process | In Delivery | Undelivered | Delivered | Return in Transit | Return | Cancelled

**Search:** Placeholder `"Search orders"` — searches: order ID, tracking number, customer name, phone, store URL

**Filter button:** `Filter` (opens filter panel)

**Actions dropdown button:** `Actions`

**Actions items:** Update Statuses | Upload Orders | Approve | Cancel | Update Tag | Update Remarks | Assign Courier

**Empty state:** "No orders found"

### Commission Models (`/orders-management/commission-models`)
**Page heading:** "Commission Models"
**Subtitle:** "Define per-country commission rates for agencies."

### Agency Registrations (`/orders-management/agency-registrations`)
**Page heading:** "Agency Registrations"
**Subtitle:** "Review and manage agency applications."
**Tabs:** All | Pending | Approved | OnHold | Rejected

### Gold Subscriptions (`/orders-management/gold-subscriptions`)
**Search options:** Email | Phone | User ID
**Tabs:** All users | Gold users
**Buttons:** Search | Clear

### Agents (`/orders-management/agents`)
**Search placeholder:** "Search by Name, Email or Country"
**Button:** `Create Agent`

### Purchase Orders (`/orders-management/purchase-orders`)
**PO Status values:** Draft | Received | Partially Received | Cancelled | Submitted

### Dispatch Batches (`/orders-management/dispatch-batches`)
**tracking_status values:** New | Generating | Partial | Generated | Failed
**document_status values:** Not Ready | Preparing | Ready | Invalidated

### Inventory Movements (`/orders-management/inventory-movements`)
**Movement types:** SKU_TO_SKU | WAREHOUSE_TRANSFER | DAMAGED
**Status types:** In Transit | Received
