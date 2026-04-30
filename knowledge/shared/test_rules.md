# Shared — Global Test Generation Rules

These rules apply to ALL test cases generated for the Zambeel platform, regardless of portal.

---

## 1. Selector Rules

### REQUIRED Patterns
```
button:has-text('exact button text')        # buttons
input[placeholder='exact placeholder']      # inputs
a:has-text('exact link text')               # nav links
div[role='dialog']                          # modals/drawers
label:has-text('Label') >> input            # labeled inputs
button:has-text('option text')              # Flowbite dropdowns
```

### FORBIDDEN Patterns
```
#elementId                                  # NO IDs — the app has none
.class-name >> text                         # avoid class-based if text works
[data-testid]                               # no test IDs in this codebase
```

### Flowbite Components (NOT native HTML)
- Select dropdowns in this app are **Flowbite Select** components — they render as `button` triggers, NOT native `<select>`.
- Always use `CLICK_OPTION` or `button:has-text()` for Flowbite selects.
- Native `<select>` elements DO exist in some filter panels — check which is which.
- Textareas are standard `<textarea>` elements.

---

## 2. Navigation Rules

- After login, always assert the expected landing URL before any interaction.
- Navigate to pages via direct URL (`NAVIGATE /path`) for test stability.
- Do NOT rely on sidebar clicks to navigate unless specifically testing sidebar behavior.
- Always wait for page content to load (assert a heading or key element) before interacting.

---

## 3. Form Interaction Rules

- Fill ALL required fields before clicking submit.
- Check field by its placeholder or label, NOT by position in DOM.
- For multi-step forms/wizards: assert the step indicator changes after each step.
- For drawer/modal forms: assert modal is visible BEFORE filling fields.
- For drawer/modal forms: assert modal is closed AFTER successful save.

---

## 4. Assertion Rules

- After every navigation: assert page title (`h1` or `text=`) to confirm correct page loaded.
- After every form submit: assert the success toast or success message text.
- After every error trigger: assert exact error message text.
- After drawer close: assert the new/updated item in the list.
- Never assert generic text like "Success" — assert the specific toast message.

---

## 5. Validation Testing Rules

- Always test the minimum valid input (e.g., description = exactly 10 chars, reason = exactly 3 chars).
- Always test one below minimum (e.g., 9 chars for description) — submit button should remain disabled.
- Always test required fields: attempt submit without filling, assert button is disabled or error appears.
- Duplicate validation: if a field must be unique (e.g., model name, country in commission rule), test the duplicate case.

---

## 6. Button State Rules

- Before clicking `Save Model`, `Confirm Approve`, `Put on Hold`, `Confirm Reject` — assert the condition that enables them.
- Disabled buttons: use `ASSERT_DISABLED button:has-text('...')` to confirm they are disabled.
- Loading states: buttons like `Submitting...`, `Sending...`, `Deleting...` appear briefly — do NOT assert these unless testing loading UX.

---

## 7. Portal-Specific Rules

### OMS Rules
- Commission model: always add at least one rule before saving.
- Agency registration: select a commission model before clicking `Confirm Approve`.
- Hold reason: must be ≥ 3 characters.
- Reject reason: must be ≥ 3 characters.

### Seller Portal Rules
- Ticket description: min 10 chars, max 2000 chars.
- File uploads in tickets: max 3 files, max 5MB each, images only.
- Phone number: must match `/^\+\d{10,15}$/` in international format.

### Agency Portal Rules
- Agency registration: both file uploads AND terms checkbox required to submit step 2.
- City field: disabled until country is selected.
- Agency settings `Save` button: only enabled when form is dirty (changed).
- `Add Member` button is currently DISABLED — do not attempt to click it in happy-path tests.

---

## 8. Test Data Rules

- Use test-specific prefixes: e.g., "TEST_" or "SQA_" in model names, agency names, etc.
- Never hardcode real user emails or IDs — use test accounts defined in auth sessions.
- For country-specific tests, always use UAE (AED) as default unless testing other countries.
- Commission model currency: always 3 uppercase chars (e.g., AED, SAR, KWD).

---

## 9. Error Handling Rules

- Always assert the exact error message text from the knowledge base.
- Do NOT assert partial error text — match the full string.
- For API errors surfaced as toasts, assert the toast text.
- For inline validation errors, assert the element text near the input.

---

## 10. Test Structure Template

Every generated test should follow this structure:

```
1. NAVIGATE <route>
2. ASSERT_TEXT <page title>           # confirm correct page
3. [Optional setup steps]
4. [Interaction steps]                # click, fill, select
5. [Submit step]                      # click submit/save button
6. ASSERT_TEXT <success message>      # or ASSERT_URL <new route>
7. [Post-condition assertions]        # verify in list, drawer closed, etc.
```

---

## 11. Knowledge Base References

When generating tests, consult these files for exact information:

| Need | File |
|------|------|
| Exact button text for OMS | `knowledge/oms/selectors.md` |
| Exact button text for Seller | `knowledge/seller/selectors.md` |
| Exact button text for Agency | `knowledge/agency/selectors.md` |
| OMS user flows | `knowledge/oms/flows.md` |
| Seller user flows | `knowledge/seller/flows.md` |
| Agency user flows | `knowledge/agency/flows.md` |
| OMS test examples | `knowledge/oms/test_patterns.md` |
| Seller test examples | `knowledge/seller/test_patterns.md` |
| Agency test examples | `knowledge/agency/test_patterns.md` |
| API endpoints | `knowledge/shared/api_endpoints.md` |
| Auth setup | `knowledge/shared/auth.md` |
| Jira transitions | `knowledge/shared/jira_statuses.md` |

---

## 12. NEVER Do These

- NEVER guess a button text — always look it up in the selectors file.
- NEVER use `#id` selectors — the app has none.
- NEVER assert elements from the wrong portal (e.g., OMS selectors in a seller test).
- NEVER assume a sub-category without checking the ticketing constants.
- NEVER assert a route that doesn't exist in the pages files.
- NEVER write duplicate country rules in a commission model test.
- NEVER click `Add Member` — it is currently disabled.
- NEVER test production environment with write operations.
