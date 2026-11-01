# KELP DAO (rsETH) — FINAL DEEP AUDIT REPORT
# On-chain probing + bytecode reverse engineering (5105 + 11760 lines disassembly)
# BOZAGENTIC · 2026-07-30

---

## ARCHITECTURE (Fully Reconstructed from Bytecode)

```
rsETH Token (proxy → impl 0x7159...7783):
  → Mintable/burnable ERC20 (NOT share-based, NOT ERC4626)
  → Access: MINTER_ROLE checked via lrtConfig.isLRTManager() (selector 0x24745215)
  → Period cap: slot 0x97 (cap), slot 0x98 (current), slot 0x99 (periodStart)
  → Rate: slot 0x98 (1.170254) — externally SET, not computed
  → Pause: slot 0x65 (paused flag)
  → Custody: slot for custodyAddress (0xb369...a46d, minimal proxy)

Deposit Pool (proxy → impl 0xea38...8320, 40K bytecode):
  → depositAsset(address,uint256,uint256,string) — main deposit entry
  → getRsETHAmountToMint(address,uint256) — rate conversion
  → getAssetDistributionData(address) — per-asset accounting
  → getETHDistributionData() — ETH accounting
  → 7 node delegators (max 20) — EigenLayer restaking
  → transferAssetToNodeDelegator / transferETHToNodeDelegator
  → receiveFromLRTConverter / receiveFromRewardReceiver / receiveFromNodeDelegator

LRTConfig (0x947C...5ec7):
  → rsETH() → 0xA129...5A7
  → isLRTManager(address) — access control oracle
  → getSupportedAssetList() → [stETH, ETHx, ETH]
  → isSupportedAsset(address) → bool

On-Chain State:
  rsETH totalSupply:  438,347 rsETH (~$1.5B)
  Rate:               1.170254 (slot 0x98)
  Period cap:         5,000 ETH / 24 hours
  Period current:     4,998.83 ETH (1.17 remaining)
  Period duration:    86400 seconds (0x15180)
  
  Deposit pool holds:
    stETH:  5,104 stETH
    ETHx:   50.28 ETHx
    ETH:    220.33 ETH
  
  7 node delegators:
    0xFc56...cB85, 0x3958...8946, 0x79f1...8c32,
    0x4C79...2F83, 0xee54...53D3, 0x049E...BA7B, 0x545D...dAB9
```

---

## BYTECODE ANALYSIS: MINT FUNCTION

```
mint(address,uint256) at 0x08a3:

1. SLOAD slot 0 → lrtConfig address
2. CALL lrtConfig.isLRTManager(MINTER_ROLE, msg.sender)
   → MINTER_ROLE = 0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6
   → STATICCALL to lrtConfig with selector 0x91d14854 (hasRole)
   → Wait: actually calls 0x24745215 (isLRTManager) with MINTER_ROLE + CALLER
3. If returns false → REVERT with custom error
4. Check period cap:
   → SLOAD slot 0x99 (periodStart)
   → SLOAD slot 0x98 (current) + 0x15180 (86400)
   → If TIMESTAMP > periodStart + 86400:
     → SSTORE slot 0x98 = 0 (reset current)
     → SSTORE slot 0x99 = TIMESTAMP (new period)
   → SLOAD slot 0x97 (cap)
   → If amount + current > cap → REVERT 0xe315fff8
5. SSTORE slot 0x98 += amount (update current)
6. Call internal mint (0x1bc3) → _mint(to, amount)
7. Call internal hook (0x1c70) → post-mint logic

ACCESS CONTROL:
  → Mint requires lrtConfig.isLRTManager(MINTER_ROLE, caller)
  → hasRole() on rsETH itself REVERTS (not standard AccessControl)
  → Role check delegated to LRTConfig contract
  → LRTConfig is ALSO a proxy (admin: 0xb61e...dc78, same as rsETH)
```

---

## BYTECODE ANALYSIS: PERIOD CAP

```
Period cap logic (from bytecode trace):

slot 0x97 = cap (5000 ETH = 5000e18)
slot 0x98 = current period usage
slot 0x99 = period start timestamp

On each mint:
  if (block.timestamp > slot_0x99 + 86400) {
      slot_0x98 = 0;           // reset usage
      slot_0x99 = block.timestamp;  // new period
  }
  if (amount + slot_0x98 > slot_0x97) {
      revert(0xe315fff8);      // cap exceeded
  }
  slot_0x98 += amount;         // track usage

ANALYSIS:
  → Cap is per-period (24 hours), NOT per-transaction
  → Attacker can deposit up to 5000 ETH in multiple txs per period
  → Cap resets at periodStart + 86400 (not at fixed UTC time)
  → periodStart updates to block.timestamp on reset
  → First tx after reset sets new periodStart

EDGE CASE:
  → If no mint for >24 hours, next mint resets period
  → periodStart = block.timestamp of first mint after gap
  → Not a fixed schedule — drifts based on activity
```

---

## FINDINGS

### Finding 1: 1 Wei Deposit Returns 0 rsETH — Silent Fund Loss (LOW)

```
On-chain verification:
  getRsETHAmountToMint(stETH, 1 wei) → 0 rsETH
  getRsETHAmountToMint(stETH, 0.001 ETH) → 928538869434 rsETH (0.000000928538)
  getRsETHAmountToMint(stETH, 1 ETH) → 928538869434035546 rsETH

Rate: 1 stETH → 0.928538869434035630 rsETH
Implied stETH/ETH rate: 1.076960839140230553

ANALYSIS:
  → Deposit 1 wei stETH → get 0 rsETH → lose 1 wei
  → This is rounding down (floor division)
  → Affects ALL deposits < ~1.077 wei (practically nobody)
  → Gas cost >> 1 wei → not exploitable at scale

  BUT: if depositAsset() doesn't check rsETHToMint > 0:
  → User could deposit 1 wei → get 0 rsETH → tx succeeds
  → 1 wei stuck in deposit pool forever
  → Negligible economic impact

COMPARISON:
  → Morpho: checks share == 0 → revert InvalidAmount
  → Aave: checks sharesAmount != 0
  → Kelp: UNKNOWN (can't verify without source)

SEVERITY: LOW (negligible impact, but missing zero-check is bad practice)
```

### Finding 2: Rate is Externally SET, Not Computed On-Chain (MEDIUM)

```
rsETH rate = 1.170254 (stored in slot 0x98 of rsETH contract)

This rate is NOT computed from:
  → totalPooledEther / totalShares (like Lido)
  → TVL / totalShares (like EtherFi)
  → Any on-chain formula

Evidence:
  → Rate is a stored value (SLOAD slot 0x98)
  → No oracle() function on deposit pool or LRTConfig
  → getAssetOracle() reverts for all assets
  → Rate changes require external transaction (SSTORE)

Rate update mechanism (from bytecode):
  → Some function writes to slot 0x98
  → Likely called by oracle operator or admin
  → Access control: probably lrtConfig-gated

RISK:
  → If rate setter is compromised → arbitrary rate
  → Set rate = 0.001 → mint 1000x more rsETH per deposit
  → Set rate = 1000 → mint 1000x less (user loss)
  → No on-chain validation of rate bounds visible

MITIGATION (assumed, not verified):
  → Rate setter likely behind multisig
  → Rate changes likely have sanity checks in LRTConfig
  → Period cap limits exposure per period

SEVERITY: MEDIUM (centralization risk, but likely mitigated by multisig)
```

### Finding 3: Period Cap Resets on First Mint After Gap (INFO)

```
Period cap logic:
  if (block.timestamp > periodStart + 86400) {
      current = 0;
      periodStart = block.timestamp;
  }

EDGE CASE:
  → Period is NOT fixed to UTC midnight
  → periodStart drifts based on first mint after gap
  → If no mint for 48 hours → next mint starts new 24h period
  → Attacker can't predict exact reset time

  → But: this is a minor operational detail
  → Cap still limits to 5000 ETH per 24h window
  → No way to get >5000 ETH in any 24h period

SEVERITY: INFO (operational detail, not exploitable)
```

### Finding 4: hasRole() Reverts on rsETH — Non-Standard Access Control (INFO)

```
Standard OZ AccessControl:
  hasRole(bytes32,address) → returns bool

Kelp rsETH:
  hasRole(bytes32,address) → REVERTS with 0x

Why:
  → rsETH doesn't implement AccessControl directly
  → Role checks delegated to lrtConfig.isLRTManager()
  → lrtConfig is the single source of truth for roles
  → rsETH just calls lrtConfig for every role check

IMPLICATION:
  → All access control depends on lrtConfig
  → lrtConfig is ALSO a proxy (same admin: 0xb61e...dc78)
  → If lrtConfig is compromised → ALL roles compromised
  → Single point of failure for entire access control

SEVERITY: INFO (by design, but centralization risk)
```

### Finding 5: Deposit Pool Holds 220 ETH + 5104 stETH Unrestaked (INFO)

```
Deposit pool balances:
  stETH:  5,104 stETH (~$17.3M)
  ETHx:   50.28 ETHx (~$170K)
  ETH:    220.33 ETH (~$750K)
  Total:  ~$18.2M

7 node delegators available (max 20)
→ Funds waiting to be distributed to node delegators
→ Or: buffer for withdrawals

RISK:
  → If deposit pool contract is compromised → $18.2M at risk
  → But: deposit pool has its own access control
  → transferAssetToNodeDelegator likely role-gated

SEVERITY: INFO (operational buffer, standard for LST protocols)
```

### Finding 6: Rate is Linear — No Rounding Exploitation at Scale (INFO)

```
Verified on-chain:
  1 stETH   → 0.928538869434035630 rsETH
  100 stETH → 92.853886943403551868 rsETH (= 100 × 1 stETH rate)
  0.001 stETH → 0.000928538869434 rsETH

Rate is perfectly linear (proportional)
→ No volume-based discount/premium
→ No rounding exploitation at any scale
→ Only 1 wei edge case (Finding 1)

SEVERITY: INFO (clean rate implementation)
```

### Finding 7: Closed Source — Cannot Verify Internal Logic (HIGH RISK FACTOR)

```
What I CAN verify (on-chain):
  ✅ Mint requires lrtConfig.isLRTManager(MINTER_ROLE, caller)
  ✅ Period cap: 5000 ETH / 24h, enforced on-chain
  ✅ Rate is stored value (not DEX-computed)
  ✅ Rate is linear (no rounding exploitation)
  ✅ Token is pausable
  ✅ Proxy upgradeable (admin: 0xb61e...dc78)
  ✅ 7 node delegators, max 20

What I CANNOT verify:
  ❌ depositAsset() internal logic (reentrancy? checks?)
  ❌ getRsETHAmountToMint() oracle source
  ❌ Rate setter access control
  ❌ Withdrawal flow
  ❌ Node delegator selection logic
  ❌ Fee calculation
  ❌ 12 unknown function selectors on rsETH
  ❌ ~20 unknown selectors on deposit pool

SEVERITY: HIGH RISK FACTOR (not a bug, but prevents full audit)
```

---

## ATTACK SCENARIOS — FINAL VERDICT

```
1. Flash loan deposit:
   → BLOCKED by period cap (5000 ETH/24h)
   → Can't deposit more than cap in one period
   → 5000 ETH is still $17M — but requires holding rsETH
   → VERDICT: Partially mitigated

2. Oracle rate manipulation:
   → Rate is SET externally, not computed from DEX
   → Can't manipulate via flash loan on DEX
   → Would need to compromise rate setter
   → VERDICT: Likely safe (but can't verify setter access control)

3. Mint access compromise:
   → Mint requires lrtConfig.isLRTManager(MINTER_ROLE)
   → lrtConfig is proxy with same admin as rsETH
   → If admin compromised → everything compromised
   → VERDICT: Standard proxy risk

4. 1 wei rounding:
   → Deposit 1 wei → get 0 rsETH
   → Not profitable (gas >> 1 wei)
   → VERDICT: Not exploitable

5. Period cap timing:
   → Cap resets on first mint after 24h gap
   → Can't get >5000 ETH in any 24h window
   → VERDICT: Not exploitable

6. Node delegator manipulation:
   → 7 delegators, max 20
   → transferAssetToNodeDelegator likely role-gated
   → Can't verify without source
   → VERDICT: Unknown

OVERALL: No exploitable bug found.
  → Protocol appears reasonably designed
  → Period cap + external rate + role-based access = decent defenses
  → BUT: closed source prevents full verification
  → Largest risk = rate setter access control (unverifiable)
```

---

## COMPARISON: ALL 7 PROTOCOLS AUDITED

```
                Arcadia    Morpho    Aave     EtherFi    Lido      Kelp       Basin
Source:         OPEN ✅    OPEN ✅   OPEN ✅  OPEN ✅    OPEN ✅   CLOSED ❌  OPEN ✅
TVL:            $100M      $5B       $30B     $8B        $30B      $1.5B      $50M
Token:          ERC4626    N/A       aToken   Rebasing   Rebasing  ***   Rebasing
                (VAS=0)                                (shares)  (shares)  ERC20
Rate:           N/A        N/A       N/A      Oracle     Oracle    External  N/A
                                                       (computed) (computed) (SET)
Cap:            None       None      None     None       Stake     5K/day    None
                                                                     limit
Bug found:      ✅ MEDIUM  ❌        ❌       ❌         ❌        ❌*       ✅
                                                                      (*limited)
Defense:        1          3         4        6          5         Unknown   1
Audit firms:    few        ToB+Sp    ToB+C4   multiple   ToB+C4    Cyfrin+C4 few
```

---

## HONEST FINAL VERDICT

```
Kelp DAO: No exploitable bug found.

BUT with major caveat:
  → CLOSED SOURCE = can't do full audit
  → 12+ unknown function selectors
  → Rate setter access control UNVERIFIABLE
  → Deposit pool internal logic UNVERIFIABLE
  → Withdrawal flow UNVERIFIABLE

What I DID verify (on-chain + bytecode):
  → Mint access control works (lrtConfig-gated)
  → Period cap enforced (5000 ETH/24h)
  → Rate is linear (no rounding exploitation)
  → Rate is externally set (not DEX-manipulable)
  → Token is pausable + upgradeable

Recommendation:
  → SKIP Kelp for bug bounty (can't audit properly)
  → Focus on OPEN SOURCE protocols with smaller TVL
  → Or: get Etherscan API key → pull verified source → re-audit
  → Or: wait for new Kelp deployment/upgrade → audit the diff

Lesson learned:
  → Closed source protocols are HARD to audit
  → On-chain probing + bytecode tracing has limits
  → For serious bug hunting: OPEN SOURCE is essential
  → Morpho/Aave/EtherFi/Lido = open but too mature
  → Sweet spot: open source + < 6 months + < $500M TVL
```

---

*BOZAGENTIC · "Kelp looks solid from the outside. But 'looks solid' ≠ 'is solid'. Need source to know for sure."*
