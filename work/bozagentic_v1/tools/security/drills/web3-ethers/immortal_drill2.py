"""
WEB3.PY IMMORTAL DRILL 2: Fixed + Interaction Graph + Storage Diff + Event DB + Advanced Patterns
"""
from web3 import Web3
import json
from collections import Counter, defaultdict

w3 = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com", request_kwargs={'timeout': 15}))
latest = w3.eth.block_number
print(f"Block: {latest}")

# ============================================================
# 1. CONTRACT INTERACTION GRAPH (FIXED)
# ============================================================
print("\n" + "="*60)
print("1. CONTRACT INTERACTION GRAPH")
print("="*60)

block = w3.eth.get_block(latest, full_transactions=True)
interaction_graph = defaultdict(lambda: defaultdict(int))

for tx in block['transactions'][:100]:
    if tx['to']:
        receipt = w3.eth.get_transaction_receipt(tx['hash'])
        for log in receipt['logs']:
            caller = tx['to'][:10]
            target = log['address'][:10]
            if caller != target:
                interaction_graph[caller][target] += 1

# Most connected
connectivity = {caller: len(targets) for caller, targets in interaction_graph.items()}
top_connected = sorted(connectivity.items(), key=lambda x: -x[1])[:10]
print(f"  Most connected contracts:")
for addr, count in top_connected:
    total = sum(interaction_graph[addr].values())
    print(f"    {addr}... : {count} targets, {total} events")

# Hub contracts
hub_scores = defaultdict(int)
for caller, targets in interaction_graph.items():
    for target in targets:
        hub_scores[target] += 1

top_hubs = sorted(hub_scores.items(), key=lambda x: -x[1])[:10]
print(f"\n  Hub contracts (most callers):")
for addr, count in top_hubs:
    print(f"    {addr}... : {count} callers")

# ============================================================
# 2. STORAGE DIFF FORENSICS
# ============================================================
print("\n" + "="*60)
print("2. STORAGE DIFF FORENSICS")
print("="*60)

USDT = Web3.to_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")
slots = {"owner (0)": 0, "totalSupply (1)": 1, "balances (2)": 2, "allowances (3)": 3}

block_range = range(latest - 20, latest + 1, 5)
print(f"  USDT storage across blocks:")
for slot_name, slot_num in slots.items():
    values = []
    for blk in block_range:
        raw = w3.eth.get_storage_at(USDT, slot_num, block_identifier=blk)
        values.append((blk, int(raw.hex(), 16)))
    
    changed = any(v[1] != values[0][1] for v in values)
    if changed:
        print(f"    {slot_name}: CHANGED")
        for blk, val in values:
            print(f"      Block {blk}: {val}")
    else:
        print(f"    {slot_name}: stable ({values[0][1]})")

# ============================================================
# 3. EVENT SIGNATURE DATABASE
# ============================================================
print("\n" + "="*60)
print("3. EVENT SIGNATURE DATABASE")
print("="*60)

EVENT_DB = {}
event_sigs = [
    "Transfer(address,address,uint256)", "Approval(address,address,uint256)",
    "Deposit(address,uint256)", "Withdrawal(address,uint256)",
    "Sync(uint112,uint112)", "Swap(address,uint256,uint256,uint256,uint256,address)",
    "Mint(address,uint256)", "Burn(address,uint256)",
    "OwnershipTransferred(address,address)", "Upgraded(address)",
    "AdminChanged(address,address)", "Paused(address)", "Unpaused(address)",
    "PairCreated(address,address,address,uint256)",
    "FlashLoan(address,address,address,uint256,uint8,uint256,uint16)",
    "ReserveDataUpdated(address,uint256,uint256,uint256,uint256,uint256)",
    "Borrow(address,address,uint256,uint8,uint256)",
    "Repay(address,address,uint256)",
    "LiquidationCall(address,address,address,uint256,bool)",
    "Deposit(address indexed caller, address indexed withdrawer, bytes publicKey, bytes signature)",
    "ChangedGlobalFee(uint256 newGlobalFee)", "ChangedOperatorFee(uint256 newOperatorFee)",
    "ChangedAdmin(address newAdmin)", "ChangedTreasury(address newTreasury)",
    "ExitRequest(address caller, bytes pubkey)",
    "NewOperator(address operatorAddress, address feeRecipientAddress, uint256 index)",
    "Withdrawal(address indexed withdrawer, address indexed feeRecipient, bytes32 pubKeyRoot, uint256 rewards, uint256 nodeOperatorFee, uint256 treasuryFee)",
]
for sig in event_sigs:
    EVENT_DB[Web3.keccak(text=sig).hex()] = sig

print(f"  Event DB: {len(EVENT_DB)} signatures")

# Decode events from recent block
all_events = []
for tx in block['transactions'][:50]:
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    for log in receipt['logs']:
        if log['topics']:
            topic0 = log['topics'][0].hex()
            name = EVENT_DB.get(topic0, 'UNKNOWN')
            all_events.append(name)

event_counts = Counter(all_events)
print(f"  Events in recent txs:")
for name, count in event_counts.most_common(15):
    print(f"    {name[:50]:50s} : {count}")

# ============================================================
# 4. ADVANCED: Reentrancy Detection via Log Ordering
# ============================================================
print("\n" + "="*60)
print("4. REENTRANCY DETECTION (LOG ORDERING)")
print("="*60)

TRANSFER = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().replace("0x","")

reentrancy_suspects = []
for tx in block['transactions'][:50]:
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    
    # Group Transfer events by token contract
    token_transfers = defaultdict(list)
    for log in receipt['logs']:
        if log['topics'] and log['topics'][0].hex() == TRANSFER:
            token_transfers[log['address']].append(log)
    
    # Check for reentrancy pattern: same sender, multiple transfers from same token
    for token, logs in token_transfers.items():
        senders = [Web3.to_checksum_address('0x' + l['topics'][1].hex()[-40:]) for l in logs]
        sender_counts = Counter(senders)
        repeated = {s: c for s, c in sender_counts.items() if c >= 2}
        if repeated:
            reentrancy_suspects.append({
                'tx': tx['hash'].hex()[:14],
                'token': token[:14],
                'senders': repeated,
                'total_transfers': len(logs),
            })

print(f"  Reentrancy suspects: {len(reentrancy_suspects)}")
for s in reentrancy_suspects[:5]:
    print(f"    TX {s['tx']}... token={s['token']}... transfers={s['total_transfers']}")
    for sender, count in s['senders'].items():
        print(f"      {sender[:14]}... sent {count} times")

# ============================================================
# 5. ADVANCED: Flash Loan Detection
# ============================================================
print("\n" + "="*60)
print("5. FLASH LOAN DETECTION")
print("="*60)

# Aave V3 FlashLoan event
AAVE_V3 = Web3.to_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")
FLASH_LOAN = "0x" + Web3.keccak(text="FlashLoan(address,address,address,uint256,uint8,uint256,uint16)").hex().replace("0x","")

# dYdX flash loan (ActionWithdraw + ActionDeposit in same tx)
# Balancer flash loan (FlashLoan event)
BALANCER_VAULT = Web3.to_checksum_address("0xBA12222222228d8Ba445958a75a0704d566BF2C8")
BALANCER_FL = "0x" + Web3.keccak(text="FlashLoan(address,address,uint256,uint256)").hex().replace("0x","")

# Uniswap V2 flash swap (Swap event with amount0Out > 0 AND amount1Out > 0)
SWAP_TOPIC = "0x" + Web3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex().replace("0x","")

try:
    # Check Aave
    aave_fl = w3.eth.get_logs({
        'fromBlock': latest - 50, 'toBlock': 'latest',
        'address': AAVE_V3, 'topics': [FLASH_LOAN]
    })
    print(f"  Aave V3 flash loans (50 blocks): {len(aave_fl)}")
    for log in aave_fl[:3]:
        target = Web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
        data = log['data'].hex().replace('0x','')
        amount = int(data[0:64], 16) / 10**18
        premium = int(data[128:192], 16) / 10**18
        print(f"    Target: {target[:14]}... Amount: {amount:.2f} Premium: {premium:.6f}")
except Exception as e:
    print(f"  Aave query: {str(e)[:60]}")

try:
    # Check Balancer
    bal_fl = w3.eth.get_logs({
        'fromBlock': latest - 50, 'toBlock': 'latest',
        'address': BALANCER_VAULT, 'topics': [BALANCER_FL]
    })
    print(f"  Balancer flash loans (50 blocks): {len(bal_fl)}")
except Exception as e:
    print(f"  Balancer query: {str(e)[:60]}")

# Check for flash swaps (Uniswap V2)
try:
    swap_logs = w3.eth.get_logs({
        'fromBlock': latest - 10, 'toBlock': 'latest',
        'topics': [SWAP_TOPIC]
    })
    flash_swaps = 0
    for log in swap_logs:
        data = log['data'].hex().replace('0x','')
        a0out = int(data[128:192], 16)
        a1out = int(data[192:256], 16)
        # Flash swap: both outputs > 0 (borrow both tokens)
        if a0out > 0 and a1out > 0:
            flash_swaps += 1
    print(f"  Uniswap V2 flash swaps (10 blocks): {flash_swaps}/{len(swap_logs)}")
except Exception as e:
    print(f"  Swap query: {str(e)[:60]}")

# ============================================================
# 6. ADVANCED: Access Control Mapping
# ============================================================
print("\n" + "="*60)
print("6. ACCESS CONTROL MAPPING")
print("="*60)

# Map all access-controlled functions for Kiln
KILN = Web3.to_checksum_address("0x0A7272e8573aea8359FEC143ac02AED90F822bD0")

# Functions that should be admin-only
admin_funcs = [
    'setGlobalFee(uint256)', 'setOperatorFee(uint256)', 'setTreasury(address)',
    'setDepositsStopped(bool)', 'setWithdrawerCustomizationEnabled(bool)',
    'addOperator(address,address)', 'setOperatorLimit(uint256,uint256,uint256)',
    'setOperatorAddresses(uint256,address,address)',
    'deactivateOperator(uint256,address)', 'activateOperator(uint256,address)',
    'transferOwnership(address)',
]

# Functions that should be permissionless
public_funcs = [
    'deposit()', 'withdraw(bytes)', 'withdrawELFee(bytes)', 'withdrawCLFee(bytes)',
    'batchWithdraw(bytes)', 'requestValidatorsExit(bytes)',
    'getAdmin()', 'getTreasury()', 'getGlobalFee()', 'getOperatorFee()',
    'getAvailableValidatorCount()', 'getDepositsStopped()',
]

# Test each function
attacker = "0x000000000000000000000000000000000000dEaD"

print(f"  Admin functions (should revert for non-admin):")
for func in admin_funcs:
    sel = '0x' + Web3.keccak(text=func)[:4].hex()
    # Encode minimal args
    if 'uint256' in func:
        calldata = sel + hex(0)[2:].zfill(64)
    elif 'address' in func and 'uint256' not in func:
        calldata = sel + '0' * 64
    elif 'bool' in func:
        calldata = sel + '0' * 64
    elif 'uint256,uint256,uint256' in func:
        calldata = sel + '0' * 192
    elif 'uint256,address' in func:
        calldata = sel + '0' * 128
    elif 'address,address' in func:
        calldata = sel + '0' * 128
    else:
        calldata = sel
    
    try:
        w3.eth.call({'from': attacker, 'to': KILN, 'data': calldata})
        print(f"    !! {func}: SUCCESS (NO ACCESS CONTROL!)")
    except Exception as e:
        err = str(e)
        if '0x82b42900' in err:
            print(f"    OK {func}: Unauthorized ✓")
        elif 'revert' in err.lower():
            print(f"    OK {func}: Reverted ✓")
        else:
            print(f"    ?? {func}: {err[:50]}")

print(f"\n  Public functions (should work for anyone):")
for func in public_funcs[:6]:
    sel = '0x' + Web3.keccak(text=func)[:4].hex()
    if 'bytes' in func:
        calldata = sel + '0' * 128  # offset + length
    else:
        calldata = sel
    
    try:
        result = w3.eth.call({'from': attacker, 'to': KILN, 'data': calldata})
        print(f"    OK {func}: returned {len(result)} bytes ✓")
    except Exception as e:
        err = str(e)
        if '0x82b42900' in err:
            print(f"    !! {func}: Unauthorized (should be public!)")
        else:
            print(f"    -- {func}: {err[:50]}")

# ============================================================
# 7. ADVANCED: Token Allowance Scanner
# ============================================================
print("\n" + "="*60)
print("7. TOKEN ALLOWANCE SCANNER")
print("="*60)

# Scan for unlimited approvals (security risk)
APPROVAL = "0x" + Web3.keccak(text="Approval(address,address,uint256)").hex().replace("0x","")
MAX_UINT = 2**256 - 1

try:
    approvals = w3.eth.get_logs({
        'fromBlock': latest - 5, 'toBlock': 'latest',
        'address': USDT, 'topics': [APPROVAL]
    })
    
    unlimited = 0
    for log in approvals:
        val = int(log['data'].hex(), 16)
        if val >= MAX_UINT // 2:
            unlimited += 1
            owner = Web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
            spender = Web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:])
            if unlimited <= 5:
                print(f"  !! UNLIMITED: {owner[:14]}... -> {spender[:14]}...")
    
    print(f"  Approvals (5 blocks): {len(approvals)}, Unlimited: {unlimited} ({unlimited/max(1,len(approvals))*100:.0f}%)")
except Exception as e:
    print(f"  Rate limited: {str(e)[:60]}")

# ============================================================
# 8. ADVANCED: Whale Movement Tracker
# ============================================================
print("\n" + "="*60)
print("8. WHALE MOVEMENT TRACKER")
print("="*60)

# Track large ETH and token movements
whale_threshold_eth = w3.to_wei(50, 'ether')
whale_threshold_usdt = 500000 * 10**6  # $500K

eth_whales = []
for tx in block['transactions']:
    if tx['value'] > whale_threshold_eth:
        eth_whales.append({
            'from': tx['from'][:14],
            'to': (tx['to'] or 'CREATE')[:14],
            'value': w3.from_wei(tx['value'], 'ether'),
            'hash': tx['hash'].hex()[:14],
        })

print(f"  ETH whales (>50 ETH): {len(eth_whales)}")
for w in eth_whales[:5]:
    print(f"    {w['from']}... -> {w['to']}... : {w['value']:.2f} ETH")

# USDT whales
try:
    usdt_transfers = w3.eth.get_logs({
        'fromBlock': latest - 3, 'toBlock': 'latest',
        'address': USDT, 'topics': [TRANSFER]
    })
    
    usdt_whales = []
    for log in usdt_transfers:
        val = int(log['data'].hex(), 16)
        if val > whale_threshold_usdt:
            frm = Web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
            to = Web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:])
            usdt_whales.append({'from': frm[:14], 'to': to[:14], 'value': val / 10**6})
    
    print(f"\n  USDT whales (>$500K, 3 blocks): {len(usdt_whales)}")
    for w in usdt_whales[:5]:
        print(f"    {w['from']}... -> {w['to']}... : ${w['value']:,.0f}")
except Exception as e:
    print(f"  Rate limited: {str(e)[:60]}")

# ============================================================
# 9. ADVANCED: Contract Age + Risk Score
# ============================================================
print("\n" + "="*60)
print("9. CONTRACT RISK SCORING")
print("="*60)

def risk_score(addr):
    """Calculate risk score for a contract"""
    addr = Web3.to_checksum_address(addr)
    score = 0
    factors = []
    
    code = w3.eth.get_code(addr)
    if len(code) == 0:
        return 0, ["EOA (no code)"]
    
    code_bytes = bytes.fromhex(code.hex().replace('0x',''))
    
    # Factor 1: Self-destruct
    sd_count = sum(1 for b in code_bytes if b == 0xff)
    if sd_count > 0:
        score += 30
        factors.append(f"SELFDESTRUCT x{sd_count}")
    
    # Factor 2: Delegatecall (proxy risk)
    dc_count = sum(1 for b in code_bytes if b == 0xf4)
    if dc_count > 0:
        score += 10
        factors.append(f"DELEGATECALL x{dc_count}")
    
    # Factor 3: Very small contract (potential rug)
    if len(code) < 500:
        score += 20
        factors.append(f"Tiny contract ({len(code)}B)")
    
    # Factor 4: No metadata (unverified)
    if 'a264' not in code.hex() and 'a265' not in code.hex():
        score += 15
        factors.append("No metadata (unverified)")
    
    # Factor 5: Balance (holds funds = higher impact)
    balance = w3.eth.get_balance(addr)
    if balance > w3.to_wei(100, 'ether'):
        score += 20
        factors.append(f"Holds {w3.from_wei(balance, 'ether'):.0f} ETH")
    
    # Factor 6: CREATE2 (can redeploy to same address)
    c2_count = sum(1 for b in code_bytes if b == 0xf5)
    if c2_count > 0:
        score += 5
        factors.append(f"CREATE2 x{c2_count}")
    
    return min(score, 100), factors

# Score some contracts
contracts_to_score = {
    "Kiln Staking": KILN,
    "USDT": USDT,
    "Hop Bridge": "0xb8901acB165ed027E32754E0FFe830802919727f",
    "Multichain (RIP)": "0x6b7a87899490EcE95443e979cA9485CBE7E71522",
}

for name, addr in contracts_to_score.items():
    score, factors = risk_score(addr)
    risk_level = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH"
    print(f"  {name:25s}: {score:3d}/100 ({risk_level})")
    for f in factors:
        print(f"    - {f}")

# ============================================================
# 10. ADVANCED: Gas Optimization Detector
# ============================================================
print("\n" + "="*60)
print("10. GAS OPTIMIZATION DETECTOR")
print("="*60)

# Analyze recent txs for gas waste
gas_analysis = []
for tx in block['transactions'][:30]:
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    efficiency = receipt['gasUsed'] / tx['gas'] * 100
    gas_analysis.append({
        'hash': tx['hash'].hex()[:10],
        'used': receipt['gasUsed'],
        'limit': tx['gas'],
        'eff': efficiency,
        'status': receipt['status'],
        'logs': len(receipt['logs']),
    })

# Failed txs (wasted gas)
failed = [g for g in gas_analysis if g['status'] == 0]
low_eff = [g for g in gas_analysis if g['eff'] < 50]

print(f"  Analyzed: {len(gas_analysis)} txs")
print(f"  Failed (wasted gas): {len(failed)}")
for f in failed[:3]:
    print(f"    {f['hash']}... : {f['used']:,} gas wasted")
print(f"  Low efficiency (<50%): {len(low_eff)}")
for l in low_eff[:3]:
    print(f"    {l['hash']}... : {l['eff']:.0f}% ({l['used']:,}/{l['limit']:,})")

avg_eff = sum(g['eff'] for g in gas_analysis) / len(gas_analysis)
print(f"  Average efficiency: {avg_eff:.1f}%")

print("\n✓ IMMORTAL DRILL 2 COMPLETE")
