"""
WEB3.PY LEGENDARY DRILL: Oracle Manipulation + Governance + Flash Loan Sim + Upgrade Detection
"""
from web3 import Web3
import json
from collections import Counter

w3 = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com", request_kwargs={'timeout': 15}))
latest = w3.eth.block_number
print(f"Block: {latest}")

# === 1. FIX: PROPER SELECTOR EXTRACTION ===
print("\n=== 1. SELECTOR EXTRACTION (FIXED) ===")
KILN = Web3.to_checksum_address("0x0A7272e8573aea8359FEC143ac02AED90F822bD0")
code = w3.eth.get_code(KILN)
code_bytes = bytes.fromhex(code.hex().replace('0x',''))

# Proper disassembly
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

# Extract selectors: PUSH4 followed by EQ
selectors = set()
for i, (offset, name, data) in enumerate(ops):
    if name == 'PUSH4' and data:
        # Check if next few ops contain EQ
        for j in range(i+1, min(i+6, len(ops))):
            if ops[j][1] == 'EQ':
                selectors.add('0x' + data)
                break

# Match against known functions
KNOWN_FUNCS = [
    'deposit()', 'withdraw(bytes)', 'withdrawELFee(bytes)', 'withdrawCLFee(bytes)',
    'batchWithdraw(bytes)', 'batchWithdrawELFee(bytes)', 'batchWithdrawCLFee(bytes)',
    'requestValidatorsExit(bytes)', 'addValidators(uint256,uint256,bytes,bytes)',
    'removeValidators(uint256,uint256[])', 'addOperator(address,address)',
    'setOperatorLimit(uint256,uint256,uint256)', 'setGlobalFee(uint256)',
    'setOperatorFee(uint256)', 'setTreasury(address)', 'setDepositsStopped(bool)',
    'setWithdrawerCustomizationEnabled(bool)', 'setWithdrawer(bytes,address)',
    'transferOwnership(address)', 'acceptOwnership()',
    'getAdmin()', 'getTreasury()', 'getGlobalFee()', 'getOperatorFee()',
    'getOperator(uint256)', 'getValidator(uint256,uint256)',
    'getAvailableValidatorCount()', 'getDepositsStopped()',
    'getWithdrawer(bytes)', 'getWithdrawerFromPublicKeyRoot(bytes32)',
    'getExitRequestedFromRoot(bytes32)', 'getWithdrawnFromPublicKeyRoot(bytes32)',
    'getEnabledFromPublicKeyRoot(bytes32)', 'getOperatorFeeRecipient(bytes32)',
    'getELFeeRecipient(bytes)', 'getCLFeeRecipient(bytes)', 'getPendingAdmin()',
    'initialize_1(address,address,address,address,address,address,uint256,uint256,uint256,uint256)',
    'initialize_2(uint256,uint256)', 'setOperatorAddresses(uint256,address,address)',
    'deactivateOperator(uint256,address)', 'activateOperator(uint256,address)',
    'toggleWithdrawnFromPublicKeyRoot(bytes32)',
    'DEPOSIT_SIZE()', 'PUBLIC_KEY_LENGTH()', 'SIGNATURE_LENGTH()',
    'deposit(bytes,bytes,bytes,bytes32)', 'init(address,bytes32)', 'withdraw()',
]

computed = {}
for f in KNOWN_FUNCS:
    sel = '0x' + Web3.keccak(text=f)[:4].hex()
    computed[sel] = f

matched = {s: computed[s] for s in selectors if s in computed}
unknown = [s for s in selectors if s not in computed]
print(f"  Selectors: {len(selectors)}, Matched: {len(matched)}, Unknown: {len(unknown)}")
for sel in sorted(matched.keys())[:15]:
    print(f"    {sel} = {matched[sel]}")
if unknown:
    print(f"  Unknown: {', '.join(sorted(unknown)[:5])}")

# === 2. ORACLE MANIPULATION DETECTION ===
print(f"\n=== 2. ORACLE MANIPULATION DETECTION ===")
# Check Uniswap V2 pair reserves for manipulation
# Pattern: sudden reserve changes in single tx (flash loan manipulation)

UNISWAP_V2_FACTORY = Web3.to_checksum_address("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
SYNC_TOPIC = "0x" + Web3.keccak(text="Sync(uint112,uint112)").hex().replace("0x","")

# Get recent Sync events (reserve updates)
try:
    sync_logs = w3.eth.get_logs({
        'fromBlock': latest - 5,
        'toBlock': 'latest',
        'topics': [SYNC_TOPIC]
    })
    
    # Group by pair
    pair_syncs = {}
    for log in sync_logs:
        pair = log['address']
        if pair not in pair_syncs:
            pair_syncs[pair] = []
        data = log['data'].hex().replace('0x','')
        reserve0 = int(data[0:64], 16)
        reserve1 = int(data[64:128], 16)
        pair_syncs[pair].append({
            'block': log['blockNumber'],
            'tx': log['transactionHash'].hex()[:14],
            'reserve0': reserve0,
            'reserve1': reserve1,
        })
    
    print(f"  Pairs with Sync events: {len(pair_syncs)}")
    
    # Detect manipulation: multiple syncs in same block for same pair
    for pair, syncs in pair_syncs.items():
        block_counts = Counter(s['block'] for s in syncs)
        for blk, count in block_counts.items():
            if count >= 3:
                print(f"  !! {pair[:16]}... : {count} syncs in block {blk} (potential manipulation)")
                for s in syncs:
                    if s['block'] == blk:
                        print(f"     TX {s['tx']}... r0={s['reserve0']} r1={s['reserve1']}")
    
    # Show top pairs by activity
    active_pairs = sorted(pair_syncs.items(), key=lambda x: -len(x[1]))[:5]
    print(f"\n  Most active pairs:")
    for pair, syncs in active_pairs:
        print(f"    {pair[:16]}... : {len(syncs)} syncs")
except Exception as e:
    print(f"  Rate limited: {str(e)[:60]}")

# === 3. GOVERNANCE ATTACK DETECTION ===
print(f"\n=== 3. GOVERNANCE ATTACK DETECTION ===")
# Check for governance proposal manipulation
# Pattern: large voting power changes right before proposal deadline

# Compound Governor
GOVERNOR = Web3.to_checksum_address("0xc0Da02939E1441F497fd74F78cE7Decb17B66529")
PROPOSAL_CREATED = "0x" + Web3.keccak(text="ProposalCreated(uint256,address,address[],uint256[],string[],bytes[],uint256,uint256,string)").hex().replace("0x","")

try:
    proposals = w3.eth.get_logs({
        'fromBlock': latest - 1000,
        'toBlock': 'latest',
        'address': GOVERNOR,
        'topics': [PROPOSAL_CREATED]
    })
    print(f"  Compound proposals (1000 blocks): {len(proposals)}")
except:
    print(f"  Governor query limited")

# Check for large COMP transfers (voting power accumulation)
COMP = Web3.to_checksum_address("0xc00e94Cb662C3520282E6f5717214004A7f26888")
TRANSFER = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().replace("0x","")

try:
    comp_transfers = w3.eth.get_logs({
        'fromBlock': latest - 100,
        'toBlock': 'latest',
        'address': COMP,
        'topics': [TRANSFER]
    })
    
    # Find large transfers (>10000 COMP)
    large = []
    for log in comp_transfers:
        val = int(log['data'].hex(), 16) / 10**18
        if val > 10000:
            frm = Web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
            to = Web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:])
            large.append({'from': frm[:14], 'to': to[:14], 'amount': val})
    
    print(f"  COMP transfers (100 blocks): {len(comp_transfers)}")
    print(f"  Large (>10K COMP): {len(large)}")
    for l in large[:3]:
        print(f"    {l['from']}... -> {l['to']}... : {l['amount']:,.0f} COMP")
except Exception as e:
    print(f"  COMP query: {str(e)[:60]}")

# === 4. FLASH LOAN ATTACK SIMULATION ===
print(f"\n=== 4. FLASH LOAN SIMULATION ===")
# Simulate: What if we flash loan 1000 WETH and manipulate a pool?

WETH = Web3.to_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
AAVE_V3 = Web3.to_checksum_address("0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")

# Read current WETH liquidity in Aave
weth_abi = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]')
weth = w3.eth.contract(address=WETH, abi=weth_abi)

aave_weth_bal = weth.functions.balanceOf(AAVE_V3).call()
print(f"  Aave V3 WETH liquidity: {w3.from_wei(aave_weth_bal, 'ether'):,.2f} WETH")

# Simulate price impact of flash loan on Uniswap V2
# USDC/WETH pair
USDC_WETH_PAIR = Web3.to_checksum_address("0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc")
pair_abi = json.loads('[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"type":"function"}]')
pair = w3.eth.contract(address=USDC_WETH_PAIR, abi=pair_abi)

reserves = pair.functions.getReserves().call()
reserve_usdc = reserves[0] / 10**6
reserve_weth = reserves[1] / 10**18
print(f"  USDC/WETH pair: {reserve_usdc:,.0f} USDC, {reserve_weth:,.2f} WETH")
print(f"  Current price: ${reserve_usdc / reserve_weth:.2f} / ETH")

# Simulate flash loan impact
flash_amounts = [100, 500, 1000, 5000]
print(f"\n  Flash loan price impact simulation:")
for amount in flash_amounts:
    # Sell WETH for USDC (constant product formula)
    # new_reserve_weth = reserve_weth + amount
    # new_reserve_usdc = k / new_reserve_weth
    k = reserve_usdc * reserve_weth
    new_weth = reserve_weth + amount
    new_usdc = k / new_weth
    usdc_out = reserve_usdc - new_usdc
    effective_price = usdc_out / amount
    slippage = (1 - effective_price / (reserve_usdc / reserve_weth)) * 100
    
    print(f"    {amount:5d} WETH -> {usdc_out:,.0f} USDC (price ${effective_price:.2f}, slippage {slippage:.2f}%)")

# === 5. UPGRADE DETECTION ===
print(f"\n=== 5. UPGRADE DETECTION ===")
# Check if any proxy was recently upgraded
UPGRADED_TOPIC = "0x" + Web3.keccak(text="Upgraded(address)").hex().replace("0x","")
ADMIN_CHANGED = "0x" + Web3.keccak(text="AdminChanged(address,address)").hex().replace("0x","")

# Scan for upgrade events
try:
    upgrades = w3.eth.get_logs({
        'fromBlock': latest - 500,
        'toBlock': 'latest',
        'topics': [UPGRADED_TOPIC]
    })
    print(f"  Upgraded events (500 blocks): {len(upgrades)}")
    for u in upgrades[:5]:
        proxy = u['address']
        new_impl = Web3.to_checksum_address('0x' + u['topics'][1].hex()[-40:])
        print(f"    {proxy[:16]}... -> {new_impl[:16]}... (block {u['blockNumber']})")
except Exception as e:
    print(f"  Upgrade query: {str(e)[:60]}")

# Check specific proxies
PROXIES = {
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "Kiln Staking": "0x0A7272e8573aea8359FEC143ac02AED90F822bD0",
}

EIP1967_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
for name, addr in PROXIES.items():
    impl_raw = w3.eth.get_storage_at(Web3.to_checksum_address(addr), EIP1967_IMPL)
    impl_val = int(impl_raw.hex(), 16)
    if impl_val > 0:
        impl = Web3.to_checksum_address('0x' + impl_raw.hex()[-40:])
        print(f"  {name}: proxy -> {impl}")
    else:
        # Check if it IS an implementation (not a proxy)
        code = w3.eth.get_code(Web3.to_checksum_address(addr))
        print(f"  {name}: implementation ({len(code)} bytes, not a proxy)")

# === 6. ADVANCED: Token Flow Graph ===
print(f"\n=== 6. TOKEN FLOW GRAPH ===")
# Build a directed graph of token flows in recent blocks
USDT = Web3.to_checksum_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")

try:
    transfers = w3.eth.get_logs({
        'fromBlock': latest - 3,
        'toBlock': 'latest',
        'address': USDT,
        'topics': [TRANSFER]
    })
    
    # Build flow graph
    flows = {}
    for log in transfers:
        frm = Web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
        to = Web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:])
        val = int(log['data'].hex(), 16) / 10**6
        
        key = (frm[:10], to[:10])
        flows[key] = flows.get(key, 0) + val
    
    # Top flows
    sorted_flows = sorted(flows.items(), key=lambda x: -x[1])[:10]
    total_vol = sum(int(l['data'].hex(), 16) / 10**6 for l in transfers)
    
    print(f"  USDT transfers (3 blocks): {len(transfers)}")
    print(f"  Total volume: ${total_vol:,.0f}")
    print(f"  Unique flows: {len(flows)}")
    print(f"  Top flows:")
    for (frm, to), val in sorted_flows:
        print(f"    {frm}... -> {to}... : ${val:,.0f}")
    
    # Detect circular flows (potential wash trading)
    circular = 0
    for (frm, to), val in flows.items():
        reverse = (to, frm)
        if reverse in flows:
            circular += 1
            if circular <= 3:
                print(f"  !! Circular: {frm}... <-> {to}... (${val:,.0f} / ${flows[reverse]:,.0f})")
    print(f"  Circular flows: {circular}")
except Exception as e:
    print(f"  Rate limited: {str(e)[:60]}")

# === 7. ADVANCED: Contract Age Analysis ===
print(f"\n=== 7. CONTRACT AGE ANALYSIS ===")
# New contracts are higher risk (potential rugs)
# Check creation block of recent contracts

block = w3.eth.get_block(latest, full_transactions=True)
new_contracts = []
for tx in block['transactions']:
    if tx['to'] is None:
        receipt = w3.eth.get_transaction_receipt(tx['hash'])
        if receipt['contractAddress']:
            new_contracts.append({
                'address': receipt['contractAddress'],
                'creator': tx['from'],
                'block': receipt['blockNumber'],
                'gas': receipt['gasUsed'],
            })

print(f"  New contracts in block: {len(new_contracts)}")
for nc in new_contracts[:5]:
    code = w3.eth.get_code(nc['address'])
    is_1167 = '363d3d373d3d3d363d73' in code.hex()
    print(f"    {nc['address'][:16]}... by {nc['creator'][:14]}... ({len(code)}B, {'clone' if is_1167 else 'original'})")

# === 8. ADVANCED: ETH Flow Analysis ===
print(f"\n=== 8. ETH FLOW ANALYSIS ===")
# Track ETH flows in the block
eth_flows = {}
for tx in block['transactions']:
    if tx['value'] > 0:
        frm = tx['from'][:10]
        to = (tx['to'] or 'CREATE')[:10]
        val = w3.from_wei(tx['value'], 'ether')
        key = (frm, to)
        eth_flows[key] = eth_flows.get(key, 0) + val

total_eth = sum(w3.from_wei(tx['value'], 'ether') for tx in block['transactions'])
sorted_eth = sorted(eth_flows.items(), key=lambda x: -x[1])[:5]

print(f"  Total ETH moved: {total_eth:,.2f} ETH")
print(f"  Top ETH flows:")
for (frm, to), val in sorted_eth:
    print(f"    {frm}... -> {to}... : {val:.4f} ETH")

# === 9. ADVANCED: Mempool Analysis ===
print(f"\n=== 9. MEMPOOL ANALYSIS ===")
try:
    pending = w3.eth.get_block('pending', full_transactions=True)
    pending_txs = pending['transactions']
    print(f"  Pending txs: {len(pending_txs)}")
    
    # Analyze pending txs
    high_value = [tx for tx in pending_txs if tx['value'] > w3.to_wei(10, 'ether')]
    contract_calls = [tx for tx in pending_txs if tx['to'] and len(tx['input']) > 10]
    creates = [tx for tx in pending_txs if tx['to'] is None]
    
    print(f"  High value (>10 ETH): {len(high_value)}")
    print(f"  Contract calls: {len(contract_calls)}")
    print(f"  Contract creates: {len(creates)}")
    
    # Top gas prices in mempool
    gas_prices = sorted([tx.get('gasPrice', tx.get('maxFeePerGas', 0)) for tx in pending_txs], reverse=True)
    if gas_prices:
        print(f"  Gas prices: max={w3.from_wei(gas_prices[0], 'gwei'):.1f}, median={w3.from_wei(gas_prices[len(gas_prices)//2], 'gwei'):.1f} gwei")
except Exception as e:
    print(f"  Pending block: {str(e)[:60]}")

print("\n✓ LEGENDARY DRILL COMPLETE")
