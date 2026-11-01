#!/usr/bin/env python3
"""
BOZAGENTIC Bounty Hunting Automation v1.0
Complete pipeline from target selection to submission.
Usage: python3 bounty_hunter.py <contract_address> [chain] [output_dir]
"""
import sys, json, os, subprocess, urllib.request
from datetime import datetime
from web3 import Web3

def main():
    addr = sys.argv[1] if len(sys.argv) > 1 else '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'
    chain = sys.argv[2] if len(sys.argv) > 2 else 'eth'
    output_dir = sys.argv[3] if len(sys.argv) > 3 else f'./audit_{addr[:10]}'
    
    os.makedirs(output_dir, exist_ok=True)
    w3 = Web3(Web3.HTTPProvider('https://ethereum-rpc.publicnode.com', request_kwargs={'timeout': 15}))
    addr = Web3.to_checksum_address(addr)
    
    report = {'address': addr, 'timestamp': datetime.now().isoformat(), 'steps': {}}
    
    # Step 1: Fetch source
    print(f'[1/8] Fetching source from Blockscout...')
    base = f'https://{"eth" if chain == "eth" else chain}.blockscout.com/api/v2'
    try:
        req = urllib.request.Request(f'{base}/smart-contracts/{addr}', headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            source = data.get('source_code', '')
            name = data.get('name', 'Unknown')
            compiler = data.get('compiler_version', 'Unknown')
            additional = data.get('additional_sources', [])
            
            # Save source
            with open(os.path.join(output_dir, f'{name}.sol'), 'w') as f:
                f.write(source)
            for i, extra in enumerate(additional):
                extra_name = extra.get('file_path', f'additional_{i}.sol')
                extra_source = extra.get('source_code', '')
                safe_name = extra_name.replace('/', '_')
                with open(os.path.join(output_dir, safe_name), 'w') as f:
                    f.write(extra_source)
            
            report['steps']['source'] = {'name': name, 'compiler': compiler, 'files': 1 + len(additional)}
            print(f'  Saved: {name} ({len(source):,} chars, {len(additional)} additional files)')
    except Exception as e:
        print(f'  Error: {e}')
        report['steps']['source'] = {'error': str(e)[:60]}
    
    # Step 2: On-chain analysis
    print(f'[2/8] On-chain analysis...')
    code = w3.eth.get_code(addr)
    bal = float(w3.from_wei(w3.eth.get_balance(addr), 'ether'))
    
    EIP1967_IMPL = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
    EIP1967_ADMIN = '0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
    impl_raw = w3.eth.get_storage_at(addr, EIP1967_IMPL)
    admin_raw = w3.eth.get_storage_at(addr, EIP1967_ADMIN)
    is_proxy = int(impl_raw.hex(), 16) > 0
    
    scan_code = code
    if is_proxy:
        impl = Web3.to_checksum_address('0x' + impl_raw.hex()[-40:])
        scan_code = w3.eth.get_code(impl)
    
    # Opcode analysis
    cb = bytes.fromhex(scan_code.hex().replace('0x',''))
    ops = {}
    i = 0
    while i < len(cb):
        op = cb[i]
        names = {0x54:'SLOAD',0x55:'SSTORE',0xf1:'CALL',0xf2:'CALLCODE',0xf4:'DELEGATECALL',
                 0xfa:'STATICCALL',0xf0:'CREATE',0xf5:'CREATE2',0xff:'SELFDESTRUCT',
                 0x32:'ORIGIN',0x5c:'TLOAD',0x5d:'TSTORE'}
        if op in names: ops[names[op]] = ops.get(names[op], 0) + 1
        if 0x60 <= op <= 0x7f: i += (op - 0x5f) + 1
        else: i += 1
    
    report['steps']['onchain'] = {
        'code_size': len(code),
        'balance': bal,
        'is_proxy': is_proxy,
        'opcodes': ops,
    }
    print(f'  Code: {len(code)}B, Balance: {bal:.4f} ETH, Proxy: {is_proxy}')
    
    # Step 3: Vulnerability pattern scan
    print(f'[3/8] Vulnerability pattern scan...')
    findings = []
    hex_code = scan_code.hex()
    
    if ops.get('SELFDESTRUCT', 0) > 0:
        findings.append({'severity': 'HIGH', 'pattern': 'SELFDESTRUCT', 'count': ops['SELFDESTRUCT']})
    if ops.get('CALLCODE', 0) > 0:
        findings.append({'severity': 'HIGH', 'pattern': 'CALLCODE', 'count': ops['CALLCODE']})
    if ops.get('ORIGIN', 0) > 0:
        findings.append({'severity': 'MEDIUM', 'pattern': 'tx.origin', 'count': ops['ORIGIN']})
    if 'a264' not in hex_code and 'a265' not in hex_code:
        findings.append({'severity': 'MEDIUM', 'pattern': 'unverified'})
    
    report['steps']['patterns'] = findings
    print(f'  Findings: {len(findings)}')
    for f in findings:
        print(f'    [{f["severity"]}] {f["pattern"]}')
    
    # Step 4: Access control check
    print(f'[4/8] Access control check...')
    for fname, sel in [('owner()', '0x8da5cb5b'), ('getAdmin()', '0x6e9960c3')]:
        if sel.replace('0x','') in hex_code:
            try:
                r = w3.eth.call({'to': addr, 'data': sel})
                if len(r) >= 32:
                    val = Web3.to_checksum_address('0x' + r.hex()[-40:])
                    report['steps'][f'access_{fname}'] = val
                    print(f'  {fname}: {val}')
            except: pass
    
    # Step 5: Selector extraction
    print(f'[5/8] Selector extraction...')
    selectors = set()
    ops_list = []
    i = 0
    while i < len(cb):
        op = cb[i]
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f
            data = cb[i+1:i+1+n].hex()
            ops_list.append((i, f'PUSH{n}', data))
            i += 1 + n
        else:
            names = {0x14:'EQ'}
            ops_list.append((i, names.get(op, ''), ''))
            i += 1
    
    for idx, (offset, op_name, data) in enumerate(ops_list):
        if op_name == 'PUSH4' and data:
            for j in range(idx+1, min(idx+10, len(ops_list))):
                if ops_list[j][1] == 'EQ':
                    selectors.add('0x' + data)
                    break
                if ops_list[j][1] == 'PUSH4' and j > idx+1:
                    break
    
    report['steps']['selectors'] = len(selectors)
    print(f'  Selectors: {len(selectors)}')
    
    # Step 6: Risk scoring
    print(f'[6/8] Risk scoring...')
    risk = sum({'HIGH':25,'MEDIUM':15,'LOW':5}.get(f['severity'], 0) for f in findings)
    risk = min(risk, 100)
    level = 'LOW' if risk < 25 else 'MEDIUM' if risk < 50 else 'HIGH' if risk < 75 else 'CRITICAL'
    report['risk'] = {'score': risk, 'level': level}
    print(f'  Risk: {risk}/100 ({level})')
    
    # Step 7: Generate report
    print(f'[7/8] Generating report...')
    report_path = os.path.join(output_dir, 'audit_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f'  Saved: {report_path}')
    
    # Step 8: Summary
    print(f'[8/8] Summary')
    print(f'  Target: {addr}')
    print(f'  Risk: {risk}/100 ({level})')
    print(f'  Findings: {len(findings)}')
    print(f'  Output: {output_dir}/')
    print(f'  Done!')

if __name__ == '__main__':
    main()
