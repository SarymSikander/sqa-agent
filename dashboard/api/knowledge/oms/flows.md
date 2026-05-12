# OMS — Step-by-Step User Flows

## Flow 1: Admin Login

1. Navigate to `/login`
2. Enter email + password (Firebase `signInWithEmailAndPassword`)
3. Firebase returns ID token → `POST /login` with `{idToken}`
4. Zambeel returns JWT + user data with `role: 'Admin'` or `role: 'Agent'`
5. `RootRedirect` checks role → redirects to `/orders-management/dashboard`
6. Sidebar loads with role-appropriate items

**Expected landing URL:** `/orders-management/dashboard`

---

## Flow 2: Create Commission Model

1. Navigate to `/orders-management/commission-models`
2. Assert page title: "Commission Models"
3. Click `+ New Model` button
4. Drawer opens — assert title contains "Create Commission Model"
5. Fill `Model Name*` field: `input[placeholder='Enter model name']`
6. Click `+ Add Rule` to add a country rule
7. Select country from `Country*` dropdown
   - After selection, `Currency*` field auto-fills with ISO code
8. Select commission type from `Type*` dropdown:
   - `% of Revenue` → `percentage_of_delivered_revenue`
   - `Flat per Order` → `flat_per_delivered_order`
9. Enter a positive number in `Value*` field
10. Verify `Currency*` field (auto-filled, length = 3)
11. Click `Save Model`
12. Assert drawer closes
13. Assert new model card appears in the list with correct name and rules

**Validation triggers:**
- Duplicate country in same model → alert: "Each country can only appear once inside the same model."
- Empty model name → `Save Model` button stays disabled
- Missing currency (not 3 chars) → `Save Model` button stays disabled

---

## Flow 3: Edit Commission Model

1. Navigate to `/orders-management/commission-models`
2. Find a model row — click `Edit` button
3. Drawer opens with existing values pre-filled
4. Modify any field
5. Click `Save Model`
6. Assert changes reflected in model card

---

## Flow 4: Review & Approve Agency Application

1. Navigate to `/orders-management/agency-registrations`
2. Assert tabs: All | Pending | Approved | OnHold | Rejected
3. Click `Pending` tab
4. Find an application row — click `Review` button
5. Drawer opens showing: agency name, unique ID, Country, City, Phone, POC, Status, Submitted date
6. Click `Identity Document` → opens file in new tab
7. Click `Approve Agency` button
8. Sub-form appears: "Assign Commission Model"
9. Select commission model from dropdown: `Select commission model`
10. Click `Confirm Approve`
11. Application status changes to `Approved`
12. Agency unique ID becomes visible (format: `ZMB-AG-XXXXXX`)

---

## Flow 5: Put Agency Application On Hold

1. Navigate to `/orders-management/agency-registrations` → click `Pending` tab
2. Click `Review` on a pending application
3. Click `Put on Hold`
4. Sub-form appears: "Hold Reason"
5. Fill textarea: `input[placeholder='Explain what needs to be fixed...']` (min 3 chars)
6. Toggle checkbox "Allow applicant to resubmit documents" if needed
7. Click `Put on Hold` (button disabled until hold reason ≥ 3 chars)
8. Application moves to `OnHold` tab

---

## Flow 6: Reject Agency Application

1. Navigate to `/orders-management/agency-registrations` → click `Pending` tab
2. Click `Review` → click `Reject`
3. Sub-form appears: "Rejection Reason"
4. Fill textarea: `[placeholder='Reason for rejection...']` (min 3 chars)
5. Click `Confirm Reject` (disabled until reason ≥ 3 chars)
6. Application moves to `Rejected` tab

---

## Flow 7: Revoke Agency License

1. Navigate to `Approved` tab in Agency Registrations
2. Click `Review` on an approved agency
3. Click `Revoke License`
4. Agency license status changes to `Revoked`

---

## Flow 8: Revert Application to Pending

1. Navigate to `Rejected` tab in Agency Registrations
2. Click `Review` on a rejected application
3. Click `Revert to Pending`
4. Application returns to `Pending` tab

---

## Flow 9: Approve Orders (Bulk)

1. Navigate to `/orders-management/orders`
2. Click tab `Confirmation Pending`
3. Select orders via checkboxes
4. Click `Actions` dropdown → click `Approve`
5. Confirm bulk approval
6. Orders move to `Approved` status with substatus `Checking Inventory For Dispatching`

---

## Flow 10: Generate Dispatch Batches

1. Navigate to `/orders-management/dispatch-batches`
2. Click `Generate Batches` → `POST /orders/generate-batches` with `{country_id}`
3. Batches created (tracking_status: `New`)
4. Select a batch → click `Generate Tracking IDs`
5. Wait for status to change: `Generating` → `Generated` (or `Failed`)
6. Click `Generate Documents`
7. Wait for document_status: `Preparing` → `Ready`
8. Click `Download AWBs` → triggers `POST /orders/download-awbs`
9. Click `Download Packing List` → triggers `POST /orders/download-packing-list`

---

## Flow 11: Create Purchase Order

1. Navigate to `/orders-management/purchase-orders`
2. Click `Create PO`
3. Select country → `GET /purchase-orders/countries`
4. Select warehouse → `GET /purchase-orders/warehouses/country/:countryId`
5. Search SKU → `GET /purchase-orders/warehouses/:warehouseId/search?sku=X`
6. Add line items (SKU + quantity)
7. Click `Submit` (status: `Draft`)
8. PO created — appears in list with status badge `Draft`

---

## Flow 12: Grant Gold Access

1. Navigate to `/orders-management/gold-subscriptions`
2. Select search type: `Email` | `Phone` | `User ID`
3. Enter search value → click `Search`
4. Click `View Details` on a user
5. Click `Give Gold Access`
6. Enter expiry date
7. Confirm → API `POST /admin/gold-subscriptions/give`
8. User tab changes to appear in `Gold users` tab

---

## Flow 13: Create Admin Ticket

1. Navigate to `/orders-management/ticketing`
2. Click `Create New Ticket` (admin-initiated)
3. Search for store by name/ID
4. Optionally find order within store by order ID or number
5. Select category: `Order Issue` | `Catalog & Pricing Updates` | `Payments & Payouts`
6. Select sub-category (dependent on category)
7. Enter description (min 10, max 2000 chars)
8. Submit → `POST /tickets/admin`
9. Ticket appears in table with status `Pending`

---

## Flow 14: Update Ticket Status (Admin)

1. Open any ticket via `View` button
2. Ticket details modal opens
3. Change status dropdown to: `In Progress` | `Resolved`
4. Optionally assign to a team
5. Optionally add resolution notes in textarea
6. Click `Update Ticket`
7. Success message: "Ticket updated successfully!"
8. Modal reflects new status

---

## Flow 15: Inventory Movement (SKU to SKU)

1. Navigate to `/orders-management/inventory-movements`
2. Select movement type: `SKU → SKU`
3. Select reason: `SKU Merge` | `Wrong SKU Mapping` | `Repackaging` | etc.
4. Select source warehouse
5. Enter source variant SKU (search) → `POST /inventory-movements/find-variant`
6. Enter destination variant SKU
7. Enter quantity (min 1)
8. Submit → `POST /inventory-movements/transactions`
9. Movement appears with status `In Transit`

---

## Order Lifecycle (Reference)

```
Confirmation Pending
    ↓
Approved ←→ Cancelled
    ↓
Checking Inventory For Dispatching (substatus)
    ↓
Inventory In Transit → Calculating Dispatching Time (substatus)
    ↓
[Courier Assigned → Dispatch Batch → Tracking Generated]
    ↓
In Delivery
    ↓
Delivered | NDR (Non-Delivery Report)
    ↓
Return in Transit → Return
```
