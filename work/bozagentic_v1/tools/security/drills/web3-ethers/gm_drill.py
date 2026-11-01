"""
WEB3.PY GRANDMASTER DRILL 2: CEI + State Override + Packed Storage + Calldata
"""
from web3 import Web3
import json
from collections import Counter

w3 = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com", request_kwargs={'timeout': 15}))
latest = w3.eth.block_number
print(f"Block: {latest}")

# === 1. CEI ANALYSIS ===
print("\n=== 1. CEI ANALYSIS: Kiln ===")
KILN = Web3.to_checksum_address("0x0A7272e8573aea8359FEC143ac02AED90F822bD0")
code = w3.eth.get_code(KILN)
code_bytes = bytes.fromhex(code.hex().replace('0x',''))

OPCODES = {0x54:'SLOAD',0x55:'SSTORE',0xf1:'CALL',0xf4:'DELEGATECALL',0xfa:'STATICCALL',
           0xf0:'CREATE',0xf5:'CREATE2',0xfd:'REVERT',0xf3:'RETURN',0x00:'STOP',
           0x56:'JUMP',0x57:'JUMPI',0x5b:'JUMPDEST'}
for i in range(32): OPCODES[0x60+i] = f'PUSH{i+1}'

ops = []
i = 0
while i < len(code_bytes):
    op = code_bytes[i]
    name = OPCODES.get(op, f'OP_{op:02x}')
    if 0x60 <= op <= 0x7f:
        n = op - 0x5f
        data = code_bytes[i+1:i+1+n].hex()
        ops.append((i, name, data))
        i += 1 + n
    else:
        ops.append((i, name, ''))
        i += 1

# Find function entries
func_entries = {}
for i, (offset, name, data) in enumerate(ops):
    if name == 'PUSH4' and data:
        for j in range(i+1, min(i+5, len(ops))):
            if ops[j][1] == 'EQ':
                for k in range(j+1, min(j+4, len(ops))):
                    if ops[k][1] in ('PUSH1', 'PUSH2') and ops[k][2]:
                        target = int(ops[k][2], 16)
                        func_entries['0x' + data] = target
                        break
                break

KNOWN = {
    '0xd0e30db0': 'deposit()', '0x0968f264': 'withdraw(bytes)',
    '0x2ba03a79': 'withdrawCLFee(bytes)', '0xbf509bd4': 'withdrawELFee(bytes)',
    '0xe8a0c121': 'batchWithdraw(bytes)', '0xb6b06dec': 'requestValidatorsExit(bytes)',
    '0xb747e7dd': 'addValidators(...)', '0x1864636c': 'removeValidators(...)',
    '0x8a1af4c4': 'addOperator(...)', '0x291206f6': 'setGlobalFee(uint256)',
    '0x1d095805': 'setOperatorFee(uint256)', '0xf0f44260': 'setTreasury(address)',
    '0x7680fdf5': 'setDepositsStopped(bool)', '0xe99454f5': 'setWithdrawer(bytes,address)',
    '0xb86bcaf7': 'toggleWithdrawn(bytes32)', '0xf2fde38b': 'transferOwnership(address)',
    '0x79ba5097': 'acceptOwnership()',
}

print(f"  Functions: {len(func_entries)}")
cei_issues = 0
for sel, start in sorted(func_entries.items(), key=lambda x: x[1]):
    fname = KNOWN.get(sel, sel)
    calls = []
    sstores = []
    in_func = False
    for offset, name, data in ops:
        if offset == start:
            in_func = True
        if in_func:
            if name == 'CALL':
                calls.append(offset)
            if name == 'SSTORE':
                sstores.append(offset)
            if name in ('RETURN', 'REVERT', 'STOP') and offset > start + 10:
                break
    
    if calls and sstores:
        first_call = min(calls)
        last_sstore = max(sstores)
        if first_call < last_sstore:
            cei_issues += 1
            print(f"  !! {fname}: CALL@{first_call} before SSTORE@{last_sstore}")
        else:
            print(f"  OK {fname}: SSTORE before CALL")
    elif calls:
        print(f"  -- {fname}: CALL only")

if cei_issues == 0:
    print(f"  No CEI violations detected")

# === 2. STATE OVERRIDE ===
print(f"\n=== 2. STATE OVERRIDE ATTACK SIM ===")
USDT = Web3.to_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")
usdt_abi = json.loads('[{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"}]')
usdt = w3.eth.contract(address=USDT, abi=usdt_abi)

attacker = "0x000000000000000000000000000000000000dEaD"

# Override owner
try:
    result = w3.eth.call(
        {'to': USDT, 'data': usdt.encode_abi('owner')},
        state_override={USDT: {'stateDiff': {'0x' + '0'*64: '0x' + '0'*24 + attacker[2:].lower()}}}
    )
    sim_owner = Web3.to_checksum_address('0x' + result.hex()[-40:])
    print(f"  Override owner -> {sim_owner[:14]}... : {'PASS' if sim_owner.lower() == attacker.lower() else 'FAIL'}")
except Exception as e:
    print(f"  Override owner: {str(e)[:60]}")

# Override totalSupply
try:
    result = w3.eth.call(
        {'to': USDT, 'data': usdt.encode_abi('totalSupply')},
        state_override={USDT: {'stateDiff': {'0x' + '0'*63 + '1': '0x' + '0'*63 + '3e7'}}}
    )
    sim_supply = int(result.hex(), 16)
    print(f"  Override totalSupply -> {sim_supply} : {'PASS' if sim_supply == 999 else 'FAIL'}")
except Exception as e:
    print(f"  Override supply: {str(e)[:60]}")

# === 3. PACKED STORAGE ===
print(f"\n=== 3. PACKED STORAGE: Kiln VFI ===")
vfi_base = int(Web3.keccak(text="StakingContract.validatorsFundingInfo").hex(), 16)
found_vfi = False
for slot_offset in range(4):
    raw = w3.eth.get_storage_at(KILN, vfi_base + slot_offset)
    val = int(raw.hex(), 16)
    if val == 0:
        continue
    found_vfi = True
    for inner in range(4):
        shift = inner * 64
        chunk = (val >> shift) & 0xFFFFFFFFFFFFFFFF
        if chunk == 0:
            continue
        available = chunk & 0xFFFFFFFF
        funded = (chunk >> 32) & 0xFFFFFFFF
        op_index = slot_offset * 4 + inner
        print(f"  Operator {op_index}: available={available}, funded={funded}")
if not found_vfi:
    print(f"  All VFI slots empty (implementation contract, state in proxy)")

# === 4. CALLDATA PATTERNS ===
print(f"\n=== 4. CALLDATA PATTERNS ===")
block = w3.eth.get_block(latest, full_transactions=True)

selector_freq = Counter()
size_dist = {'empty': 0, 'selector_only': 0, 'small': 0, 'medium': 0, 'large': 0, 'create': 0}

for tx in block['transactions']:
    data = tx['input']
    if tx['to'] is None:
        size_dist['create'] += 1
    elif len(data) <= 2:
        size_dist['empty'] += 1
    else:
        sel = data.hex()[:10]
        selector_freq[sel] += 1
        if len(data) <= 10:
            size_dist['selector_only'] += 1
        elif len(data) <= 138:
            size_dist['small'] += 1
        elif len(data) <= 650:
            size_dist['medium'] += 1
        else:
            size_dist['large'] += 1

print(f"  Distribution ({len(block['transactions'])} txs):")
for k, v in size_dist.items():
    pct = v / len(block['transactions']) * 100
    print(f"    {k:15s}: {v:4d} ({pct:.1f}%)")

KNOWN_SELS = {
    '0xa9059cbb': 'transfer', '0x23b872dd': 'transferFrom', '0x095ea7b3': 'approve',
    '0x70a08231': 'balanceOf', '0x38ed1739': 'swapExactTokensForTokens',
    '0x18cbafe5': 'swapExactTokensForETH', '0x7ff36ab5': 'swapExactETHForTokens',
    '0x3593564c': 'execute (UniRouter)', '0xac9650d8': 'multicall',
    '0x128acb08': 'swap (V3 pool)', '0xd0e30db0': 'deposit',
    '0x2e1a7d4d': 'withdraw', '0x5ae401dc': 'multicall(uint256,bytes[])',
    '0xfb3bdb41': 'swapETHForExactTokens', '0x414bf389': 'exactInputSingle',
    '0xdb3e2198': 'exactOutputSingle', '0x24856bc3': 'execute(bytes,bytes[])',
}
print(f"\n  Top selectors:")
for sel, count in selector_freq.most_common(10):
    name = KNOWN_SELS.get(sel, 'unknown')
    print(f"    {sel} ({count:3d}x) = {name}")

# === 5. EVENT CORRELATION ===
print(f"\n=== 5. EVENT CORRELATION ===")
multi_contract = []
for tx in block['transactions'][:50]:
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    contracts = set(log['address'] for log in receipt['logs'])
    if len(contracts) >= 3:
        multi_contract.append({
            'hash': tx['hash'].hex()[:14],
            'contracts': len(contracts),
            'logs': len(receipt['logs']),
        })

print(f"  Multi-contract txs (3+): {len(multi_contract)}")
for mc in multi_contract[:5]:
    print(f"    {mc['hash']}... : {mc['contracts']} contracts, {mc['logs']} logs")

# === 6. BALANCE CHANGES ===
print(f"\n=== 6. BALANCE CHANGES ===")
target = None
for tx in block['transactions'][:50]:
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    if len(receipt['logs']) >= 5:
        target = tx
        break

if target:
    receipt = w3.eth.get_transaction_receipt(target['hash'])
    blk_num = target['blockNumber']
    
    addresses = set()
    addresses.add(target['from'])
    if target['to']:
        addresses.add(target['to'])
    for log in receipt['logs']:
        addresses.add(log['address'])
        for t in log['topics'][1:3]:
            if len(t.hex()) >= 42:
                addresses.add(Web3.to_checksum_address('0x' + t.hex()[-40:]))
    
    changes = []
    for addr in list(addresses)[:10]:
        try:
            before = w3.eth.get_balance(addr, block_identifier=blk_num - 1)
            after = w3.eth.get_balance(addr, block_identifier=blk_num)
            delta = after - before
            if delta != 0:
                changes.append((addr, delta))
        except:
            pass
    
    print(f"  TX: {target['hash'].hex()[:14]}... ({len(receipt['logs'])} logs)")
    if changes:
        for addr, delta in sorted(changes, key=lambda x: -abs(x[1])):
            d = "+" if delta > 0 else ""
            print(f"    {addr[:14]}... : {d}{w3.from_wei(delta, 'ether'):.6f} ETH")
    else:
        print(f"    No ETH balance changes (token-only)")

# === 7. GAS ANALYSIS ===
print(f"\n=== 7. GAS ANALYSIS ===")
gas_data = []
for tx in block['transactions'][:20]:
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    eff = receipt['gasUsed'] / tx['gas'] * 100
    gas_data.append({'hash': tx['hash'].hex()[:10], 'used': receipt['gasUsed'], 'limit': tx['gas'], 'eff': eff, 'logs': len(receipt['logs'])})

avg_eff = sum(g['eff'] for g in gas_data) / len(gas_data)
failed = sum(1 for tx in block['transactions'][:20] if w3.eth.get_transaction_receipt(tx['hash'])['status'] == 0)
print(f"  Avg efficiency: {avg_eff:.1f}%")
print(f"  Failed txs: {failed}/20")
gas_data.sort(key=lambda x: -x['used'])
print(f"  Top gas: {gas_data[0]['hash']}... {gas_data[0]['used']:,} gas ({gas_data[0]['eff']:.0f}%)")

# === 8. ETH_GETPROOF ===
print(f"\n=== 8. MERKLE PROOF ===")
try:
    proof = w3.eth.get_proof(USDT, [0, 1], 'latest')
    print(f"  USDT balance: {w3.from_wei(proof['balance'], 'ether')} ETH")
    print(f"  Nonce: {proof['nonce']}")
    print(f"  Code hash: {proof['codeHash'].hex()[:20]}...")
    print(f"  Storage hash: {proof['storageHash'].hex()[:20]}...")
    print(f"  Account proof: {len(proof['accountProof'])} nodes")
    print(f"  Storage proofs: {len(proof['storageProof'])} slots")
except Exception as e:
    print(f"  eth_getProof: {str(e)[:60]}")

print("\nDONE")
