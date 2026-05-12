"""
OMS live UI exploration — uses email/password login from .env.
Visits every OMS page on staging, extracts all interactive elements,
clicks dropdowns/tabs/modals, and saves JSON + screenshots to exploration_output/.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_URL = "https://staging.myzambeel.com"
EMAIL    = os.getenv("ADMIN_STAGING_EMAIL", "").strip()
PASSWORD = os.getenv("ADMIN_STAGING_PASSWORD", "").strip()

OUT_DIR = Path(__file__).parent / "exploration_output"
OUT_DIR.mkdir(exist_ok=True)

OMS_ROUTES = [
    "/orders-management/dashboard",
    "/orders-management/orders",
    "/orders-management/inventory-movements",
    "/orders-management/ticketing",
    "/orders-management/commission-models",
    "/orders-management/dispatch-batches",
    "/orders-management/purchase-orders",
    "/orders-management/return-orders",
    "/orders-management/agency-registrations",
    "/orders-management/agents",
    "/orders-management/gold-subscriptions",
    "/orders-management/ticker-config",
    "/orders-management/stores-settings",
    "/orders-management/ratings-settings",
    "/orders-management/tags-management",
    "/orders-management/invoice-upload",
]

DOM_JS = """() => {
    const txt = el => (el.innerText||el.textContent||'').trim().replace(/\\s+/g,' ');
    return {
        title:        document.title,
        url:          location.href,
        buttons:      [...new Set([...document.querySelectorAll('button')].map(txt).filter(Boolean))],
        inputs:       [...document.querySelectorAll('input')].map(i=>({
                          placeholder:i.placeholder, type:i.type,
                          name:i.name, ariaLabel:i.getAttribute('aria-label')||''}))
                          .filter(i=>i.placeholder||i.ariaLabel),
        selects:      [...document.querySelectorAll('select')].map(s=>({
                          name:s.name, ariaLabel:s.getAttribute('aria-label')||'',
                          options:[...s.options].map(o=>o.text.trim()).filter(Boolean)})),
        headings:     [...document.querySelectorAll('h1,h2,h3,h4')]
                          .map(h=>({tag:h.tagName.toLowerCase(),text:txt(h)})).filter(h=>h.text),
        tableHeaders: [...new Set([...document.querySelectorAll('th')].map(txt).filter(Boolean))],
        tabs:         [...new Set([...document.querySelectorAll(
                          "[role='tab'],button[aria-selected]")].map(txt).filter(Boolean))],
        labels:       [...new Set([...document.querySelectorAll('label')].map(txt).filter(Boolean))],
        badges:       [...new Set([...document.querySelectorAll(
                          "span[class*='rounded'],span[class*='badge'],span[class*='status']")]
                          .map(txt).filter(Boolean))].slice(0,40),
        dropdownTriggers: [...new Set([...document.querySelectorAll(
                          "[aria-haspopup],[data-dropdown-toggle]")].map(txt).filter(Boolean))],
        visibleText:  [...new Set([...document.querySelectorAll('td,li,p,span.text-sm,span.text-xs')]
                          .map(txt).filter(t=>t.length>1&&t.length<120))].slice(0,100),
        allSelectOptions: (() => {
            const out = {};
            [...document.querySelectorAll('select')].forEach((s, i) => {
                const key = s.getAttribute('aria-label')||s.name||s.id||('select_'+i);
                out[key] = [...s.options].map(o=>o.text.trim()).filter(Boolean);
            });
            return out;
        })(),
    };
}"""


def do_login(page):
    print(f"[login] {EMAIL}")
    page.goto(f"{BASE_URL}/login", timeout=30000, wait_until="networkidle")
    page.wait_for_selector('input[type="email"], input[type="text"]', timeout=15000)
    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
    page.wait_for_timeout(3000)
    print(f"[login] OK → {page.url}")


def ss(page, label):
    p = OUT_DIR / f"{label}.png"
    try:
        page.screenshot(path=str(p), full_page=True)
        return str(p)
    except Exception as e:
        return f"error:{e}"


def get_dom(page):
    try:
        return page.evaluate(DOM_JS)
    except Exception as e:
        return {"error": str(e)}


def click_tabs(page, slug):
    results = {}
    tabs = page.locator("[role='tab'], button[aria-selected]").all()
    for i, tab in enumerate(tabs[:10]):
        try:
            label = (tab.inner_text() or "").strip()[:50]
            tab.click(timeout=4000)
            page.wait_for_timeout(1500)
            results[f"tab_{i}_{label}"] = {
                "tab_text": label,
                "dom": get_dom(page),
                "screenshot": ss(page, f"{slug}_tab{i}"),
            }
        except Exception as e:
            results[f"tab_{i}_err"] = str(e)
    return results


def click_dropdowns(page, slug):
    """Click aria-haspopup triggers and capture dropdown options."""
    results = {}

    results["native_selects"] = page.evaluate("""() => {
        const out = {};
        [...document.querySelectorAll('select')].forEach((s, i) => {
            const key = s.getAttribute('aria-label')||s.name||s.id||('select_'+i);
            out[key] = [...s.options].map(o=>o.text.trim()).filter(Boolean);
        });
        return out;
    }""")

    triggers = page.locator(
        "[aria-haspopup='listbox'],[aria-haspopup='menu'],"
        "[data-dropdown-toggle],[aria-expanded='false']:not([disabled])"
    ).all()
    for i, btn in enumerate(triggers[:15]):
        try:
            label = (btn.inner_text() or btn.get_attribute("aria-label") or "").strip()[:40]
            if not btn.is_visible(timeout=1000):
                continue
            btn.click(timeout=4000)
            page.wait_for_timeout(1000)
            opts = page.locator(
                "[role='option'],[role='menuitem'],ul[role='listbox'] li,[role='listbox'] li"
            ).all_inner_texts()
            results[f"dropdown_{i}_{label}"] = {
                "trigger": label,
                "options": [o.strip() for o in opts if o.strip()],
                "screenshot": ss(page, f"{slug}_dd{i}"),
            }
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        except Exception as e:
            results[f"dropdown_{i}_err"] = str(e)
    return results


def open_modals(page, slug):
    """Click Create/Add/New/Upload buttons to expose modal form fields."""
    results = {}
    triggers = [
        ("button:has-text('+ New')",        "new"),
        ("button:has-text('+ New Model')",  "new_model"),
        ("button:has-text('Create')",        "create"),
        ("button:has-text('Add')",           "add"),
        ("button:has-text('Upload')",        "upload"),
        ("button:has-text('New Ticket')",    "new_ticket"),
        ("button:has-text('Approve')",       "approve"),
    ]
    for selector, key in triggers:
        try:
            btn = page.locator(selector).first
            if not btn.count() or not btn.is_visible(timeout=1000):
                continue
            btn.click(timeout=4000)
            page.wait_for_timeout(1500)
            if page.locator("div[role='dialog']").count():
                results[f"modal_{key}"] = {
                    "dom": get_dom(page),
                    "screenshot": ss(page, f"{slug}_modal_{key}"),
                }
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:
            pass
    return results


def explore_ticketing_filters(page, slug):
    """Deep-dive into the Ticketing filter row: click each filter-type option."""
    result = {}
    result["initial_dom"] = get_dom(page)
    result["screenshot"] = ss(page, f"{slug}_filters_initial")

    for label in ["Store Name", "Ticket ID", "Order ID", "Status", "Team ID", "Filter"]:
        for locator in [page.get_by_text(label, exact=True).first,
                        page.get_by_text(label, exact=False).first]:
            try:
                if locator.count() and locator.is_visible(timeout=1500):
                    locator.click(timeout=3000)
                    page.wait_for_timeout(1000)
                    opts = page.locator("[role='option'],[role='menuitem']").all_inner_texts()
                    dom_after = get_dom(page)
                    result[f"click_{label}"] = {
                        "options": [o.strip() for o in opts if o.strip()],
                        "inputs_after": dom_after.get("inputs", []),
                        "screenshot": ss(page, f"{slug}_filter_{label.replace(' ','_')}"),
                    }
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(400)
                    break
            except Exception:
                pass

    # Also grab all native selects in filter area
    result["all_native_selects"] = page.evaluate("""() => {
        const out = {};
        [...document.querySelectorAll('select')].forEach((s, i) => {
            const key = s.getAttribute('aria-label')||s.name||s.id||('select_'+i);
            out[key] = [...s.options].map(o=>o.text.trim()).filter(Boolean);
        });
        return out;
    }""")
    return result


def explore_inventory_pagination(page, slug):
    """Scroll to bottom and extract pagination controls for Inventory Movements."""
    result = {}
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1500)
    result["bottom_screenshot"] = ss(page, f"{slug}_bottom")

    result["native_selects"] = page.evaluate("""() => {
        const out = {};
        [...document.querySelectorAll('select')].forEach((s, i) => {
            const key = s.getAttribute('aria-label')||s.name||s.id||('select_'+i);
            out[key] = [...s.options].map(o=>({v:o.value,t:o.text.trim()})).filter(o=>o.t);
        });
        return out;
    }""")

    result["bottom_text"] = page.evaluate("""() => {
        return [...new Set([...document.querySelectorAll('*')]
            .filter(el => {
                const r = el.getBoundingClientRect();
                return el.children.length === 0 && r.top > window.innerHeight * 0.6;
            })
            .map(el => (el.innerText||'').trim())
            .filter(t => t.length > 0 && t.length < 120)
        )].slice(0, 60);
    }""")

    result["pagination_elements"] = page.evaluate("""() => {
        const out = [];
        const sels = ['select','input[type="number"]',
            '[aria-label*="page" i]','[aria-label*="rows" i]',
            '[class*="pagination"]','[class*="per-page"]','[class*="page-size"]'];
        sels.forEach(sel => {
            [...document.querySelectorAll(sel)].forEach(el => {
                out.push({
                    tag: el.tagName.toLowerCase(),
                    aria: el.getAttribute('aria-label')||'',
                    ph: el.getAttribute('placeholder')||'',
                    cls: (el.getAttribute('class')||'').slice(0,80),
                    opts: el.tagName==='SELECT'
                        ? [...el.options].map(o=>o.text.trim())
                        : []
                });
            });
        });
        return out;
    }""")

    return result


def navigate_to(page, route):
    full_url = BASE_URL + route
    try:
        page.goto(full_url, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(2500)
        if "/login" not in page.url:
            return True
    except Exception as e:
        print(f"  [nav] goto error: {e}")

    # Fallback: sidebar link click
    try:
        link = page.locator(f"a[href='{route}']").first
        if link.count():
            link.click(timeout=6000)
            page.wait_for_timeout(2500)
            page.wait_for_load_state("networkidle", timeout=15000)
            if "/login" not in page.url:
                return True
    except Exception as e:
        print(f"  [nav] sidebar fallback error: {e}")

    return False


def explore_page(page, route, slug):
    data = {
        "route": route,
        "url": page.url,
        "dom": get_dom(page),
        "screenshot": ss(page, f"{slug}_default"),
        "tabs": click_tabs(page, slug),
        "dropdowns": click_dropdowns(page, slug),
        "modals": open_modals(page, slug),
    }

    if "ticketing" in route:
        data["ticketing_filters"] = explore_ticketing_filters(page, slug)

    if "inventory-movements" in route:
        data["pagination"] = explore_inventory_pagination(page, slug)

    return data


def main():
    if not EMAIL or not PASSWORD:
        print("[ERROR] ADMIN_STAGING_EMAIL or ADMIN_STAGING_PASSWORD not set in .env")
        return

    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        do_login(page)

        for route in OMS_ROUTES:
            slug = "oms_" + route.strip("/").replace("/", "_")
            print(f"\n[{route}]")

            ok = navigate_to(page, route)
            if not ok:
                print("  auth lost — re-logging in")
                try:
                    do_login(page)
                    ok = navigate_to(page, route)
                except Exception as e:
                    print(f"  re-login failed: {e}")

            if not ok:
                entry = {"route": route, "error": "navigation_failed"}
                all_results.append(entry)
                (OUT_DIR / f"{slug}.json").write_text(json.dumps(entry, indent=2))
                continue

            data = explore_page(page, route, slug)
            all_results.append(data)
            (OUT_DIR / f"{slug}.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False)
            )
            print(f"  saved {slug}.json")

        browser.close()

    (OUT_DIR / "oms_all.json").write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False)
    )
    print(f"\nDone. {len(all_results)} pages → {OUT_DIR}")


if __name__ == "__main__":
    main()
