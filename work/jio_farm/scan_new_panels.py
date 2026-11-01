#!/usr/bin/env python3
"""Scan 2 new live panels for Jio Gemini activation links (parallel)."""
import asyncio, aiohttp, re, html, sys
from urllib.parse import unquote

ACT = re.compile(
    r"https?://serviceactivation[.]google[.]com/subscription/new/"
    r"(?P<token>[A-Za-z0-9_-]{50,})(?P<padding>={0,2})",
    re.IGNORECASE,
)

PANELS = {
    "https://jackie-7a125-default-rtdb.firebaseio.com": "",
    "https://vicky-singh-20bdd-default-rtdb.firebaseio.com": "",
}

OUT = "/root/jio_farm/new_panels_gemini_links.txt"

def extract(text):
    t = html.unescape(text or "")
    for _ in range(4):
        d = unquote(t)
        if d == t:
            break
        t = d
    m = ACT.search(t)
    if not m:
        return None
    return "https://serviceactivation.google.com/subscription/new/" + m.group("token") + m.group("padding")

async def get_json(s, url, params=None):
    try:
        async with s.get(url, params=params or {}) as r:
            if r.status != 200:
                return None
            txt = await r.text()
            if not txt or txt == "null":
                return None
            return __import__("json").loads(txt)
    except Exception:
        return None

async def scan_device(s, base, dev, sem, hits):
    async with sem:
        data = await get_json(s, f"{base}/messages/{dev}.json",
                              {"orderBy": '"$key"', "limitToLast": "100"})
        if isinstance(data, dict) and "error" in data:
            data = await get_json(s, f"{base}/messages/{dev}.json")
        if not isinstance(data, dict):
            return
        for mk, item in data.items():
            if not isinstance(item, dict):
                continue
            url = extract(str(item.get("message", "")))
            if url:
                hits.append((base, dev, mk, url))

async def main():
    hits = []
    timeout = aiohttp.ClientTimeout(total=30)
    conn = aiohttp.TCPConnector(limit=50)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
        for base in PANELS:
            top = await get_json(s, f"{base}/.json", {"shallow": "true"})
            keys = list(top.keys()) if isinstance(top, dict) else []
            print(f"{base} → {len(keys)} top-level keys", flush=True)
            # device list: messages node if present else all top keys
            msgs = await get_json(s, f"{base}/messages.json", {"shallow": "true"})
            if isinstance(msgs, dict) and msgs:
                devices = list(msgs.keys())
            else:
                devices = keys
            print(f"  scanning {len(devices)} devices...", flush=True)
            sem = asyncio.Semaphore(40)
            await asyncio.gather(*[scan_device(s, base, d, sem, hits) for d in devices])
            print(f"  hits so far: {len(hits)}", flush=True)
        # extra nodes
        for base in PANELS:
            for node in ("_scary_links", "links", "activation", "gemini"):
                d = await get_json(s, f"{base}/{node}.json")
                if d is not None:
                    print(f"node {base}/{node}: {str(d)[:300]}", flush=True)
                    txt = html.unescape(str(d))
                    for m in ACT.finditer(txt):
                        hits.append((base, node, "-", m.group(0)))
    with open(OUT, "w") as f:
        for base, dev, mk, url in hits:
            f.write(f"{url}\t{base}\t{dev}\t{mk}\n")
    print(f"TOTAL: {len(hits)}", flush=True)
    for base, dev, mk, url in hits:
        print(f"{url} | {base} | {dev} | {mk}", flush=True)

asyncio.run(main())
