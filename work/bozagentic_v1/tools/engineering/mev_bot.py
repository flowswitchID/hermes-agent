#!/usr/bin/env python3
"""
BOZAGENTIC MEV BOT — Base Chain
Sandwich bot: detect large swap → frontrun buy → backrun sell
"""
import json, os, sys, time, hashlib
from datetime import datetime
from typing import Optional

# ======= CONFIG =======
RPC_URL = "https://base-rpc.publicnode.com"
WALLET = "0xWALLET_ADDR_REDACTED"
PRIVATE_KEY = "PK_REDACTED_USE_ENV_VAR"
MIN_PROFIT_USD = 5  # Minimum profit to execute
MIN_TX_VALUE_USD = 500  # Min victim tx size to sandwich

# Uniswap V3 Router
UNISWAP_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# ======= FUNCTIONS =======
def w3_call(method, params=None):
    """Simple JSON-RPC call"""
    import urllib.request
    payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    req = urllib.request.Request(RPC_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "MEVbot/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

def get_pending_txs():
    """Get pending transactions from mempool"""
    block = w3_call("eth_getBlockByNumber", ["pending", True])
    if "result" not in block or not block["result"]:
        return []
    return block["result"].get("transactions", [])

def decode_swap(tx):
    """Check if tx is a Uniswap V3 swap and decode details"""
    if not tx.get("to"):
        return None
    to_addr = tx["to"].lower()
    if to_addr != UNISWAP_ROUTER.lower():
        return None
    
    inp = tx.get("input", "0x")
    if not inp or inp == "0x":
        return None
    
    selector = inp[2:10]
    
    # exactInputSingle selector
    if selector == "414bf389":
        try:
            # Parse struct fields (each 32 bytes)
            data = inp[10:]
            token_in = "0x" + data[24:64]
            token_out = "0x" + data[88:128]
            fee = int(data[128:192], 16)
            recipient = "0x" + data[216:256]
            amount_in = int(data[320:384], 16)
            value = int(tx.get("value", "0x0"), 16)
            
            # Check if it's WETH -> USDC (buy or sell)
            is_weth_buy = token_in.lower() == WETH.lower() and token_out.lower() == USDC.lower()
            is_weth_sell = token_in.lower() == USDC.lower() and token_out.lower() == WETH.lower()
            
            return {
                "type": "exactInputSingle",
                "token_in": token_in,
                "token_out": token_out,
                "fee": fee,
                "amount_in": amount_in,
                "value": value,
                "from": tx.get("from", ""),
                "hash": tx.get("hash", ""),
                "is_weth_buy": is_weth_buy,
                "is_weth_sell": is_weth_sell,
            }
        except:
            return None
    
    return None

def estimate_sandwich_profit(victim_tx):
    """Estimate profit from sandwiching a victim tx"""
    if not victim_tx:
        return 0
    
    # For WETH buy: we frontrun by buying before, they push price up, we sell after
    if victim_tx.get("is_weth_buy"):
        amount = victim_tx["amount_in"] / 1e18  # WETH amount
        # Rough estimate: victim tx moves price by ~0.1-0.5% depending on pool depth
        # With $111M WETH/USDC pool, a $1k buy moves price ~0.001%
        usd_value = amount * 1880  # in USD
        price_impact = usd_value / 111_000_000 * 100  # % impact on $111M pool
        profit = amount * price_impact / 100 * 1880 * 0.5  # 50% capture rate
        return profit
    
    return 0

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def main():
    log(" BOZAGENTIC MEV BOT — Base Chain")
    log(f"Wallet: {WALLET}")
    log(f"Monitoring mempool every 2s...")
    log("")
    
    scan_count = 0
    while True:
        try:
            txs = get_pending_txs()
            scan_count += 1
            
            for tx in txs[:100]:  # Check first 100 txs
                decoded = decode_swap(tx)
                if decoded:
                    profit = estimate_sandwich_profit(decoded)
                    if profit > MIN_PROFIT_USD:
                        log(f"🟡 SANDWICH OPPORTUNITY!")
                        log(f"   Tx: {decoded['hash'][:50]}...")
                        log(f"   Amount: ${decoded['amount_in']/1e18*1880:.2f}")
                        log(f"   Est profit: ${profit:.2f}")
                    else:
                        # Only log interesting ones
                        if decoded["amount_in"] / 1e18 * 1880 > MIN_TX_VALUE_USD:
                            log(f"📡 Detected swap: ${decoded['amount_in']/1e18*1880:.0f} | profit: ${profit:.2f}")
            
            if scan_count % 30 == 0:
                log(f"📊 Scanned {scan_count}x | Pending: {len(txs)} txs")
            
            time.sleep(2)
            
        except Exception as e:
            log(f"⚠️ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("🛑 Stopped")
