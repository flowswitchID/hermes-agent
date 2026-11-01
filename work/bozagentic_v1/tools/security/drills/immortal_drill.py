"""
WEB3.PY IMMORTAL DRILL 1: Cross-Chain Forensics + MEV Bundle Analysis + CFG Reconstruction
"""
from web3 import Web3
import json
from collections import Counter, defaultdict

# Multi-chain providers
CHAINS = {
    "ethereum": "https://ethereum-rpc.publicnode.com",
    "base": "https://mainnet.base.org",
}

providers = {}
for chain, rpc in CHAINS.items():
    try:
        w = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))
        if w.is_connected():
            providers[chain] = w
            print(f"  {chain}: connected (block {w.eth.block_number})")
    except:
        print(f"  {chain}: FAILED")

w3 = providers["ethereum"]
latest = w3.eth.block_number

# ============================================================
# 1. CROSS-CHAIN BRIDGE FORENSICS
# ============================================================
print("\n" + "="*60)
print("1. CROSS-CHAIN BRIDGE FORENSICS")
print("="*60)

# Analyze bridge contracts on Ethereum
BRIDGES = {
    "Wormhole TokenBridge": "0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
    "Stargate Router": "0x8731d54E9D02c286767d56ac03e8037C07e01e98",
    "Hop ETH Bridge": "0xb8901acB165ed027E32754E0FFe830802919727f",
    "Synapse Bridge": "0x2796317b0fF8538F253012862c06787Adfb8cEb6",
    "Multichain (RIP)": "0x6b7a87899490EcE95443e979cA9485CBE7E71522",
    "Across Protocol": "0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5",
    "Optimism Bridge": "0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1",
    "Arbitrum Inbox": "0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f",
}

TRANSFER = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().replace("0x","")

for name, addr in BRIDGES.items():
    try:
        code = w3.eth.get_code(Web3.to_checksum_address(addr))
        if len(code) == 0:
            print(f"  {name:25s}: NO CODE (destroyed?)")
            continue
        
        # Analyze bytecode
        code_bytes = bytes.fromhex(code.hex().replace('0x',''))
        delegatecalls = sum(1 for b in code_bytes if b == 0xf4)
        selfdestructs = sum(1 for b in code_bytes if b == 0xff)
        creates = sum(1 for b in code_bytes if b == 0xf0)
        create2s = sum(1 for b in code_bytes if b == 0xf5)
        
        # Check proxy
        EIP1967 = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
        impl_raw = w3.eth.get_storage_at(Web3.to_checksum_address(addr), EIP1967)
        is_proxy = int(impl_raw.hex(), 16) > 0
        
        # Check balance (bridges hold funds!)
        balance = w3.eth.get_balance(Web3.to_checksum_address(addr))
        
        print(f"  {name:25s}: {len(code):>6}B, proxy={'Y' if is_proxy else 'N'}, "
              f"DC={delegatecalls}, SD={selfdestructs}, C={creates}, C2={create2s}, "
              f"bal={w3.from_wei(balance, 'ether'):.4f} ETH")
    except Exception as e:
        print(f"  {name:25s}: Error - {str(e)[:50]}")

# Cross-chain comparison: same token on different chains
print(f"\n  Cross-chain token comparison:")
if "base" in providers:
    base_w3 = providers["base"]
    
    tokens = {
        "USDC": {
            "ethereum": "0xA0b86991c627Ce246199B89fF4b35b54C5c85687",
            "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        },
        "WETH": {
            "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "base": "0x4200000000000000000000000000000000000006",
        },
    }
    
    erc20_abi = json.loads('[{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')
    
    for token_name, addrs in tokens.items():
        for chain_name, addr in addrs.items():
            try:
                prov = providers[chain_name]
                token = prov.eth.contract(address=Web3.to_checksum_address(addr), abi=erc20_abi)
                supply = token.functions.totalSupply().call()
                dec = token.functions.decimals().call()
                code = prov.eth.get_code(Web3.to_checksum_address(addr))
                print(f"    {token_name} on {chain_name:10s}: supply={supply/10**dec:>18,.0f}, code={len(code)}B")
            except Exception as e:
                print(f"    {token_name} on {chain_name:10s}: {str(e)[:50]}")

# ============================================================
# 2. MEV BUNDLE ANALYSIS
# ============================================================
print("\n" + "="*60)
print("2. MEV BUNDLE ANALYSIS")
print("="*60)

# Analyze block for MEV patterns
block = w3.eth.get_block(latest, full_transactions=True)
txs = block['transactions']
coinbase = block['miner']

print(f"  Block {latest}: {len(txs)} txs, builder={coinbase[:14]}...")

# Pattern 1: Direct ETH transfers to builder (bribes)
bribes = [tx for tx in txs if tx['to'] and tx['to'].lower() == coinbase.lower() and tx['value'] > 0]
print(f"  Builder bribes: {len(bribes)}")
for b in bribes[:3]:
    print(f"    {w3.from_wei(b['value'], 'ether'):.6f} ETH from {b['from'][:14]}...")

# Pattern 2: Consecutive txs from same sender (atomic arb)
sender_txs = defaultdict(list)
for i, tx in enumerate(txs):
    sender_txs[tx['from']].append((i, tx))

multi_tx_senders = {s: txlist for s, txlist in sender_txs.items() if len(txlist) >= 3}
print(f"\n  Multi-tx senders (3+): {len(multi_tx_senders)}")
for sender, txlist in sorted(multi_tx_senders.items(), key=lambda x: -len(x[1]))[:5]:
    total_value = sum(tx['value'] for _, tx in txlist)
    indices = [i for i, _ in txlist]
    consecutive = all(indices[j+1] - indices[j] <= 2 for j in range(len(indices)-1))
    print(f"    {sender[:14]}... : {len(txlist)} txs, indices={indices[:5]}{'...' if len(indices)>5 else ''}, "
          f"consecutive={'Y' if consecutive else 'N'}, value={w3.from_wei(total_value, 'ether'):.4f} ETH")

# Pattern 3: Frontrun detection (high gas + swap before victim)
SWAP_TOPIC = "0x" + Web3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex().replace("0x","")

swap_txs = []
for i, tx in enumerate(txs):
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    swaps = [l for l in receipt['logs'] if l['topics'] and l['topics'][0].hex() == SWAP_TOPIC.replace("0x","")]
    if swaps:
        gas_price = tx.get('gasPrice', tx.get('maxFeePerGas', 0))
        swap_txs.append({'index': i, 'tx': tx, 'swaps': swaps, 'gas': gas_price, 'from': tx['from']})

print(f"\n  Swap txs: {len(swap_txs)}")

# Find potential sandwiches: same sender, buy then sell
sender_swaps = defaultdict(list)
for st in swap_txs:
    sender_swaps[st['from']].append(st)

sandwiches = 0
for sender, sts in sender_swaps.items():
    if len(sts) >= 2:
        first = sts[0]
        last = sts[-1]
        # Check same pair
        if first['swaps'][0]['address'] == last['swaps'][0]['address']:
            # Decode directions
            def decode_swap(log):
                data = log['data'].hex().replace('0x','')
                return {
                    'a0in': int(data[0:64], 16), 'a1in': int(data[64:128], 16),
                    'a0out': int(data[128:192], 16), 'a1out': int(data[192:256], 16),
                }
            fs = decode_swap(first['swaps'][0])
            ls = decode_swap(last['swaps'][0])
            
            # Buy: a0in>0, a1out>0; Sell: a1in>0, a0out>0
            if fs['a0in'] > 0 and fs['a1out'] > 0 and ls['a1in'] > 0 and ls['a0out'] > 0:
                victims = [st for st in swap_txs if st['index'] > first['index'] and st['index'] < last['index']]
                profit = ls['a0out'] - fs['a0in']
                sandwiches += 1
                print(f"  !! SANDWICH: {sender[:14]}...")
                print(f"     Buy tx#{first['index']}, Sell tx#{last['index']}, Victims: {len(victims)}")
                print(f"     Profit (token0): {profit}")

if sandwiches == 0:
    print(f"  No sandwiches detected in this block")

# Pattern 4: Gas price analysis (frontrunners pay more)
gas_prices = [(tx, tx.get('gasPrice', tx.get('maxFeePerGas', 0))) for tx in txs]
gas_prices.sort(key=lambda x: -x[1])
print(f"\n  Top gas prices:")
for tx, gp in gas_prices[:5]:
    print(f"    {w3.from_wei(gp, 'gwei'):.2f} gwei from {tx['from'][:14]}... to {(tx['to'] or 'CREATE')[:14]}...")

# ============================================================
# 3. CONTROL FLOW GRAPH RECONSTRUCTION
# ============================================================
print("\n" + "="*60)
print("3. CONTROL FLOW GRAPH RECONSTRUCTION")
print("="*60)

KILN = Web3.to_checksum_address("0x0A7272e8573aea8359FEC143ac02AED90F822bD0")
code = w3.eth.get_code(KILN)
code_bytes = bytes.fromhex(code.hex().replace('0x',''))

# Full disassembly
OPCODES = {
    0x00:'STOP',0x01:'ADD',0x02:'MUL',0x03:'SUB',0x04:'DIV',
    0x10:'LT',0x11:'GT',0x14:'EQ',0x15:'ISZERO',0x16:'AND',0x17:'OR',
    0x20:'KECCAK256',0x30:'ADDRESS',0x31:'BALANCE',0x33:'CALLER',0x34:'CALLVALUE',
    0x35:'CALLDATALOAD',0x36:'CALLDATASIZE',0x37:'CALLDATACOPY',
    0x50:'POP',0x51:'MLOAD',0x52:'MSTORE',0x54:'SLOAD',0x55:'SSTORE',
    0x56:'JUMP',0x57:'JUMPI',0x5b:'JUMPDEST',
    0xf1:'CALL',0xf3:'RETURN',0xf4:'DELEGATECALL',0xfa:'STATICCALL',
    0xfd:'REVERT',0xff:'SELFDESTRUCT',
}
for i in range(32): OPCODES[0x60+i] = f'PUSH{i+1}'
for i in range(16): OPCODES[0x80+i] = f'DUP{i+1}'
for i in range(16): OPCODES[0x90+i] = f'SWAP{i+1}'
for i in range(5):  OPCODES[0xa0+i] = f'LOG{i}'

ops = []
i = 0
while i < len(code_bytes):
    op = code_bytes[i]
    name = OPCODES.get(op, f'DATA_{op:02x}')
    if 0x60 <= op <= 0x7f:
        n = op - 0x5f
        data = code_bytes[i+1:i+1+n].hex()
        ops.append((i, name, data))
        i += 1 + n
    else:
        ops.append((i, name, ''))
        i += 1

# Build JUMPDEST map
jumpdests = set()
for offset, name, _ in ops:
    if name == 'JUMPDEST':
        jumpdests.add(offset)

# Build basic blocks
blocks = {}
current_start = 0
current_ops = []

for i, (offset, name, data) in enumerate(ops):
    current_ops.append((offset, name, data))
    
    # Block ends at terminator
    if name in ('JUMP', 'JUMPI', 'RETURN', 'REVERT', 'STOP'):
        blocks[current_start] = {
            'start': current_start,
            'end': offset,
            'ops': current_ops,
            'terminator': name,
            'size': len(current_ops),
        }
        # Next block starts at next instruction
        if i + 1 < len(ops):
            current_start = ops[i+1][0]
        current_ops = []

# Build edges
edges = []
for start, block in blocks.items():
    term = block['terminator']
    last_op = block['ops'][-1]
    
    if term == 'JUMP':
        # Find PUSH before JUMP for target
        for j in range(len(block['ops'])-2, -1, -1):
            if block['ops'][j][1].startswith('PUSH') and block['ops'][j][2]:
                target = int(block['ops'][j][2], 16)
                if target in jumpdests:
                    edges.append((start, target, 'jump'))
                break
    
    elif term == 'JUMPI':
        # Conditional: both fall-through and jump target
        # Fall-through
        next_offset = block['end'] + 1
        # Find next block start
        for s in sorted(blocks.keys()):
            if s > block['end']:
                edges.append((start, s, 'fall'))
                break
        
        # Jump target
        for j in range(len(block['ops'])-2, -1, -1):
            if block['ops'][j][1].startswith('PUSH') and block['ops'][j][2]:
                target = int(block['ops'][j][2], 16)
                if target in jumpdests:
                    edges.append((start, target, 'branch'))
                break

# Analyze CFG
print(f"  Instructions: {len(ops)}")
print(f"  Basic blocks: {len(blocks)}")
print(f"  Edges: {len(edges)}")
print(f"  JUMPDESTs: {len(jumpdests)}")

# Block size distribution
sizes = [b['size'] for b in blocks.values()]
print(f"  Block sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.1f}")

# Terminator distribution
terms = Counter(b['terminator'] for b in blocks.values())
print(f"  Terminators: {dict(terms)}")

# Find unreachable blocks (dead code)
reachable = set()
worklist = [0]
edge_map = defaultdict(list)
for src, dst, typ in edges:
    edge_map[src].append((dst, typ))

while worklist:
    addr = worklist.pop()
    if addr in reachable:
        continue
    reachable.add(addr)
    for dst, typ in edge_map.get(addr, []):
        if dst not in reachable:
            worklist.append(dst)
    # Fall-through for non-JUMP terminators
    if addr in blocks:
        block = blocks[addr]
        if block['terminator'] not in ('JUMP', 'RETURN', 'REVERT', 'STOP'):
            for s in sorted(blocks.keys()):
                if s > block['end'] and s not in reachable:
                    worklist.append(s)
                    break

unreachable = len(blocks) - len(reachable)
print(f"  Reachable: {len(reachable)}, Unreachable: {unreachable} ({unreachable/len(blocks)*100:.1f}% dead code)")

# Find loops (back edges)
# A back edge goes from a block to an ancestor in the DFS tree
loops = 0
for src, dst, typ in edges:
    if dst < src and typ in ('jump', 'branch'):
        loops += 1
print(f"  Back edges (loops): {loops}")

# ============================================================
# 4. REAL-TIME SECURITY SCANNER
# ============================================================
print("\n" + "="*60)
print("4. REAL-TIME SECURITY SCANNER")
print("="*60)

# Scan recent blocks for security events
security_events = {
    'large_transfers': [],
    'contract_creations': [],
    'self_destructs': [],
    'proxy_upgrades': [],
    'unusual_gas': [],
}

UPGRADED = "0x" + Web3.keccak(text="Upgraded(address)").hex().replace("0x","")

for offset in range(5):
    blk_num = latest - offset
    blk = w3.eth.get_block(blk_num, full_transactions=True)
    
    for tx in blk['transactions']:
        # Large ETH transfers
        if tx['value'] > w3.to_wei(100, 'ether'):
            security_events['large_transfers'].append({
                'block': blk_num,
                'from': tx['from'][:14],
                'to': (tx['to'] or 'CREATE')[:14],
                'value': w3.from_wei(tx['value'], 'ether'),
            })
        
        # Contract creations
        if tx['to'] is None:
            receipt = w3.eth.get_transaction_receipt(tx['hash'])
            if receipt['contractAddress']:
                code = w3.eth.get_code(receipt['contractAddress'])
                security_events['contract_creations'].append({
                    'block': blk_num,
                    'address': receipt['contractAddress'][:14],
                    'creator': tx['from'][:14],
                    'size': len(code),
                })
        
        # Unusual gas (very high gas price = potential frontrun)
        gas_price = tx.get('gasPrice', tx.get('maxFeePerGas', 0))
        if gas_price > w3.to_wei(100, 'gwei'):
            security_events['unusual_gas'].append({
                'block': blk_num,
                'from': tx['from'][:14],
                'gas': w3.from_wei(gas_price, 'gwei'),
            })

# Check for upgrades
try:
    upgrades = w3.eth.get_logs({
        'fromBlock': latest - 100,
        'toBlock': 'latest',
        'topics': [UPGRADED]
    })
    for u in upgrades:
        security_events['proxy_upgrades'].append({
            'block': u['blockNumber'],
            'proxy': u['address'][:14],
            'impl': Web3.to_checksum_address('0x' + u['topics'][1].hex()[-40:])[:14],
        })
except:
    pass

print(f"  Security scan (5 blocks):")
for event_type, events in security_events.items():
    print(f"    {event_type}: {len(events)}")
    for e in events[:3]:
        details = ', '.join(f"{k}={v}" for k, v in e.items())
        print(f"      {details}")

# ============================================================
# 5. ADVANCED: Contract Interaction Graph
# ============================================================
print("\n" + "="*60)
print("5. CONTRACT INTERACTION GRAPH")
print("="*60)

# Build a graph of contract interactions from recent txs
interaction_graph = defaultdict(lambda: defaultdict(int))

for tx in block['transactions'][:100]:
    if tx['to']:
        receipt = w3.eth.get_transaction_receipt(tx['hash'])
        for log in receipt['logs']:
            caller = tx['to'][:10]
            target = log['address'][:10]
            if caller != target:
                interaction_graph[caller][target] += 1

# Find most connected contracts
connectivity = {}
for caller, targets in interaction_graph.items():
    connectivity[caller] = len(targets)

top_connected = sorted(connectivity.items(), key=lambda x: -x[1])[:10]
print(f"  Most connected contracts (by unique targets):")
for addr, count in top_connected:
    total_events = sum(interaction_graph[addr].values())
    print(f"    {addr}... : {count} unique targets, {total_events} events")

# Find hub contracts (interacted with by many callers)
hub_scores = defaultdict(int)
for caller, targets in interaction_graph.items():
    for target in targets:
        hub_scores[target] += 1

top_hubs = sorted(hub_scores.items(), key=lambda x: -x[1])[:10]
print(f"\n  Hub contracts (most callers):")
for addr, count in top_hubs:
    print(f"    {addr}... : {count} unique callers")

# ============================================================
# 6. ADVANCED: Storage Diff Forensics
# ============================================================
print("\n" + "="*60)
print("6. STORAGE DIFF FORENSICS")
print("="*60)

# Track storage changes for a specific contract across blocks
USDT = Web3.to_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")

# Read key slots at multiple blocks
slots = {
    "owner (0)": 0,
    "totalSupply (1)": 1,
    "balances base (2)": 2,
    "allowances base (3)": 3,
}

block_range = range(latest - 20, latest + 1, 5)
print(f"  USDT storage across blocks:")
for slot_name, slot_num in slots.items():
    values = []
    for blk in block_range:
        raw = w3.eth.get_storage_at(USDT, slot_num, block_identifier=blk)
        val = int(raw.hex(), 16)
        values.append((blk, val))
    
    # Check for changes
    changed = any(v[1] != values[0][1] for v in values)
    if changed:
        print(f"    {slot_name}: CHANGED")
        for blk, val in values:
            print(f"      Block {blk}: {val}")
    else:
        print(f"    {slot_name}: stable ({values[0][1]})")

# ============================================================
# 7. ADVANCED: Event Signature Database
# ============================================================
print("\n" + "="*60)
print("7. EVENT SIGNATURE DATABASE")
print("="*60)

# Build comprehensive event DB
EVENT_DB = {}
event_sigs = [
    "Transfer(address,address,uint256)", "Approval(address,address,uint256)",
    "Deposit(address,uint256)", "Withdrawal(address,uint256)",
    "Sync(uint112,uint112)", "Swap(address,uint256,uint256,uint256,uint256,address)",
    "Mint(address,uint256)", "Burn(address,uint256)",
    "OwnershipTransferred(address,address)", "Upgraded(address)",
    "AdminChanged(address,address)", "Paused(address)", "Unpaused(address)",
    "Deposit(address indexed caller, address indexed withdrawer, bytes publicKey, bytes signature)",
    "ValidatorKeysAdded(uint256 indexed operatorIndex, bytes publicKeys, bytes signatures)",
    "ValidatorKeyRemoved(uint256 indexed operatorIndex, bytes publicKey)",
    "ChangedWithdrawer(bytes publicKey, address newWithdrawer)",
    "ChangedGlobalFee(uint256 newGlobalFee)", "ChangedOperatorFee(uint256 newOperatorFee)",
    "ChangedAdmin(address newAdmin)", "ChangedTreasury(address newTreasury)",
    "ExitRequest(address caller, bytes pubkey)",
    "NewOperator(address operatorAddress, address feeRecipientAddress, uint256 index)",
    "DeactivatedOperator(uint256 _operatorIndex)", "ActivatedOperator(uint256 _operatorIndex)",
    "SetWithdrawerCustomizationStatus(bool _status)",
    "ChangedDepositsStopped(bool isStopped)",
    "Withdrawal(address indexed withdrawer, address indexed feeRecipient, bytes32 pubKeyRoot, uint256 rewards, uint256 nodeOperatorFee, uint256 treasuryFee)",
    "PairCreated(address,address,address,uint256)",
    "FlashLoan(address,address,address,uint256,uint8,uint256,uint16)",
    "ReserveDataUpdated(address,uint256,uint256,uint256,uint256,uint256)",
    "Borrow(address,address,uint256,uint8,uint256)",
    "Repay(address,address,uint256)",
    "LiquidationCall(address,address,address,uint256,bool)",
]
for sig in event_sigs:
    topic = Web3.keccak(text=sig).hex()
    EVENT_DB[topic] = sig

print(f"  Event DB: {len(EVENT_DB)} signatures")

# Scan recent block and decode ALL events
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

print("\n✓ IMMORTAL DRILL 1 COMPLETE")
