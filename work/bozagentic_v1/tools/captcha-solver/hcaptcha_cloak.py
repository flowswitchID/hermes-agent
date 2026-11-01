"""hCaptcha solver via fresh CloakBrowser per solve.

Merges boz-agent's fresh-browser architecture with our superior vision/image solving.
Three modes:
  1. Checkbox (route-intercept): widget on intercepted page → click checkbox →
     harvest token. If image challenge → solve via Gemini/Mistral vision.
  2. Invisible (execute): hcaptcha.execute() — zero interaction.
  3. Real page: navigate actual site, pre_actions, solve, post_fetch, cookies.
"""
import asyncio
import logging
import os
import time
from pathlib import Path

import cloakbrowser

log = logging.getLogger(__name__)
_solve_lock = asyncio.Lock()

# Template: dark bg, flexbox center (boz-agent pattern)
_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>hCaptcha</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{background:#1a1a1a;display:flex;justify-content:center;align-items:center;min-height:100vh}</style>
</head><body>
<!-- hcaptcha widget -->
<script src="https://js.hcaptcha.com/1/api.js" async defer></script>
</body></html>"""

_INVISIBLE_PAGE = """<!DOCTYPE html><html><head>
<script src="https://js.hcaptcha.com/1/api.js?onload=onloadHC&render=explicit" async defer></script>
</head><body>
<script>
window.__token="";window.__err="";
function onloadHC(){try{var w=hcaptcha.render('hc',{sitekey:'__SITEKEY__',size:'invisible',
callback:function(t){window.__token=t},
'error-callback':function(e){window.__err=String(e)},
'expired-callback':function(){window.__err='expired'}});
setTimeout(function(){hcaptcha.execute(w)},300)}catch(e){window.__err=String(e)}}
</script><div id="hc"></div></body></html>"""

_WIDGET_INJECT_JS = (
    "(k) => {"
    "  const d=document.createElement('div');d.className='h-captcha';"
    "  d.setAttribute('data-sitekey',k);document.body.prepend(d);"
    "  if(!document.querySelector(\"script[src*='js.hcaptcha.com']\")){"
    "    const s=document.createElement('script');s.src='https://js.hcaptcha.com/1/api.js';"
    "    s.async=true;s.defer=true;document.head.appendChild(s);}}"
)

# ── Vision backend (lazy) ──
_vision_pool = None


def _get_vision_pool():
    global _vision_pool
    if _vision_pool is not None:
        return _vision_pool
    backend = os.getenv("HCAPTCHA_VISION", "gemini")
    keyfile = str(Path(__file__).parent / "apikey.txt")
    try:
        if backend == "mistral":
            from mistral_vision import KeyPool
            model = os.getenv("HCAPTCHA_MISTRAL_MODEL", "mistral-large-latest")
            _vision_pool = KeyPool(keyfile, model=model)
        else:
            from gemini_vision import KeyPool
            _vision_pool = KeyPool(keyfile)
    except Exception as e:
        log.warning("vision pool init failed: %s", e)
        return None
    return _vision_pool


# ── Token harvest ──

async def _get_token(page, max_attempts=30):
    """Poll DOM textarea + hcaptcha.getResponse() API for token."""
    for _ in range(max_attempts):
        # Method 1: DOM textarea (most reliable)
        try:
            tok = await page.evaluate(
                "() => {"
                "  const el = document.querySelector('[name=h-captcha-response]');"
                "  if (el && el.value && el.value.length > 10) return el.value;"
                "  return '';"
                "}"
            )
            if tok and len(tok) > 10 and "[object" not in tok:
                return tok
        except Exception:
            pass
        # Method 2: hcaptcha.getResponse() API
        try:
            tok = await page.evaluate(
                "() => {"
                "  try {"
                "    const r = hcaptcha.getResponse();"
                "    if (typeof r === 'string' && r.length > 10) return r;"
                "    if (r && typeof r === 'object' && r.response) return r.response;"
                "    return '';"
                "  } catch(e) { return ''; }"
                "}"
            )
            if tok and len(tok) > 10 and "[object" not in tok:
                return tok
        except Exception:
            pass
        await asyncio.sleep(1)
    return ""


# ── Checkbox click with retry ──

async def _click_checkbox(page, attempts=20):
    """Click hCaptcha checkbox inside cross-origin iframe. 20 retries."""
    for _ in range(attempts):
        for fr in page.frames:
            u = fr.url or ""
            if "#frame=checkbox" in u:
                for sel in ("#checkbox", "div[role=checkbox]", "label", "body"):
                    try:
                        await fr.click(sel, timeout=2000)
                        return True
                    except Exception:
                        continue
        # Also try broader selectors (our improvement over boz-agent)
        for fr in page.frames:
            u = fr.url or ""
            if "hcaptcha" in u and "checkbox" in u:
                for sel in ("iframe[src*='frame=checkbox']", "iframe[title*='checkbox' i]",
                            "iframe[data-hcaptcha-widget-id]", "iframe[src*='hcaptcha.com']"):
                    try:
                        box = page.locator(sel)
                        if await box.count() > 0:
                            await box.first.click(force=True, timeout=2000)
                            return True
                    except Exception:
                        continue
        await asyncio.sleep(1)
    return False


# ── Challenge detection ──

def _has_challenge(page):
    for fr in page.frames:
        u = fr.url or ""
        if "#frame=challenge" in u and "hcaptcha" in u:
            return True
    return False


def _find_challenge_frame(page):
    for fr in page.frames:
        u = fr.url or ""
        if "#frame=challenge" in u and "hcaptcha" in u:
            return fr
    return None


async def _close_challenge(page):
    """Dismiss open challenge by clicking Skip/close."""
    for fr in page.frames:
        u = fr.url or ""
        if "#frame=challenge" in u and "hcaptcha" in u:
            try:
                btn = await fr.query_selector(".button-submit")
                if btn:
                    text = (await btn.inner_text()).lower()
                    if text in ("skip", "跳过", "huppel", "ohita", "überspringen"):
                        await btn.click(timeout=3000)
                        await asyncio.sleep(1)
                        return True
                close = await fr.query_selector(".close.button")
                if close:
                    await close.click(timeout=3000)
                    await asyncio.sleep(1)
                    return True
            except Exception:
                pass
    return False


# ── Image challenge solver (uses our hcaptcha_image_solve.py strengths) ──

async def _solve_image_challenge(page, keypool, max_rounds=10, seen_canvases=None):
    """Solve hCaptcha image challenge using our vision backend.

    Imports from hcaptcha_image_solve.py — keeps our strengths:
    - Best-canvas selection (score by size*opacity)
    - Montage grid overlay (upscale tiles, preserves content)
    - Multi-retry with diverse prompts + majority voting
    - Scattered challenge handling (coordinate clicks)
    - Hard challenge skip (odd-one-out, rotation, etc.)
    - Canvas hash guard (no re-click same shape)
    """
    if seen_canvases is None:
        seen_canvases = set()
    challenge_type_counts = {}  # track repeated challenge types
    try:
        from hcaptcha_image_solve import (
            _find_challenge_frame as _find_fr, _challenge_meta, _get_best_canvas,
            _grid_overlay, _pick_cells, _click_tiles, _click_submit,
            _solve_drag, is_hard_challenge, _is_scattered,
            _pick_scattered_point, _click_point, _canvas_is_scattered,
        )
        import hashlib
        from collections import Counter

        last_scattered_hash = ""

        for round_no in range(max_rounds):
            fr = _find_fr(page)
            if not fr:
                log.info("vision: no challenge frame round %d", round_no)
                break

            # Wait for canvas (up to 8s)
            canvas_found = False
            for _ in range(16):
                meta = await _challenge_meta(fr)
                if meta.get("canvasRect"):
                    canvas_found = True
                    break
                await asyncio.sleep(0.5)
            if not canvas_found:
                log.info("vision: no canvas after wait")
                break

            if meta.get("isDrag"):
                solved = await _solve_drag(fr, page, keypool)
                if not solved:
                    await _click_submit(fr)
                await asyncio.sleep(1)
                tok = await _get_token(page, 5)
                if tok:
                    return tok
                continue

            target = meta.get("target", "")
            if not target:
                log.info("vision: no target text")
                break

            # Skip hard challenges
            if is_hard_challenge(target):
                log.info("vision: hard challenge skip (%r)", target)
                await _click_submit(fr)
                await asyncio.sleep(1)
                continue

            # Scattered layout
            cr = meta.get("canvasRect") or {}
            cw, ch = cr.get("w", 0), cr.get("h", 0)
            canvas_scattered = False
            try:
                canvas_scattered = _canvas_is_scattered(cw, ch)
            except Exception:
                pass

            if _is_scattered(target) or canvas_scattered:
                log.info("vision: scattered (%r %dx%d)", target, cw, ch)
                b64g, _ci = await _get_best_canvas(fr)
                chash = hashlib.md5(b64g.encode()).hexdigest()[:12] if b64g else ""

                # Canvas hash guard: if same canvas appeared before,
                # we already clicked it — try verify/advance instead
                if chash and chash in seen_canvases:
                    log.info("vision: canvas %s already seen — verify/advance", chash)
                    await _click_submit(fr, wait_for_btn=4, mode="verify")
                    await asyncio.sleep(1)
                    tok = await _get_token(page, 5)
                    if tok:
                        return tok
                    # Still no token → skip (wrong answer loop)
                    log.info("vision: still stuck on %s — skip", chash)
                    await _click_submit(fr, wait_for_btn=3, mode="skip")
                    await asyncio.sleep(1)
                    continue
                if chash:
                    seen_canvases.add(chash)

                pts, cidx = await _pick_scattered_point(fr, keypool, target)
                if not pts:
                    log.warning("vision: scattered no picks — submit")
                    await _click_submit(fr, wait_for_btn=3)
                    await asyncio.sleep(1)
                    continue

                # Click ALL points (multi-select returns multiple)
                log.info("vision scattered: %d points (idx %d): %s", len(pts), cidx, pts)
                for pt in pts:
                    await _click_point(page, fr, pt, cidx)
                    await asyncio.sleep(0.5)
                await asyncio.sleep(1.5)
                await _click_submit(fr, wait_for_btn=6, mode="verify")
                try:
                    await fr.evaluate("() => { const b = document.querySelector('.button-submit'); if(b) b.click(); }")
                except Exception:
                    pass
                # Poll canvas change
                for _ in range(8):
                    await asyncio.sleep(1)
                    try:
                        nb, _ = await _get_best_canvas(fr)
                        nh = hashlib.md5(nb.encode()).hexdigest()[:12] if nb else ""
                        if nh and nh != chash:
                            break
                    except Exception:
                        pass
                # Token may appear after Verify → poll longer
                tok = await _get_token(page, 10)
                if tok:
                    return tok
                # Also try: challenge might be done, wait for frame close
                await asyncio.sleep(2)
                tok = await _get_token(page, 5)
                if tok:
                    return tok
                continue

            # Grid challenge: 3 vision calls → majority vote
            round_picks = []
            for _ in range(3):
                picks = await _pick_cells(fr, keypool, target)
                log.info("vision round %d pick: %s", round_no + 1, picks)
                if picks:
                    round_picks.append(set(picks))
                await asyncio.sleep(0.3)

            if not round_picks:
                log.warning("vision: no picks — skip")
                await _click_submit(fr)
                await asyncio.sleep(1)
                continue

            cnt = Counter(c for s in round_picks for c in s)
            majority = [c for c, n in cnt.most_common() if n >= 2]
            if majority:
                log.info("vision voted: %s", majority)
                await _click_tiles(page, fr, majority)
            else:
                fallback = [c for c, n in cnt.most_common() if n >= 1][:4]
                log.warning("vision no consensus — fallback %s", fallback)
                if fallback:
                    await _click_tiles(page, fr, fallback)

            await asyncio.sleep(1)
            await _click_submit(fr)
            await asyncio.sleep(1)
            tok = await _get_token(page, 5)
            if tok:
                return tok

        return ""
    except ImportError as e:
        log.warning("vision import fail: %s", e)
        return ""
    except Exception as e:
        log.warning("vision error: %s", e)
        return ""


# ── Helpers ──

def _browser_kwargs(proxy=None):
    prefix = "HCAPTCHA"
    default_headless = "0"  # checkbox/hcaptcha = headed (better trust score)
    kw = {"humanize": True, "headless": os.getenv("BROWSER_HEADLESS", default_headless) != "0"}
    if proxy:
        kw["proxy"] = proxy
    if os.getenv(f"{prefix}_GEOIP") == "1":
        kw["geoip"] = True
    license_key = os.getenv("CLOAK_LICENSE_KEY", "")
    if license_key:
        kw["license_key"] = license_key
    return kw


def _route_glob(url: str) -> str:
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    if parts.path in ("", "/"):
        return f"{parts.scheme}://{parts.netloc}/**"
    return url


async def _run_pre_actions(page, actions):
    for i, action in enumerate(actions):
        atype = action.get("type", "")
        selector = action.get("selector", "")
        value = action.get("value", "")
        timeout = action.get("timeout", 10000)
        log.info("pre-action %d: %s %s", i + 1, atype, (selector or "")[:60])
        if atype == "click":
            loc = page.locator(selector)
            await loc.click(timeout=timeout)
        elif atype == "fill":
            loc = page.locator(selector)
            await loc.fill(value, timeout=timeout)
        elif atype == "select":
            loc = page.locator(selector)
            await loc.select_option(value, timeout=timeout)
        elif atype == "press":
            await page.keyboard.press(value)
        elif atype == "wait":
            await asyncio.sleep(float(value or 1))
        await asyncio.sleep(0.5)


async def _run_post_fetch(page, post_fetch, token):
    results = []
    _FETCH_JS = (
        "async ({u, m, b}) => { try {"
        " const r = await fetch(u, {method: m,"
        " headers: {'Content-Type': 'application/json'},"
        " body: b, credentials: 'include'});"
        " return {status: r.status, body: await r.text()};"
        " } catch(e) { return {status: 0, body: String(e)}; } }"
    )
    import json
    for pf in post_fetch:
        pf_url = pf["url"]
        pf_method = pf.get("method", "POST")
        body_str = json.dumps(pf.get("body", {})).replace("__TOKEN__", token)
        try:
            fr = await page.evaluate(_FETCH_JS, {"u": pf_url, "m": pf_method.upper(), "b": body_str})
            log.info("post_fetch %s: %d", pf_url, fr.get("status", 0))
            results.append({"url": pf_url, **fr})
        except Exception as e:
            log.warning("post_fetch %s failed: %s", pf_url, e)
            results.append({"url": pf_url, "status": 0, "body": str(e)})
    return results


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

async def solve_hcaptcha_cloak(sitekey: str, url: str, timeout_s: int = 120,
                                proxy: str = None, real_page: bool = False,
                                pre_actions=None, post_fetch=None) -> dict:
    """Solve hCaptcha via fresh CloakBrowser per solve.

    Checkbox (default): route-intercept → inject widget → click checkbox →
    if image challenge → Gemini/Mistral vision solve → return token.

    Returns {solved: True, token, elapsed, method} or {solved: False, error}.
    """
    t0 = time.time()
    max_attempts = 2  # 2 fresh browsers, then fall through to capsolver
    async with _solve_lock:
        async with await cloakbrowser.launch_async(**_browser_kwargs(proxy)) as browser:
            page = await browser.new_page()
            try:
                if real_page:
                    return await _solve_real_page(
                        page, sitekey, url, timeout_s, pre_actions, post_fetch, t0
                    )

                # Route-intercept: inject widget on target page
                div = f'<div class="h-captcha" data-sitekey="{sitekey}"></div>'
                page_data = _TEMPLATE.replace("<!-- hcaptcha widget -->", div)
                glob = _route_glob(url)
                await page.route(glob, lambda r: r.fulfill(body=page_data, status=200))
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                keypool = _get_vision_pool()
                seen_canvases = set()  # canvas hash guard

                for attempt in range(1, max_attempts + 1):
                    log.info("hCaptcha attempt %d/%d", attempt, max_attempts)

                    # Try auto-populate (passive config)
                    token = await _get_token(page, 5)
                    if token:
                        return {"solved": True, "token": token,
                                "elapsed": round(time.time() - t0, 1),
                                "method": "cloak-no-click"}

                    # Close leftover challenge
                    await _close_challenge(page)

                    clicked = await _click_checkbox(page)
                    log.info("checkbox clicked=%s", clicked)
                    await asyncio.sleep(3)

                    # Solve image challenge if present
                    if _has_challenge(page):
                        log.info("challenge detected — solving via vision")
                        if keypool:
                            tok = await _solve_image_challenge(page, keypool, seen_canvases=seen_canvases)
                            if tok:
                                return {"solved": True, "token": tok,
                                        "elapsed": round(time.time() - t0, 1),
                                        "method": "cloak-vision"}
                        else:
                            log.warning("no vision pool — skip challenge")
                        await _close_challenge(page)

                    # Check for token
                    token = await _get_token(page, 15)
                    if token:
                        return {"solved": True, "token": token,
                                "elapsed": round(time.time() - t0, 1),
                                "method": "cloak-route"}

                    await asyncio.sleep(3 * attempt)  # backoff

                return {"solved": False, "error": "No token obtained after max attempts",
                        "elapsed": round(time.time() - t0, 1)}

            finally:
                try:
                    await page.close()
                except Exception:
                    pass


async def solve_hcaptcha_invisible(sitekey: str, url: str, proxy: str = None) -> dict:
    """Invisible mode: hcaptcha.execute() — zero interaction."""
    t0 = time.time()
    body = _INVISIBLE_PAGE.replace("__SITEKEY__", sitekey)
    async with _solve_lock:
        async with await cloakbrowser.launch_async(**_browser_kwargs(proxy)) as browser:
            page = await browser.new_page()
            try:
                glob = _route_glob(url)
                await page.route(glob, lambda r: r.fulfill(body=body, status=200))
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                for _ in range(25):
                    await asyncio.sleep(1)
                    tok = await page.evaluate("() => window.__token || ''")
                    if tok:
                        return {"solved": True, "token": tok,
                                "elapsed": round(time.time() - t0, 1),
                                "method": "cloak-invisible"}
                    err = await page.evaluate("() => window.__err || ''")
                    if err:
                        return {"solved": False, "error": f"execute() failed: {err}",
                                "elapsed": round(time.time() - t0, 1)}
                return {"solved": False, "error": "execute() timed out",
                        "elapsed": round(time.time() - t0, 1)}
            finally:
                try:
                    await page.close()
                except Exception:
                    pass


async def _solve_real_page(page, sitekey, url, timeout_s, pre_actions, post_fetch, t0):
    """Navigate real site, run pre_actions, solve hCaptcha, harvest token+cookies."""
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    if pre_actions:
        await _run_pre_actions(page, pre_actions)
        await asyncio.sleep(1)

    # Inject widget if page doesn't have one
    if sitekey:
        await page.evaluate(_WIDGET_INJECT_JS, sitekey)
        await asyncio.sleep(3)

    keypool = _get_vision_pool()
    clicked = await _click_checkbox(page)
    log.info("real-page checkbox clicked=%s", clicked)
    await asyncio.sleep(1)

    if _has_challenge(page) and keypool:
        log.info("real-page: solving image challenge")
        await _solve_image_challenge(page, keypool)

    # Harvest token
    token = ""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            token = await page.evaluate(
                "() => (document.querySelector('[name=h-captcha-response]') || {}).value || ''"
            )
            if token:
                break
        except Exception:
            pass
        await asyncio.sleep(1)

    try:
        cookies = await page.context.cookies()
    except Exception:
        cookies = []

    result = {"solved": bool(token), "token": token,
              "verify_success": bool(token), "cookies": cookies,
              "method": "cloak-realpage",
              "elapsed": round(time.time() - t0, 1)}

    if post_fetch and token:
        result["post_fetch"] = await _run_post_fetch(page, post_fetch, token)

    return result
