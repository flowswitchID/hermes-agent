"""Solve + verify Cloudflare Turnstile locally via CloakBrowser.

Route-intercept → solve the Turnstile widget on a fake page served at the
target origin, then verify the token from the same browser session (keeps the
origin/cookies and stays inside the token's 300s single-use window).
"""
import asyncio
import json
import logging
import time
from pathlib import Path

import cloakbrowser

from common.browser import browser_kwargs, run_pre_actions, run_post_fetch, fetch_from_page, route_glob

log = logging.getLogger(__name__)
_solve_lock = asyncio.Lock()
_TEMPLATE_PATH = Path(__file__).parent / "template.html"
HTML_TEMPLATE = _TEMPLATE_PATH.read_text()


def _browser_kwargs(proxy: str = None) -> dict:
    return browser_kwargs("TURNSTILE", proxy=proxy)


def _error_codes(body: str) -> list:
    """Pull Cloudflare siteverify error-codes out of a verify response."""
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return []
    return data.get("error-codes") or data.get("details") or []


# ── Route-intercept (fast, generic) ─────────────────────────────────

async def _get_turnstile_response_route(page, max_attempts: int = 20) -> str:
    """Retrieve token from route-intercepted page (Theyka pattern)."""
    for _ in range(max_attempts):
        try:
            val = await page.input_value("[name=cf-turnstile-response]")
            if val == "":
                try:
                    await page.click("//div[@class='cf-turnstile']", timeout=3000)
                except Exception:
                    pass
                await asyncio.sleep(1)
            else:
                el = await page.query_selector("[name=cf-turnstile-response]")
                if el:
                    return await el.get_attribute("value")
                break
        except Exception:
            await asyncio.sleep(1)
    raise TimeoutError("Token not received via route-intercept")


async def solve_turnstile(sitekey: str, url: str, action: str = None,
                          cdata: str = None, proxy: str = None) -> dict:
    """Solve Turnstile via route interception. Returns {token, expires_in}."""
    t0 = time.monotonic()
    async with _solve_lock:
        target = url
        div = (f'<div class="cf-turnstile" data-sitekey="{sitekey}"'
               + (f' data-action="{action}"' if action else '')
               + (f' data-cdata="{cdata}"' if cdata else '')
               + '></div>')
        page_data = HTML_TEMPLATE.replace("<!-- cf turnstile -->", div)

        async with await cloakbrowser.launch_async(**_browser_kwargs(proxy)) as browser:
            page = await browser.new_page()
            try:
                await page.route(route_glob(target), lambda r: r.fulfill(body=page_data,
                                                             status=200))
                await page.goto(target, wait_until="domcontentloaded")
                token = await _get_turnstile_response_route(page)
                return {"token": token, "expires_in": 300,
                        "elapsed": round(time.monotonic() - t0, 1),
                        "method": "route"}
            finally:
                await page.close()


# ── solve_and_verify ────────────────────────────────────────────────

async def solve_and_verify(sitekey: str, verify_url: str,
                           verify_payload: dict = None,
                           action: str = None, cdata: str = None,
                           page_url: str = None, proxy: str = None) -> dict:
    """Solve via route-intercept, then verify from the same browser session."""
    t0 = time.monotonic()
    async with _solve_lock:
        target = page_url or verify_url
        div = (f'<div class="cf-turnstile" data-sitekey="{sitekey}"'
               + (f' data-action="{action}"' if action else '')
               + (f' data-cdata="{cdata}"' if cdata else '')
               + '></div>')
        page_data = HTML_TEMPLATE.replace("<!-- cf turnstile -->", div)

        async with await cloakbrowser.launch_async(**_browser_kwargs(proxy)) as browser:
            page = await browser.new_page()
            try:
                await page.route(route_glob(target), lambda r: r.fulfill(
                    body=page_data, status=200))
                await page.goto(target, wait_until="domcontentloaded",
                                timeout=30000)
                token = await _get_turnstile_response_route(page)
                log.info("Route-intercept: token obtained in %.1fs",
                         time.monotonic() - t0)

                payload = dict(verify_payload or {})
                payload["token"] = token
                # Parameterized: verify_url + payload pass as evaluate() args, never
                # interpolated into JS source (injection-safe).
                result = await fetch_from_page(
                    page, verify_url, "POST", json.dumps(payload))
                codes = _error_codes(result["body"])
                # Do NOT log the response body — it may carry session tokens/JWTs.
                log.info("Route-intercept verify: %d codes=%s",
                         result["status"], codes)

                return {"token": token, "expires_in": 300,
                        "verify_status": result["status"],
                        "verify_body": result["body"],
                        "verify_error_codes": codes,
                        "method": "route",
                        "elapsed": round(time.monotonic() - t0, 1)}
            finally:
                await page.close()


# ── Real-page solver ────────────────────────────────────────────────

# Sitekey is passed as the evaluate() arg `k` — never interpolated into JS source
# (injection-safe). No data-theme: a hard-coded theme is a fixed real-page fingerprint.
# render=explicit sites (e.g. GPTMail) won't auto-render from a div — must call
# window.turnstile.render() after the widget is in the DOM.
_WIDGET_INJECT_JS = (
    "(o) => {"
    "  const k = o.k, a = o.a;"
    "  const ensureScript = () => {"
    "    if (document.querySelector('script[src*=turnstile]')) return;"
    "    const s = document.createElement('script');"
    "    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';"
    "    s.async = true; s.defer = true;"
    "    document.head.appendChild(s);"
    "  };"
    "  ensureScript();"
    "  const d = document.createElement('div');"
    "  d.className = 'cf-turnstile';"
    "  d.setAttribute('data-sitekey', k);"
    "  if (a) d.setAttribute('data-action', a);"
    "  document.body.prepend(d);"
    "  let rendered = false;"
    "  const tryRender = () => {"
    "    if (window.turnstile && window.turnstile.render) {"
    "      try {"
    "        if (!rendered) {"
    "          const opts = {"
    "            sitekey: k,"
    "            callback: (tok) => {"
    "              const inp = document.createElement('input');"
    "              inp.name = 'cf-turnstile-response';"
    "              inp.value = tok;"
    "              document.body.appendChild(inp);"
    "            }"
    "          };"
    "          if (a) opts.action = a;"
    "          window.turnstile.render(d, opts);"
    "          rendered = true;"
    "          setTimeout(() => {"
    "            try { window.turnstile.execute(d); } catch (e) { console.log('ts_exec_err', e); }"
    "          }, 1500);"
    "        }"
    "      } catch (e) { console.log('ts_render_err', e); }"
    "    } else {"
    "      setTimeout(tryRender, 500);"
    "    }"
    "  };"
    "  tryRender();"
    "}"
)


async def _inject_turnstile_widget(page, sitekey: str, action: str = None) -> None:
    """Inject a .cf-turnstile widget with the sitekey passed as data (evaluate arg)."""
    await page.evaluate(_WIDGET_INJECT_JS, {"k": sitekey, "a": action})


async def _human_click_iframe(page, fr) -> bool:
    """Click the Turnstile checkbox via humanized page-level mouse movement.

    CloakBrowser's humanizer hooks page.mouse.click (B-spline paths + overshoot) but
    NOT frame.click, so fr.click() inside the cross-origin iframe sends a robotic instant
    click. Instead we resolve the iframe's page-absolute box and click at the checkbox
    offset (left edge + 30px, vertical centre) via the humanized page.mouse.
    """
    try:
        el = await fr.frame_element()
        box = await el.bounding_box()
    except Exception:
        return False
    if not box or box["width"] < 20:
        return False
    x = box["x"] + 30
    y = box["y"] + box["height"] / 2
    await page.mouse.click(x, y)  # humanized (B-spline) — page-level, not frame
    return True


async def _click_turnstile_checkbox(page, attempts: int = 25) -> bool:
    """Click the checkbox inside the cross-origin Cloudflare iframe.

    Prefers a humanized page-level mouse click on the iframe's box; falls back to
    a frame-level selector click (not humanized) if the box can't be resolved.
    Only targets VISIBLE iframes — pages may embed multiple Turnstile widgets
    (own + injected), and clicking a hidden one does nothing.
    """
    for _ in range(attempts):
        for fr in page.frames:
            if "challenges.cloudflare.com" not in (fr.url or ""):
                continue
            try:
                el = await fr.frame_element()
                box = await el.bounding_box()
            except Exception:
                box = None
            if not box or box["width"] < 20 or box["height"] < 20:
                continue  # hidden / zero-size iframe — skip
            if await _human_click_iframe(page, fr):
                return True
            for sel in ("input[type=checkbox]", "label", "body"):
                try:
                    await fr.click(sel, timeout=2000)
                    return True
                except Exception:
                    continue
        await asyncio.sleep(1)
    return False


async def solve_turnstile_realpage(url: str, sitekey: str = None,
                                   timeout_s: int = 60,
                                   action: str = None,
                                   pre_actions: list = None,
                                   post_fetch: list = None,
                                   proxy: str = None) -> dict:
    """Navigate a real page, execute pre_actions, click the CF Turnstile checkbox,
    return the token and browser cookies.

    pre_actions — optional list of steps before Turnstile appears:
      [{"type": "click", "selector": "text=Continue with Email"},
       {"type": "fill", "selector": "input[type=email]", "value": "user@example.com"},
       {"type": "click", "selector": "button[type=submit]"}]

    post_fetch — optional list of API calls to make from the SAME browser session
    after solving (keeps cookies/session for endpoints that require same-origin):
      [{"url": "https://app.kilo.ai/api/auth/verify-turnstile", "method": "POST", "body": {"token": "__TOKEN__"}},
       {"url": "https://app.kilo.ai/api/auth/magic-link", "method": "POST", "body": {"email": "user@example.com", "callbackUrl": "/"}}]

    Use __TOKEN__ placeholder in body to inject the solved Turnstile token.

    Selector formats supported: CSS, XPath (//), text=, regex=, role=
    """
    t0 = time.monotonic()

    async with _solve_lock:
        async with await cloakbrowser.launch_async(**_browser_kwargs(proxy)) as browser:
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)

                if pre_actions:
                    await run_pre_actions(page, pre_actions)
                    await asyncio.sleep(2)

                # Inject sitekey widget if given (override page's own).
                if sitekey:
                    await _inject_turnstile_widget(page, sitekey, action)
                    await asyncio.sleep(3)
                    # Bring the injected widget on-screen and on top — the page's
                    # own CSS may hide .cf-turnstile or render it below the fold,
                    # and interactive challenges need a visible, clickable box.
                    await page.evaluate(
                        "() => {"
                        "  const d = document.querySelector('.cf-turnstile');"
                        "  if (!d) return;"
                        "  d.style.position = 'fixed';"
                        "  d.style.top = '16px';"
                        "  d.style.right = '16px';"
                        "  d.style.zIndex = '2147483647';"
                        "  d.style.background = '#fff';"
                        "  d.style.padding = '8px';"
                        "  d.style.borderRadius = '8px';"
                        "  d.style.boxShadow = '0 4px 20px rgba(0,0,0,.3)';"
                        "}"
                    )
                    await asyncio.sleep(1)

                clicked = await _click_turnstile_checkbox(page)
                log.info("Real-page checkbox clicked=%s", clicked)

                # Harvest token, bounded by timeout_s. Prefer the page's own
                # response input; fall back to turnstile.getResponse().
                token = ""
                deadline = time.monotonic() + timeout_s
                while time.monotonic() < deadline:
                    try:
                        token = await page.evaluate(
                            "() => { const e=document.querySelector('[name=cf-turnstile-response]');"
                            " return e ? e.value : '' }")
                    except Exception:
                        token = ""
                    if token:
                        break
                    # Explicit getResponse covers invisible-mode widgets whose
                    # token lives in the widget's own hidden input, not the
                    # page-level [name=cf-turnstile-response] we look for above.
                    try:
                        token = await page.evaluate(
                            "() => { try { return window.turnstile ? (window.turnstile.getResponse() || '') : '' }"
                            " catch (e) { return '' } }")
                    except Exception:
                        pass
                    if token:
                        break
                    await asyncio.sleep(1)

                # Post_fetch from the same session (parameterized — injection-safe).
                result = {"token": token,
                          "verify_success": bool(token),
                          "method": "real-page",
                          "elapsed": round(time.monotonic() - t0, 1)}
                if post_fetch and token:
                    result["post_fetch"] = await run_post_fetch(page, post_fetch, token)

                # Capture cookies AFTER post_fetch — browser-verification sets
                # gm_browser_verified/cf_clearance which are needed for later API calls.
                cookies = await page.context.cookies()
                result["cookies"] = cookies

                return result
            finally:
                await page.close()
