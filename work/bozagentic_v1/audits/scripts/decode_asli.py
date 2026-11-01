import subprocess, re, json, urllib.request

# Get bytecode
r = subprocess.run(['cast', 'code', '0x0F7Ae28dE1C8532170AD4ee566B5801485c13a0E',
    '--rpc-url', 'https://base.gateway.tenderly.co'],
    capture_output=True, text=True, timeout=15)
code = r.stdout.strip()
bc = code[2:] if code.startswith('0x') else code

print(f"Bytecode: {len(code)} chars ({len(code)//2} bytes)")
print(f"Starts with: {code[:40]}")
print()

# Extract ALL function selectors from method ID table
# Look for PUSH4 (0x63 + 4 bytes selector)
sels = set()
for m in re.finditer(r'63([0-9a-f]{8})', bc):
    sel_hex = m.group(1)
    # Filter: reasonable selectors are 0x01000000 - 0xffffffff
    val = int(sel_hex, 16)
    if 0x01000000 <= val <= 0xffffffff:
        sels.add('0x' + sel_hex)

print(f"SELECTORS: {len(sels)}")
for s in sorted(sels):
    try:
        url = f'https://api.4byte.directory/api/v1/signatures/?hex_signature={s[2:]}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        results = data.get('results', [])
        sig = results[0]['text_signature'] if results else '(unknown)'
    except:
        sig = '(error)'
    print(f"  {s} -> {sig}")
print()

# Check opcodes
print("OPCODES (hex):")
checks = {
    'CALL': 'f1', 'DELEGATECALL': 'f4', 'STATICCALL': 'fa',
    'CREATE': 'f0', 'CREATE2': 'f5', 'SELFDESTRUCT': 'ff',
    'SSTORE': '55', 'SLOAD': '54', 'REVERT': 'fd',
    'RETURN': 'f3', 'STOP': '00', 'INVALID': 'fe',
    'JUMPI': '57', 'JUMP': '56', 'JUMPDEST': '5b',
    'PUSH1': '60', 'PUSH2': '61', 'PUSH4': '63',
    'PUSH20': '73', 'PUSH32': '7f',
    'DUP1': '80', 'DUP2': '81', 'SWAP1': '90', 'SWAP2': '91',
    'ADD': '01', 'MUL': '02', 'SUB': '03', 'DIV': '04',
    'MOD': '06', 'LT': '10', 'GT': '11', 'EQ': '14',
    'AND': '16', 'OR': '17', 'XOR': '18', 'NOT': '19',
    'SHA3': '20', 'ADDRESS': '30', 'BALANCE': '31', 'CALLER': '33',
    'CALLVALUE': '34', 'CALLDATALOAD': '35', 'CALLDATASIZE': '36',
    'RETURNDATASIZE': '3d', 'RETURNDATACOPY': '3e',
}
for name, op in checks.items():
    found = op in bc.lower()
    print(f"  {'+' if found else '-'} {name} ({op})")
