#!/usr/bin/env python3
"""
BOZAGENTIC — Token Sniper & Opportunity Scanner
Monitors Base chain for new token pairs and arbitrage opportunities.
Runs as cron job. Alerts on profitable setups.
"""
import json, urllib.request, os, sys
from datetime import datetime

BASE_RPC = "https://1rpc.io/base"
WALLET = "0xWALLET_ADDR_REDACTED"

def scan_dex_pairs():
    """Scan DexScreener for best opportunities on Base"""
    req = urllib.request.Request(
        "https://api.dexscreener.com/token-pairs/v1/base/0x4200000000000000000000000000000000000006",
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    data = json.loads(urllib.request.urlopen(req, timeout=10).read())
    
    # Group by base token
    from collections import defaultdict
    by_token = defaultdict(list)
    
    for p in data:
        base = p.get('baseToken', {}).get('symbol', '')
        quote = p.get('quoteToken', {}).get('symbol', '')
        if quote not in ('USDC', 'USDT', 'DAI'):
            continue
        price = float(p.get('priceUsd', 0) or 0)
        liq = float(p.get('liquidity', {}).get('usd', 0) or 0)
        vol24 = float(p.get('volume', {}).get('h24', 0) or 0)
        txns = p.get('txns', {}).get('h24', {}).get('buys', 0) or 0
        
        if liq < 10000:
            continue
        
        by_token[base].append({
            'dex': p.get('dexId', ''),
            'price': price,
            'liq': liq,
            'vol24': vol24,
            'txns': txns,
            'pair': p.get('pairAddress', ''),
            'url': p.get('url', '')
        })
    
    # Find spreads > 0.5%
    opportunities = []
    for token, entries in by_token.items():
        if len(entries) < 2:
            continue
        prices = [e['price'] for e in entries]
        liqs = [e['liq'] for e in entries]
        lo, hi = min(prices), max(prices)
        spread_pct = (hi - lo) / lo * 100
        
        if spread_pct >= 0.3 and min(liqs) >= 20000:
            lo_entry = min(entries, key=lambda x: x['price'])
            hi_entry = max(entries, key=lambda x: x['price'])
            opportunities.append({
                'token': token,
                'spread': spread_pct,
                'buy_dex': lo_entry['dex'],
                'buy_price': lo['price'],
                'sell_dex': hi_entry['dex'],
                'sell_price': hi['price'],
                'buy_liq': lo_entry['liq'],
                'sell_liq': hi_entry['liq'],
            })
    
    return sorted(opportunities, key=lambda x: x['spread'], reverse=True)

def get_wallet_balance():
    """Get wallet ETH balance on Base"""
    data = json.dumps({
        "jsonrpc": "2.0", "method": "eth_getBalance",
        "params": [WALLET, "latest"], "id": 1
    }).encode()
    req = urllib.request.Request(BASE_RPC, data=data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    if 'result' in resp:
        return int(resp['result'], 16) / 1e18
    return 0

def get_gas_price():
    """Get current gas price on Base"""
    data = json.dumps({
        "jsonrpc": "2.0", "method": "eth_gasPrice",
        "params": [], "id": 1
    }).encode()
    req = urllib.request.Request(BASE_RPC, data=data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    if 'result' in resp:
        return int(resp['result'], 16) / 1e9
    return 0

if __name__ == "__main__":
    now = datetime.now().strftime("%H:%M WIB")
    
    # Check wallet
    eth_bal = get_wallet_balance()
    gas = get_gas_price()
    
    # Scan opportunities
    opps = scan_dex_pairs()
    
    print(f"🔍 BOZAGENTIC SCAN — {now}")
    print(f"💰 Wallet: {eth_bal:.4f} ETH | ⛽ Gas: {gas:.2f} gwei")
    print()
    
    if opps:
        print(" OPPORTUNITIES FOUND:")
        print(f"{'TOKEN':<10} {'SPREAD':<8} {'BUY':<18} {'SELL':<18} {'LIQ':<10}")
        print("─" * 64)
        for opp in opps[:5]:
            profit_per_1k = 1000 * opp['spread'] / 100
            print(f"{opp['token']:<10} {opp['spread']:+.2f}%  {opp['buy_dex']:<8}${opp['buy_price']:<8.2f} {opp['sell_dex']:<8}${opp['sell_price']:<8.2f} ${opp['buy_liq']:<8,.0f}")
            print(f"{'':10} {'':8} Profit/$1k: ${profit_per_1k:.2f}")
    else:
        print("📭 No significant arb opportunities right now.")
    
    print()
    print("💡 Next scan: next cron tick | Gas suitable for batch ops: YES" if gas < 1 else "Gas tinggi — tunggu turun")
