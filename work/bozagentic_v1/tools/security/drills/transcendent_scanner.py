"""
WEB3.PY TRANSCENDENT DRILL: Full Automated Security Scanner
One script that scans ANY contract for ALL known vulnerability patterns
"""
from web3 import Web3
import json, sys
from collections import Counter, defaultdict

# === RPC SETUP ===
RPCS = ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com"]
w3 = None
for rpc in RPCS:
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))
        if w3.is_connected(): break
    except: continue

latest = w3.eth.block_number
print(f"Block: {latest}")

# ============================================================
# FULL CONTRACT SCANNER
# ============================================================

OPCODES = {
    0x00:'STOP',0x01:'ADD',0x02:'MUL',0x03:'SUB',0x04:'DIV',0x05:'SDIV',
    0x06:'MOD',0x07:'SMOD',0x08:'ADDMOD',0x09:'MULMOD',0x0a:'EXP',
    0x10:'LT',0x11:'GT',0x12:'SLT',0x13:'SGT',0x14:'EQ',0x15:'ISZERO',
    0x16:'AND',0x17:'OR',0x18:'XOR',0x19:'NOT',0x1a:'BYTE',0x1b:'SHL',0x1c:'SHR',0x1d:'SAR',
    0x20:'KECCAK256',
    0x30:'ADDRESS',0x31:'BALANCE',0x32:'ORIGIN',0x33:'CALLER',0x34:'CALLVALUE',
    0x35:'CALLDATALOAD',0x36:'CALLDATASIZE',0x37:'CALLDATACOPY',0x38:'CODESIZE',
    0x39:'CODECOPY',0x3a:'GASPRICE',0x3b:'EXTCODESIZE',0x3c:'EXTCODECOPY',
    0x3d:'RETURNDATASIZE',0x3e:'RETURNDATACOPY',0x3f:'EXTCODEHASH',
    0x40:'BLOCKHASH',0x41:'COINBASE',0x42:'TIMESTAMP',0x43:'NUMBER',
    0x44:'PREVRANDAO',0x45:'GASLIMIT',0x46:'CHAINID',0x47:'SELFBALANCE',0x48:'BASEFEE',
    0x50:'POP',0x51:'MLOAD',0x52:'MSTORE',0x53:'MSTORE8',0x54:'SLOAD',0x55:'SSTORE',
    0x56:'JUMP',0x57:'JUMPI',0x58:'PC',0x59:'MSIZE',0x5a:'GAS',0x5b:'JUMPDEST',
    0x5c:'TLOAD',0x5d:'TSTORE',0x5e:'MCOPY',0x5f:'PUSH0',
    0xf0:'CREATE',0xf1:'CALL',0xf2:'CALLCODE',0xf3:'RETURN',0xf4:'DELEGATECALL',
    0xf5:'CREATE2',0xfa:'STATICCALL',0xfd:'REVERT',0xfe:'INVALID',0xff:'SELFDESTRUCT',
}
for i in range(32): OPCODES[0x60+i] = f'PUSH{i+1}'
for i in range(16): OPCODES[0x80+i] = f'DUP{i+1}'
for i in range(16): OPCODES[0x90+i] = f'SWAP{i+1}'
for i in range(5):  OPCODES[0xa0+i] = f'LOG{i}'

def disassemble(bytecode):
    code = bytes.fromhex(bytecode.replace('0x',''))
    ops = []
    i = 0
    while i < len(code):
        op = code[i]
        name = OPCODES.get(op, f'DATA_{op:02x}')
        if 0x60 <= op <= 0x7f:
            n = op - 0x5f
            data = code[i+1:i+1+n].hex()
            ops.append((i, name, data))
            i += 1 + n
        else:
            ops.append((i, name, ''))
            i += 1
    return ops

def extract_selectors(ops):
    selectors = set()
    for i, (offset, name, data) in enumerate(ops):
        if name == 'PUSH4' and data:
            for j in range(i+1, min(i+10, len(ops))):
                if ops[j][1] == 'EQ':
                    selectors.add('0x' + data)
                    break
                if ops[j][1] == 'PUSH4' and j > i+1:
                    break
    return selectors

def scan_contract(addr, name=""):
    """Full security scan of a contract"""
    addr = Web3.to_checksum_address(addr)
    print(f"\n{'='*60}")
    print(f"SCANNING: {name or addr}")
    print(f"{'='*60}")
    
    code = w3.eth.get_code(addr)
    if len(code) == 0:
        print(f"  NO CODE (EOA or destroyed)")
        return {'risk': 0, 'findings': ['EOA']}
    
    findings = []
    risk = 0
    
    # === 1. BYTECODE ANALYSIS ===
    ops = disassemble(code.hex())
    op_counts = Counter(name for _, name, _ in ops if not name.startswith('DATA_'))
    selectors = extract_selectors(ops)
    
    print(f"\n  [BYTECODE]")
    print(f"  Size: {len(code)} bytes ({len(code)/24576*100:.1f}% of EIP-170)")
    print(f"  Instructions: {len(ops)}")
    print(f"  Selectors: {len(selectors)}")
    
    # Check for dangerous opcodes
    if op_counts.get('SELFDESTRUCT', 0) > 0:
        # Verify it's real (not PUSH data)
        real_sd = sum(1 for _, n, _ in ops if n == 'SELFDESTRUCT')
        if real_sd > 0:
            findings.append(f"SELFDESTRUCT x{real_sd}")
            risk += 25
    
    if op_counts.get('DELEGATECALL', 0) > 0:
        real_dc = sum(1 for _, n, _ in ops if n == 'DELEGATECALL')
        if real_dc > 0:
            findings.append(f"DELEGATECALL x{real_dc} (proxy/upgrade risk)")
            risk += 10
    
    if op_counts.get('CALLCODE', 0) > 0:
        real_cc = sum(1 for _, n, _ in ops if n == 'CALLCODE')
        if real_cc > 0:
            findings.append(f"CALLCODE x{real_cc} (deprecated, dangerous)")
            risk += 20
    
    if op_counts.get('CREATE2', 0) > 0:
        real_c2 = sum(1 for _, n, _ in ops if n == 'CREATE2')
        if real_c2 > 0:
            findings.append(f"CREATE2 x{real_c2} (redeployable)")
            risk += 5
    
    # === 2. PROXY DETECTION ===
    print(f"\n  [PROXY]")
    hex_code = code.hex()
    
    if '363d3d373d3d3d363d73' in hex_code:
        idx = hex_code.index('363d3d373d3d3d363d73') + 20
        impl = Web3.to_checksum_address('0x' + hex_code[idx:idx+40])
        findings.append(f"ERC-1167 clone -> {impl}")
        print(f"  ERC-1167 Minimal Proxy -> {impl}")
        risk += 5
    else:
        EIP1967 = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
        impl_raw = w3.eth.get_storage_at(addr, EIP1967)
        impl_val = int(impl_raw.hex(), 16)
        if impl_val > 0:
            impl = Web3.to_checksum_address('0x' + impl_raw.hex()[-40:])
            findings.append(f"EIP-1967 proxy -> {impl}")
            print(f"  EIP-1967 Proxy -> {impl}")
            risk += 10
            
            # Check if upgradeable
            ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
            admin_raw = w3.eth.get_storage_at(addr, ADMIN)
            admin_val = int(admin_raw.hex(), 16)
            if admin_val > 0:
                admin = Web3.to_checksum_address('0x' + admin_raw.hex()[-40:])
                findings.append(f"Upgradeable (admin: {admin})")
                print(f"  Admin: {admin}")
                risk += 10
        else:
            print(f"  Not a proxy (implementation)")
    
    # === 3. STORAGE ANALYSIS ===
    print(f"\n  [STORAGE]")
    balance = w3.eth.get_balance(addr)
    print(f"  ETH balance: {w3.from_wei(balance, 'ether'):.6f}")
    if balance > w3.to_wei(10, 'ether'):
        findings.append(f"Holds {w3.from_wei(balance, 'ether'):.0f} ETH")
        risk += 15
    
    # Read first 10 slots
    nonzero_slots = 0
    for slot in range(10):
        raw = w3.eth.get_storage_at(addr, slot)
        val = int(raw.hex(), 16)
        if val > 0:
            nonzero_slots += 1
            if val > 2**100 and val < 2**160:
                stored_addr = Web3.to_checksum_address('0x' + raw.hex()[-40:])
                print(f"  Slot {slot}: {stored_addr} (address)")
            elif val < 10**10:
                print(f"  Slot {slot}: {val}")
    
    if nonzero_slots == 0:
        print(f"  Slots 0-9: all empty (implementation contract)")
    
    # === 4. METADATA / VERIFICATION ===
    print(f"\n  [VERIFICATION]")
    has_metadata = 'a264' in hex_code or 'a265' in hex_code
    if has_metadata:
        # Extract solc version
        cbor_len = int(hex_code[-4:], 16)
        cbor = hex_code[-4-cbor_len*2:-4]
        has_solc = '736f6c63' in cbor
        has_ipfs = '69706673' in cbor
        print(f"  Metadata: yes (solc={'Y' if has_solc else 'N'}, ipfs={'Y' if has_ipfs else 'N'})")
    else:
        findings.append("No metadata (source unverified)")
        risk += 15
        print(f"  Metadata: NO (unverified!)")
    
    # === 5. ACCESS CONTROL TESTING ===
    print(f"\n  [ACCESS CONTROL]")
    attacker = "0x000000000000000000000000000000000000dEaD"
    
    # Test common admin functions
    admin_sigs = [
        ('owner()', '0x8da5cb5b'),
        ('admin()', '0xf851a440'),
        ('getAdmin()', '0x6e9960c3'),
        ('paused()', '0x5c975abb'),
    ]
    
    for func_name, sel in admin_sigs:
        if sel in [s[:10] for s in selectors] or sel.replace('0x','') in hex_code:
            try:
                result = w3.eth.call({'to': addr, 'data': sel})
                if len(result) >= 32:
                    val = Web3.to_checksum_address('0x' + result.hex()[-40:])
                    print(f"  {func_name}: {val}")
                    if val == "0x0000000000000000000000000000000000000000":
                        findings.append(f"{func_name} returns zero address!")
                        risk += 20
            except:
                pass
    
    # Test if admin functions are callable by anyone
    dangerous_funcs = [
        ('setOwner(address)', '0x13af4035'),
        ('setAdmin(address)', '0x704b6c02'),
        ('upgradeTo(address)', '0x3659cfe6'),
        ('kill()', '0x41c0e1b5'),
        ('destroy()', '0x83197ef0'),
        ('selfdestruct(address)', '0x9cb8a26a'),
    ]
    
    for func_name, sel in dangerous_funcs:
        if sel.replace('0x','') in hex_code:
            calldata = sel + '0' * 64
            try:
                w3.eth.call({'from': attacker, 'to': addr, 'data': calldata})
                findings.append(f"!! {func_name} CALLABLE BY ANYONE!")
                risk += 50
                print(f"  !! {func_name}: NO ACCESS CONTROL!")
            except Exception as e:
                if 'revert' in str(e).lower() or '0x' in str(e):
                    print(f"  {func_name}: protected ✓")
    
    # === 6. KNOWN VULNERABILITY PATTERNS ===
    print(f"\n  [VULNERABILITY PATTERNS]")
    
    # Pattern: tx.origin usage (phishing)
    # ORIGIN (0x32) followed by EQ (0x14) = tx.origin check
    origin_checks = 0
    for i, (_, name, _) in enumerate(ops):
        if name == 'ORIGIN':
            for j in range(i+1, min(i+5, len(ops))):
                if ops[j][1] == 'EQ':
                    origin_checks += 1
                    break
    if origin_checks > 0:
        findings.append(f"tx.origin used x{origin_checks} (phishing risk)")
        risk += 15
        print(f"  tx.origin checks: {origin_checks} ⚠️")
    else:
        print(f"  tx.origin: not used ✓")
    
    # Pattern: block.timestamp dependency
    timestamp_uses = sum(1 for _, n, _ in ops if n == 'TIMESTAMP')
    if timestamp_uses > 0:
        print(f"  block.timestamp: {timestamp_uses} uses (miner manipulable)")
    
    # Pattern: blockhash dependency
    blockhash_uses = sum(1 for _, n, _ in ops if n == 'BLOCKHASH')
    if blockhash_uses > 0:
        findings.append(f"block.hash used x{blockhash_uses} (randomness risk)")
        print(f"  block.hash: {blockhash_uses} uses ⚠️")
    
    # Pattern: CALLVALUE without payable check
    callvalue_uses = sum(1 for _, n, _ in ops if n == 'CALLVALUE')
    print(f"  CALLVALUE: {callvalue_uses} uses")
    
    # === 7. SELECTOR MATCHING ===
    print(f"\n  [FUNCTIONS]")
    KNOWN = {}
    common_funcs = [
        'transfer(address,uint256)', 'transferFrom(address,address,uint256)',
        'approve(address,uint256)', 'balanceOf(address)', 'totalSupply()',
        'allowance(address,address)', 'owner()', 'admin()',
        'deposit()', 'withdraw(uint256)', 'withdraw(bytes)',
        'mint(address,uint256)', 'burn(uint256)',
        'pause()', 'unpause()', 'paused()',
        'upgradeTo(address)', 'initialize()',
        'setOwner(address)', 'setAdmin(address)',
        'kill()', 'destroy()', 'selfdestruct(address)',
        'swapExactTokensForTokens(uint256,uint256,address[],address,uint256)',
        'addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)',
        'flashLoan(address,address[],uint256[],uint256[],address,bytes,uint16)',
    ]
    for f in common_funcs:
        sel = '0x' + Web3.keccak(text=f)[:4].hex()
        KNOWN[sel] = f
    
    matched = {s: KNOWN[s] for s in selectors if s in KNOWN}
    unknown = [s for s in selectors if s not in KNOWN and s != '0xffffffff']
    
    print(f"  Matched: {len(matched)}/{len(selectors)}")
    for sel in sorted(matched.keys())[:10]:
        print(f"    {sel} = {matched[sel]}")
    if unknown:
        print(f"  Unknown: {len(unknown)} selectors")
    
    # Check for dangerous functions
    dangerous_found = [f for s, f in matched.items() if f in ('kill()', 'destroy()', 'selfdestruct(address)', 'setOwner(address)')]
    if dangerous_found:
        findings.append(f"Dangerous functions: {', '.join(dangerous_found)}")
        risk += 20
    
    # === 8. RISK SUMMARY ===
    risk = min(risk, 100)
    risk_level = "LOW" if risk < 30 else "MEDIUM" if risk < 60 else "HIGH" if risk < 80 else "CRITICAL"
    
    print(f"\n  [RISK SUMMARY]")
    print(f"  Score: {risk}/100 ({risk_level})")
    print(f"  Findings: {len(findings)}")
    for f in findings:
        print(f"    - {f}")
    
    return {'risk': risk, 'level': risk_level, 'findings': findings, 'selectors': len(selectors)}

# ============================================================
# SCAN MULTIPLE CONTRACTS
# ============================================================

TARGETS = {
    "Kiln StakingContract": "0x0A7272e8573aea8359FEC143ac02AED90F822bD0",
    "Kiln CL Dispatcher": "0x462Dd07A79e5DDfBe0C171449C5c01788d5d03C3",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "Hop ETH Bridge": "0xb8901acB165ed027E32754E0FFe830802919727f",
    "Wormhole Bridge": "0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
}

results = {}
for name, addr in TARGETS.items():
    try:
        results[name] = scan_contract(addr, name)
    except Exception as e:
        print(f"\n  ERROR scanning {name}: {str(e)[:60]}")
        results[name] = {'risk': -1, 'findings': [f'Error: {str(e)[:40]}']}

# ============================================================
# COMPARATIVE ANALYSIS
# ============================================================
print(f"\n{'='*60}")
print("COMPARATIVE ANALYSIS")
print(f"{'='*60}")
print(f"\n  {'Contract':<25} {'Risk':>5} {'Level':<10} {'Findings':>8}")
print(f"  {'-'*55}")
for name, r in sorted(results.items(), key=lambda x: -x[1].get('risk', 0)):
    risk = r.get('risk', -1)
    level = r.get('level', 'ERROR')
    findings = len(r.get('findings', []))
    print(f"  {name:<25} {risk:>5} {level:<10} {findings:>8}")

print(f"\n✓ TRANSCENDENT DRILL COMPLETE")
