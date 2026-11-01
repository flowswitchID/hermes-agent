#!/usr/bin/env python3
"""
BOZAGENTIC Contract Scanner v1.0
Usage: python3 scanner.py <address> [rpc_url]
"""
import sys
from web3 import Web3

def scan(addr, rpc="https://ethereum-rpc.publicnode.com"):
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 15}))
    addr = Web3.to_checksum_address(addr)
    
    code = w3.eth.get_code(addr)
    if len(code) == 0:
        print(f"NO CODE at {addr}")
        return
    
    print(f"Contract: {addr}")
    print(f"Size: {len(code)} bytes")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(addr), 'ether')} ETH")
    
    # Opcode analysis
    code_bytes = bytes.fromhex(code.hex().replace('0x',''))
    ops = {0x54:'SLOAD',0x55:'SSTORE',0xf1:'CALL',0xf2:'CALLCODE',
           0xf4:'DELEGATECALL',0xfa:'STATICCALL',0xf0:'CREATE',
           0xf5:'CREATE2',0xff:'SELFDESTRUCT',0x32:'ORIGIN'}
    counts = {}
    i = 0
    while i < len(code_bytes):
        op = code_bytes[i]
        if op in ops: counts[ops[op]] = counts.get(ops[op], 0) + 1
        if 0x60 <= op <= 0x7f: i += (op - 0x5f) + 1
        else: i += 1
    
    print(f"Opcodes: {counts}")
    
    # Proxy detection
    EIP1967 = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    impl_raw = w3.eth.get_storage_at(addr, EIP1967)
    if int(impl_raw.hex(), 16) > 0:
        print(f"Proxy: EIP-1967 -> {Web3.to_checksum_address('0x' + impl_raw.hex()[-40:])}")
    elif '363d3d373d3d3d363d73' in code.hex():
        idx = code.hex().index('363d3d373d3d3d363d73') + 20
        print(f"Proxy: ERC-1167 -> {Web3.to_checksum_address('0x' + code.hex()[idx:idx+40])}")
    else:
        print(f"Proxy: None (implementation)")
    
    # Metadata
    has_meta = 'a264' in code.hex() or 'a265' in code.hex()
    print(f"Verified: {'yes' if has_meta else 'NO'}")
    
    # Risk
    risk = 0
    if counts.get('SELFDESTRUCT', 0) > 0: risk += 25
    if counts.get('CALLCODE', 0) > 0: risk += 20
    if counts.get('ORIGIN', 0) > 0: risk += 15
    if not has_meta: risk += 15
    if w3.eth.get_balance(addr) > w3.to_wei(10, 'ether'): risk += 15
    if counts.get('DELEGATECALL', 0) > 0: risk += 10
    
    level = "LOW" if risk < 30 else "MEDIUM" if risk < 60 else "HIGH"
    print(f"Risk: {min(risk,100)}/100 ({level})")

if __name__ == "__main__":
    addr = sys.argv[1] if len(sys.argv) > 1 else "0x0A7272e8573aea8359FEC143ac02AED90F822bD0"
    rpc = sys.argv[2] if len(sys.argv) > 2 else "https://ethereum-rpc.publicnode.com"
    scan(addr, rpc)
