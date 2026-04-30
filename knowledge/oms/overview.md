# OMS (Order Management System) — Overview

## What Is OMS?
OMS is the **Admin/Agent portal** for Zambeel operations staff. It is the back-office system used to manage order fulfillment, courier assignment, inventory, agency registrations, invoicing, and seller oversight across all environments.

## Who Uses It?
| Role | Access Level |
|------|-------------|
| `Admin` | Full access to all OMS pages and actions |
| `Agent` | Restricted access — Orders + Ticketing only; cannot access admin-only pages |

## Base URLs
| Environment | URL |
|------------|-----|
| Local | `http://localhost:5173` |
| Staging | `https://staging.myzambeel.com` |
| Production | `https://portal.myzambeel.com` |

## Post-Login Landing Page
After successful login, Admin/Agent lands on: `/orders-management/dashboard`

## Layout
- Uses `FullLayout` wrapper
- Left vertical sidebar (collapsible) — component: `Sidebaritems.tsx`
- `AgencyContextBanner` appears in header when admin is proxying as an agency

## Route Guard
- All `/orders-management/*` routes are protected by `ProtectedRoute`
- Allowed roles: `Admin`, `Agent`
- Unauthorized users are redirected to `/login`

## Tech Stack (Frontend)
- React 18, TypeScript, Vite
- React Router v7
- Zustand (state)
- TanStack React Query (server state, 5-min stale, 1 retry)
- Tailwind CSS, Flowbite React
- React Hook Form
- React Toastify (top-right, 3s, max 4 toasts)

## Sidebar Navigation (all items)
| Menu Item | URL | Role Required |
|-----------|-----|--------------|
| Dashboard | `/orders-management/dashboard` | Admin + Agent |
| Orders | `/orders-management/orders` | Admin + Agent |
| Dispatch Batches | `/orders-management/dispatch-batches` | Admin only |
| Agents | `/orders-management/agents` | Admin only |
| Ratings Settings | `/orders-management/ratings-settings` | Admin only |
| Stores Settings | `/orders-management/stores-settings` | Admin only |
| Tags Management | `/orders-management/tags-management` | Admin only |
| Purchase Orders | `/orders-management/purchase-orders` | Admin only |
| Return Orders | `/orders-management/return-orders` | Admin only |
| Ticketing | `/orders-management/ticketing` | Admin + Agent |
| Gold Subscriptions | `/orders-management/gold-subscriptions` | Admin only |
| Inventory Movements | `/orders-management/inventory-movements` | Admin only |
| Ticker Config | `/orders-management/ticker-config` | Admin only |
| Agency Registrations | `/orders-management/agency-registrations` | Admin only |
| Commission Models | `/orders-management/commission-models` | Admin only |
| Invoice Upload | `/orders-management/invoice-upload` | Admin only |
| Update Invoice | `/orders-management/invoice-update` | Admin only |
| Profile | `/orders-management/profile` | Admin + Agent |
