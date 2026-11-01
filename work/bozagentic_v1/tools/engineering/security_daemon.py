#!/usr/bin/env python3
"""
BOZAGENTIC Production Security Daemon v2.0
Monitors Ethereum mainnet for security events in real-time.
Usage: python3 security_daemon.py [interval] [rpc]
"""
import sys, time, json, os
from datetime import datetime
from web3 import Web3

INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 12
RPC = sys.argv[2] if len(sys.argv) > 2 else "https://ethereum-rpc.publicnode.com"
LOG_DIR = os.path.expanduser("~/.hermes/bozagentic-v7/reports/alerts")
os.makedirs(LOG_DIR, exist_ok=True)

w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 10}))

TRANSFER = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().replace("0x","")
APPROVAL = "0x" + Web3.keccak(text="Approval(address,address,uint256)").hex().replace("0x","")
UPGRADED = "0x" + Web3.keccak(text="Upgraded(address)").hex().replace("0x","")
OWNERSHIP = "0x" + Web3.keccak(text="OwnershipTransferred(address,address)").hex().replace("0x","")
PAUSED = "0x" + Web3.keccak(text="Paused(address)").hex().replace("0x","")

WATCH_TOKENS = {
    "USDT": ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 6, 1_000_000),
    "USDC": ("0xA0b86991c627Ce246199B89fF4b35b54C5c85687", 6, 1_000_000),
    "WETH": ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18, 500),
}

last_block = w3.eth.block_number
alert_log = os.path.join(LOG_DIR, f"alerts_{datetime.now().strftime('%Y%m%d')}.jsonl")

def log_alert(alert):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {alert['icon']} [{alert['type']}] {alert['detail']}"
    print(line)
    with open(alert_log, "a") as f:
        f.write(json.dumps({"ts": ts, **alert}) + "
")

print(f"BOZAGENTIC Security Daemon v2.0")
print(f"Block: {last_block}, Interval: {INTERVAL}s")
print(f"Log: {alert_log}")
print("=" * 60)

while True:
    try:
        current = w3.eth.block_number
        if current <= last_block:
            time.sleep(INTERVAL)
            continue
        
        for blk_num in range(last_block + 1, current + 1):
            blk = w3.eth.get_block(blk_num, full_transactions=True)
            
            for tx in blk["transactions"]:
                if tx["value"] > w3.to_wei(100, "ether"):
                    val = w3.from_wei(tx["value"], "ether")
                    log_alert({"icon": "🐋", "type": "WHALE_ETH", "block": blk_num,
                              "detail": f"{val:.0f} ETH: {tx['from'][:12]}... -> {(tx['to'] or 'CREATE')[:12]}..."})
                
                if tx["to"] is None:
                    receipt = w3.eth.get_transaction_receipt(tx["hash"])
                    if receipt and receipt["contractAddress"]:
                        code = w3.eth.get_code(receipt["contractAddress"])
                        log_alert({"icon": "📦", "type": "NEW_CONTRACT", "block": blk_num,
                                  "detail": f"{receipt['contractAddress'][:14]}... ({len(code)}B)"})
            
            try:
                logs = w3.eth.get_logs({"fromBlock": blk_num, "toBlock": blk_num})
                for log in logs:
                    if not log["topics"]: continue
                    t0 = log["topics"][0].hex()
                    
                    if t0 == UPGRADED.replace("0x",""):
                        impl = Web3.to_checksum_address("0x" + log["topics"][1].hex()[-40:])
                        log_alert({"icon": "🔄", "type": "UPGRADE", "block": blk_num,
                                  "detail": f"{log['address'][:14]}... -> {impl[:14]}..."})
                    
                    elif t0 == OWNERSHIP.replace("0x",""):
                        new = Web3.to_checksum_address("0x" + log["topics"][2].hex()[-40:])
                        log_alert({"icon": "👑", "type": "OWNERSHIP", "block": blk_num,
                                  "detail": f"{log['address'][:14]}... -> {new[:14]}..."})
                    
                    elif t0 == PAUSED.replace("0x",""):
                        log_alert({"icon": "⏸️", "type": "PAUSED", "block": blk_num,
                                  "detail": f"{log['address'][:14]}... PAUSED"})
                    
                    elif t0 == APPROVAL.replace("0x",""):
                        val = int(log["data"].hex(), 16)
                        if val >= 2**255:
                            owner = Web3.to_checksum_address("0x" + log["topics"][1].hex()[-40:])
                            spender = Web3.to_checksum_address("0x" + log["topics"][2].hex()[-40:])
                            log_alert({"icon": "⚠️", "type": "UNLIMITED_APPROVAL", "block": blk_num,
                                      "detail": f"{owner[:12]}... -> {spender[:12]}... on {log['address'][:12]}..."})
                    
                    elif t0 == TRANSFER.replace("0x",""):
                        for tname, (taddr, dec, threshold) in WATCH_TOKENS.items():
                            if log["address"].lower() == taddr.lower():
                                val = int(log["data"].hex(), 16) / 10**dec
                                if val > threshold:
                                    frm = Web3.to_checksum_address("0x" + log["topics"][1].hex()[-40:])
                                    to = Web3.to_checksum_address("0x" + log["topics"][2].hex()[-40:])
                                    log_alert({"icon": "🐋", "type": f"WHALE_{tname}", "block": blk_num,
                                              "detail": f"{tname} {val:,.0f}: {frm[:12]}... -> {to[:12]}..."})
                                break
            except:
                pass
        
        last_block = current
    except Exception as e:
        print(f"[ERROR] {str(e)[:60]}")
    
    time.sleep(INTERVAL)
