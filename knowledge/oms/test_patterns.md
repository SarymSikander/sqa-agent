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
ASSERT_VISIBLE input[placeholder='Search orders']
CLICK button:has-text('Confirmation Pending')
ASSERT_TEXT Confirmation Pending
FILL input[placeholder='Search orders'] | TEST-ORDER-001
# Assert table updates (or empty state)
```

## Pattern 5: Ticket View and Status Update

```python
NAVIGATE /orders-management/ticketing
ASSERT_VISIBLE input[placeholder='Search tickets, stores, orders...']
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

## General OMS Test Rules

1. Always assert page title text after navigation before interacting
2. Commission model drawer: always click `+ Add Rule` before filling rule fields
3. Agency registration drawer: wait for status-specific action buttons before clicking
4. Hold/Reject reason textareas require minimum 3 characters before submit button enables
5. For approve flow: must select a commission model or button stays disabled
6. Ticket detail modal: always verify `Update Ticket` button is visible before updating
7. Use `CLICK_OPTION` for all Flowbite Select/Dropdown components — they are not native `<select>` elements
8. After drawer closes, always assert the drawer is no longer visible before asserting list changes

## Selector Quick Reference (OMS)

| Element | Selector |
|---------|----------|
| Commission Models page | `h1:has-text('Commission Models')` |
| New Model button | `button:has-text('+ New Model')` |
| Model name input | `input[placeholder='Enter model name']` |
| Add rule button | `button:has-text('+ Add Rule')` |
| Currency input | `input[placeholder='AED']` |
| Save model button | `button:has-text('Save Model')` |
| Review button (registrations) | `button:has-text('Review')` |
| Approve button | `button:has-text('Approve Agency')` |
| Confirm approve | `button:has-text('Confirm Approve')` |
| Hold textarea | `textarea[placeholder='Explain what needs to be fixed...']` |
| Reject textarea | `textarea[placeholder='Reason for rejection...']` |
| Confirm reject | `button:has-text('Confirm Reject')` |
| OMS search | `input[placeholder='Search orders']` |
| Ticket search | `input[placeholder='Search tickets, stores, orders...']` |
| Update ticket | `button:has-text('Update Ticket')` |
| Resolution notes | `textarea[placeholder='Add notes about the resolution...']` |
