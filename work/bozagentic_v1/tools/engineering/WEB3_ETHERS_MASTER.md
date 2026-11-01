# WEB3.PY & ETHERS.JS MASTERY REFERENCE
# BOZAGENTIC v7 BOZAGENTIC — On-Chain Analysis Toolkit

## INSTALL
```bash
pip install web3          # v7.16+
npm install ethers        # v6.17+
```

## WEB3.PY CHEAT SHEET

### Provider
```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com"))
w3.is_connected()
w3.eth.chain_id
w3.eth.block_number
w3.client_version
```

### Account
```python
w3.eth.get_balance(addr)                    # wei
w3.eth.get_transaction_count(addr)          # nonce
w3.eth.get_code(addr)                       # bytecode (b'' = EOA)
w3.from_wei(balance, 'ether')               # format
Web3.to_checksum_address(addr)              # checksum
```

### Block & Tx
```python
block = w3.eth.get_block('latest')          # or block number
tx = w3.eth.get_transaction(tx_hash)
receipt = w3.eth.get_transaction_receipt(tx_hash)
```

### Contract
```python
import json
abi = json.loads('[...]')
contract = w3.eth.contract(address=addr, abi=abi)
result = contract.functions.name().call()
result = contract.functions.balanceOf(addr).call()
```

### Events
```python
# v7: topics MUST have 0x prefix
TRANSFER = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().replace("0x","")
logs = w3.eth.get_logs({
    'fromBlock': latest - 100,
    'toBlock': 'latest',
    'address': contract_addr,
    'topics': [TRANSFER]                    # topic0 filter
    # 'topics': [TRANSFER, padded_addr]     # topic0 + topic1 (from)
})
# Decode: from = '0x' + log['topics'][1].hex()[-40:]
#         value = int(log['data'].hex(), 16)
```

### Storage Reading (SECURITY CRITICAL)
```python
# Raw slot
w3.eth.get_storage_at(addr, slot_number)

# Mapping: mapping(address => uint256) at slot N
def mapping_slot(key_addr, base_slot):
    key = bytes.fromhex(key_addr[2:].lower().zfill(64))
    slot = base_slot.to_bytes(32, 'big')
    return Web3.keccak(key + slot)

# Nested: mapping(address => mapping(address => uint256)) at slot N
def nested_slot(owner, spender, base_slot):
    inner = mapping_slot(owner, base_slot)
    key = bytes.fromhex(spender[2:].lower().zfill(64))
    return Web3.keccak(key + inner)

# Array: element i of array at slot N
# slot = keccak256(N) + i

# Struct: field offset from base slot
```

### Proxy Detection
```python
# EIP-1967
IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
impl = w3.eth.get_storage_at(proxy, IMPL_SLOT)
impl_addr = Web3.to_checksum_address('0x' + impl.hex()[-40:])

# ERC-1167 minimal proxy: bytecode contains 363d3d373d3d3d363d73
code = w3.eth.get_code(addr)
is_clone = '363d3d373d3d3d363d73' in code.hex()

# NOTE: Some proxies (TUPProxy) use custom slots, not EIP-1967!
# Always check bytecode for DELEGATECALL (f4) pattern
```

### Utilities
```python
Web3.keccak(text="Transfer(address,address,uint256)")  # event topic
Web3.keccak(text="StakingContract.globalFee")           # storage slot
Web3.to_wei(1, 'ether')                                 # 10**18
Web3.from_wei(10**18, 'ether')                          # 1.0
```

## ETHERS.JS CHEAT SHEET

### Provider
```javascript
const { ethers } = require("ethers");
const provider = new ethers.JsonRpcProvider("https://ethereum-rpc.publicnode.com");
await provider.getBlockNumber();
await provider.getNetwork();  // { chainId, name }
```

### Account
```javascript
await provider.getBalance(addr);              // BigInt wei
await provider.getTransactionCount(addr);     // nonce
await provider.getCode(addr);                 // "0x" = EOA
ethers.formatEther(balance);                  // format
ethers.getAddress(addr);                      // checksum (STRICT!)
```

### Block & Tx
```javascript
const block = await provider.getBlock("latest");        // or number
const block = await provider.getBlock("latest", true);  // prefetch txs
const tx = await provider.getTransaction(hash);
const receipt = await provider.getTransactionReceipt(hash);
```

### Contract
```javascript
const abi = ["function balanceOf(address) view returns (uint256)",
             "event Transfer(address indexed from, address indexed to, uint256 value)"];
const contract = new ethers.Contract(addr, abi, provider);
await contract.balanceOf(addr);
```

### Events
```javascript
// Query past events
const events = await contract.queryFilter("Transfer", fromBlock, toBlock);
// Filtered
const filter = contract.filters.Transfer(null, toAddr);  // to = specific
const events = await contract.queryFilter(filter, from, to);
// Parse event args
event.args.from, event.args.to, event.args.value
```

### ABI Encoding/Decoding (SECURITY CRITICAL)
```javascript
const iface = new ethers.Interface(abi);
// Encode
const calldata = iface.encodeFunctionData("balanceOf", [addr]);
// Decode
const decoded = iface.parseTransaction({ data: calldata });
decoded.name;    // "balanceOf"
decoded.args[0]; // address
// Event topic
iface.getEvent("Transfer").topicHash;
// Selector
calldata.slice(0, 10);  // "0x70a08231"
```

### Storage Reading
```javascript
await provider.getStorage(addr, slot);  // slot = number or hex string

// Mapping slot calculation
const slot = ethers.keccak256(
    ethers.AbiCoder.defaultAbiCoder().encode(["address","uint256"], [key, baseSlot])
);
```

### Proxy Detection
```javascript
const EIP1967_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
const implRaw = await provider.getStorage(proxy, EIP1967_IMPL);
const implAddr = ethers.getAddress("0x" + implRaw.slice(26));
```

### CREATE2 Prediction
```javascript
ethers.getCreate2Address(deployer, salt, initCodeHash);
```

### Utilities
```javascript
ethers.id("Transfer(address,address,uint256)");     // keccak256
ethers.parseEther("1.5");                           // BigInt wei
ethers.formatEther(1500000000000000000n);           // "1.5"
ethers.solidityPackedKeccak256(["address","uint256"], [addr, 0]);
ethers.Wallet.createRandom();                       // new wallet
```

## SECURITY AUDIT PATTERNS

### 1. Verify deployed vs source
```python
# Compare bytecode hash
deployed = w3.eth.get_code(addr)
# Compare with forge inspect output
```

### 2. Read proxy implementation
```python
# EIP-1967, ERC-1167, or custom (TUPProxy)
# Check DELEGATECALL in bytecode
```

### 3. Decode suspicious transactions
```python
selector = tx['input'].hex()[:10]
# Match against known signatures
# Decode params with ABI
```

### 4. Monitor events for anomalies
```python
# Large transfers, unusual patterns
# Track specific addresses via topic filters
```

### 5. Storage layout verification
```python
# Calculate expected slot for mapping/array
# Compare with actual storage value
# Verify access control state (admin, paused, etc.)
```

## PITFALLS
- web3.py v7: topics MUST have 0x prefix
- ethers.js v6: getAddress() is STRICT checksum (use lowercase input)
- Proxy storage: implementation has NO state, all state in proxy
- TUPProxy: custom pause slot, NOT standard EIP-1967
- Public RPCs: rate limited, use fallback chain
- getLogs: block range limited (~10K blocks on public RPCs)
- ENS: requires mainnet provider with ENS support

## RPC ENDPOINTS (public, no key)
```
Ethereum: https://ethereum-rpc.publicnode.com  (rate limited ~50 calls)
          https://1rpc.io/eth                  (getLogs limited to 5 blocks)
          https://rpc.ankr.com/eth             (NOW REQUIRES API KEY!)
Base:     https://mainnet.base.org             (works, no key)
          https://base-rpc.publicnode.com
```

## DEEP DRILL RESULTS

### EVM Disassembler (web3.py)
- Full opcode map: 0x00-0xff with PUSH1-32, DUP1-16, SWAP1-16, LOG0-4
- Selector extraction: scan for PUSH4 + EQ pattern in dispatcher
- USDT: 32 selectors found, 11 matched known signatures
- Storage layout: slot 0=owner, 1=totalSupply, 7=name, 8=symbol, 9=decimals

### Proxy Detection (ALL types)
- ERC-1167: bytecode contains `363d3d373d3d3d363d73` + 20-byte impl addr
- EIP-1967: storage slot `0x3608...2bbc` (Transparent/UUPS)
- EIP-1967 Beacon: slot `0xa3f0...3d50`
- Legacy: slot 0 or 1 contains address
- Custom: has DELEGATECALL (f4) in bytecode but no standard slot
- Kiln: 0x0A72... detected as ERC-1167 (false positive from bytecode pattern)
- Kiln Proxy 0x1e68...: 0 bytes bytecode = NOT deployed or wrong address!

### Security Forensics
- Reentrancy: check log ordering (same sender multiple Transfer in 1 tx)
- Unlimited approvals: value >= MAX_UINT/2
- Flash loans: Aave V3 FlashLoan event topic
- Bot detection: nonce > 100,000
- Self-destruct: code becomes 0x after tx
- Whale tracking: tx.value > 100 ETH
- MEV sandwich: same sender, multiple swaps in same block

### Ethers.js Advanced
- Multicall3: `aggregate3.staticCall(calls)` for batch reads
- EIP-191: `wallet.signMessage()` + `ethers.verifyMessage()`
- EIP-712: `wallet.signTypedData()` + `ethers.verifyTypedData()`
- Raw TX: `wallet.signTransaction()` + `ethers.Transaction.from()`
- CREATE: `ethers.getCreateAddress({from, nonce})`
- CREATE2: `ethers.getCreate2Address(deployer, salt, initCodeHash)`
- Error decoding: `iface.encodeErrorResult()` + `iface.parseError()`
- Cross-chain: same ABI, different provider per chain

### Pitfalls (UPDATED)
- Ankr RPC now requires API key (2026)
- 1rpc.io: getLogs limited to 5 blocks, rate limited after ~30 calls
- publicnode.com: rate limited after ~50 calls, state override WORKS
- ethers v6: `block.logsBloom` may be undefined
- ethers v6: HDNodeWallet.fromPhrase(mnemonic, undefined, path) for derivation
- ethers v6: multicall uses `.staticCall()` not direct call
- USDC address: must use `ethers.getAddress()` for checksum
- web3.py state_override: slot keys must be full 66-char hex strings
- Kiln proxy 0x1e68...: 0 bytes = address truncated in bounty page
- Kiln EL Dispatcher 0xca4D...a7fC: 0 bytes = WRONG ADDRESS in bounty!
- Risk scoring: raw byte counting has FP (PUSH data contains 0xff etc)
- Proper disassembly MUST skip PUSH data bytes

## TRANSCENDENT SCANNER RESULTS

### Automated Scanner (both web3.py + ethers.js)
Scans: bytecode, proxy, storage, metadata, access control, selectors, risk score

| Contract | Risk | Level | Key Findings |
|----------|------|-------|-------------|
| Kiln Staking | 50 | MEDIUM | ERC-1167 FP, admin=0 (impl contract) |
| USDT | 35 | MEDIUM | Unverified, paused()=0 (bool not addr) |
| Kiln CL Dispatcher | 20 | LOW | Clean implementation |
| Wormhole | 20 | LOW | EIP-1967 proxy, 3.3 ETH |
| Hop Bridge | 15 | LOW | Holds 603 ETH |
| Multicall3 | 0 | LOW | Perfect score |

### Access Control Verification (Kiln)
ALL 11 admin functions protected:
- setGlobalFee, setOperatorFee, setTreasury → Unauthorized (0x82b42900)
- setDepositsStopped, setWithdrawerCustomization → Unauthorized
- addOperator, setOperatorLimit → Reverted
- transferOwnership → Unauthorized
- Public functions (deposit, withdraw, getters) → accessible ✓

### CFG Reconstruction (Kiln)
- 13,020 instructions, 1,136 basic blocks, 1,258 edges
- 810 JUMPDESTs, 93 back edges (loops)
- 73.3% unreachable (dispatcher padding, not dead code)
- Terminators: JUMP=615, JUMPI=371, REVERT=146, STOP=3, RETURN=1

### Cross-Chain
- Ethereum + Base connected simultaneously
- USDC: 4.16B on Base, WETH: 2.27M on Ethereum
- Bridge analysis: 8 bridges scanned (Wormhole, Stargate, Hop, Synapse, etc)

### MEV Analysis
- Sandwich detection: scan for same-sender buy+sell around victims
- Builder bribes: direct ETH to coinbase
- Bot detection: nonce > 100K, multi-tx per block
- Flash loan sim: constant product formula for price impact

### Real-Time Monitoring
- Event subscription (provider.on("block"))
- Whale alerts (Transfer > threshold)
- Mempool analysis (pending txs, gas prices)
- Security scanner (large transfers, creations, upgrades)

## COMPLETE DRILL LOG
```
web3.py:   CORE → ADVANCED → DEEP(1-8) → EXPERT → GRANDMASTER → MYTHIC → IMMORTAL(1-2) → TRANSCENDENT
ethers.js: CORE → ADVANCED → DEEP(1-5) → EXPERT → GRANDMASTER(1-2) → TRANSCENDENT
Total: 30+ drills, 80+ patterns, 16 toolkits, ~3000 lines
```


## ZENITH/HORIZON UPDATES

### CREATE2 Prediction (FIXED)
```python
# Uniswap V2 uses abi.encodePacked (20 bytes per address, NOT 32!)
salt = keccak256(token0_bytes20 ++ token1_bytes20)  # NOT zfill(64)!
address = keccak256(0xff ++ factory ++ salt ++ initCodeHash)[-20:]
# VERIFIED: DAI/WETH pair prediction = PASS
```

### Advanced Reentrancy Patterns
1. Classic CEI: CALL before SSTORE (DAO hack)
2. Read-only: CALL then STATICCALL (Curve hack)
3. Self-call: ADDRESS + CALL (recursive)
4. Delegate-after-call: CALL then DELEGATECALL (state corruption)

### ERC-4337 Account Abstraction
- EntryPoint v0.6: 0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789
- EntryPoint v0.7: 0x0000000071727De22E5E9d8BAf0edAc6f37da032
- Detection: type 4 txs, UserOperationEvent logs
- Bundler detection: tx.to == EntryPoint

### EIP-4844 Blob Analysis
- Type 3 txs carry blobVersionedHashes
- Each blob = 131,072 bytes (128 KB)
- Blob gas = 2^17 per blob
- Track: blobGasUsed, excessBlobGas per block

### ERC-7201 Namespaced Storage
- slot = keccak256(abi.encode(keccak256(ns) - 1)) & ~0xff
- Used by OpenZeppelin v5+ upgradeable contracts
- Kiln uses custom keccak-based (pre-standard, but safe)

### Flash Loan Attack Simulation
- Read real reserves from Uniswap V2 pairs
- Calculate price impact: constant product formula
- Model: flash loan → dump → borrow at manipulated price → profit
- Key insight: manipulation alone ≠ profit, need vulnerable oracle

### Governance Attack Simulation
- State override to simulate admin compromise
- Test all admin functions for damage potential
- Kiln: fee capped (InvalidFee guard), 2-step ownership transfer
