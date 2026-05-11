# Seller Portal — Overview

## What Is It?
The Seller Portal is the merchant-facing interface of Zambeel. Sellers use it to manage their stores, upload and track orders, manage payments and bank accounts, create support tickets, view invoices, and access the Zambeel Academy.

## Who Uses It?
| Role | Portal Access |
|------|--------------|
| `Seller` | Full seller portal — all merchant features |
| `Agency` | Seller portal (merchant tab) + Agency portal (agency tab) |

## Base URLs
| Environment | URL |
|------------|-----|
| Local | `http://localhost:5173` |
| Staging | `https://staging.myzambeel.com` |
| Production | `https://portal.myzambeel.com` |

## Post-Login Landing Page
After login, sellers land on: `/get-started` (first time) or `/dashboard` (returning users)
- `RootRedirect` checks role → Seller/Agency → `/dashboard` or `/get-started`

## Layout
- Uses `RootLayout` → `AuthWrapper`
- Left sidebar with two portal tabs at top: **Merchant** | **Agency**
- Sidebar themes:
  - **default**: dark purple/indigo
  - **gold**: amber/honey (for Gold subscribers)
  - **agency**: emerald/cyan (when in Agency portal view)

## Route Guard
- All seller routes protected by `SellerProtectedRoute`
- Allowed roles: `Seller`, `Agency`
- Agency-specific portal routes also require `AgencyApprovedRoute` (registration_status === "Approved")

## Sidebar Items (Merchant Tab — All Sellers)
| Item | URL | Notes |
|------|-----|-------|
| Get Started ▾ | `/get-started` | Dropdown with 3 sub-items |
| ↳ Dropshipping | `/get-started/dropshipping` | |
| ↳ Zambeel 360 | `/get-started/zambeel-360` | |
| ↳ 3PL Services | `/get-started/3pl-services` | |
| Dashboard | `/dashboard` | |
| Zambeel Academy | `/academy` | |
| Orders | `/orders` | |
| Orders Analytics | `/orders-analytics` | |
| Gold Subscription | `/gold-subscription` | |
| Bank Accounts | `/settings` | |
| Stores Integration | `/stores/integration` | |
| Ticketing | `/ticketing` | Green pulse badge if new tickets |
| My Invoice | `/my-invoices` | Green pulse badge if new invoices |
| My Inventory | `/seller/inventory` | Only if `showInventory` flag enabled |

## Supported Countries
Kuwait | Qatar | Saudi Arabia | United Arab Emirates | Pakistan | Oman | Bahrain | Iraq

## Currency Map
| Country | Currency |
|---------|---------|
| UAE | AED |
| Saudi Arabia | SAR |
| Kuwait | KWD |
| Qatar | QAR |
| Bahrain | BHD |
| Oman | OMR |
| Pakistan | PKR |
| Iraq | IQD |

## Payment Methods for Bank Accounts
- Bank Account
- USDT
- PayPal

## Withdrawal Days
Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday

## Payment Processing Timeline
1. Payment Method Locked — Thu 6 PM
2. Orders Cut-Off for Invoices — Thu 7 PM
3. Invoice uploaded on Portal — Fri 6 PM
4. Payments Processed by Zambeel — Mon-Tue

## Store Platforms Supported
Shopify | EasyOrder | Light Funnels | YouCan | Salla | Manual (no platform)

## Webhook Integrations (Inbound)
Order events arrive via webhooks from: Shopify, EasyOrder, LightFunnels, Salla, YouCan, Smartlane, Wati (WhatsApp), iMile, Tawseel

## Key Zustand Stores (Seller-relevant)
| Store | Key | Contents |
|-------|-----|---------|
| `useAuthStore` | `"auth-storage"` | authToken, userRole, user, showInventory, products[] |
| `useAgencyViewStore` | `"agency-view-storage"` | isAgencyView, context: {agencyName, merchantUserId, merchantName, storeName, storeId, allowedStoreIds} |
| `useGoldPlanStore` | `"gold-plan-storage"` | isGoldPlanActive, planExpiryTime |
| `useInvoicesStore` | — | invoicesUploadReload (bool) |
| `usePurchaseOrdersStore` | — | orders[], filteredOrders[], loading, filters, pagination |
| `useReturnOrderStore` | — | Similar to purchase orders |

## First-Time User Detection
`useAuthStore.isFirstTimeUser()` returns `true` if user.createdAt < 24 hours ago. Controls onboarding flow redirect.

## Agency Proxy Mode (for Agency users viewing seller data)
When `useAgencyViewStore.isAgencyView === true`:
- All API calls include `x-agency-context-store-id: <storeId>` header
- Agency Context Banner shown at top of every page
- Context cleared when navigating back to `/agency/portal/*`
