# EIGENLAYER — FULL FRAMEWORK AUDIT + CODE REFERENCE
# Restaking Protocol · $15B+ TVL · 21K lines
# BOZAGENTIC · 2026-07-30
# Source: github.com/Layr-Labs/eigenlayer-contracts

---

## ARCHITECTURE

```
EigenLayer: Restaking on Ethereum
  → Stakers deposit ETH/LSTs → delegate to operators
  → Operators allocate stake to AVS (Actively Validated Services)
  → AVS can slash operators → stakers lose proportionally
  → Rewards distributed via Merkle tree claims

Core Contracts:
  DelegationManager.sol (1079 lines) — delegation + withdrawal queue
  AllocationManager.sol (1077 lines) — magnitude allocation + slashing
  RewardsCoordinator.sol (912 lines) — reward distribution (Merkle)
  StrategyManager.sol (591 lines) — deposit/withdraw shares
  EigenPod.sol (756 lines) — beacon chain proof verification
  EigenPodManager.sol (368 lines) — pod management
  EmissionsController.sol (481 lines) — reward emissions

Libraries:
  SlashingLib.sol (190 lines) — slashing math (WAD-based)
  Snapshots.sol — historical magnitude tracking
  BeaconChainProofs.sol (338 lines) — SSZ proof verification
  Merkle.sol (341 lines) — Merkle proof verification

Strategies:
  StrategyBase.sol (294 lines) — base ERC4626-like vault
  DurationVaultStrategy.sol (420 lines) — time-locked strategy
  StrategyFactory.sol (195 lines) — strategy deployment

Permissions:
  PermissionController.sol (246 lines) — role-based access
  KeyRegistrar.sol (376 lines) — operator key registration
  Pausable.sol — pause mechanism

Multichain:
  OperatorTableUpdater.sol (407 lines) — cross-chain operator table
  BN254CertificateVerifier.sol (391 lines) — BLS signature verification
  ECDSACertificateVerifier.sol (363 lines) — ECDSA verification
  CrossChainRegistry.sol (346 lines) — cross-chain registry
```

---

## KEY PATTERNS (Learn from EigenLayer)

### Pattern 1: Magnitude-Based Slashing (UNIQUE to EigenLayer)

```solidity
// Each operator has a "maxMagnitude" per strategy (starts at WAD = 1e18)
// Slashing reduces maxMagnitude proportionally
// Staker's withdrawable shares = depositShares * depositScalingFactor * slashingFactor

// slashingFactor = operatorMaxMagnitude (for ERC20 strategies)
// slashingFactor = operatorMaxMagnitude * beaconChainSlashingFactor (for beacon ETH)

// SlashingLib.calcSlashedAmount:
function calcSlashedAmount(uint256 operatorShares, uint256 prevMaxMagnitude, uint256 newMaxMagnitude)
    internal pure returns (uint256) {
    // Round UP the remaining shares → round DOWN the slashed amount
    // This favors the operator (less slashed)
    return operatorShares - operatorShares.mulDiv(newMaxMagnitude, prevMaxMagnitude, Math.Rounding.Up);
}

// WHY THIS IS CLEVER:
// → Slashing is proportional to magnitude reduction
// → Multiple slashes compound (each reduces remaining magnitude)
// → Rounding favors operator (prevents over-slashing)
// → Staker's DSF adjusts on deposit to "forgive" prior slashing
```

### Pattern 2: DepositScalingFactor (DSF) — Anti-Slashing-Griefing

```solidity
// DSF converts between deposit shares and withdrawable shares
// withdrawable = depositShares * DSF * slashingFactor

// On new deposit (prevDepositShares == 0):
//   DSF = DSF / slashingFactor
//   → "Forgives" prior slashing for new deposits
//   → New deposits start fresh (not penalized by old slashing)

// On additional deposit (prevDepositShares > 0):
//   newDSF = (currentShares + addedShares) / ((prevDepositShares + addedShares) * slashingFactor)
//   → Blends old and new shares at current slashing rate
//   → Prevents gaming by depositing/withdrawing around slashes

// WHY:
// → Without DSF: staker who deposited before slash gets penalized forever
// → With DSF: new deposits "reset" the slashing impact
// → Existing deposits maintain their proportional loss
```

### Pattern 3: Withdrawal Queue with Slashing Window

```solidity
// queueWithdrawals:
//   1. Get slashing factors at CURRENT block
//   2. Scale deposit shares → scaledShares (depositShares * DSF)
//   3. Queue withdrawal with startBlock
//   4. Shares remain SLASHABLE during MIN_WITHDRAWAL_DELAY_BLOCKS

// completeQueuedWithdrawal:
//   1. Wait for MIN_WITHDRAWAL_DELAY_BLOCKS to pass
//   2. Get slashing factors AT slashableUntil block (startBlock + delay)
//   3. Apply slashing: sharesToWithdraw = scaledShares * slashingFactor
//   4. If receiveAsTokens: withdraw tokens
//   5. If receiveAsShares: re-deposit with NEW operator's slashing factor

// WHY:
// → Prevents "slash and run" (queue withdrawal, avoid slashing)
// → Shares remain slashable during delay period
// → Slashing applied at the END of delay (not at queue time)
// → Staker can't escape slashing by queueing early
```

### Pattern 4: Allocation Delay + Deallocation Delay

```solidity
// Allocation: operator allocates magnitude to AVS operator sets
// → Allocation takes effect after operatorAllocationDelay blocks
// → New magnitude NOT slashable until delay passes

// Deallocation: operator removes magnitude from AVS
// → Deallocation takes effect after DEALLOCATION_DELAY blocks
// → Magnitude REMAINS SLASHABLE during delay
// → Prevents "slash and run" (deallocate before slash)

// modifyAllocations:
//   if (pendingDiff < 0) {  // deallocation
//     if (isSlashable) {
//       // Magnitude freed after DEALLOCATION_DELAY
//       // Still slashable until then
//       allocation.effectBlock = block.number + DEALLOCATION_DELAY + 1;
//     } else {
//       // Instant deallocation if not slashable
//     }
//   } else if (pendingDiff > 0) {  // allocation
//     // Magnitude consumed immediately
//     // But NOT slashable until allocationDelay passes
//     allocation.effectBlock = block.number + operatorAllocationDelay;
//   }
```

### Pattern 5: StrategyBase — Virtual Shares (Inflation Protection)

```solidity
// StrategyBase uses balanceOf() for accounting (like Arcadia/Basin!)
// BUT: has virtual shares + virtual balance as inflation protection

uint256 internal constant SHARES_OFFSET = 1e3;   // virtual shares
uint256 internal constant BALANCE_OFFSET = 1e3;  // virtual balance

// deposit():
uint256 virtualShareAmount = priorTotalShares + SHARES_OFFSET;
uint256 virtualTokenBalance = _tokenBalance() + BALANCE_OFFSET;
uint256 virtualPriorTokenBalance = virtualTokenBalance - amount;
newShares = (amount * virtualShareAmount) / virtualPriorTokenBalance;
require(newShares != 0, NewSharesZero());

// _tokenBalance():
function _tokenBalance() internal view virtual returns (uint256) {
    return underlyingToken.balanceOf(address(this));  // ← balanceOf!
}

// COMPARISON:
//   Arcadia: VAS = 0 → VULNERABLE
//   OZ default: virtual shares = 1 → minimal protection
//   Morpho: VIRTUAL_SHARES = 1e6 → strong protection
//   EigenLayer: SHARES_OFFSET = 1e3, BALANCE_OFFSET = 1e3 → moderate protection

// ATTACK COST ANALYSIS:
//   For victim deposit Y, attacker must donate X where:
//   X > Y * (SHARES_OFFSET + 1) - BALANCE_OFFSET - 1
//   X > Y * 1001 - 1001
//   → Attack cost ≈ 1000x victim's deposit
//   → NOT PROFITABLE for any meaningful amount
//   → But: MUCH weaker than Morpho's 1e6 (which costs 1M x)
```

### Pattern 6: Merkle-Based Reward Claims

```solidity
// RewardsCoordinator uses Merkle tree for reward distribution
// 1. rewardsUpdater submits distribution root (Merkle root)
// 2. Root has activationDelay before claims allowed
// 3. Earner submits Merkle proof: earnerLeaf + tokenLeaves
// 4. Contract verifies proof against root
// 5. Claim amount = cumulativeEarnings - cumulativeClaimed
// 6. cumulativeClaimed updated → prevents double claim

// WHY MERKLE:
// → O(1) on-chain storage (just root hash)
// → O(log n) proof verification
// → Off-chain computation of rewards
// → On-chain verification + payment

// SECURITY:
// → Root submitted by trusted rewardsUpdater
// → activationDelay prevents instant claims
// → Root can be disabled by owner
// → Cumulative claim prevents double-spend
```

---

## AUDIT FINDINGS

### Finding 1: StrategyBase Uses balanceOf() with Small Virtual Offsets (LOW)

```solidity
// _tokenBalance() = underlyingToken.balanceOf(address(this))
// SHARES_OFFSET = 1e3, BALANCE_OFFSET = 1e3

// Direct token donation to strategy inflates share price
// Attack cost ≈ 1000x victim's deposit (for 18-decimal tokens)

// For 6-decimal tokens (USDC):
//   SHARES_OFFSET = 1000 = 0.001 USDC
//   Attack cost ≈ 1000x victim's deposit
//   Still not profitable

// For 0-decimal tokens:
//   SHARES_OFFSET = 1000 tokens
//   Attack cost ≈ 1000x victim's deposit
//   Still not profitable

// COMPARISON:
//   Morpho: 1e6 virtual shares → attack cost 1M x
//   EigenLayer: 1e3 virtual shares → attack cost 1K x
//   Both make attack unprofitable, but EigenLayer is 1000x weaker

// MITIGATION: deposit/withdraw only via StrategyManager (not permissionless)
//   → Attacker can't directly call strategy.deposit()
//   → Must go through StrategyManager.depositIntoStrategy()
//   → But: anyone can send tokens directly to strategy contract

// SEVERITY: LOW (attack cost 1000x deposit, not profitable)
// NOTE: EigenLayer acknowledges this in comments:
//   "We acknowledge that this mitigation has the known downside of the
//    virtual shares causing some losses to users"
```

### Finding 2: Slashing Factor Can Round to Zero — Staker DoS (MEDIUM)

```solidity
// From DelegationManager._getSlashingFactor:
// "Be mindful of rounding in mulWad(), it's possible for the slashing factor
//  to round down to 0 even when both operatorMaxMagnitude and
//  beaconChainSlashingFactor are non-zero."

// For beacon chain strategy:
//   slashingFactor = operatorMaxMagnitude.mulWad(beaconChainSlashingFactor)
//   = operatorMaxMagnitude * beaconChainSlashingFactor / 1e18

// If operatorMaxMagnitude = 1 (after heavy slashing)
// And beaconChainSlashingFactor = 1e9 (0.000000001)
// → slashingFactor = 1 * 1e9 / 1e18 = 0 (rounds to 0!)

// IMPACT:
//   In _increaseDelegation: require(slashingFactor != 0, FullySlashed())
//   → Staker can't deposit more shares (revert)
//   → Staker can't re-deposit withdrawal as shares (revert)
//   → Staker CAN withdraw as tokens (receiveAsTokens = true)
//   → But: withdrawable shares = depositShares * DSF * 0 = 0
//   → Staker gets NOTHING

// SCENARIO:
//   1. Operator slashed repeatedly → maxMagnitude very low
//   2. Beacon chain slashing also applied → compound effect
//   3. slashingFactor rounds to 0
//   4. ALL stakers of this operator lose ALL withdrawable shares
//   5. Stakers can't even withdraw as tokens (0 shares)

// MITIGATION:
//   → This requires EXTREME slashing (magnitude near 0)
//   → Operator would need to be slashed ~99.9999999999999999%
//   → In practice, operators are fully slashed (magnitude = 0) before this
//   → When magnitude = 0, slashingFactor = 0 is EXPECTED (fully slashed)

// SEVERITY: MEDIUM (edge case, but total fund loss for affected stakers)
// NOTE: This is somewhat by design — extreme slashing = extreme loss
//   But: the rounding to 0 happens BEFORE magnitude reaches 0
//   → There's a window where magnitude > 0 but slashingFactor = 0
//   → Stakers lose more than the actual slash amount
```

### Finding 3: DepositScalingFactor Division Precision Loss (LOW)

```solidity
// SlashingLib.update():
// newDSF = (currentShares + addedShares) / (prevDepositShares + addedShares) / slashingFactor
//        = newShares.divWad(prevDepositShares + addedShares).divWad(slashingFactor)

// Two sequential divWad operations → precision loss compounds
// divWad(x, y) = x * 1e18 / y (rounds down)

// Example:
//   newShares = 100, prevDepositShares + addedShares = 100, slashingFactor = 0.999
//   Step 1: 100 * 1e18 / 100 = 1e18
//   Step 2: 1e18 * 1e18 / 0.999e18 = 1.001001...e18 → rounds to 1001001001001001001
//   Actual: 1/0.999 = 1.001001001001001001...
//   Error: ~1 wei per operation

// Over many deposits/slashes, DSF accumulates rounding errors
// → Staker's withdrawable shares slightly less than expected
// → Error is tiny (wei-level) but compounds over time

// MITIGATION:
//   → require(newDepositScalingFactor != 0) prevents underflow
//   → Error is negligible for practical amounts
//   → Rounding favors protocol (staker gets slightly less)

// SEVERITY: LOW (wei-level precision loss, not exploitable)
```

### Finding 4: redelegate() Atomicity — No Slashing Gap (INFO)

```solidity
function redelegate(address newOperator, ...) external returns (bytes32[] memory) {
    withdrawalRoots = undelegate(msg.sender);  // queues withdrawals
    delegateTo(newOperator, ...);              // delegates to new operator
}

// Both operations in SAME TRANSACTION
// → No external state change between undelegate and delegateTo
// → No slashing can occur between the two calls
// → Staker's shares are removed from old operator and added to new operator atomically

// BUT: undelegate queues withdrawals (doesn't complete them)
// → Shares remain slashable during MIN_WITHDRAWAL_DELAY_BLOCKS
// → If old operator is slashed during delay → staker loses shares
// → This is BY DESIGN (can't escape slashing by redelegating)

// SEVERITY: INFO (by design, no vulnerability)
```

### Finding 5: RewardsCoordinator — rewardsUpdater is Single Address (INFO)

```solidity
modifier onlyRewardsUpdater() {
    require(msg.sender == rewardsUpdater, UnauthorizedCaller());
    _;
}

// rewardsUpdater = single address (set by owner)
// Submits Merkle distribution roots
// → If compromised: can submit fake roots → steal all rewards
// → But: activationDelay prevents instant claims
// → Owner can disable roots

// COMPARISON with Kelp:
//   Kelp: rate setter = 2/4 multisig, no timelock on rate
//   EigenLayer: rewardsUpdater = single address, but activationDelay
//   → EigenLayer has TIME-BASED protection (activationDelay)
//   → Kelp has NO time-based protection on rate changes

// SEVERITY: INFO (standard trust assumption, mitigated by activationDelay)
```

### Finding 6: EigenPod — Beacon Chain Proof Verification (INFO)

```solidity
// Uses EIP-4788 beacon block root oracle (0x000F3df6D732807Ef1319fB7B8bB8522d0Beac02)
// Verifies SSZ proofs against beacon state root
// Balance updates in Gwei (1e9 wei)

// SECURITY:
// → Beacon roots from EIP-4788 (consensus-verified)
// → SSZ proof verification (cryptographic)
// → Can't fake proofs without consensus-level attack
// → Gwei precision (1e9 wei) → rounding at gwei level

// POTENTIAL ISSUE:
// → Gwei precision means balances rounded to nearest gwei
// → 1 gwei = 1e9 wei = $0.003 at current prices
// → Negligible for practical amounts
// → But: many validators × many checkpoints = accumulated rounding

// SEVERITY: INFO (consensus-verified, gwei rounding negligible)
```

### Finding 7: AllocationManager — clearDeallocationQueue Permissionless (INFO)

```solidity
function clearDeallocationQueue(address operator, IStrategy[] calldata strategies, uint16[] calldata numToClear)
    external onlyWhenNotPaused(PAUSED_MODIFY_ALLOCATIONS) {
    // NO access control! Anyone can clear deallocation queue
    for (uint256 i = 0; i < strategies.length; ++i) {
        _clearDeallocationQueue(operator, strategies[i], numToClear[i]);
    }
}

// WHY PERMISSIONLESS:
// → Clearing deallocation queue FREES magnitude for the operator
// → This HELPS the operator (more magnitude available)
// → No griefing vector (can't harm operator by clearing)
// → Operator benefits from freed magnitude

// BUT: _clearDeallocationQueue is also called in modifyAllocations
// → With type(uint16).max to clear ALL pending deallocations
// → Before allocating new magnitude

// SEVERITY: INFO (permissionless but beneficial, not harmful)
```

---

## COMPARISON: ALL 8 PROTOCOLS AUDITED

```
                Arcadia  Morpho  Aave   EtherFi  Lido   Kelp    Basin  EigenLayer
Source:         OPEN ✅  OPEN ✅ OPEN ✅ OPEN ✅  OPEN ✅ CLOSED❌ OPEN ✅ OPEN ✅
TVL:            $100M    $5B     $30B   $8B      $30B   $1.5B   $50M   $15B
Type:           Lending  Lending Lending LST/LRT  LST    LRT     Lending Restaking
Code:           1.3K     555     21K    39K      36K    ~20K    ~2K    21K

Bug found:      ✅ MED   ❌      ❌     ❌       ❌     ❌*     ✅     ❌
                                                    (*limited)

TVL accounting: balOf❌  stored✅ virt✅ stored✅ stored✅ ext.SET❌ balOf❌ balOf⚠️
Inflation:      VULN     IMMUNE  IMMUNE IMMUNE   IMMUNE IMMUNE  VULN   MITIGATED
                                                                    (1e3 offset)

Slashing:       N/A      N/A     N/A    N/A      N/A    N/A     N/A    ✅ magnitude
Withdrawal:     instant  instant instant NFT+Q   queue  unknown queue  queue+delay
Bad debt:       cascade  isol.   Umbrella N/A    social unknown N/A    slashing

Defense:        1        3       4      6        5      unknown 1      5+
Audit firms:    few      ToB+Sp  ToB+C4 multiple ToB+C4 Cyfrin  few    ToB+Zellic+multiple
```

---

## WHAT TO STEAL FROM EIGENLAYER

```
1. Magnitude-based slashing
   → Proportional, composable, multi-AVS
   → Each slash reduces remaining magnitude
   → Rounding favors operator (prevents over-slashing)

2. DepositScalingFactor (DSF)
   → Converts between deposit shares and withdrawable shares
   → "Forgives" prior slashing for new deposits
   → Prevents gaming around slash events

3. Withdrawal delay with slashing window
   → Shares remain slashable during delay
   → Can't escape slashing by queueing withdrawal
   → Slashing applied at END of delay (not queue time)

4. Allocation/Deallocation delays
   → New allocation: not slashable until delay passes
   → Deallocation: remains slashable until delay passes
   → Prevents "slash and run" in both directions

5. Virtual shares in StrategyBase (1e3 offset)
   → Mitigates inflation attack (cost = 1000x deposit)
   → Not as strong as Morpho (1e6) but sufficient
   → Acknowledged downside in comments (honest!)

6. Merkle-based reward claims
   → O(1) on-chain storage
   → Cumulative claim prevents double-spend
   → activationDelay prevents instant claims
```

---

## HONEST ASSESSMENT

```
EigenLayer: 0 exploitable bugs found

Findings:
  → 1 MEDIUM: slashing factor rounding to 0 (edge case DoS)
  → 2 LOW: balanceOf() with small offsets, DSF precision loss
  → 4 INFO: redelegate atomicity, rewardsUpdater trust, beacon proofs, permissionless clear

WHY NO EXPLOITABLE BUGS:
  → 21K lines, audited by ToB + Zellic + multiple C4/Sherlock contests
  → Extensive comments explaining design decisions
  → Careful rounding (favors protocol/operator consistently)
  → Multiple delay mechanisms prevent timing attacks
  → Slashing math is well-derived (formal equations in comments)
  → StrategyBase inflation protection (1e3 offset, not perfect but sufficient)

MOST INTERESTING FINDING:
  → Finding 2 (slashing factor rounding to 0)
  → Edge case where magnitude > 0 but slashingFactor = 0
  → Stakers lose MORE than actual slash amount
  → But: requires extreme slashing (~99.9999999999999999%)
  → Unlikely in practice (operators fully slashed before this)
  → Would need PoC to verify exact threshold

VERDICT:
  → EigenLayer is one of the most carefully designed protocols I've audited
  → Slashing math is rigorous (formal derivations in comments)
  → Multiple defense layers (delays, snapshots, magnitude system)
  → Not a good target for bug bounty (too well-audited)
  → But: EXCELLENT reference for learning DeFi security patterns
```

---

*BOZAGENTIC · "EigenLayer: the PhD thesis of DeFi protocol design. Every line has a reason."*
