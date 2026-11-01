"""Shared browser helpers for the captcha solvers.

Single source for selector resolution, pre-action execution, per-solver browser
kwargs, and the post_fetch loop. All caller values reach the browser as evaluate()
args, never interpolated into JS source (injection-safe).
"""
import asyncio
import json
import logging
import os
import re

log = logging.getLogger(__name__)

# Parameterized fetch: caller values (url, method, body, headers) arrive as
# evaluate() args, NEVER interpolated into JS source — safe against quotes/injection.
# GET/HEAD never carry a body (browser fetch throws otherwise).
_FETCH_JS = (
    "async ({u, m, b, hd}) => { try {"
    " const opts = {method: m, credentials: 'include'};"
    " const h = Object.assign({'Content-Type': 'application/json'}, hd || {});"
    " opts.headers = h;"
    " if (m !== 'GET' && m !== 'HEAD') opts.body = b;"
    " const r = await fetch(u, opts);"
    " return {status: r.status, body: await r.text()};"
    " } catch(e) { return {status: 0, body: String(e)}; } }"
)


async def resolve_selector(page, selector: str, timeout: int = 10000):
    """Resolve a selector string to a Playwright locator.

    Supports:
      - CSS (default): input[type=email]
      - XPath:         //button[@type='submit']
      - Text:          text=Continue with Email
      - Regex:         regex=Continue.*Email
      - Role:          role=button[name='Submit']
    """
    if selector.startswith("//") or selector.startswith("(//"):
        return page.locator(f"xpath={selector}")
    if selector.startswith("text="):
        return page.get_by_text(selector[5:], exact=False)
    if selector.startswith("regex="):
        return page.locator(f"text=/{selector[6:]}/")
    if selector.startswith("role="):
        m = re.match(r"role=(\w+)(?:\[name=['\"](.+?)['\"]\])?", selector)
        if m:
            role, name = m.group(1), m.group(2)
            kwargs = {"name": name} if name else {}
            return page.get_by_role(role, **kwargs)
    return page.locator(selector)


async def run_pre_actions(page, actions: list):
    """Execute a list of pre-actions before solving.

    Each action: {"type": "click|fill|select|press|wait", "selector": "...",
                  "value": "...", "timeout": N}
    """
    for i, action in enumerate(actions):
        atype = action.get("type", "")
        selector = action.get("selector", "")
        value = action.get("value", "")
        timeout = action.get("timeout", 10000)
        log.info("Pre-action %d: %s %s", i + 1, atype, (selector or "")[:60])
        if atype == "click":
            loc = await resolve_selector(page, selector, timeout)
            await loc.click(timeout=timeout)
        elif atype == "fill":
            loc = await resolve_selector(page, selector, timeout)
            await loc.fill(value, timeout=timeout)
        elif atype == "select":
            loc = await resolve_selector(page, selector, timeout)
            await loc.select_option(value, timeout=timeout)
        elif atype == "press":
            await page.keyboard.press(value)
        elif atype == "wait":
            await asyncio.sleep(float(value or 1))
        else:
            log.warning("Unknown pre-action type: %s", atype)
        await asyncio.sleep(0.5)


def browser_kwargs(prefix: str, proxy: str = None) -> dict:
    """Browser-trust levers shared by all browser solvers.

    Headless is GLOBAL via BROWSER_HEADLESS (all providers share it).
    Code defaults when unset: Turnstile family headless=1; interactive
    checkbox solvers (recaptcha/hcaptcha/botguard) headless=0.
    Service sets BROWSER_HEADLESS=0 so every solver runs headed under Xvfb.

    Proxy is per-request only — pass `proxy` explicitly. No env fallback.
    GEOIP stays per-prefix ({PREFIX}_GEOIP) because only proxy-aligned paths need it.
    """
    default_headless = "1" if prefix == "TURNSTILE" else "0"
    kw = {"humanize": True,
          "headless": os.getenv("BROWSER_HEADLESS", default_headless) != "0"}
    if proxy:
        kw["proxy"] = proxy
    if os.getenv(f"{prefix}_GEOIP") == "1":
        kw["geoip"] = True
    return kw


def route_glob(url: str) -> str:
    """Glob for page.route() that matches the target with or without a trailing slash,
    plus any sub-path.

    goto("https://ex.com") actually requests "https://ex.com/", so a bare-URL route
    pattern silently misses and the solve hangs until timeout. Appending `/**` matches
    the bare, trailing-slash, and deeper-path forms. Only origin-only URLs are rewritten;
    a URL that already carries a path matches exactly as-is.
    """
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    if parts.path in ("", "/"):          # origin-only → needs the glob
        return f"{parts.scheme}://{parts.netloc}/**"
    return url                            # has a path → exact match already works


async def fetch_from_page(page, url: str, method: str, body: str,
                          headers: dict = None) -> dict:
    """One parameterized fetch from the page's session. Returns {status, body}."""
    return await page.evaluate(_FETCH_JS,
                               {"u": url, "m": method.upper(), "b": body, "hd": headers or {}})


async def run_post_fetch(page, post_fetch: list, token: str) -> list:
    """Run post_fetch API calls from the SAME browser session (keeps cookies/origin).

    Each entry: {"url": ..., "method": "POST", "body": {...}, "headers": {...}}.
    `__TOKEN__` in the JSON body is replaced with the solved token.
    GET/HEAD requests never carry a body. All values are passed as evaluate()
    args (never interpolated into JS source).

    Chaining: `__PF{n}.a.b__` in body/headers/url is replaced with the JSON path
    a.b from the response of post_fetch entry n (0-based). Example:
      entry 1 returns {"auth": {"token": "..."}}
      entry 2 headers: {"x-inbox-token": "__PF1.auth.token__"}
    """
    results = []
    for i, pf in enumerate(post_fetch):
        pf_url = pf["url"]
        pf_method = pf.get("method", "POST")
        body_str = json.dumps(pf.get("body", {})).replace("__TOKEN__", token)
        headers = {k: str(v) for k, v in (pf.get("headers") or {}).items()}
        # resolve __PF{n}.path__ placeholders from earlier results
        body_str, headers = _resolve_pf_placeholders(body_str, headers, results)
        pf_url = _resolve_pf_in_string(pf_url, results)
        try:
            fr = await fetch_from_page(page, pf_url, pf_method, body_str,
                                       headers=headers)
            log.info("post_fetch %s: %d", pf_url, fr["status"])
            results.append({"url": pf_url, **fr})
        except Exception as e:
            log.warning("post_fetch %s failed: %s", pf_url, e)
            results.append({"url": pf_url, "status": 0, "body": str(e)})
    return results


def _pf_lookup(path: str, results: list):
    """Resolve '__PF{n}.a.b.c__' style path against prior post_fetch responses."""
    import re as _re
    m = _re.match(r"__PF(\d+)\.(.+)__", path)
    if not m:
        return None
    idx, jp = int(m.group(1)), m.group(2)
    if idx >= len(results):
        return None
    try:
        val = json.loads(results[idx].get("body") or "{}")
    except Exception:
        return None
    for part in jp.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        elif isinstance(val, list) and part.isdigit():
            val = val[int(part)]
        else:
            return None
    return val


def _resolve_pf_in_string(s: str, results: list) -> str:
    import re as _re
    def _rep(m):
        v = _pf_lookup(m.group(0), results)
        return str(v) if v is not None else m.group(0)
    return _re.sub(r"__PF\d+\.[\w.]+__", _rep, s)


def _resolve_pf_placeholders(body_str: str, headers: dict, results: list):
    body_str = _resolve_pf_in_string(body_str, results)
    headers = {k: _resolve_pf_in_string(v, results) for k, v in headers.items()}
    return body_str, headers
