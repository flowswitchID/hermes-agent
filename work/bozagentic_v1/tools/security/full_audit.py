#!/usr/bin/env python3
"""
BOZAGENTIC Full Audit Pipeline v2.0
Usage: python3 full_audit.py <address> [rpc_url]
Generates comprehensive audit report with all checks
"""
import sys, json, os
from datetime import datetime
from web3 import Web3

def main():
    addr = sys.argv[1] if len(sys.argv) > 1 else "0x0A7272e8573aea8359FEC143ac02AED90F822bD0"
    rpc = sys.argv[2] if len(sys.argv) > 2 else "https://ethereum-rpc.publicnode.com"
    
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 15}))
    addr = Web3.to_checksum_address(addr)
    
    report = {
        'contract': addr,
        'timestamp': datetime.now().isoformat(),
        'rpc': rpc,
        'checks': {},
        'findings': [],
        'risk_score': 0,
    }
    
    # 1. Bytecode
    code = w3.eth.get_code(addr)
    report['checks']['bytecode'] = {
        'size': len(code),
        'has_code': len(code) > 0,
        'verified': 'a264' in code.hex() or 'a265' in code.hex(),
    }
    
    if len(code) == 0:
        report['findings'].append(('INFO', 'No code at address'))
        print(json.dumps(report, indent=2))
        return
    
    # 2. Proxy
    hex_code = code.hex()
    if '363d3d373d3d3d363d73' in hex_code:
        idx = hex_code.index('363d3d373d3d3d363d73') + 20
        impl = Web3.to_checksum_address('0x' + hex_code[idx:idx+40])
        report['checks']['proxy'] = {'type': 'ERC-1167', 'impl': impl}
    else:
        EIP1967 = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
        impl_raw = w3.eth.get_storage_at(addr, EIP1967)
        if int(impl_raw.hex(), 16) > 0:
            impl = Web3.to_checksum_address('0x' + impl_raw.hex()[-40:])
            report['checks']['proxy'] = {'type': 'EIP-1967', 'impl': impl}
        else:
            report['checks']['proxy'] = {'type': 'None'}
    
    # 3. Balance
    bal = w3.from_wei(w3.eth.get_balance(addr), 'ether')
    report['checks']['balance'] = bal
    
    # 4. Dangerous opcodes
    cb = bytes.fromhex(hex_code.replace('0x',''))
    sd = cc = origin = 0
    i = 0
    while i < len(cb):
        if cb[i] == 0xff: sd += 1
        elif cb[i] == 0xf2: cc += 1
        elif cb[i] == 0x32: origin += 1
        if 0x60 <= cb[i] <= 0x7f: i += (cb[i] - 0x5f) + 1
        else: i += 1
    
    report['checks']['opcodes'] = {'selfdestruct': sd, 'callcode': cc, 'tx_origin': origin}
    
    if sd > 0: report['findings'].append(('HIGH', f'SELFDESTRUCT x{sd}'))
    if cc > 0: report['findings'].append(('HIGH', f'CALLCODE x{cc}'))
    if origin > 0: report['findings'].append(('MEDIUM', f'tx.origin x{origin}'))
    
    # 5. Selectors
    selectors = set()
    i = 0
    ops = []
    while i < len(cb):
        op = cb[i]
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f
            data = cb[i+1:i+1+n].hex()
            ops.append((i, f'PUSH{n}', data))
            i += 1 + n
        else:
            names = {0x14:'EQ',0x56:'JUMP',0x57:'JUMPI',0xf3:'RETURN',0xfd:'REVERT',0x00:'STOP'}
            ops.append((i, names.get(op, f'OP_{op:02x}'), ''))
            i += 1
    
    for i, (offset, name, data) in enumerate(ops):
        if name == 'PUSH4' and data:
            for j in range(i+1, min(i+10, len(ops))):
                if ops[j][1] == 'EQ':
                    selectors.add('0x' + data)
                    break
                if ops[j][1] == 'PUSH4' and j > i+1:
                    break
    
    report['checks']['selectors'] = len(selectors)
    
    # 6. Access control
    attacker = "0x000000000000000000000000000000000000dEaD"
    for fname, sel in [('owner()', '0x8da5cb5b'), ('getAdmin()', '0x6e9960c3')]:
        if sel in selectors:
            try:
                result = w3.eth.call({'to': addr, 'data': sel})
                if len(result) >= 32:
                    val = Web3.to_checksum_address('0x' + result.hex()[-40:])
                    report['checks'][fname] = val
                    if val == "0x0000000000000000000000000000000000000000":
                        report['findings'].append(('HIGH', f'{fname} returns zero!'))
            except: pass
    
    # Risk score
    risk = 0
    if sd > 0: risk += 25
    if cc > 0: risk += 20
    if origin > 0: risk += 15
    if not report['checks']['bytecode']['verified']: risk += 15
    if bal > 100: risk += 10
    report['risk_score'] = min(risk, 100)
    report['risk_level'] = 'LOW' if risk < 30 else 'MEDIUM' if risk < 60 else 'HIGH'
    
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
