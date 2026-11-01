#!/usr/bin/env python3
"""BOZAGENTIC Honeypot Detector v1.0"""
import sys
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com", request_kwargs={'timeout': 10}))

def check(addr):
    addr = Web3.to_checksum_address(addr)
    code = w3.eth.get_code(addr)
    if len(code) == 0:
        print(f"NO CODE at {addr}")
        return
    
    hex_code = code.hex()
    cb = bytes.fromhex(hex_code.replace('0x',''))
    
    checks = {}
    checks['size'] = len(code)
    checks['pause'] = '5c975abb' in hex_code and '8456cb59' in hex_code
    checks['mint'] = '40c10f19' in hex_code
    checks['owner'] = '8da5cb5b' in hex_code
    
    # Self-destruct check
    sd = 0
    i = 0
    while i < len(cb):
        if cb[i] == 0xff: sd += 1
        if 0x60 <= cb[i] <= 0x7f: i += (cb[i] - 0x5f) + 1
        else: i += 1
    checks['selfdestruct'] = sd > 0
    
    # Proxy check
    EIP1967 = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    impl_raw = w3.eth.get_storage_at(addr, EIP1967)
    checks['proxy'] = int(impl_raw.hex(), 16) > 0
    
    # Verified
    checks['verified'] = 'a264' in hex_code or 'a265' in hex_code
    
    risk = 0
    if checks['pause']: risk += 15
    if checks['mint']: risk += 20
    if checks['selfdestruct']: risk += 30
    if checks['proxy']: risk += 15
    if not checks['verified']: risk += 15
    
    verdict = 'SAFE' if risk < 10 else 'LOW_RISK' if risk < 30 else 'MEDIUM_RISK' if risk < 60 else 'HIGH_RISK'
    
    print(f"Address: {addr}")
    print(f"Size: {checks['size']}B")
    print(f"Verified: {checks['verified']}")
    print(f"Pause: {checks['pause']}")
    print(f"Mint: {checks['mint']}")
    print(f"Self-destruct: {checks['selfdestruct']}")
    print(f"Proxy: {checks['proxy']}")
    print(f"Risk: {risk}/100 ({verdict})")

if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "0xdAC17F958D2ee523a2206206994597C13D831ec7")
