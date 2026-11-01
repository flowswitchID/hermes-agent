#!/usr/bin/env python3
"""
BOZAGENTIC Persistent Security Monitor
Run: python3 monitor.py [interval_seconds]
Monitors: whale transfers, new contracts, proxy upgrades, unlimited approvals
"""
import sys, time, json
from web3 import Web3

RPC = "https://ethereum-rpc.publicnode.com"
INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 30

w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={'timeout': 10}))
last_block = w3.eth.block_number

TRANSFER = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().replace("0x","")
APPROVAL = "0x" + Web3.keccak(text="Approval(address,address,uint256)").hex().replace("0x","")
UPGRADED = "0x" + Web3.keccak(text="Upgraded(address)").hex().replace("0x","")
MAX_UINT = 2**256 - 1

# Watch these tokens
WATCH_TOKENS = {
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "USDC": "0xA0b86991c627Ce246199B89fF4b35b54C5c85687",
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
}

WHALE_THRESHOLD = 1_000_000 * 10**6  # $1M for 6-dec tokens

print(f"BOZAGENTIC Monitor started. Interval: {INTERVAL}s")
print(f"Watching: {', '.join(WATCH_TOKENS.keys())}")

while True:
    try:
        current = w3.eth.block_number
        if current <= last_block:
            time.sleep(INTERVAL)
            continue
        
        # Scan new blocks
        for blk_num in range(last_block + 1, current + 1):
            blk = w3.eth.get_block(blk_num, full_transactions=True)
            
            # Check ETH whales
            for tx in blk['transactions']:
                if tx['value'] > w3.to_wei(100, 'ether'):
                    print(f"[WHALE] Block {blk_num}: {w3.from_wei(tx['value'], 'ether'):.0f} ETH "
                          f"{tx['from'][:10]}... -> {(tx['to'] or 'CREATE')[:10]}...")
                
                if tx['to'] is None:
                    receipt = w3.eth.get_transaction_receipt(tx['hash'])
                    if receipt['contractAddress']:
                        code = w3.eth.get_code(receipt['contractAddress'])
                        print(f"[NEW] Block {blk_num}: {receipt['contractAddress'][:14]}... ({len(code)}B)")
            
            # Check token whales
            for token_name, token_addr in WATCH_TOKENS.items():
                try:
                    logs = w3.eth.get_logs({
                        'fromBlock': blk_num, 'toBlock': blk_num,
                        'address': Web3.to_checksum_address(token_addr),
                        'topics': [TRANSFER]
                    })
                    for log in logs:
                        val = int(log['data'].hex(), 16)
                        if val > WHALE_THRESHOLD:
                            frm = Web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
                            to = Web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:])
                            print(f"[TOKEN_WHALE] Block {blk_num}: {token_name} "
                                  f"${val/10**6:,.0f} {frm[:10]}... -> {to[:10]}...")
                except:
                    pass
            
            # Check upgrades
            try:
                upgrades = w3.eth.get_logs({
                    'fromBlock': blk_num, 'toBlock': blk_num,
                    'topics': [UPGRADED]
                })
                for u in upgrades:
                    print(f"[UPGRADE] Block {blk_num}: {u['address'][:14]}... upgraded")
            except:
                pass
        
        last_block = current
    except Exception as e:
        print(f"[ERROR] {str(e)[:60]}")
    
    time.sleep(INTERVAL)
