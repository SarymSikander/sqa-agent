# Shared — Authentication & Login Flows

## Overview
All portals use **Firebase** for authentication (email/password + social OAuth). After Firebase auth, users get a Zambeel JWT via `POST /login`. The JWT is stored in Zustand (`useAuthStore`) and sent as Bearer token on all subsequent API calls.

## Login Flow — All Portals

1. Navigate to `/login`
2. Enter email + password
3. Firebase `signInWithEmailAndPassword(email, password)` → returns Firebase user with ID token
4. `POST /login` with body: `{ idToken: firebaseIdToken }`
5. Zambeel API verifies token via Firebase Admin SDK → returns:
   ```json
   { "token": "<JWT>", "user": { "role": "Admin|Agent|Seller|Agency", ... } }
   ```
6. Zustand stores token and role
7. `RootRedirect` component checks role and redirects:
   - `Admin` or `Agent` → `/orders-management/dashboard`
   - `Seller` or `Agency` → `/get-started` (first time) or `/dashboard`

## Route Guard Components
| Component | Roles Allowed |
|-----------|--------------|
| `ProtectedRoute` | Admin, Agent |
| `SellerProtectedRoute` | Seller, Agency |
| `AgencyApprovedRoute` | Seller/Agency with `registration_status === "Approved"` |

## Social Login
- Google OAuth available on `/login` page
- Apple OAuth available on `/login` page
- Social sign-in creates Firebase user → same `POST /login` flow

## Auth Sessions (Playwright)
Sessions are saved as JSON files in `auth/`:
- `seller_local.json` — Seller portal, local env
- `seller_staging.json` — Seller portal, staging env
- `admin_local.json` — Admin portal, local env
- `admin_staging.json` — Admin portal, staging env
- `agency_local.json` — Agency portal, local env
- `agency_staging.json` — Agency portal, staging env

To refresh: `python tools/auth_setup.py <portal> <env>`

## Post-Login Success URLs

| Portal | Expected Path After Login |
|--------|--------------------------|
| Admin/Agent | `/orders-management/dashboard` |
| Seller | `/get-started` or `/dashboard` |
| Agency (approved) | `/get-started` or `/dashboard` |

## Login Page Selectors

```python
# Login form
input[type='email']                 → email field
input[type='password']              → password field
button:has-text('Sign In')          → or button[type='submit']

# Social login
button:has-text('Continue with Google')
button:has-text('Continue with Apple')

# Links
a:has-text('Forgot Password')       → /forgot-password
a:has-text('Register')              → /register
a:has-text("Don't have an account") → /register
```

## Registration Page (`/register`)

```python
input[name='username']              → or by placeholder 'Username'
input[type='email']
input[type='password']
input[placeholder='Confirm Password']   → or second password field
input[placeholder]                  → Phone number
select                              → Country code prefix
select                              → Country
input[placeholder]                  → Promo code (optional)
button:has-text('Register')         → or button[type='submit']
```

## Forgot Password (`/forgot-password`)

```python
input[type='email']
button:has-text('Send Reset Email')
text='Check your email for the reset link'    → success state
```

## Logout
- No specific button selector — logout typically via user avatar dropdown or sidebar footer
- Clears Zustand store → Firebase `signOut()` → redirect to `/login`

## Token Storage
- JWT stored in Zustand store (with `persist` plugin)
- Authorization header format: `Bearer <JWT>`
- `x-agency-context-store-id` header added when agency is in proxy mode

## Zustand Auth Stores — localStorage Keys

| Store | Key | Contents |
|-------|-----|---------|
| `useAuthStore` | `"auth-storage"` | `authToken`, `userRole`, `user`, `showInventory`, `products[]` |
| `useOrdersStore` | `"orders-storage"` | `selectedOrders` (Set), `isPersistentSelectionMode` — orders[] stripped on persist to prevent quota overflow |
| `useAgencyViewStore` | `"agency-view-storage"` | `isAgencyView`, `context: {agencyName, merchantUserId, merchantName, storeName, storeId, allowedStoreIds}` |
| `useGoldPlanStore` | `"gold-plan-storage"` | `isGoldPlanActive`, `planExpiryTime` |
| `useCustomizerStore` | `"customizer-storage"` | `isLanguage` (language preference only — other fields not persisted) |

## First-Time User Detection
`useAuthStore.isFirstTimeUser()` returns `true` if `user.createdAt` is within the last 24 hours. Used to show onboarding flows.

## Firebase Errors (client-side messages)
| Firebase Error Code | Display Message |
|--------------------|----------------|
| auth/user-not-found | User not found |
| auth/wrong-password | Incorrect password |
| auth/email-already-in-use | Email already in use |
| auth/weak-password | Password too weak |
| auth/invalid-email | Invalid email address |
| auth/too-many-requests | Too many attempts, try later |

## Test Auth Setup
```bash
# Create/refresh seller session on local
python tools/auth_setup.py seller local

# Create/refresh admin session on staging
python tools/auth_setup.py admin staging

# Create/refresh agency session on local
python tools/auth_setup.py agency local
```
