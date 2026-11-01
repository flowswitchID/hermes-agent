# MEV & CROSS-PROTOCOL ATTACK MASTER
# BOZAGENTIC | 2026-08-01
# Tujuan: Front-running, sandwich, cross-protocol interaction bugs

---

## 1. MEV (Maximal Extractable Value)

### Types of MEV:

```
TYPE              | MECHANISM                    | PROFIT SOURCE
══════════════════|══════════════════════════════|══════════════════
Sandwich          | Frontrun + backrun user swap | Slippage
Arbitrage         | Price diff across DEXs       | Price inefficiency
Liquidation       | Race to liquidate positions  | Liquidation bonus
JIT Liquidity     | Add/remove LP around swap    | Fee capture
Oracle frontrun   | Update oracle before tx      | Stale price exploit
Governance        | Frontrun proposal/vote       | Policy manipulation
```

### Sandwich Attack — Detail:

```
Victim: swap 100 ETH → USDC on Uniswap (slippage 1%)

Attacker tx1 (BEFORE victim):
  Buy USDC with 1000 ETH → pushes price up

Victim tx (MIDDLE):
  Swap 100 ETH → USDC at WORSE price (higher)

Attacker tx2 (AFTER victim):
  Sell USDC → ETH at inflated price

Profit = victim's extra slippage × attacker's volume
```

### Audit Questions for MEV:

```
1. "Can user tx be sandwiched?" → check slippage protection
2. "Can oracle update be frontrun?" → check commit-reveal
3. "Can liquidation be raced?" → check liquidation mechanism
4. "Can LP add/remove be JIT'd?" → check fee distribution timing
5. "Can governance vote be frontrun?" → check snapshot mechanism
```

### Protection Patterns:

```solidity
// 1. Slippage protection
function swap(uint256 amountIn, uint256 minAmountOut) external {
    uint256 amountOut = _executeSwap(amountIn);
    require(amountOut >= minAmountOut, "Slippage exceeded");
}

// 2. Commit-reveal for oracle
function commit(bytes32 hash) external {
    commits[msg.sender] = Commit(hash, block.number);
}
function reveal(uint256 value, bytes32 salt) external {
    require(keccak256(abi.encode(value, salt)) == commits[msg.sender].hash);
    require(block.number > commits[msg.sender].block + MINIMUM_DELAY);
    // Now use value
}

// 3. Flashbots Protect / private mempool
// User submits tx directly to block builder, bypassing public mempool
```

---

## 2. CROSS-PROTOCOL INTERACTION BUGS

### The Meta-Pattern:

```
Protocol A assumes X about Protocol B.
Protocol B changes X (upgrade, exploit, edge case).
Protocol A breaks because assumption violated.

90% of cross-protocol bugs = VIOLATED ASSUMPTIONS.
```

### Common Assumptions That Break:

```
ASSUMPTION                          | HOW IT BREAKS
════════════════════════════════════|══════════════════════════════════
"Token balance only changes on      | Rebase tokens, fee-on-transfer,
 transfer/transferFrom"             | rebasing (stETH, aTokens)

"Token has 18 decimals"            | USDC (6), WBTC (8), custom

"Token transfer returns bool"       | USDT returns nothing

"Oracle price is always fresh"      | Oracle down, stale, manipulated

"External contract won't upgrade"   | Proxy upgrade changes behavior

"Callback won't re-enter"           | ERC777, ERC1363 hooks

"Pool ratio reflects true price"    | Flash loan manipulates ratio

"Admin won't rug"                   | Admin key compromised

"Bridge message is authentic"       | Signature verification bypass
```

### Real Cross-Protocol Bugs:

#### Bug 1: Aave + Fee-on-transfer Token
```
Aave assumes: amount received == amount sent
Fee-on-transfer: amount received == amount sent - fee

Result: Aave records deposit of X, but only has X - fee
        → Protocol becomes insolvent
        → Last withdrawer gets less

Audit check: "Does this protocol handle fee-on-transfer tokens?"
```

#### Bug 2: Uniswap V3 + Rebase Token
```
Uniswap V3 assumes: liquidity is constant unless mint/burn
Rebase token: balance changes without mint/burn

Result: Pool accounting breaks
        → LP positions worth less than expected

Audit check: "Does this AMM handle rebasing tokens?"
```

#### Bug 3: Lending + Flash Loan Governance
```
Lending protocol: deposit → receive governance tokens
Governance: vote on proposals

Flash loan: deposit → vote → withdraw in 1 tx
Result: Governance captured without capital at risk

Audit check: "Can governance power be acquired and used in 1 tx?"
```

#### Bug 4: Bridge + Optimistic Verification
```
Bridge: message valid unless challenged within 7 days
Attacker: submit fake message + prevent challenges (DoS)
Result: Fake message accepted after timeout

Audit check: "Can the challenge mechanism be DoS'd?"
```

#### Bug 5: Oracle + Lending Liquidation
```
Oracle: updates price every heartbeat (1 hour)
Between updates: price is stale

Attacker: wait for market crash → liquidate at stale (high) price
Result: Borrower liquidated unfairly

Audit check: "What happens if oracle is stale during volatility?"
```

---

## 3. CROSS-PROTOCOL AUDIT FRAMEWORK

### Step-by-step:

```
STEP 1: Map all external dependencies
  → What contracts does this protocol CALL?
  → What contracts CALL this protocol?
  → What tokens does it hold?
  → What oracles does it read?

STEP 2: List assumptions about each dependency
  → "We assume token X has 18 decimals"
  → "We assume oracle Y updates every hour"
  → "We assume contract Z won't upgrade"

STEP 3: Break each assumption
  → "What if token X has 6 decimals?"
  → "What if oracle Y is 24 hours stale?"
  → "What if contract Z upgrades to malicious code?"

STEP 4: Check if breaking the assumption is profitable
  → Cost to break vs profit from breaking
  → If profit > cost → BUG

STEP 5: Check if there's a safeguard
  → Validation, bounds check, circuit breaker
  → If no safeguard → CRITICAL/HIGH
```

### Interaction Matrix Template:

```
For protocol with N external dependencies:

         | Token A | Token B | Oracle | DEX | Bridge |
═════════|═════════|═════════|════════|═════|════════|
Deposit  | ✓       | ✓       |        |     |        |
Withdraw | ✓       | ✓       |        | ✓   |        |
Liquidate|         |         | ✓      | ✓   |        |
Bridge   |         |         |        |     | ✓      |

For each ✓: "What if this dependency misbehaves?"
```

---

## 4. SPEED READING DRILL

### The 5-Minute Contract Scan:

```
MINUTE 1: Surface scan
  - Contract name, inheritance chain
  - External functions (attack surface)
  - Modifiers (access control)
  - Events (what state changes happen)

MINUTE 2: Money flow
  - Where does money come IN?
  - Where does money go OUT?
  - Who controls the flow?
  - What's the accounting?

MINUTE 3: Trust assumptions
  - Who is trusted? (admin, oracle, user)
  - What can trusted party do?
  - Can trust be violated? (key compromise, upgrade)

MINUTE 4: Edge cases
  - Zero amounts
  - Max amounts (overflow)
  - Empty arrays
  - First/last user
  - Reentrancy paths

MINUTE 5: Economic attacks
  - Flash loan: what can be done in 1 tx?
  - Donation: what breaks if balance changes unexpectedly?
  - Front-running: what tx can be sandwiched?
  - Governance: can voting be manipulated?
```

### Red Flags That Should Trigger Deep Dive:

```
🔴 balanceOf() used for accounting → inflation attack
🔴 Public sync()/update() function → donation attack
🔴 No slippage protection → sandwich
🔴 Oracle read without staleness check → manipulation
🔴 Admin can drain without limit → rug
🔴 Governance without snapshot → flash loan vote
🔴 Reward claim without time lock → flash loan claim
🔴 delegatecall to non-immutable address → storage hijack
🔴 selfdestruct in any reachable code → forced ether
🔴 tx.origin for auth → phishing
🔴 Unchecked external call return → silent failure
🔴 Loop over unbounded array → DoS
```

---

## 5. CERTORA CVL — Formal Verification Language

### Basics:

```
CVL = Certora Verification Language
Purpose: Prove properties hold for ALL possible inputs/paths

Key concepts:
  - invariant: always true
  - rule: if precondition → postcondition
  - ghost: tracking variable (not in contract)
  - hook: intercept state changes
```

### Example: Prove cap is never exceeded

```cvl
// CashbackRewards.spec

methods {
    function rewards(address, bytes32) external returns (RewardState) envfree;
    function maxRewardBasisPoints(address) external returns (uint256) envfree;
}

// Ghost: track total rewarded per payment
ghost uint256 totalRewarded {
    init_state axiom totalRewarded == 0;
}

// Hook: track when distributed or allocated changes
hook Sstore rewards[address campaign][bytes32 hash].distributed uint120 newVal (uint120 oldVal) {
    totalRewarded = totalRewarded - oldVal + newVal;
}

hook Sstore rewards[address campaign][bytes32 hash].allocated uint120 newVal (uint120 oldVal) {
    totalRewarded = totalRewarded - oldVal + newVal;
}

// Rule: total rewarded never exceeds cap
rule capNeverExceeded(address campaign, bytes32 hash) {
    uint256 bps = maxRewardBasisPoints(campaign);
    require bps > 0;
    require bps <= 10000;
    
    // After any sequence of operations:
    // totalRewarded <= paymentAmount * bps / 10000
    
    // This would FAIL for the buggy implementation
    // because SEND doesn't count allocated
}

// Invariant: allocated + distributed <= cap
invariant totalBounded(address campaign, bytes32 hash) {
    RewardState state = rewards(campaign, hash);
    uint256 bps = maxRewardBasisPoints(campaign);
    bps == 0 || (state.allocated + state.distributed) <= cap(campaign, hash)
}
```

### CVL Learning Path:

```
WEEK 1: Basics
  - Install Certora Prover (needs API key)
  - Write first spec: simple invariant
  - Run on a simple contract

WEEK 2: Intermediate
  - Ghost variables
  - Hooks for state tracking
  - Rules with preconditions

WEEK 3: Advanced
  - Quantifiers (forall, exists)
  - Multi-contract specs
  - Loop invariants

WEEK 4: Real-world
  - Write spec for CashbackRewards
  - Prove the bug exists (rule should FAIL)
  - Prove the fix works (rule should PASS)
```

### Without API Key — What You Can Do:

```
1. Read Certora's public specs on GitHub
   → github.com/Certora/examples
   → Learn patterns from real specs

2. Use Halmos as free alternative
   → Symbolic execution, similar concepts
   → No API key needed

3. Use Z3 directly
   → Most powerful, most flexible
   → Steepest learning curve

4. Read Certora contest reports
   → See how formal verification finds bugs
   → Understand what properties to prove
```

---

## 6. NOVEL BUG DISCOVERY FRAMEWORK

### How to find bugs NOBODY else found:

```
STEP 1: Read the code with FRESH EYES
  → Don't assume it's correct because others audited it
  → Don't trust previous audit reports
  → Read every line like it's the first time

STEP 2: Ask "WHAT IF" questions
  → What if this function is called twice in 1 tx?
  → What if the caller is a contract, not an EOA?
  → What if the token is malicious (callback on transfer)?
  → What if the oracle returns 0? Or max uint?
  → What if two users do this simultaneously?
  → What if admin does X then Y in wrong order?

STEP 3: Follow the MONEY
  → Where can money get stuck?
  → Where can money be extracted?
  → Where does rounding favor the attacker?
  → Where can fees be avoided?

STEP 4: Break COMPOSITION
  → What if this contract is used as a token?
  → What if this contract receives a callback?
  → What if this contract is upgraded?
  → What if a dependency is upgraded?

STEP 5: Think like an ADVERSARY
  → "I have unlimited ETH. What do I do?"
  → "I am the admin. What's the worst I can do?"
  → "I am a malicious token. What callbacks do I get?"
  → "I control the oracle. What price do I report?"
  → "I am a miner/validator. What tx ordering do I choose?"
```

### The "Nobody Checked This" Checklist:

```
□ What happens on the FIRST call ever? (empty state)
□ What happens on the LAST call? (drain state)
□ What if block.timestamp is manipulated ±15s?
□ What if gas is exactly at the limit?
□ What if calldata is malformed but valid ABI?
□ What if the same tx is included in 2 blocks? (reorg)
□ What if a contract is deployed at the same address? (CREATE2)
□ What if the chain forks and both branches are valid?
□ What if a token has multiple entry points? (ERC777)
□ What if the protocol is paused mid-operation?
```
