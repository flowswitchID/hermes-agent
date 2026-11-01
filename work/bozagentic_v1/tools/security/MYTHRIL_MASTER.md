# MYTHRIL MASTER — Complete Reference
# BOZAGENTIC | All modes, options, and patterns

---

## MODES

### 1. analyze (main mode)
```bash
mythril analyze contract.sol --execution-timeout 60 -t 3
```
- Symbolic execution: explores ALL possible paths
- `-t N`: max N transactions (multi-tx analysis)
- `--strategy`: dfs, bfs, naive-random, weighted-random, pending
- `--max-depth N`: limit call depth
- `-o text|json|markdown`: output format

### 2. safe-functions
```bash
mythril safe-functions contract.sol
```
- Lists functions that are PROVABLY SAFE (no issues in any path)
- Useful: if a function is NOT listed → needs manual review

### 3. disassemble
```bash
mythril disassemble -f bytecode.hex
mythril disassemble --bin-runtime -o hex < bytecode.hex
```
- Converts bytecode → human-readable opcodes
- Use with: `forge inspect Contract deployedBytecode > bytecode.hex`

### 4. concolic
```bash
mythril concolic input.json --branches 34,6f8
```
- Concolic execution: concrete + symbolic
- Flips specific branches to explore paths
- Needs: input.json with concrete transaction data
- Advanced: use after analyze finds interesting paths

### 5. read-storage
```bash
mythril read-storage "0,5" 0xADDRESS --rpc HOST:PORT
mythril read-storage "mapping,0,KEY1,KEY2" 0xADDRESS --rpc HOST:PORT
```
- Reads on-chain storage slots
- Format: "INDEX,NUM_SLOTS" or "mapping,INDEX,KEY1,KEY2..."
- RPC: HOST:PORT (NOT https:// URL!)
- Add --rpctls for HTTPS

### 6. function-to-hash
```bash
mythril function-to-hash "transfer(address,uint256)"
# → 0xa9059cbb
```
- Computes 4-byte function selector
- Use for: transaction-sequences, calldata crafting

### 7. hash-to-address
```bash
mythril hash-to-address 0xHASH
```
- Converts storage hash to address (for mapping keys)

---

## KEY OPTIONS

```
--execution-timeout N    Max seconds per analysis (default: 86400)
--solver-timeout N       Max ms per Z3 query (default: 25000)
--create-timeout N       Max seconds for contract creation
-t N                     Max transactions (1-3 typical)
--max-depth N            Max call depth
--strategy STR           dfs|bfs|naive-random|weighted-random|pending
--parallel-solving       Enable parallel Z3 solving
-b N                     Loop bound (default: 3)
--disable-coverage-strategy  Disable coverage-guided exploration
--solc-json FILE         Solc settings JSON (remappings, optimizer)
--solv VERSION           Solc version to use
-o FORMAT                text|json|markdown
```

---

## SOLC-JSON FORMAT (for Foundry projects)

```json
{
  "remappings": [
    "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
    "solady/=lib/solady/src/"
  ],
  "optimizer": {"enabled": true, "runs": 200},
  "viaIR": true
}
```

---

## DETECTORS (17 built-in)

```
DETECTOR                  | SWC | WHAT IT FINDS
══════════════════════════|═════|══════════════════════════
AccidentallyKillable      |     | selfdestruct reachable by anyone
ArbitraryJump             |     | Unrestricted JUMP instruction
ArbitraryStorage          |     | Write to arbitrary storage slot
ArbitraryDelegateCall     |     | delegatecall to user address
EtherThief                |     | Anyone can withdraw ETH
Exceptions                |     | Assertion violations
ExternalCalls             |     | External call (info)
IntegerArithmetics        |     | Overflow/underflow
MultipleSends             |     | Multiple sends in one tx
PredictableVariables      |     | block.timestamp dependence
RequirementsViolation     |     | require() can be violated
StateChangeAfterCall      |     | Reentrancy pattern
TransactionOrderDependence|     | Front-running sensitivity
TxOrigin                  |     | tx.origin authentication
UncheckedRetval           |     | Unchecked return value
UnexpectedEther           |     | Unexpected ETH balance
UserAssertions            |     | User assert() triggered
```

---

## LIMITATIONS (KNOW THESE!)

```
1. LOGIC BUGS: Mythril CANNOT detect business logic bugs
   - CashbackRewards maxRewardBps bypass → NOT detected
   - Inconsistent state tracking → NOT detected
   - Economic attacks → NOT detected

2. TIMEOUT: Complex contracts timeout
   - Flywheel.sol (692 lines) → timeout with -t 3
   - Use: --execution-timeout 120 --max-depth 10

3. SOLC VERSION: Must match contract pragma
   - Use --solv 0.8.23 for pragma 0.8.23
   - solc-bin.ethereum.org may be blocked → use GitHub releases

4. REMAPPINGS: Must use --solc-json (not --solc-args)
   - solc-args doesn't work with Standard JSON mode
   - Create settings.json with remappings array

5. FALSE POSITIVES: Many findings are noise
   - PredictableVariables: block.timestamp in deadline (normal)
   - ExternalCalls: any external call (informational)
   - StateChangeAfterCall: check for nonReentrant first
```

---

## WORKFLOW

```
1. Run analyze with -t 1 first (fast, single-tx)
2. If 0 issues → run with -t 3 (multi-tx, slower)
3. Check safe-functions → functions NOT listed need review
4. For deployed contracts: read-storage to verify state
5. For interesting paths: concolic to explore deeper
6. ALWAYS verify findings manually (high FP rate)
```

---

## LEVEL ASSESSMENT

```
BEFORE: 55% (could run, often errored)
NOW:    75% (all modes work, solc-json fixed, FP triage)
EXPERT: 90% (concolic mastery, custom modules, multi-contract)
GAP:    concolic workflow, custom detection modules
```
