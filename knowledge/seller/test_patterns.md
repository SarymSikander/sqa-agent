# Seller Portal — Test Patterns

## Pattern 1: Seller Login and Landing

```python
NAVIGATE /login
FILL input[type='email'] | seller@example.com
FILL input[type='password'] | password123
CLICK button:has-text('Sign In')
ASSERT_URL /dashboard  # or /get-started for new accounts
ASSERT_VISIBLE a:has-text('Orders')
ASSERT_VISIBLE a:has-text('Ticketing')
```

## Pattern 2: Orders Page — Verify Two Sections

```python
NAVIGATE /orders
ASSERT_TEXT Your Store Orders
ASSERT_TEXT Orders with Zambeel
ASSERT_VISIBLE button:has-text('Send To Zambeel')
ASSERT_VISIBLE button:has-text('Delete')
```

## Pattern 3: Create Support Ticket — Happy Path

```python
NAVIGATE /ticketing
ASSERT_TEXT Ticketing System
CLICK button:has-text('Create New Ticket')
ASSERT_VISIBLE div[role='dialog']
# Step 1: Select store
# (select first available store from dropdown)
CLICK button:has-text('Next')
# Step 2: Category
CLICK text='Onboarding & Integration'
CLICK text='Store integration failure'
CLICK button:has-text('Next')
# Step 3: Description
FILL textarea | This is a test ticket description for integration testing purposes.
CLICK button:has-text('Next')
# Step 4: Review & submit
CLICK button:has-text('Submit')
ASSERT_TEXT Ticket Created Successfully!
```

## Pattern 4: Ticket Status Filter

```python
NAVIGATE /ticketing
ASSERT_VISIBLE button:has-text('Tickets Assigned by Zambeel')
CLICK button:has-text('Tickets Assigned to Zambeel')
# Select status filter
SELECT select | Pending
ASSERT_TEXT Pending
```

## Pattern 5: Filter Processed Orders

```python
NAVIGATE /orders
# Wait for Orders with Zambeel section
CLICK button:has-text('Filter')
FILL input[placeholder='Search by Order ID'] | 12345
CLICK button:has-text('Apply Filters')
# Verify filtered results
CLICK button:has-text('Reset')
```

## Pattern 6: Store Integration Page Load

```python
NAVIGATE /stores/integration
ASSERT_VISIBLE button:has-text('Connect Shopify')
ASSERT_VISIBLE button:has-text('Create Manual Store')
```

## Pattern 7: Bank Account Settings Page

```python
NAVIGATE /settings
ASSERT_VISIBLE button:has-text('Bank Account')
ASSERT_VISIBLE button:has-text('USDT')
ASSERT_VISIBLE button:has-text('PayPal')
```

## Pattern 8: My Invoices Page

```python
NAVIGATE /my-invoices
# Page loads with invoice list or empty state
# Verify sidebar badge clears after visit
```

## Pattern 9: Dashboard Page Load

```python
NAVIGATE /dashboard
ASSERT_TEXT Total Orders    # or translated text
# KPI cards loaded
```

## Pattern 10: Send Order Validation (Missing Country)

```python
NAVIGATE /orders
# Select an order with missing country
CLICK button:has-text('Send To Zambeel')
ASSERT_TEXT Country    # validation error
```

## Pattern 11: Ticket File Upload Limit

```python
# Inside Create Ticket wizard, step 3
# Attempt to upload 4 files
ASSERT_TEXT Maximum 3 files allowed
```

## Pattern 12: Orders Tab Navigation

```python
NAVIGATE /orders
# Seller orders page has two main sections, not status tabs like OMS
ASSERT_TEXT Your Store Orders
ASSERT_TEXT Orders with Zambeel
# Verify processed orders filter
ASSERT_VISIBLE input[placeholder='Search by Order ID']
```

## Selector Quick Reference (Seller)

| Element | Selector |
|---------|----------|
| Create ticket | `button:has-text('Create New Ticket')` |
| Send to Zambeel | `button:has-text('Send To Zambeel')` |
| Ticketing header | `h1:has-text('Ticketing System')` |
| Orders header | `h1:has-text('Orders Dashboard')` |
| Order ID search | `input[placeholder='Search by Order ID']` |
| Phone search | `input[placeholder='Search by Phone']` |
| Filter toggle | `button:has-text('Filter')` |
| Apply filters | `button:has-text('Apply Filters')` |
| Reset filters | `button:has-text('Reset')` |
| Ticket success | `h3:has-text('Ticket Created Successfully!')` |
| By Zambeel tab | `button:has-text('Tickets Assigned by Zambeel')` |
| To Zambeel tab | `button:has-text('Tickets Assigned to Zambeel')` |

## Error Messages Reference

| Error | Trigger |
|-------|---------|
| "Country" | Missing delivery country in order |
| "Phone Number" | Missing phone in order |
| "Phone Number must contain only digits" | Non-numeric phone |
| "Invalid Order item - SKU is missing" | Order has item with no SKU |
| "Gold subscription required for order processing" | No gold plan |
| "Maximum 3 files allowed" | >3 files in ticket upload |
| "File {name} is too large. Maximum size is 5MB." | File >5MB |
| "Store Nick name already exists..." | Duplicate store name |
| "No orders selected for deletion" | Delete clicked with none selected |
