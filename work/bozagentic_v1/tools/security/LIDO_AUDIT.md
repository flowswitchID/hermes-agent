# LIDO — FULL FRAMEWORK AUDIT + CODE REFERENCE
# Largest LST Protocol ($30B+ TVL) · 36K lines
# BOZAGENTIC · 2026-07-30
# Source: github.com/lidofinance/lido-dao

---

## ARCHITECTURE

```
Lido: Liquid staking on Ethereum (largest protocol by TVL)
  → Users deposit ETH → receive stETH (rebasing)
  → ETH staked via node operators on beacon chain
  → Oracle reports rewards → stETH rebases

Core (Legacy, Solidity 0.4.24):
  Lido.sol (1572 lines) — stETH token + deposit + oracle rebase
  StETH.sol (590 lines) — share-based ERC20
  NodeOperatorsRegistry.sol (1496 lines) — operator management

Oracle System (0.8.9):
  AccountingOracle.sol (916 lines) — report processing
  HashConsensus.sol (1096 lines) — oracle consensus
  ValidatorsExitBus.sol (1148 lines) — validator exits
  OracleReportSanityChecker.sol (1588 lines) — sanity checks
  DepositSecurityModule.sol (598 lines) — deposit security

NEW: Vaults System (0.8.25) ← LEAST AUDITED, MOST INTERESTING
  VaultHub.sol (1772 lines) — vault management hub
  StakingVault.sol (745 lines) — individual vault
  OperatorGrid.sol (904 lines) — operator tiers
  LazyOracle.sol (683 lines) — per-vault oracle
  PredepositGuarantee.sol (954 lines) — pre-deposit guarantee
  Dashboard.sol (827 lines) — vault dashboard

Withdrawal:
  WithdrawalQueueBase.sol (596 lines) — withdrawal queue
```

---

## KEY PATTERNS (Learn from Lido)

### Pattern 1: Share-Based Rebasing (stETH)
```solidity
// stETH = share-based token (like EtherFi eETH, like Lido's own design)
// balanceOf(user) = shares[user] * totalPooledEther / totalShares

// Deposit:
function _submit(address _referral) internal returns (uint256) {
    require(msg.value != 0, "ZERO_DEPOSIT");
    _decreaseStakingLimit(msg.value);
    uint256 sharesAmount = getSharesByPooledEth(msg.value);
    _mintShares(msg.sender, sharesAmount);
    _setBufferedEther(_getBufferedEther() + msg.value);
}

// TVL calculation (V2 — with external shares from VaultHub):
function _getTotalPooledEther() internal view returns (uint256) {
    uint256 internalEther = _getInternalEther();
    return internalEther + _getExternalEther(internalEther);
}

// External ether (from VaultHub vaults):
function _getExternalEther(uint256 _internalEther) internal view returns (uint256) {
    (uint256 totalShares, uint256 externalShares) = _getTotalAndExternalShares();
    uint256 internalShares = totalShares - externalShares;
    return (externalShares * _internalEther) / internalShares;
}

// WHY NO INFLATION ATTACK:
// → Mint ONLY via submit() (sends ETH) or mintExternalShares (VaultHub only)
// → No permissionless "donate" function
// → TVL = buffered + CL validators + CL pending + deposited
// → Direct ETH transfer to Lido contract ≠ TVL increase
// → "Stone in the elevator": internalShares never 0
```

### Pattern 2: External Shares (VaultHub Integration)
```solidity
// NEW in Lido V2: VaultHub can mint "external shares"
// These are stETH shares backed by vault ETH (not Lido's internal ETH)

// VaultHub.mintShares():
function mintShares(address _vault, address _recipient, uint256 _amountOfShares) external {
    // 1. Check connection + ownership
    // 2. Check fresh report
    // 3. Increase vault liability (reserve ratio check)
    // 4. LIDO.mintExternalShares(_recipient, _amountOfShares)
}

// External shares ratio bounded:
function _getMaxMintableExternalShares() internal view returns (uint256) {
    uint256 maxRatioBP = _getMaxExternalRatioBP();
    if (maxRatioBP == 0) return 0;
    if (maxRatioBP == TOTAL_BASIS_POINTS) return uint256(-1);
    // Formula: x <= (totalShares * maxBP - externalShares * totalBP) / (totalBP - maxBP)
}

// WHY: limits how much stETH can be backed by external vaults
// Prevents vault system from dominating Lido's TVL
// Governance-configurable ratio
```

### Pattern 3: Reserve Ratio + Locked Value (VaultHub)
```solidity
// Each vault must maintain a reserve ratio:
// locked = liability + max(reserve, minimalReserve)
// reserve = liability * reserveRatioBP / (10000 - reserveRatioBP)

function _locked(uint256 _liabilityShares, uint256 _minimalReserve, uint256 _reserveRatioBP)
    internal view returns (uint256) {
    uint256 liability = _getPooledEthBySharesRoundUp(_liabilityShares);
    uint256 reserve = Math256.ceilDiv(
        liability * _reserveRatioBP, TOTAL_BASIS_POINTS - _reserveRatioBP
    );
    return liability + Math256.max(reserve, _minimalReserve);
}

// Example: reserveRatioBP = 3000 (30%)
// liability = 100 ETH → reserve = 100 * 3000 / 7000 = 42.86 ETH
// locked = 100 + 42.86 = 142.86 ETH
// → Vault must hold 142.86 ETH to back 100 ETH of stETH

// WHY: overcollateralization protects against slashing
// If validator slashed 30%, vault still covers stETH holders
```

### Pattern 4: Bad Debt Socialization (VaultHub)
```solidity
// If vault has bad debt (liability > totalValue):
// Option 1: socializeBadDebt — transfer to another vault (same operator)
// Option 2: internalizeBadDebt — protocol absorbs loss

function socializeBadDebt(address _badDebtVault, address _vaultAcceptor, uint256 _maxShares)
    external onlyRole(BAD_DEBT_MASTER_ROLE) {
    // Must be same node operator
    // Acceptor must have capacity (totalValueShares > liabilityShares)
    // Transfer liability from bad vault to acceptor
}

function internalizeBadDebt(address _badDebtVault, uint256 _maxShares)
    external onlyRole(BAD_DEBT_MASTER_ROLE) {
    // Decrease vault liability
    // Store in badDebtToInternalize counter
    // Accounting Oracle settles during next report
    // → Protocol loss socialized to ALL stETH holders
}

// COMPARISON:
// Arcadia: tranche cascade (can brick pool)
// Aave: deficit + Umbrella (external backstop)
// EtherFi: N/A (no borrow)
// Lido VaultHub: socialize to same operator OR internalize to protocol
// → Most flexible bad debt handling of all protocols studied
```

### Pattern 5: Force Rebalance (Permissionless)
```solidity
// ANYONE can force rebalance an unhealthy vault:
function forceRebalance(address _vault) external {
    // 1. Check connection + fresh report
    // 2. Calculate available balance
    // 3. Calculate obligations shares
    // 4. Rebalance: burn shares + withdraw ETH + convert to internal
}

// WHY permissionless:
// → Unhealthy vault = risk to stETH holders
// → Don't wait for vault owner to act
// → Anyone can trigger rebalance
// → Uses vault's own ETH (no external funds needed)

// Rebalance flow:
// 1. _decreaseLiability (burn vault's liability shares)
// 2. _withdraw (pull ETH from vault to VaultHub)
// 3. _rebalanceExternalEtherToInternal (convert external → internal)
// → stETH holders protected without governance action
```

### Pattern 6: Report Freshness (Anti-Stale Oracle)
```solidity
function _isReportFresh(VaultRecord storage _record) internal view returns (bool) {
    uint256 latestReportTimestamp = _lazyOracle().latestReportTimestamp();
    return
        uint48(latestReportTimestamp) <= _record.report.timestamp &&
        block.timestamp - latestReportTimestamp < REPORT_FRESHNESS_DELTA; // 2 days
}

// WHY: prevents operations on stale data
// If oracle hasn't reported in 2 days → all vault operations blocked
// Protects against: stale prices, missed reports, oracle downtime
// Applied to: mintShares, burnShares, withdraw, rebalance, updateConnection
```

### Pattern 7: Anti-Loop Protection in Report Application
```solidity
function _applyVaultReport(...) internal {
    // Prevent 1-tx loop:
    // 1. bring ETH (TV+)
    // 2. mint stETH (locked+)
    // 3. burn stETH
    // 4. bring last report (locked-)
    // 5. withdraw ETH (TV-)
    
    if (_record.maxLiabilityShares == _reportMaxLiabilityShares) {
        _record.maxLiabilityShares = SafeCast.toUint96(
            Math256.max(_record.liabilityShares, _reportLiabilityShares)
        );
    }
    // If maxLiabilityShares changed since report → don't update
    // Prevents unlocking collateral via report replay
}

// WHY: prevents vault owner from:
// → Minting stETH on fresh funds
// → Burning stETH
// → Applying old report to unlock collateral
// → Withdrawing ETH
// All in 1 transaction
```

---

## AUDIT FINDINGS

### Finding 1: External Ether Calculation — Division by Zero Edge Case (INFO)
```solidity
function _getExternalEther(uint256 _internalEther) internal view returns (uint256) {
    (uint256 totalShares, uint256 externalShares) = _getTotalAndExternalShares();
    uint256 internalShares = totalShares - externalShares;
    return (externalShares * _internalEther) / internalShares;
}

// If internalShares == 0 → division by zero → revert
// MITIGATION: "stone in the elevator" — initial shares minted at deploy
// → internalShares can never be 0 (initial shares never burned)
// → Comment: "never 0 because of the stone in the elevator"

// SEVERITY: INFO (mitigated by design)
```

### Finding 2: VaultHub — maxLiabilityShares Anti-Loop Bypass Window (LOW)
```solidity
// _applyVaultReport only updates maxLiabilityShares if unchanged:
if (_record.maxLiabilityShares == _reportMaxLiabilityShares) {
    _record.maxLiabilityShares = SafeCast.toUint96(
        Math256.max(_record.liabilityShares, _reportLiabilityShares)
    );
}

// Edge case: if vault owner mints AND burns between reports:
// → maxLiabilityShares increases (mint) then decreases (burn)
// → But maxLiabilityShares only goes UP (max function)
// → So: maxLiabilityShares stays at peak → locked stays high
// → Vault owner can't unlock until next report

// This is CONSERVATIVE (locks MORE than needed)
// Not exploitable for profit, but vault owner's capital efficiency reduced

// SEVERITY: LOW (conservative, not exploitable)
```

### Finding 3: VaultHub — forceRebalance Uses RoundUp for Shares (INFO)
```solidity
function _rebalance(address _vault, VaultRecord storage _record, uint256 _shares) internal {
    uint256 valueToRebalance = _getPooledEthBySharesRoundUp(_shares);
    _decreaseLiability(_vault, _record, _shares);
    _withdraw(_vault, _record, address(this), valueToRebalance);
    _rebalanceExternalEtherToInternal(valueToRebalance, _shares);
}

// RoundUp means vault pays slightly MORE ETH than shares are worth
// → Favors stETH holders (protocol) over vault owner
// → Conservative rounding (correct for security)

// SEVERITY: INFO (correct design)
```

### Finding 4: VaultHub — socializeBadDebt Same Operator Check (INFO)
```solidity
if (_nodeOperator(_vaultAcceptor) != _nodeOperator(_badDebtVault)) {
    revert BadDebtSocializationNotAllowed();
}

// Bad debt can only be socialized within same node operator
// → Prevents one operator's bad debt from affecting another
// → But: if operator has only 1 vault → can't socialize → must internalize
// → Internalize = protocol loss (all stETH holders absorb)

// SEVERITY: INFO (by design, limits contagion)
```

### Finding 5: Lido.sol — Solidity 0.4.24 (INFO)
```solidity
pragma solidity 0.4.24;  // Core Lido contract

// No built-in overflow checks (SafeMath used instead)
// No custom errors (string requires)
// No transient storage
// AragonApp framework (legacy governance)

// RISK: older compiler = more potential for subtle bugs
// BUT: battle-tested since 2020, $30B+ TVL, multiple audits
// New code (VaultHub) uses 0.8.25 (modern)

// SEVERITY: INFO (legacy but battle-tested)
```

### Finding 6: VaultHub — REPORT_FRESHNESS_DELTA = 2 days (INFO)
```solidity
uint256 public constant REPORT_FRESHNESS_DELTA = 2 days;

// If oracle stops reporting for 2+ days:
// → All vault operations blocked (mint, burn, withdraw, rebalance)
// → forceRebalance also blocked (requires fresh report)
// → Vault owners can't withdraw their own ETH

// This is a SAFETY feature (no operations on stale data)
// But: creates dependency on oracle availability
// If oracle is down → vault system frozen

// MITIGATION: HashConsensus has multiple oracle members
// → Single oracle failure doesn't freeze system
// → Requires majority failure

// SEVERITY: INFO (safety trade-off)
```

---

## COMPARISON: ALL 6 PROTOCOLS STUDIED

```
                Arcadia    Morpho    Aave V3    EtherFi    Lido       Basin
Type:           Lending    Lending   Lending    LST/LRT    LST        Lending
TVL:            ~$100M     ~$5B      ~$30B      ~$8B       ~$30B      ~$50M
Code:           1.3K       555       21K        39K        36K        ~2K
Solidity:       0.8.x      0.8.19    0.8.10+    0.8.13+    0.4+0.8    0.8.x
Upgradeable:    No         No        Proxy      UUPS       Proxy      No

Bug found:      ✅ MEDIUM  ❌        ❌         ❌         ❌         ✅ (pending)
TVL accounting: balanceOf❌ stored✅  virtual✅  stored✅   stored✅   balanceOf❌
Inflation:      VULNERABLE IMMUNE   IMMUNE     IMMUNE     IMMUNE     VULNERABLE
Bad debt:       cascade❌   isolated✅ Umbrella✅ N/A       socialize✅ N/A

Defense layers: 1          3         4          6          5          1
Audit history:  few        ToB+Sp    ToB+C4+Z   multiple   ToB+C4+Sp  few
```

---

## WHAT TO STEAL FROM LIDO

```
1. External shares with ratio cap
   → Limit how much stETH backed by external vaults
   → Governance-configurable max ratio
   → Prevents vault system from dominating protocol

2. Reserve ratio (overcollateralization)
   → Vault must hold liability + reserve
   → Protects against slashing
   → Configurable per vault tier

3. Permissionless forceRebalance
   → Anyone can fix unhealthy vault
   → Don't wait for owner/governance
   → Uses vault's own funds

4. Bad debt socialization (same operator)
   → Transfer bad debt to healthy vault (same operator)
   → Or internalize to protocol (last resort)
   → Most flexible bad debt handling studied

5. Anti-loop in report application
   → maxLiabilityShares prevents 1-tx exploit
   → Conservative: locks MORE than needed
   → Better safe than sorry

6. Report freshness (2-day window)
   → No operations on stale data
   → Hardcoded constant (not configurable)
   → Safety > availability
```

---

## HONEST ASSESSMENT

```
Lido: 0 exploitable bugs found
  → $30B+ TVL, most audited protocol in DeFi
  → Core (0.4.24): battle-tested since 2020
  → VaultHub (0.8.25): newest code, but well-designed
  → Multiple defense layers: reserve ratio, force rebalance,
    bad debt socialization, report freshness, anti-loop

VaultHub is the most interesting target:
  → Newest code (2025)
  → Complex vault accounting
  → Multiple roles (owner, master, redemption, bad debt, validator exit)
  → But: still well-designed with conservative rounding

WHERE BUGS MIGHT HID:
  → LazyOracle (683 lines) — per-vault oracle logic
  → PredepositGuarantee (954 lines) — pre-deposit validation
  → OperatorGrid (904 lines) — tier management
  → Cross-contract: VaultHub ↔ Lido ↔ StakingVault ↔ LazyOracle
  → Upgrade transactions (storage layout changes)
  → Edge cases in disconnect flow (pending disconnect + report)
```

---

*BOZAGENTIC · "Lido: the protocol that wrote the book on liquid staking security. VaultHub is their most ambitious chapter."*
