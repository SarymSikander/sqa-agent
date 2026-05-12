# Shared — Error Messages

Covers backend API error messages (from constants files and route handlers) and frontend inline error messages.

---

## Backend: Order Error Constants (`constants/orders.constants.js`)

| Constant | Message |
|----------|---------|
| `ORDER_NOT_FOUND` | `"Order not found"` |
| `ORDER_ALREADY_EXISTS` | `"Order already exists"` |
| `ORDER_NOT_CREATED` | `"Order not created"` |
| `ORDER_NOT_UPDATED` | `"Order not updated"` |
| `ORDER_NOT_DELETED` | `"Order not deleted"` |
| `ORDER_NOT_FETCHED` | `"Order not fetched"` |
| `ORDER_NOT_UPLOADED` | `"Order not uploaded"` |
| `STORE_NOT_FOUND` | `"Store not found"` |

## Backend: Order Success Constants

| Constant | Message |
|----------|---------|
| `ORDER_CREATED` | `"Order created successfully"` |
| `ORDER_UPDATED` | `"Order updated successfully"` |
| `ORDER_DELETED` | `"Order deleted successfully"` |
| `ORDER_FETCHED` | `"Order fetched successfully"` |
| `ORDER_UPLOADED` | `"Order uploaded successfully"` |

---

## Backend: Store Error Constants (`constants/store.constants.js`)

| Constant | Message |
|----------|---------|
| `STORE_NOT_FOUND` | `"Store not found"` |
| `FAILED_TO_GET_STORE` | `"Failed to get store"` |
| `FAILED_TO_GET_STORES` | `"Failed to get stores"` |
| `FAILED_TO_UPDATE_STORE` | `"Failed to update store"` |
| `FAILED_TO_CHECK_STORE_NAME` | `"Failed to check store name"` |
| `NO_STORES_FOR_USER` | `"No stores found for this user"` |
| `INVALID_SORT_ORDER` | `"Invalid sort order. Use 'asc' or 'desc'."` |
| `INTERNAL_SERVER_ERROR` | `"Internal server error"` |
| `USER_NOT_FOUND` | `"User not found"` |
| `NO_PRIMARY_BANK_ACCOUNT` | `"User must have at least one primary bank account before creating a store."` |

## Backend: Store Success Constants

| Constant | Message |
|----------|---------|
| `STORES_FETCHED` | `"Stores fetched successfully"` |
| `STORE_FETCHED` | `"Store fetched successfully"` |
| `STORE_UPDATED` | `"Store updated successfully"` |
| `STORE_NAME_CHECKED` | `"Store name checked successfully"` |
| `STORE_CREATED` | `"Store created successfully"` |
| `STORE_DELETED` | `"Store deleted successfully"` |

---

## Backend: JWT / Auth Errors (from `middlewares/verifyJWT.js`)

| HTTP Status | Scenario |
|------------|----------|
| 401 | Invalid or expired token |
| 403 | Valid token but role not in allowed list |

Frontend handles 401 by calling `tokenUtils.handleSessionExpiration()` which clears the auth store and redirects to `/login`.

---

## Backend: Joi Validation Error Messages

Joi validation failures return HTTP 400 with the Joi error message string. Key custom messages:

| Schema | Field | Error message |
|--------|-------|--------------|
| `csvOrderUploadSchema` | `payment_mode` | `"Payment Mode" must be COD"` |
| `csvOrderUploadSchema` | `payment_mode` | `"Payment Mode" must be a string"` |
| `csvOrderUploadSchema` | `payment_mode` | `"Payment Mode" is required"` |
| `csvOrderUploadSchema` | `customer_phone_number` | `"Phone number" must be a valid number"` |
| `csvOrderUploadSchema` | `customer_phone_number` | `"Phone number" is required"` |
| `getDispatchBatchesSchema` | `tracking_status` | `"Tracking status must be one of: New, Generating, Partial, Generated, Failed"` |
| `generateTrackingIdsSchema` | `mode` | `"Mode must be either 'All' or 'Missing'"` |
| `assignCourierWithBatchSchema` | `batchName` | `"batchName cannot be empty"` |
| `bulkCsvUpdateOrdersSchema` | body | `"Body must be an array of order updates"` |
| `bulkCsvUpdateOrdersSchema` | body | `"At least one order update is required"` |
| `associateRemarksSchema` | `orderId` | `"Order ID must be a number"` |
| `associateRemarksSchema` | `orderId` | `"Order ID must be an integer"` |
| `associateRemarksSchema` | `orderId` | `"Order ID is required"` |
| `editOrderFieldsSchema` | body | `"At least one field must be provided for update"` |

---

## Frontend: Form Validation Error Messages (inline — displayed below inputs)

| Context | Error message |
|---------|--------------|
| Phone (approve orders) | `"Phone number for {Country} must be {N} digits (excluding country code)"` |
| Phone (approve orders) | `"Phone number must contain only digits"` |
| Phone (approve orders) | `"Phone number and country are required"` |
| Country lookup | `"Invalid country selected"` |
| City (approve orders) | `"Invalid city for {Country}. Please select a valid city from the dropdown."` |
| City + Country empty | `"City and country are required"` |

---

## Frontend: HTTP Client Error Handling

From `src/api/httpClient.ts`:
- 401 response → `tokenUtils.handleSessionExpiration()` → redirects to `/login`
- Other errors → thrown as-is; calling code catches and may show toast

---

## Backend: Agency ID Generation

Agency IDs are generated with prefix `"ZMB-AG-"` + 6 random characters, up to 12 retries before failing.

---

## Backend: Webhook Error Handling

Webhook handlers (Shopify, EasyOrder, LightFunnels, Salla, Smartlane, Wati, YouCan, iMile) all follow a pattern of catching errors, logging them, and returning appropriate HTTP status codes without leaking internal details to the caller.
