# Shared — Validation Rules

All rules extracted from backend Joi schemas (`validations/`) and frontend validation utilities (`src/utils/`).

---

## Backend: Auth

**POST /signUp** (`validations/auth.js — signUpSchema`):
- `firebase_uid`: string, required
- `email`: string, email format, required
- `username`: string, required
- `phone_number`: string, optional, empty allowed
- `country`: string, optional, empty allowed
- `provider`: string, required
- `role`: string, optional
- `team_id`: integer, optional, allow null
- `email_verified`: boolean, optional
- `promo_code`: string, optional, empty allowed

**POST /login** (`loginSchema`):
- `idToken`: string, required

---

## Backend: Orders (`validations/orders.js`)

### Pagination defaults
- `page`: integer, min 1, default 1
- `limit`: integer, min 1, max 100, default 10

### Processed orders pagination
- `limit`: integer, min 1, **max 500**, default 100 (increased for export)

### SKU search
- `sku`: string, trimmed, min 3, max 50, required

### Phone number (customer update / edit order fields)
- Pattern: `/^\+?[0-9\s\-]{10,20}$/`
- Optional, allow null/empty

### Add product to order
- `order_id`: integer, required
- `variant_id`: integer, required
- `quantity`: integer, min 1, required
- `price`: decimal (2 places), min 0, required
- `discount`: decimal (2 places), min 0, default 0

### Update order details body (all optional, at least 1 required)
- `total_cost`, `total_discount`, `post_dispatch_discount`, `total_tax`, `shipping_price`: decimal(2), min 0
- `tags`: string, allow null/empty
- `activity_counter`: integer, min 0
- `ndr_meta_data`: object, allow null
- `reschedule_date`: ISO date, allow null
- `payment_method`, `customer_name`: string, allow null/empty

### CSV order upload (bulk) — required fields per row
- `order_reference_id`, `customer_name`, `Address`, `delivery_city`, `delivery_country`: string, required
- `customer_phone_number`: number, required
- `product_sku`: string, required
- `Quantity`: integer, min 1, required
- `price`: number, min 0, required
- `total_amount`: number, min 0, required
- `currency`: string, required
- `payment_mode`: string, valid `'COD'` only (case-insensitive) — **COD is the ONLY valid value**
- `selectedStoreId`: string, required
- `shipping_charges`, `Discount`: number, min 0, allow null/empty (optional)
- `area_name`, `building_society`, `national_address_short_code`: string, optional, allow null/empty

### Bulk CSV update orders (per row)
- `order_id`: number, required
- `sub_status`: string, required
- `tag`: string, optional, empty allowed
- `tracking_id`: string, optional, empty allowed
- `courier_id`: number, allow null, optional
- `vendor_id`: string, allow null/empty, optional

### Dispatch batches query
- `country_id`: integer, positive, required
- `tracking_status` valid values: `"New"`, `"Generating"`, `"Partial"`, `"Generated"`, `"Failed"`
- `start_date`, `end_date`: ISO date, optional
- `vendor_id`, `courier_id`: integer, positive, optional
- `page`: integer, min 1, default 1
- `limit`: integer, min 1, max 100, default 10
- `search`: string, optional, empty allowed

### Generate tracking IDs
- `batch_id`: string, required
- `mode`: string, valid `"All"` or `"Missing"`, required

### Assign courier with batch
- `orderIds`: array of positive integers, min 1 item, required
- `courierId`: positive integer, required
- `batchName`: string, trimmed, min 1, required

### Bulk remarks update
- `order_ids`: array of positive integers, min 1, required
- `remark_ids`: array of positive integers, required

### Check order availability / assign courier / clear courier
- `orderIds`: array of positive integers, min 1, required

### Edit order fields (at least 1 required)
- `address`, `city`, `customer_name`: string, optional, allow null/empty
- `phone`: regex `/^\+?[0-9\s\-]{10,20}$/`, optional, allow null/empty

---

## Frontend: Order Approval Validations (`src/utils/approveOrdersValidations.tsx`)

### Phone number validation
- Strips non-digits, normalizes country code
- Validates digit count using country-specific `phoneLength.min` from `countryData`
- Must be all digits after stripping country code
- Error: `"Phone number for {Country} must be {N} digits (excluding country code)"`
- Error: `"Phone number must contain only digits"`
- Error: `"Phone number and country are required"`
- Error: `"Invalid country selected"`

### City validation (`validateCity`)
- Validates against `validCitiesByCountry` lookup (case-insensitive match)
- Supported countries: UAE, Saudi Arabia, Kuwait, Qatar, Pakistan, Oman, Bahrain, Iraq, United States
- Error: `"Invalid city for {Country}. Please select a valid city from the dropdown."`
- Error: `"City and country are required"`

### Payment method validation (`validatePaymentMethod`)
- If `payment_method === "paid"` (case-insensitive), `total_cost` must be ≤ 0
- Otherwise no validation — passes through

### Area name / Building society / National address short code
- Currently no-op validations — always return `{ isValid: true }`

---

## Frontend: Toast-Level Validation Errors (from UI components)

| Field | Error message |
|-------|--------------|
| SKU (empty) | `"Please enter a SKU to search"` / `"Please enter a SKU."` |
| Name | `"Please enter a name."` |
| Email | `"Please enter a valid email."` |
| Phone | `"Please enter a valid phone number."` |
| Country | `"Please select a country."` |
| Team | `"Please select a team."` |
| Required fields | `"Please fill all the required fields"` |
| Duplicate SKU | `"This SKU already exists in the order."` |
| Countries loading | `"Please wait for countries to load"` |
| No orders selected | `"No orders selected"` |
| Batch not selected | `"Please select a batch"` |
| Courier + batch name | `"Please select a courier and enter a batch name"` |

---

## Backend: Agency Validation (`validations/agency.validations.js`)

Agency registration validation — fields validated on `startAgencyRegistration` and `completeAgencyRegistration` routes.

## Backend: User Profile Validation (`validations/userProfile.validations.js`)

Profile update fields validated on `PUT /user/profile`.

## Backend: Bank Validation (`validations/bank.validations.js`)

Bank account fields validated before creating bank account.

## Backend: Store Validation (`validations/store.validations.js`, `store.validation.js`)

Store creation requires: at least one primary bank account (`"User must have at least one primary bank account before creating a store."`).

---

## Valid City Lists by Country

| Country | City count (approx) |
|---------|---------------------|
| Saudi Arabia | 100+ cities |
| Pakistan | 400+ cities |
| UAE | 8 cities (7 emirates + Al Ain) |
| Kuwait | 40 cities |
| Qatar | 17 cities |
| Oman | 11 governorates |
| Bahrain | 10 areas |
| Iraq | 19 governorates |
| United States | 50 states |
