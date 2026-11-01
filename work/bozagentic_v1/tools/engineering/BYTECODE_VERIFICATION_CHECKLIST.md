# BYTECODE VERIFICATION CHECKLIST
# BOZAGENTIC | For every deployed contract audit

---

## STEP 1: IDENTIFY CONTRACT

```bash
# Get bytecode
cast code <address> --rpc-url <rpc>

# Check if proxy
cast storage <address> 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc --rpc-url <rpc>

# Check if ERC-1167 clone
# Prefix: 363d3d373d3d3d363d73 (10 bytes)
# Impl: bytes 10-29 (20 bytes)
# Suffix: 5af43d82803e903d91602b57fd5bf3 (15 bytes)
# Total: 45 bytes
```

## STEP 2: EXTRACT SELECTORS

```bash
# From deployed bytecode
cast code <address> | grep -oP '(?<=8063)[0-9a-f]{8}(?=14)' | sort -u

# From local build
forge inspect <Contract> methodIdentifiers

# Cross-reference: ALL local selectors must exist in deployed
# If deployed has EXTRA selectors → deployed is NEWER than repo
# If deployed MISSING selectors → deployed is OLDER than repo
```

## STEP 3: VERIFY SOURCE

```bash
# Blockscout API
curl "https://base.blockscout.com/api/v2/smart-contracts/<address>"

# Check: is_verified, compiler_version, source_code
# Save source locally for audit
# Compare with GitHub repo (may differ!)
```

## STEP 4: DECODE STORAGE

```bash
# Storage layout
forge inspect <Contract> storageLayout

# Read specific slots
cast storage <address> <slot> --rpc-url <rpc>

# Nested mapping slot calculation
# mapping(address => mapping(bytes32 => uint256)) at slot N:
#   level1 = keccak256(abi.encode(key1, N))
#   level2 = keccak256(abi.encode(key2, level1))
#   value = sload(level2)
```

## STEP 5: VERIFY PATTERNS

```
□ Reentrancy guard: SLOAD/SSTORE or TLOAD/TSTORE with guard slot
□ Proxy pattern: EIP-1967 slot or ERC-1167 prefix
□ Transient storage: TSTORE/TLOAD (EIP-1153, Cancun+)
□ CREATE2: keccak256(0xff ++ deployer ++ salt ++ initcode)
□ Immutables: in bytecode (not storage), check via forge inspect
□ Events: decode topics[0] = event signature hash
```

## STEP 6: DECODE TRANSACTIONS

```bash
# Get recent txs
cast logs --from-block X --to-block Y --address <contract> --rpc-url <rpc>

# Decode tx input
cast tx <hash> --rpc-url <rpc>  # get input field
cast 4byte <selector>           # identify function
cast calldata-decode "func(types)" <data>  # decode params

# Decode events
# topics[0] = event signature
# topics[1:] = indexed params
# data = non-indexed params (ABI-encoded)
```

## RED FLAGS

```
🔴 Deployed selectors ≠ GitHub repo → AUDIT DEPLOYED VERSION
🔴 Proxy without verified implementation → can't audit
🔴 Storage layout mismatch → upgrade bug
🔴 Missing reentrancy guard in bytecode → vulnerable
🔴 Selfdestruct opcode (0xff) in bytecode → forced ether risk
🔴 Delegatecall to non-immutable address → storage hijack
```
