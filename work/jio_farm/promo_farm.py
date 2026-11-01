"""
Google AI Pro Promo Farm — 3 Months Free
Flow: Activation Links → Status Check → Redeem via Google Session
Input: activation_links.txt (one URL per line)
Config: cookies_google.json (list of Google account cookies), optional proxies
"""
from __future__ import annotations
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import RequestException

# ==================== CONFIG ====================
ACTIVATION_LINKS_FILE = "activation_links.txt"
COOKIES_FILE = "cookies_google.json"
PROXY_FILE = "proxies.txt"  # optional, format: socks5://ip:port or http://ip:port
OUTPUT_FILE = "promo_farm_results.txt"
TELEGRAM_BOT_TOKEN = ""  # set via env TELEGRAM_BOT_TOKEN or here
TELEGRAM_CHAT_ID = ""    # set via env TELEGRAM_CHAT_ID or here
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)
HEADERS_BASE = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}
REDEEM_URL = "https://serviceactivation.google.com/subscription/activate/Z0241?source=JIO"
SUBMIT_URL = "https://www.jio.com/api/jio-ott-service/ott/submission/submit"
OTP_URL = "https://www.jio.com/api/jio-login-service/login/sendOtp"
AUTH_URL = "https://www.jio.com/api/jio-authenticate-service/authenticate/authJsonData"
MAX_RETRIES = 3
RETRY_DELAY = 2
DELAY_BETWEEN_REQUESTS = 1.5
# =============================================


def load_activation_links(path: str) -> list[str]:
    if not Path(path).exists():
        print(f"[!] File tidak ditemukan: {path}")
        return []
    with open(path, "r") as f:
        links = [line.strip() for line in f if line.strip()]
    print(f"[+] {len(links)} activation links loaded from {path}")
    return links


def load_cookies(path: str) -> list[dict]:
    if not Path(path).exists():
        print(f"[!] Cookies file tidak ditemukan: {path}")
        return []
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = [data]
    print(f"[+] {len(data)} cookie profiles loaded")
    return data


def load_proxies(path: str) -> list[str]:
    if not Path(path).exists():
        return []
    with open(path, "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    print(f"[+] {len(proxies)} proxies loaded")
    return proxies


def get_telegram_creds() -> tuple[str, str]:
    token = TELEGRAM_BOT_TOKEN or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = TELEGRAM_CHAT_ID or os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def send_telegram(text: str, parse_mode: str = "HTML"):
    token, chat_id = get_telegram_creds()
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code == 200
    except RequestException:
        return False


def build_session(cookies: dict | None = None, proxy: str | None = None) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS_BASE)
    if cookies:
        session.cookies.update(cookies)
    if proxy:
        session.proxies = {
            "http": proxy,
            "https": proxy,
        }
    return session


def check_link_status(session: requests.Session, link: str) -> tuple[str, str]:
    """Returns (status, detail)"""
    try:
        resp = session.head(link, allow_redirects=True, timeout=15)
        if resp.status_code == 200:
            return "VALID", f"HTTP {resp.status_code}"
        elif resp.status_code == 302:
            loc = resp.headers.get("Location", "")
            if "error" in loc.lower() or "invalid" in loc.lower():
                return "EXPIRED", loc
            return "VALID", f"Redirect: {loc[:80]}"
        elif resp.status_code == 404:
            return "EXPIRED", "HTTP 404"
        elif resp.status_code == 423:
            return "USED", "HTTP 423 (deactivated)"
        else:
            return "UNKNOWN", f"HTTP {resp.status_code}"
    except RequestException as e:
        return "ERROR", str(e)[:120]


def redeem_promo(session: requests.Session, link: str) -> tuple[bool, str]:
    """Attempt to redeem the Google AI Pro promo via the activation flow."""
    try:
        # Step 1: GET activation page
        resp = session.get(link, timeout=20)
        if resp.status_code != 200:
            return False, f"GET failed: {resp.status_code}"

        # Extract token/session data from page if needed
        # Most Google activation links work by setting cookies and redirecting
        # Follow redirects automatically
        final_url = resp.url
        if "serviceactivation.google.com" not in final_url:
            return False, f"Unexpected redirect: {final_url[:100]}"

        # Step 2: Check if we need to interact with form
        # The activation page may contain a form that auto-submits
        m = re.search(r'<form[^>]*action="([^"]+)"[^>]*>', resp.text)
        if m:
            form_action = m.group(1)
            form_resp = session.post(form_action, data={}, timeout=20)
            if form_resp.status_code == 200:
                if "success" in form_resp.text.lower() or "activated" in form_resp.text.lower():
                    return True, "Form submitted successfully"
                return True, f"Form posted (status {form_resp.status_code})"
            return False, f"Form POST failed: {form_resp.status_code}"

        return True, "GET completed, likely set cookies for activation"

    except RequestException as e:
        return False, str(e)[:120]


def verify_activation(session: requests.Session) -> tuple[bool, str]:
    """Verify if Google AI Pro is active on the account."""
    try:
        resp = session.get(
            "https://one.google.com/about/",
            timeout=15,
            allow_redirects=False,
        )
        if resp.status_code in (200, 302):
            # Check for AI Pro indicators in response
            if "AI Pro" in resp.text or "5 TB" in resp.text:
                return True, "AI Pro detected in account page"
            return False, "No AI Pro indicator found"
        return False, f"HTTP {resp.status_code}"
    except RequestException as e:
        return False, str(e)[:120]


def process_links(
    links: list[str],
    cookies_profiles: list[dict],
    proxies: list[str],
):
    results = []
    seen = set()
    link_iter = iter(links)

    while True:
        try:
            link = next(link_iter)
        except StopIteration:
            break

        if link in seen:
            continue
        seen.add(link)

        # Rotate cookie profile
        cookie_profile = random.choice(cookies_profiles) if cookies_profiles else None
        proxy = random.choice(proxies) if proxies else None

        session = build_session(cookies=cookie_profile, proxy=proxy)

        # Check status
        status, detail = check_link_status(session, link)
        print(f"[*] [{len(results)+1}/{len(links)}] {status}: {link[:60]}...")

        if status == "VALID":
            # Attempt redeem
            success, msg = redeem_promo(session, link)
            print(f"    redeem: {msg}")

            if success:
                # Verify
                time.sleep(2)
                ok, vmsg = verify_activation(session)
                print(f"    verify: {vmsg}")
                if ok:
                    print(f"    [***] ACTIVATED: {link}")
                    results.append({
                        "link": link,
                        "status": "ACTIVATED",
                        "verify": vmsg,
                        "cookie_profile": cookie_profile.get("email", "unknown") if cookie_profile else "none",
                    })
                    # Telegram notify on activation
                    send_telegram(
                        f"✅ <b>ACTIVATED</b>\n"
                        f"Link: {link}\n"
                        f"Account: {cookie_profile.get('email','unknown') if cookie_profile else 'none'}\n"
                        f"Verify: {vmsg}"
                    )
                else:
                    results.append({
                        "link": link,
                        "status": "REDEEMED_UNVERIFIED",
                        "redeem_msg": msg,
                        "verify_msg": vmsg,
                    })
                    send_telegram(
                        f"⚠️ <b>REDEEMED_UNVERIFIED</b>\n"
                        f"Link: {link}\n"
                        f"Verify: {vmsg}"
                    )
            else:
                results.append({
                    "link": link,
                    "status": "REDEEM_FAILED",
                    "detail": msg,
                })

        elif status == "EXPIRED":
            results.append({"link": link, "status": "EXPIRED", "detail": detail})
        elif status == "USED":
            results.append({"link": link, "status": "USED", "detail": detail})
        else:
            results.append({"link": link, "status": status, "detail": detail})

        # Save incremental
        with open(OUTPUT_FILE, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")

        time.sleep(DELAY_BETWEEN_REQUESTS + random.uniform(0, 1))

    # Summary
    activated = sum(1 for r in results if r["status"] == "ACTIVATED")
    redeemed = sum(1 for r in results if "REDEEM" in r["status"])
    expired = sum(1 for r in results if r["status"] == "EXPIRED")
    used = sum(1 for r in results if r["status"] == "USED")
    print("\n=== SUMMARY ===")
    print(f"ACTIVATED:       {activated}")
    print(f"REDEEMED:        {redeemed}")
    print(f"EXPIRED:         {expired}")
    print(f"USED:            {used}")
    print(f"TOTAL PROCESSED: {len(results)}")
    print(f"Results saved to: {OUTPUT_FILE}")

    # Telegram final summary
    send_telegram(
        f"📊 <b>PROMO FARM SUMMARY</b>\n"
        f"ACTIVATED: {activated}\n"
        f"REDEEMED: {redeemed}\n"
        f"EXPIRED: {expired}\n"
        f"USED: {used}\n"
        f"TOTAL: {len(results)}\n"
        f"Results: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    links = load_activation_links(ACTIVATION_LINKS_FILE)
    cookies = load_cookies(COOKIES_FILE)
    proxies = load_proxies(PROXY_FILE)

    if not links:
        print("[!] No links to process")
        sys.exit(1)

    process_links(links, cookies, proxies)
