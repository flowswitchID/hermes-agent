import json

with open('/tmp/dexscreener.json') as f:
    data = json.load(f)

pairs = data if isinstance(data, list) else data.get('pairs') or data.get('data') or []
print("Total pairs returned:", len(pairs))

stables = {'USDC','USDT','DAI','USDbC','USDBC','FDUSD','TUSD','BUSD','EURC'}
rows = []
for p in pairs:
    try:
        base = p.get('baseToken',{})
        quote = p.get('quoteToken',{})
        base_sym = base.get('symbol','').upper()
        quote_sym = quote.get('symbol','').upper()
        if 'WETH' in base_sym and quote_sym in stables:
            price = p.get('priceUsd')
            liq = (p.get('liquidity') or {}).get('usd', 0)
            dex = p.get('dexId','?')
            pid = p.get('pairAddress','')
            vol = (p.get('volume') or {}).get('h24', 0)
            if price:
                rows.append({'dex': dex, 'price': float(price), 'liq': liq or 0,
                    'vol24': vol or 0, 'pair': pid, 'quote': quote_sym,
                    'label': p.get('label','')})
    except Exception:
        pass

print("WETH/stable pairs found:", len(rows))
rows.sort(key=lambda r: r['liq'], reverse=True)
for r in rows[:30]:
    print(f"{r['dex']:22s} {r['quote']:6s} ${r['price']:>10.2f}  liq=${r['liq']:>14,.0f}  vol24=${r['vol24']:>14,.0f}  {r['pair'][:14]}")

# Now compute spreads among liquid pairs (>$200k liquidity)
liq_rows = [r for r in rows if r['liq'] >= 200000]
print("\n=== Pairs with >$200k liquidity:", len(liq_rows), "===")
best = None
for i in range(len(liq_rows)):
    for j in range(i+1, len(liq_rows)):
        a, b = liq_rows[i], liq_rows[j]
        lo, hi = (a,b) if a['price'] < b['price'] else (b,a)
        spread = (hi['price']-lo['price'])/lo['price']*100
        if best is None or spread > best[0]:
            best = (spread, lo, hi)

if best:
    spread, lo, hi = best
    print(f"\nMAX SPREAD: {spread:.4f}%")
    print(f"  BUY  @ {lo['dex']:20s} {lo['pair'][:16]} ${lo['price']:.2f} liq=${lo['liq']:,.0f}")
    print(f"  SELL @ {hi['dex']:20s} {hi['pair'][:16]} ${hi['price']:.2f} liq=${hi['liq']:,.0f}")
    print(f"  THRESHOLD 0.4% -> {'EXECUTE' if spread >= 0.4 else 'NO TRADE'}")
else:
    print("No liquid pairs to compare.")
