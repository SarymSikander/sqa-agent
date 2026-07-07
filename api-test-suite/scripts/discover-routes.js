#!/usr/bin/env node
/**
 * Route discovery script for the Zambeel API.
 *
 * Reads server.js and recursively follows all router require() statements,
 * extracts every HTTP method, path, and middleware, then writes api-inventory.json.
 *
 * Usage:
 *   node scripts/discover-routes.js
 *   API_REPO_PATH=/other/path node scripts/discover-routes.js
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });

const fs   = require('fs');
const path = require('path');

const API_REPO_PATH = process.env.API_REPO_PATH ||
  '/Users/sarimsikandar/Documents/GitHub/zambeel-api';

const OUTPUT_FILE = path.resolve(__dirname, '../api-inventory.json');

// ── Auth middleware → allowed roles ──────────────────────────────────────────
const AUTH_ROLES = {
  verifyUser:                          ['Admin', 'Agent'],
  verifySeller:                        ['Seller', 'Agency'],
  verifyJWT:                           ['Admin', 'Agent', 'Seller', 'Agency'],
  verifyAdminOnly:                     ['Admin'],
  verifyAdminAndSeller:                ['Admin', 'Seller'],
  verifyAgentAdminAndSeller:           ['Admin', 'Agent', 'Seller'],
  verifyAdminAndSellerWithAgencyContext: ['Admin', 'Seller', 'Agency'],
  verifyAgencyStoreContext:            ['Seller', 'Agency'],
};

// ── Category inference ────────────────────────────────────────────────────────
function inferCategory(routePath) {
  if (/\/(login|signUp|auth|verify-email)/.test(routePath)) return 'auth';
  if (/\/dashboard/.test(routePath))              return 'dashboard';
  if (/\/(teams|agents)/.test(routePath))         return 'teams';
  if (/\/orders/.test(routePath))                 return 'orders';
  if (/\/remarks/.test(routePath))                return 'orders';
  if (/\/tags/.test(routePath))                   return 'orders';
  if (/\/(tickets|comments)/.test(routePath))     return 'tickets';
  if (/\/inventory-movements/.test(routePath))    return 'inventory';
  if (/\/inventory/.test(routePath))              return 'inventory';
  if (/\/products/.test(routePath))               return 'products';
  if (/\/store/.test(routePath))                  return 'store';
  if (/\/admin/.test(routePath))                  return 'admin';
  if (/\/(shopify|notion|lightfunnels|salla|youcan|easyorder)/.test(routePath)) return 'integrations';
  return 'misc';
}

// ── Priority inference ────────────────────────────────────────────────────────
function inferPriority(method, routePath) {
  const p0Patterns = [
    /\/login$/,
    /\/orders$/,
    /\/status-counts/,
    /\/dashboard\/data/,
    /\/orderDetails/,
  ];
  if (p0Patterns.some((re) => re.test(routePath))) return 'P0';

  const p1Patterns = [
    /\/order-analytics/,
    /\/logs/,
    /\/assign-courier/,
    /\/teams$/,
    /\/agents$/,
    /\/tickets/,
    /\/inventory/,
    /\/remarks/,
    /\/comments/,
  ];
  if (p1Patterns.some((re) => re.test(routePath))) return 'P1';

  return 'P2';
}

// ── SLA key mapping ───────────────────────────────────────────────────────────
function inferSlaKey(method, routePath) {
  const map = [
    { re: /\/login$/,                              key: 'login' },
    { re: /\/orders$/,            method: 'POST',  key: 'getOrders' },
    { re: /\/status-counts/,                       key: 'statusCounts' },
    { re: /\/orderDetails/,                        key: 'orderDetails' },
    { re: /\/orders\/.+\/logs/,                    key: 'orderLogs' },
    { re: /\/teams$/,                              key: 'teamslist' },
    { re: /\/seller-inventory\/export/,            key: 'csvExport' },
    { re: /\/seller-inventory$/,                   key: 'stockValidation' },
    { re: /\/dashboard\/data/,                     key: 'sellerDashboard' },
    { re: /\/tags$/,              method: 'POST',  key: 'updateStatusTags' },
    { re: /\/remarks$/,           method: 'POST',  key: 'bulkRemarks' },
    { re: /\/assign-courier/,                      key: 'assignCourier' },
    { re: /\/inventory-movements\/movements/,      key: 'inventoryMovements' },
    { re: /\/order-analytics/,                     key: 'orderAnalytics' },
    { re: /\/tickets$/,           method: 'GET',   key: 'ticketList' },
    { re: /\/comments\/ticket/,                    key: 'ticketComments' },
    { re: /\/agents$/,                             key: 'agentsList' },
  ];
  for (const entry of map) {
    if (entry.re.test(routePath) && (!entry.method || entry.method === method)) {
      return entry.key;
    }
  }
  return null;
}

// ── Route file parser ─────────────────────────────────────────────────────────
const visited = new Set();

/**
 * Use a parenthesis-depth counter to extract individual router.METHOD(...) calls
 * from a file, handling multi-line definitions correctly.
 */
function extractRouterCalls(content) {
  const calls = [];
  const methodRe = /\brouter\.(get|post|put|patch|delete|use)\s*\(/gi;
  let m;

  while ((m = methodRe.exec(content)) !== null) {
    const httpMethod = m[1].toLowerCase();
    const start = m.index + m[0].length; // position after the opening (
    let depth = 1;
    let i = start;
    while (i < content.length && depth > 0) {
      const ch = content[i];
      if (ch === '(') depth++;
      else if (ch === ')') depth--;
      // Skip strings so parens inside them don't confuse the counter
      else if (ch === '"' || ch === "'") {
        const quote = ch;
        i++;
        while (i < content.length && content[i] !== quote) {
          if (content[i] === '\\') i++; // escape
          i++;
        }
      } else if (ch === '`') {
        i++;
        while (i < content.length && content[i] !== '`') {
          if (content[i] === '\\') i++;
          i++;
        }
      }
      i++;
    }
    const body = content.slice(start, i - 1); // inside the parens
    calls.push({ httpMethod, body });
  }
  return calls;
}

function parseRouteFile(filePath, prefix) {
  const resolved = filePath.endsWith('.js') ? filePath : filePath + '.js';
  if (!fs.existsSync(resolved) || visited.has(resolved)) return [];
  visited.add(resolved);

  let content;
  try { content = fs.readFileSync(resolved, 'utf8'); } catch { return []; }

  const routes = [];
  const calls  = extractRouterCalls(content);

  for (const { httpMethod, body } of calls) {
    // Extract the first string argument (the route path)
    const pathMatch = body.match(/^\s*['"`]([^'"`]+)['"`]/);
    if (!pathMatch) continue;
    const localPath = pathMatch[1];

    if (httpMethod === 'use') {
      // Try to find a require() call in the remaining args
      const reqMatch = body.match(/require\s*\(\s*['"`]([^'"`]+)['"`]\s*\)/);
      if (reqMatch) {
        const subRelative = reqMatch[1];
        const subFile = path.resolve(path.dirname(resolved), subRelative);
        const subRoutes = parseRouteFile(subFile, prefix + localPath.replace(/\/$/, ''));
        routes.push(...subRoutes);
      }
      continue;
    }

    // Find auth middleware names in the body
    // Strip nested paren contents first to avoid false positives inside validators
    const stripped = body.replace(/\([\s\S]*?\)/g, '()');
    const identifiers = new Set((stripped.match(/\b[a-zA-Z_]\w*\b/g) || []));

    let authRequired = false;
    let roles = [];
    for (const [name, r] of Object.entries(AUTH_ROLES)) {
      if (identifiers.has(name)) {
        authRequired = true;
        roles = r;
        break;
      }
    }

    const fullPath = '/api' + prefix + localPath;
    routes.push({
      method: httpMethod.toUpperCase(),
      path:   fullPath,
      authRequired,
      roles,
    });
  }

  return routes;
}

// ── Entry point ───────────────────────────────────────────────────────────────
function main() {
  console.log(`🔍  Discovering routes in ${API_REPO_PATH}`);

  const indexFile = path.join(API_REPO_PATH, 'routes', 'index.js');
  if (!fs.existsSync(indexFile)) {
    console.error(`❌  routes/index.js not found at ${indexFile}`);
    console.error('   Set API_REPO_PATH env var to the zambeel-api root.');
    process.exit(1);
  }

  // Add hardcoded public routes defined in server.js
  const rawRoutes = [
    { method: 'POST', path: '/api/login',        authRequired: false, roles: [] },
    { method: 'POST', path: '/api/signUp',        authRequired: false, roles: [] },
    { method: 'GET',  path: '/api/auth/check-email', authRequired: false, roles: [] },
    { method: 'GET',  path: '/api/verify-email',  authRequired: false, roles: [] },
    ...parseRouteFile(indexFile, ''),
  ];

  // De-duplicate by method+path
  const seen = new Set();
  const unique = rawRoutes.filter(({ method, path: p }) => {
    const key = `${method}:${p}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Enrich with category, priority, slaKey, TC id
  let tcIdx = 1;
  const inventory = unique.map((r) => ({
    id:          `TC_${String(tcIdx++).padStart(3, '0')}`,
    method:      r.method,
    path:        r.path,
    authRequired: r.authRequired,
    roles:       r.roles,
    category:    inferCategory(r.path),
    priority:    inferPriority(r.method, r.path),
    slaKey:      inferSlaKey(r.method, r.path),
  }));

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(inventory, null, 2));

  const byPriority = { P0: 0, P1: 0, P2: 0 };
  inventory.forEach((r) => byPriority[r.priority]++);

  console.log(`✅  Discovered ${inventory.length} routes`);
  console.log(`   P0=${byPriority.P0}  P1=${byPriority.P1}  P2=${byPriority.P2}`);
  console.log(`📄  Written to ${OUTPUT_FILE}`);
}

main();
