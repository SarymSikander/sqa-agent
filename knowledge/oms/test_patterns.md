# OMS — Test Patterns

## Pattern 1: Commission Model Happy Path

```python
# Navigate to commission models
NAVIGATE /orders-management/commission-models
ASSERT_TEXT Commission Models
ASSERT_TEXT Define per-country commission rates for agencies.

# Open create drawer
CLICK button:has-text('+ New Model')
ASSERT_VISIBLE div[role='dialog']

# Fill model name
FILL input[placeholder='Enter model name'] | Test Commission Model

# Add a rule
CLICK button:has-text('+ Add Rule')

# Select country (first dropdown in rules section)
CLICK_OPTION Country* dropdown | United Arab Emirates
# After country selection, currency auto-fills with AED
ASSERT_VALUE input[placeholder='AED'] | AED

# Select type
CLICK_OPTION Type* dropdown | % of Revenue

# Fill value
FILL input[type='number'] | 10

# Save
CLICK button:has-text('Save Model')
ASSERT_NOT_VISIBLE div[role='dialog']
ASSERT_TEXT Test Commission Model
```

## Pattern 2: Agency Registration Approve Flow

```python
NAVIGATE /orders-management/agency-registrations
CLICK button:has-text('Pending')
CLICK button:has-text('Review')
# Drawer opens — verify details visible
ASSERT_VISIBLE div[role='dialog']
CLICK button:has-text('Approve Agency')
# Commission model sub-form appears
CLICK_OPTION Select commission model | [any model name]
CLICK button:has-text('Confirm Approve')
ASSERT_NOT_VISIBLE div[role='dialog']
# Verify in Approved tab
CLICK button:has-text('Approved')
ASSERT_TEXT Approved
```

## Pattern 3: Agency Hold with Reason

```python
NAVIGATE /orders-management/agency-registrations
CLICK button:has-text('Pending')
CLICK button:has-text('Review')
CLICK button:has-text('Put on Hold')
FILL textarea[placeholder='Explain what needs to be fixed...'] | Missing document verification
CLICK button:has-text('Put on Hold')
# Verify tab change
CLICK button:has-text('OnHold')
ASSERT_TEXT OnHold
```

## Pattern 4: Order Tab Navigation and Search

```python
NAVIGATE /orders-management/orders
ASSERT_TEXT Orders Management
ASSERT_VISIBLE input[placeholder='Search orders']
CLICK button:has-text('Confirmation Pending')
ASSERT_TEXT Confirmation Pending
CLICK button:has-text('Shipped')        # verified tab name — NOT 'In Delivery'
ASSERT_TEXT Shipped
FILL input[placeholder='Search orders'] | TEST-ORDER-001
# Assert table updates (or empty state)
```

## Pattern 4b: Order Filter Modal

```python
NAVIGATE /orders-management/orders
CLICK button:has-text('Filter')
ASSERT_TEXT Filters
FILL input[placeholder='Order ID (comma-separated for multiple)'] | 12345
FILL input[placeholder='Customer Name'] | Test Customer
CLICK_OPTION button:has-text('Select Store') | My Test Store
CLICK button:has-text('Apply filter')    # verified — NOT 'Apply Filters'
# Assert filtered results load
CLICK button:has-text('Filter')
CLICK button:has-text('Clear all filters')   # verified — NOT 'Reset'
```

## Pattern 5: Ticket View and Status Update

```python
NAVIGATE /orders-management/ticketing
ASSERT_TEXT Ticketing Management
ASSERT_VISIBLE input[placeholder='Search by store name...']
CLICK button:has-text('View')    # first ticket in table
# Modal opens
ASSERT_VISIBLE button:has-text('Update Ticket')
ASSERT_VISIBLE textarea[placeholder='Add notes about the resolution...']
# Change status
SELECT select | In Progress
CLICK button:has-text('Update Ticket')
ASSERT_TEXT Ticket updated successfully!
```

## Pattern 6: Validation — Commission Model Duplicate Country

```python
NAVIGATE /orders-management/commission-models
CLICK button:has-text('+ New Model')
FILL input[placeholder='Enter model name'] | Dup Test
CLICK button:has-text('+ Add Rule')
CLICK_OPTION Country* | United Arab Emirates
CLICK button:has-text('+ Add Rule')
CLICK_OPTION Country* | United Arab Emirates    # second rule, same country
ASSERT_TEXT Each country can only appear once inside the same model.
ASSERT_DISABLED button:has-text('Save Model')
```

## Pattern 7: Gold Subscription Search

```python
NAVIGATE /orders-management/gold-subscriptions
CLICK button:has-text('Email')
FILL input | test@example.com
CLICK button:has-text('Search')
# Assert results or empty state
CLICK button:has-text('Gold users')
# Assert gold users tab loaded
```

## Pattern 8: Agent Creation

```python
NAVIGATE /orders-management/agents
ASSERT_VISIBLE input[placeholder='Search by Name, Email or Country']
CLICK button:has-text('Create Agent')
ASSERT_VISIBLE div[role='dialog']
FILL input[placeholder='John Doe'] | Test Agent
# Fill email, phone, country, team
CLICK button:has-text('Create')
```

## Pattern 9: Edit Order Address

```python
NAVIGATE /orders-management/orders
CLICK text='<order_id>'         # click order ID link in table to open modal
ASSERT_VISIBLE div[role='dialog']
ASSERT_TEXT Order Details
CLICK button:has-text('Edit Order')
# Fields are now editable inputs:
FILL input[name='customer_name'] | Updated Customer Name
FILL input[name='phone'] | 501234567
CLICK button:has-text('Save')
ASSERT_TOAST Order updated successfully
```

## Pattern 10: Bulk Upload Orders via CSV

```python
NAVIGATE /orders-management/orders
CLICK button:has-text('Actions')
CLICK button:has-text('Upload Orders')
ASSERT_VISIBLE div[role='dialog']
# Upload a CSV file — must have COD as payment_mode
# File must be < size limit
CLICK button[type='submit']   # or whatever submit button label is
# Monitor for upload results popup
```

## Pattern 11: Dispatch Batch Generate + Download

```python
NAVIGATE /orders-management/dispatch-batches
# Set country filter to target country
ASSERT_TEXT Dispatch Batches
# Find a batch with tracking_status 'New' or 'Partial'
CLICK button:has-text('Generate Tracking ID')
# Poll or wait for status to change to 'Generated'
ASSERT_TEXT Generated
CLICK button:has-text('Download Combined Doc')
ASSERT_TOAST Document downloaded successfully
# If status is 'Generating', expect warning toast:
# 'Batch is already generating tracking IDs. Please wait.'
```

## General OMS Test Rules

1. Always assert page title text after navigation before interacting
2. Commission model drawer: always click `+ Add Rule` before filling rule fields
3. Agency registration drawer: wait for status-specific action buttons before clicking
4. Hold/Reject reason textareas require minimum 3 characters before submit button enables
5. For approve flow: must select a commission model or button stays disabled
6. Ticket detail modal: always verify `Update Ticket` button is visible before updating
7. Use `CLICK_OPTION` for all Flowbite Select/Dropdown components — they are not native `<select>` elements
8. After drawer closes, always assert the drawer is no longer visible before asserting list changes

## Selector Quick Reference (OMS — verified from screenshots)

| Element | Selector | Notes |
|---------|----------|-------|
| Orders page title | `h1:has-text('Orders Management')` | NOT 'Orders' |
| Orders search | `input[placeholder='Search orders']` | |
| Shipped tab | `button:has-text('Shipped')` | NOT 'In Delivery' |
| Dispatching tab | `button:has-text('Dispatching In Process')` | Capital I |
| Filter button | `button:has-text('Filter')` | |
| Apply filter | `button:has-text('Apply filter')` | lowercase 'f' |
| Clear filters | `button:has-text('Clear all filters')` | NOT 'Reset' |
| Edit Order (modal) | `button:has-text('Edit Order')` | |
| Approve Order (modal) | `button:has-text('Approve Order')` | |
| Cancel Order (modal) | `button:has-text('Cancel Order')` | |
| Dispatch search | `input[placeholder='Search orders...']` | 3 dots |
| Generate tracking | `button:has-text('Generate Tracking ID')` | |
| Download combined | `button:has-text('Download Combined Doc')` | |
| Stores page title | `h1:has-text('Integrated Stores')` | NOT 'Stores Settings' |
| Stores search | `input[placeholder='Search by Store Name or URL']` | |
| Ticketing page title | `h1:has-text('Ticketing Management')` | OMS only |
| Ticketing search | `input[placeholder='Search by store name...']` | |
| Create ticket | `button:has-text('+ Create New Ticket')` | |
| Gold sub page title | `h1:has-text('Gold Subscription Management')` | |
| Gold sub search | `input[placeholder='Enter user email']` | |
| Inventory page title | `h1:has-text('Inventory Movements')` | |
| Add movement | `button:has-text('+ Add Inventory Movement')` | NOT 'Create' |
| Inventory search | `input[placeholder='Search Movement ID']` | |
| Ticker page title | `h1:has-text('Global Ticker Configuration')` | |
| Ticker save | `button:has-text('Update Global Ticker')` | NOT 'Save' |
| Agency reg page title | `h1:has-text('Agency Registrations')` | |
| Agency reg review | `button:has-text('Review')` | |
| Approve agency | `button:has-text('Approve Agency')` | |
| Confirm approve | `button:has-text('Confirm Approve')` | |
| Hold textarea | `textarea[placeholder='Explain what needs to be fixed...']` | |
| Reject textarea | `textarea[placeholder='Reason for rejection...']` | |
| Confirm reject | `button:has-text('Confirm Reject')` | |
| Commission page title | `h1:has-text('Commission Models')` | |
| New model | `button:has-text('+ New Model')` | |
| Model name input | `input[placeholder='Enter model name']` | |
| Edit model | `button:has-text('✏ Edit')` | includes emoji |
| Add rule | `button:has-text('+ Add Rule')` | |
| Currency input | `input[placeholder='AED']` | |
| Save model | `button:has-text('Save Model')` | |
| Update ticket | `button:has-text('Update Ticket')` | |
| Resolution notes | `textarea[placeholder='Add notes about the resolution...']` | |
