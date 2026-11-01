"""Fingerprint generation for captcha solving + API replay.

Turnstile (Cloudflare) tokens are bound to the browser fingerprint AND the TLS
fingerprint of the client that redeems them. Python-requests has a distinctive
JA3 → Cloudflare rejects the token even when UA matches (pateway 450068 /
450121). Fix: generate ONE fingerprint, solve the captcha with it, then replay
the same headers over curl_cffi (impersonate=chrome → real Chrome JA3) so the
API call looks like the same browser session.

Fingerprint includes:
  - user_agent (desktop/mobile)
  - sec-ch-ua / sec-ch-ua-mobile / sec-ch-ua-platform (must match UA)
  - accept-language
  - viewport, timezone, locale (applied to the browser context)
"""

from __future__ import annotations

import json
import random
import string

# UA templates keyed by platform. Chrome major + sec-ch-ua pairs must be kept
# in sync with the CHROMIUM_VERSION used by cloakbrowser — keep them loose:
# Cloudflare mainly checks the pair is self-consistent.
_CHROME_UA = (
    "Mozilla/5.0 ({os}) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/{ver} Safari/537.36"
)
_OS_MAP = {
    "windows": "Windows NT 10.0; Win64; x64",
    "mac": "Macintosh; Intel Mac OS X 10_15_7",
    "linux": "X11; Linux x86_64",
}
_PLATFORM_MAP = {
    "windows": 'Windows',
    "mac": 'macOS',
    "linux": 'Linux',
}
_CHROME_VERS = ["131.0.0.0", "130.0.0.0", "129.0.0.0", "132.0.0.0", "133.0.0.0"]
# sec-ch-ua string must list the same Chrome versions as the UA
_SEC_CH_UA = (
    '"Google Chrome";v="{v0}", "Chromium";v="{v0}", "Not?A_Brand";v="24"'
)


def _sec_ch_ua(ver: str) -> str:
    v0 = ver.split(".")[0]
    return _SEC_CH_UA.replace("{v0}", v0)


def generate_fingerprint(platform: str | None = None, mobile: bool = False,
                         seed: str | None = None) -> dict:
    """Generate a self-consistent browser fingerprint.

    platform: 'windows' | 'mac' | 'linux' (default random)
    mobile:   False → desktop fingerprint
    seed:     optional stable seed so the same fingerprint can be re-derived
    """
    rng = random.Random(seed)
    platform = platform or rng.choice(list(_OS_MAP.keys()))
    ver = rng.choice(_CHROME_VERS)
    ua = _CHROME_UA.format(os=_OS_MAP[platform], ver=ver)
    if mobile:
        ua = ua.replace("Mozilla/5.0 ", "Mozilla/5.0 (Linux; Android 13; Pixel 7) ")
        platform_hdr = 'Android'
    else:
        platform_hdr = _PLATFORM_MAP[platform]

    langs = ["en-US,en;q=0.9", "en-GB,en;q=0.9", "en-US,en;q=0.9,id;q=0.8"]
    timezones = ["UTC", "Asia/Singapore", "America/New_York", "Europe/London"]

    fp = {
        "platform": platform,
        "mobile": mobile,
        "user_agent": ua,
        "sec_ch_ua": _sec_ch_ua(ver),
        "sec_ch_ua_mobile": "?0" if not mobile else "?1",
        "sec_ch_ua_platform": platform_hdr,
        "accept_language": rng.choice(langs),
        "timezone": rng.choice(timezones),
        "locale": "en-US",
        "viewport": {"width": rng.choice([1280, 1366, 1440, 1536, 1920]),
                     "height": rng.choice([720, 768, 800, 900, 1080])},
        "color_scheme": rng.choice(["light", "dark", "no-preference"]),
    }
    return fp


def headers_from_fingerprint(fp: dict) -> dict:
    """Map a fingerprint to HTTP headers to replay on curl_cffi requests."""
    return {
        "User-Agent": fp["user_agent"],
        "sec-ch-ua": fp["sec_ch_ua"],
        "sec-ch-ua-mobile": fp["sec_ch_ua_mobile"],
        "sec-ch-ua-platform": fp["sec_ch_ua_platform"],
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": fp["accept_language"],
        "Origin": "https://web.pateway.ai",
        "Referer": "https://web.pateway.ai/",
    }


def json_dump(fp: dict) -> str:
    return json.dumps(fp, separators=(",", ":"))


def json_load(s: str) -> dict:
    return json.loads(s)


def random_email(domain: str) -> str:
    n = random.randint(8, 14)
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n)) + "@" + domain
