# Shared — Notifications & Toast Messages

All toast notifications use **react-toastify**. Config: position `top-right`, autoClose `3000ms`, max `4` toasts, RTL enabled for Arabic.

---

## Toast: Success Messages

| Message | Trigger |
|---------|---------|
| `"Order updated successfully"` | Saving order details in edit modal |
| `"Order approved successfully"` | Single/bulk approve action |
| `"Order cancelled successfully"` | Cancel order action |
| `"Order tag updated"` | Updating tag on order |
| `"Product added successfully"` | Adding product to order |
| `"Product removed from order"` | Removing product from order |
| `"Product updated successfully"` | Updating product on order |
| `"Packing list downloaded successfully"` | Download packing list |
| `"Document downloaded successfully"` | Download batch documents |
| `"All changes saved successfully"` | Batch save operation |
| `"Tag created successfully"` | Creating new order tag |
| `"Address updated successfully"` | Updating customer address |
| `"Financial details updated"` | Updating financial details in settings |
| `"Bank account connected successfully"` | Connecting bank account |
| `"Binance account connected successfully"` | Connecting Binance account |
| `"PayPal account connected successfully"` | Connecting PayPal account |
| `"Profile completed successfully!"` | Completing profile setup |
| `"Store settings updated successfully!"` | Saving store settings |
| `"Ticker updated successfully!"` | Updating ticker config (OMS) |
| `"Bifurcation settings updated successfully."` | Saving bifurcation settings |
| `"Confirmation settings updated successfully."` | Saving confirmation settings |
| `"Cannot receive items for an order that is not submitted"` | _(incorrectly uses toast.success — semantic bug)_ |

---

## Toast: Error Messages

| Message | Trigger |
|---------|---------|
| `"An error occurred while adding the product."` | Add product failure |
| `"An error occurred while processing your subscription"` | Subscription error |
| `"Error exporting PDF"` | PDF export failure |
| `"Error fetching gold products"` | Gold products API failure |
| `"Error searching for variant"` | Variant SKU search failure |
| `"Error fetching bank accounts"` | Bank accounts fetch failure |
| `"Failed to delete account"` | Delete account action failure |
| `"Failed to delete product"` | Delete product failure |
| `"Failed to fetch product information for this SKU."` | SKU lookup returns nothing |
| `"Failed to fetch return orders"` | Return orders API failure |
| `"Failed to initiate payment"` | Payment initiation failure |
| `"Failed to load batches"` | Dispatch batches load failure |
| `"Failed to load couriers"` | Couriers list load failure |
| `"Failed to load order remarks"` | Remarks load failure |
| `"Failed to load order tags"` | Tags load failure |
| `"Failed to load remarks"` | Remarks load failure (generic) |
| `"Failed to proceed with Shopify integration"` | Shopify OAuth initiation failure |
| `"Failed to process Shopify integration"` | Shopify OAuth callback failure |
| `"Failed to update account"` | Account update failure |
| `"Failed to update address"` | Address update failure |
| `"Failed to update financial details"` | Financial details update failure |
| `"Failed to update order tag"` | Order tag update failure |
| `"Failed to update product"` | Product update failure |
| `"Failed to update store"` | Store update failure |
| `"Failed to update ticker."` | Ticker config update failure |
| `"Failed to update trust status. Please try again."` | Trust status update failure |
| `"Invalid order or product data"` | Invalid data passed to operation |
| `"Order ID is missing"` | Missing order ID on action |
| `"Payment URL not found."` | Payment URL not returned by API |
| `"Please enter a SKU to search"` | Empty SKU on search |
| `"Please enter a SKU."` | Empty SKU on product add |
| `"Please enter a name."` | Empty name field |
| `"Please enter a valid email."` | Invalid email format |
| `"Please enter a valid phone number."` | Invalid phone format |
| `"Please fill all the required fields"` | Missing required form fields |
| `"Please select a batch"` | No batch selected for action |
| `"Please select a country."` | No country selected |
| `"Please select a courier and enter a batch name"` | Missing courier or batch name |
| `"Please select a team."` | No team selected for ticket |
| `"Store Already Exists"` / `"Store already exists"` | Duplicate store creation |
| `"Store ID is missing"` | Missing store ID |
| `"This SKU already exists in the order."` | Adding duplicate SKU to order |
| `"CSV file size limit exceeded"` | CSV file > max size |
| `"Failed to download document"` | Document download failure |
| `"Failed to download packing list"` | Packing list download failure |
| `"Failed to fetch account"` | Account fetch failure |
| `"Failed to fetch duplicate orders. Please try again."` | Duplicate orders API failure |
| `"Failed to generate PDF"` | PDF generation failure |
| `"File size exceeds 5MB limit"` | File upload > 5MB |
| `"No duplicate orders found for this customer."` | No duplicates in API response |
| `"No orders selected"` | Bulk action with no selection |
| `"Please wait for countries to load"` | Countries not yet loaded |

---

## Toast: Info Messages

| Message | Trigger |
|---------|---------|
| `"No changes detected"` | Save action with no changed fields |
| `"Redirecting to dashboard..."` | Post-login redirect |
| `"Document generation started. Status: Preparing..."` | Batch document generation initiated |
| `"Document is being prepared. Please wait..."` | Document still processing |
| `"No failed orders to download"` | Download failure report with no failures |
| `"No orders selected. 0 batches created."` | Generate batches with no selection |

---

## Toast: Warning Messages

| Message | Trigger |
|---------|---------|
| `"Batch is already generating tracking IDs. Please wait."` | Attempt to generate while in progress |
| `"Batch tracking must be Generated before downloading documents"` | Documents download before tracking complete |

---

## Socket.IO Notifications (OMS — Ticketing)

Real-time events via Socket.IO. Frontend store: `useHighlightedTicketsStore`.

| Event | Meaning |
|-------|---------|
| `ticket_status_changed` | A ticket's status changed |
| `seller_to_zambeel_ticket_created` | Seller created a new ticket |
| `zambeel_to_seller_ticket_created` | OMS created a ticket for a seller |

When a new ticket arrives via socket, the ticket badge in the sidebar navigation dot becomes visible.

---

## Customer.io Events (Backend)

Triggered via `services/customerioService.js`. Events fire on user lifecycle but do not block main flows (errors are caught and swallowed).

| Event name | Triggered by |
|-----------|-------------|
| `user_signed_up` | POST /signUp — new user creation |
| `profile_updated` | PUT /user/profile — profile update |

User is identified in Customer.io using email as the primary ID. Attributes synced: `email`, `username`, `phone_number`, `country`, `provider`, `role`, `email_verified`, `created_at` (Unix timestamp), `promo_code` (if present).
