# Agency Portal — Overview

## What Is It?
The Agency Portal is a sub-portal within the Seller interface, accessible to users who have registered and been approved as an Agency. Agencies are sales/growth partners that connect to multiple sellers, track their orders/revenue, and earn commissions on delivered orders.

## Who Uses It?
| Role | Access |
|------|--------|
| `Seller` (approved as agency) | Full Agency portal |
| `Agency` | Full Agency portal |

A Seller must first register as an agency and be **approved** by an Admin before the full Agency portal unlocks.

## Registration Status Lifecycle
```
(No registration) → Pending → Approved / OnHold / Rejected
                                           ↓
                                    (Resubmit if allowed)
                                           ↓
                                         Pending
```

## Base URLs (same as Seller Portal)
| Environment | URL |
|------------|-----|
| Local | `http://localhost:5173` |
| Staging | `https://staging.myzambeel.com` |
| Production | `https://portal.myzambeel.com` |

## Post-Login Landing for Approved Agency
After login, approved agencies still land on `/get-started` or `/dashboard` (Seller portal). They switch to Agency portal via the **Agency** tab in the sidebar.

## Route Guard
- Agency portal pages at `/agency` — protected by `SellerProtectedRoute`
- Pages at `/agency/portal/*` — additionally require `AgencyApprovedRoute` (registration_status === "Approved")
- If not approved, `/agency/portal/*` redirects to `/agency`

## Sidebar — Agency Tab Navigation

**If registration NOT approved:**
| Item | URL |
|------|-----|
| Dashboard | `/agency` |

**If registration IS approved:**
| Item | URL |
|------|-----|
| Dashboard | `/agency` |
| Merchants | `/agency/portal/merchants` |
| Commission | `/agency/portal/commission` |
| Team Members | `/agency/portal/team-members` |
| Settings | `/agency/portal/settings` |

## Agency Unique ID Format
- Format: `ZMB-AG-XXXXXX` (6 alphanumeric chars after prefix)
- Assigned at approval by OMS admin
- Merchants use this ID to connect to the agency: `POST /agency/connect`

## Commission Types
| Type | How Calculated |
|------|---------------|
| `percentage_of_delivered_revenue` | commission = revenue × (value / 100) |
| `flat_per_delivered_order` | commission = delivered_order_count × value |

Commission is calculated only on **delivered** orders.

## Invoice Statuses
`Draft` → `Sent` → `Paid`

## Merchant Connection Statuses
- Display: `Pending` | `Active` | `Inactive`
- Raw: `Pending` | `Active` | `Rejected` | `Disconnected`

## Team Member Roles
- `Owner` → displayed as `Admin`
- `Member` → displayed as-is

## Team Member Statuses
- `Active`
- `Invite Pending`

## Access Scopes (when merchant connects)
- `"all"` — agency sees all merchant stores
- `"specific"` — agency sees only specified store IDs

## Agency Invite URL Token
- Format: `/agency/invite?token=XXXXXX`
- Accept flow: `POST /agency/team-members/invite/preview` → `POST /agency/team-members/accept`
