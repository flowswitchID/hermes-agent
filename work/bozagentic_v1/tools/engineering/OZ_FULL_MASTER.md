# OZ WIZARD + DEFENDER + ADVANCED CONTRACTS — MASTER REFERENCE
# OpenZeppelin Ecosystem Deep Dive
# BOZAGENTIC · 2026-07-30
# Total: ~45K chars

---

## PART 1: OPENZEPPELIN WIZARD

### 1.1 Contract Types Available

| Type | Base | Use Case |
|------|------|----------|
| ERC20 | ERC20Upgradeable | Fungible token |
| ERC721 | ERC721Upgradeable | NFT |
| ERC1155 | ERC1155Upgradeable | Multi-token |
| Governor | GovernorUpgradeable | DAO governance |
| Custom | Upgradeable base | Any custom logic |
| RealWorldAssets | ERC20 + compliance | RWA tokens |
| Stablecoin | ERC20 + compliance | Regulated stablecoin |

### 1.2 Feature Toggles per Type

**ERC20:**
```
✅ Mintable        — _mint() exposed, access controlled
✅ Burnable        — burn() / burnFrom() public
✅ Pausable        — pause() / unpause() + whenNotPaused
✅ Permit          — EIP-2612 gasless approvals
✅ Votes           — ERC20Votes, delegation + checkpoints
✅ Flash Minting   — ERC20FlashMint (⚠️ JANGAN combine dengan ERC4626!)
✅ Wrapper         — ERC20Wrapper (wrap underlying token)
✅ Premint         — _mint() di initializer
✅ Capped          — max supply cap
```

**ERC721:**
```
✅ Mintable        — safeMint() exposed
✅ Burnable        — burn() public
✅ Pausable        — pause/unpause
✅ Enumerable      — track all token IDs + per-owner
✅ URI Storage     — per-token URI override
✅ Votes           — ERC721Votes
✅ Royalties       — ERC2981
✅ Sequential      — gas-optimized sequential mint
✅ Consecutive     — ERC2309 batch mint
✅ Incremental    — auto-increment token ID
```

**ERC1155:**
```
✅ Mintable        — _mint() / _mintBatch()
✅ Burnable        — burn() / burnBatch()
✅ Pausable        — pause/unpause
✅ Supply Tracking — totalSupply per token ID
✅ URI Storage     — per-token URI
```

**Governor:**
```
✅ Votes Token     — which token for voting power
✅ Timelock        — TimelockController / Compound
✅ Settings        — voting delay, period, quorum
✅ Quorum Fraction — quorum as % of supply
✅ Quorum Absolute — fixed quorum number
✅ Bravo           — GovernorCompatibilityBravo
✅ Prevent Overwrite — description hash protection
```

### 1.3 Access Control Options

| Option | Contract | Model |
|--------|----------|-------|
| Ownable | OwnableUpgradeable | Single owner, transferOwnership |
| Ownable2Step | Ownable2StepUpgradeable | 2-step transfer (safer) |
| Roles | AccessControlUpgradeable | Role-based (MINTER_ROLE, etc.) |
| Managed | AccessManagedUpgradeable | Authority-based (ERC-7579 style) |
| Custom | — | Developer implements |

### 1.4 Upgradeability Options

| Option | Proxy Type | Where upgrade logic lives |
|--------|-----------|--------------------------|
| Transparent | TransparentUpgradeableProxy | Proxy has admin, impl has logic |
| UUPS | ERC1967Proxy | Implementation has upgradeToAndCall() |
| Beacon | BeaconProxy | Beacon contract points to impl |
| None | — | Non-upgradeable |

### 1.5 Security Implications per Combination

```
⚠️ ERC20 + FlashMinting + ERC4626 = BROKEN
   Flash-minting shares inflates totalSupply tanpa collateral
   → corrupt exchange rate selama flash loan
   → OZ docs explicitly warns against this

⚠️ ERC721 + Sequential + Consecutive = CONFLICT
   Sequential auto-increments, Consecutive uses ERC2309 batch
   → double counting atau gap di token IDs

⚠️ Governor + no Timelock = DANGEROUS
   Proposal execute langsung tanpa delay
   → flash loan governance attack possible
   → selalu pake TimelockController

⚠️ Upgradeable + constructor = BUG
   Constructor nggak jalan di proxy context
   → pake initializer() bukan constructor
   → Wizard otomatis handle ini, tapi custom code sering salah

⚠️ Ownable + Upgradeable + no _disableInitializers() = REINIT ATTACK
   Attacker bisa call init() di implementation contract
   → ambil ownership
   → Wizard adds _disableInitializers() otomatis
```

### 1.6 Common Misconfigurations

```
1. Lupa _disableInitializers() di constructor
   → Reinitialization attack on implementation

2. Storage collision saat upgrade
   → Tambah variable di tengah, bukan di akhir
   → Pake storage gap: uint256[50] private __gap;

3. Combine FlashMint + ERC4626
   → Exchange rate corruption

4. Governor tanpa quorum minimum
   → 1 vote bisa pass proposal

5. UUPS tanpa _authorizeUpgrade override
   → Siapa aja bisa upgrade (default = no restriction)

6. Pausable tapi transfer nggak di-pause
   → Token tetap bisa pindah saat "paused"
   → By design, tapi developer sering salah paham
```

---

## PART 2: OPENZEPPELIN DEFENDER

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                OZ DEFENDER                       │
├──────────┬──────────┬──────────┬────────────────┤
│ Sentinel │ Autotask │  Relay   │     Admin      │
│(Monitor) │(Scripts) │(Meta-tx) │ (Governance)   │
├──────────┴──────────┴──────────┴────────────────┤
│              Notify (Alerts)                     │
│   Email / Slack / Discord / Telegram / Webhook   │
├─────────────────────────────────────────────────┤
│              Forta Integration                   │
│   Decentralized threat detection network         │
└─────────────────────────────────────────────────┘
```

### 2.2 Sentinel (Monitoring)

**What it does:** Watches on-chain events/transactions and triggers alerts.

**Trigger types:**
```
1. Event-based    — monitor specific contract events
   Example: Transfer, Approval, OwnershipTransferred

2. Transaction    — monitor tx to/from specific addresses
   Example: all tx to a DeFi pool

3. Forta bot      — use Forta detection bots as triggers
   Example: bot that detects flash loan attacks

4. Block          — trigger on every N blocks
```

**Conditions:**
```
- Event signature match
- Address filter (from/to/contract)
- Value threshold (msg.value > X)
- Custom expression (JavaScript)
- Block range
```

**Notification channels:**
```
- Email
- Slack webhook
- Discord webhook
- Telegram bot
- Generic webhook (POST JSON)
- Autotask trigger (chain into automation)
```

**Example: Monitor large withdrawals from DeFi pool**
```javascript
// Sentinel config (via API/dashboard)
{
  type: "FORTA",
  addresses: ["0x803ea69c7e87D1d6C86adeB40CB636cC0E6B98E2"],
  fortaConditions: {
    alertIDs: ["FORTA-FLASH-LOAN-DETECTION"],
    minimumScannerCount: 3
  },
  notificationChannels: ["slack", "autotask-pause"]
}
```

### 2.3 Autotask (Automation Scripts)

**What it does:** Serverless functions triggered by Sentinel, schedule, or webhook.

**Trigger types:**
```
1. Sentinel  — runs when Sentinel fires
2. Schedule  — cron-like (every N minutes/hours)
3. Monitor   — contract monitoring
4. Webhook   — HTTP POST endpoint
```

**SDK (defender-sdk):**
```javascript
import { AutotaskClient } from 'defender-sdk/autotask';
import { RelayClient } from 'defender-sdk/relay';
import { SentinelClient } from 'defender-sdk/sentinel';

// Auth
const client = new AutotaskClient({
  apiKey: process.env.DEFENDER_API_KEY,
  apiSecret: process.env.DEFENDER_API_SECRET,
});
```

**Example: Auto-pause on exploit detection**
```javascript
// Autotask handler (runs in Defender's serverless env)
const { Relayer } = require('defender-sdk-relay');

exports.handler = async function(event) {
  const relayer = new Relayer(event);
  
  // Check if alert is valid
  const alert = event.request.body;
  if (alert.alertId !== "EXPLOIT_DETECTED") return;
  
  // Auto-pause the contract
  const tx = await relayer.sendTransaction({
    to: "0x803ea69c7e87D1d6C86adeB40CB636cC0E6B98E2",
    functionName: "pause()",
    abi: ["function pause()"],
    speed: "fast",
  });
  
  console.log("Contract paused:", tx.hash);
};
```

**Secrets management:**
```
- Encrypted at rest
- Injected as env vars at runtime
- Set via API or dashboard
- Never in code
```

### 2.4 Relay (Meta-Transactions)

**What it does:** Gas station for meta-transactions (EIP-2771).

**How it works:**
```
1. User signs message off-chain (no gas needed)
2. Your backend sends signed message to Defender Relay
3. Relay's relayer wallet pays gas and submits tx
4. Contract receives tx with original user as _msgSender()
```

**EIP-2771 integration:**
```solidity
// Contract side
import {ERC2771Context} from "@openzeppelin/contracts/metatx/ERC2771Context.sol";

contract MyContract is ERC2771Context {
    constructor(address trustedForwarder) ERC2771Context(trustedForwarder) {}
    
    function _msgSender() internal view override(Context, ERC2771Context) 
        returns (address) {
        return ERC2771Context._msgSender();
    }
}
```

**Relayer management:**
```
- Each relayer = a wallet with its own key
- Fund relayer with ETH for gas
- Set speed: safeLow / average / fast / fastest
- Policy: whitelist of allowed addresses/functions
- Quota: max gas per day
```

### 2.5 Admin (Governance Automation)

**What it does:** Create and manage governance proposals programmatically.

**Supported protocols:**
```
- Gnosis Safe (multisig)
- Compound Governor / GovernorBravo
- OZ Governor + TimelockController
- Custom governance
```

**Example: Create Safe proposal via API**
```javascript
import { AdminClient } from 'defender-sdk/admin';

const client = new AdminClient({ apiKey, apiSecret });

await client.createProposal({
  contract: { address: "0x...", network: "base" },
  title: "Emergency pause",
  description: "Pause lending pool due to exploit",
  type: "custom",
  via: ["0xSafeAddress"],
  viaType: "Gnosis Safe",
  metadata: {
    sendTo: "0x803ea69c...",
    functionName: "pause()",
    functionInputs: [],
  },
});
```

### 2.6 Pricing

```
Free tier:
  - 1 Sentinel monitor
  - 1 Autotask
  - Limited notifications

Paid (starts ~$50/month):
  - More monitors + autotasks
  - Forta integration
  - Priority notifications
  - Team features

Enterprise:
  - Custom SLA
  - Dedicated support
  - On-premise option
```

### 2.7 Security Considerations

```
⚠️ Autotask runs in Defender's cloud — NOT on-chain
   → Jangan simpan private keys di code
   → Pake Relayer (managed keys) bukan raw keys

⚠️ Sentinel latency — NOT real-time
   → Block confirmation delay
   → Bukan untuk MEV/front-running defense
   → Untuk detection + response (pause, alert)

⚠️ Relay = trusted forwarder
   → Relayer bisa submit tx atas nama user
   → Whitelist functions di contract
   → Jangan kasih relayer akses ke admin functions

⚠️ Admin = proposal creation, NOT execution
   → Still needs multisig/governance approval
   → Defender doesn't bypass governance
```

---

## PART 3: ADVANCED OZ CONTRACTS

### 3.1 Proxy Patterns Deep Dive

**ERC1967 Storage Slots:**
```
Implementation: keccak256("eip1967.proxy.implementation") - 1
  = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc

Admin: keccak256("eip1967.proxy.admin") - 1
  = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103

Beacon: keccak256("eip1967.proxy.beacon") - 1
  = 0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50
```

**Transparent vs UUPS vs Beacon:**

| | Transparent | UUPS | Beacon |
|---|---|---|---|
| Upgrade logic in | Proxy | Implementation | Beacon |
| Gas cost | Higher (proxy check) | Lower | Medium |
| Admin slot | Yes (ERC1967) | No | No |
| Risk if impl removed | Proxy still works | BRICKED | Beacon update fixes |
| _authorizeUpgrade | Not needed | MUST override | Not needed |
| Best for | Complex admin | Gas-sensitive | Multiple proxies |

**Storage Collision:**
```
DANGEROUS:
  V1: uint256 a; uint256 b; uint256 c;
  V2: uint256 a; uint256 NEW; uint256 b; uint256 c;
  → b and c SHIFTED, data corrupted

SAFE:
  V1: uint256 a; uint256 b; uint256 c; uint256[47] __gap;
  V2: uint256 a; uint256 b; uint256 c; uint256 d; uint256[46] __gap;
  → d takes from gap, no shift

RULE: ONLY append variables. NEVER insert or reorder.
```

**Initializer Vulnerabilities:**
```
1. Missing _disableInitializers() in constructor:
   → Attacker calls initialize() on implementation
   → Takes ownership of implementation
   → Can selfdestruct (pre-Cancun) or corrupt

2. Reinitializer pattern (v5.x):
   function initializeV2() external reinitializer(2) {
       // New state for V2
   }
   → Prevents calling V1 initializer again
   → Version number must increase monotonically

3. Initializer in proxy vs implementation:
   → Proxy: initializer runs via delegatecall ✓
   → Implementation: initializer runs directly ✗ (dangerous)
   → _disableInitializers() prevents this
```

### 3.2 Governor Deep Dive

**Lifecycle:**
```
1. propose()     → creates proposal, returns proposalId
   - Requires proposer to have >= proposalThreshold votes
   - Description hash prevents frontrunning (optional)

2. Voting period → users castVote / castVoteWithReason
   - votingDelay: blocks before voting starts
   - votingPeriod: blocks voting is open
   - Votes counted at snapshot (proposal creation block)

3. queue()       → sends to TimelockController
   - Only if proposal succeeded + quorum reached
   - TimelockController adds execution delay

4. execute()     → executes after timelock delay
   - Anyone can call
   - Calls target contracts with calldata

5. cancel()      → proposer or governor can cancel
   - Before execution only
```

**Attack Vectors:**
```
⚠️ Flash Loan Governance:
   1. Flash loan voting tokens
   2. Delegate to self
   3. Propose + vote in same tx? NO — snapshot prevents this
   4. But: if votingDelay = 0, propose + vote same block possible
   → MITIGATION: votingDelay > 0, snapshot mechanism

⚠️ Proposal Frontrunning:
   1. Attacker sees propose() in mempool
   2. Frontruns with same proposal (different description)
   3. Original proposer's proposal becomes duplicate
   → MITIGATION: _isValidDescriptionForProposer (hash check)

⚠️ Timelock Bypass:
   1. If no timelock, execute() is immediate
   2. Governance can drain treasury instantly
   → MITIGATION: Always use TimelockController

⚠️ Quorum Manipulation:
   1. If quorum = % of supply, attacker can reduce supply
   2. Burn tokens to lower quorum threshold
   → MITIGATION: Use absolute quorum or GovernorVotesQuorumFraction
```

### 3.3 ERC4626 Inflation Attack (CRITICAL for audits)

**The Attack:**
```
1. Attacker deposits 1 wei → gets 1 share (supply=0, shares=assets)
2. Attacker donates X assets directly to vault (transfer)
3. totalAssets() = X + 1, totalSupply() = 1
4. Victim deposits Y assets:
   shares = Y * 1 / (X + 1) = 0 (if Y < X)
5. Victim gets 0 shares, Y assets stuck in vault
6. Attacker redeems 1 share → gets X + Y + 1
```

**OZ v4.9+ Mitigation (Virtual Shares):**
```solidity
// OZ ERC4626.sol line 237-245
function _convertToShares(uint256 assets, Math.Rounding rounding) 
    internal view virtual returns (uint256) {
    return assets.mulDiv(
        totalSupply() + 10 ** _decimalsOffset(),  // +1 virtual share
        totalAssets() + 1,                         // +1 virtual asset
        rounding
    );
}

function _convertToAssets(uint256 shares, Math.Rounding rounding) 
    internal view virtual returns (uint256) {
    return shares.mulDiv(
        totalAssets() + 1,                         // +1 virtual asset
        totalSupply() + 10 ** _decimalsOffset(),  // +1 virtual share
        rounding
    );
}
```

**Key insight:**
```
_decimalsOffset() default = 0
→ virtual shares = 10^0 = 1
→ virtual assets = 1

With VAS = 1:
  Attack cost = donation amount
  Attacker profit ≈ 0 (virtual share captures donated value)
  → Attack NON-PROFITABLE even with offset = 0

With larger offset (e.g., 6):
  Virtual shares = 10^6
  → Attack becomes orders of magnitude more expensive
  → Recommended for high-value vaults
```

**Rounding Direction Security:**
```
OZ convention:
  previewDeposit  → Floor (user gets fewer shares)
  previewMint     → Ceil  (user pays more assets)
  previewWithdraw → Ceil  (user burns more shares)
  previewRedeem   → Floor (user gets fewer assets)

RULE: ALWAYS round in favor of the vault, never the user.
  Deposit/Withdraw: round against user
  This prevents "dust extraction" attacks
```

**⚠️ CRITICAL: totalAssets() uses balanceOf()**
```solidity
function totalAssets() public view virtual returns (uint256) {
    return IERC20(asset()).balanceOf(address(this));
}
```
```
This means ANY direct token transfer inflates totalAssets()
→ Same attack vector as Arcadia's donateToTranche()
→ OZ mitigates with virtual shares (+1/+1)
→ But protocols that override totalAssets() or use custom
  accounting (like Arcadia) may NOT have this protection
```

### 3.4 CrossChain (v5.6+)

**Architecture:**
```
CrosschainLinked (base)
  ├── BridgeFungible (ERC20 bridge)
  │   ├── BridgeERC20
  │   └── BridgeERC7802 (cross-chain ERC20)
  ├── BridgeNonFungible (ERC721 bridge)
  │   └── BridgeERC721
  └── BridgeMultiToken (ERC1155 bridge)
      └── BridgeERC1155
```

**ERC-7786 Gateway:**
```
- Standardized cross-chain messaging
- Gateway contract per chain
- InteroperableAddress = chain ref + address
- Counterpart verification on receive
```

**Security risks:**
```
⚠️ Replay attacks:
   → Same message replayed on different chains
   → MITIGATION: nonce tracking per chain

⚠️ Gateway compromise:
   → If gateway is malicious, can mint arbitrary tokens
   → MITIGATION: onlyOwner link registration

⚠️ Bridge inflation:
   → Mint on destination without burn on source
   → MITIGATION: atomic lock/mint or burn/mint
```

### 3.5 Account (ERC-4337)

**Components:**
```
Account.sol (base)
  ├── validateUserOp()     — signature validation
  ├── _payPrefund()        — pay EntryPoint for gas
  ├── getNonce()           — replay protection
  └── entryPoint()         — canonical EntryPoint v0.9

Extensions:
  ├── AccountERC7579       — modular account (ERC-7579)
  ├── AccountERC7579Hooked — with hooks
  └── ERC7821             — batch execution

Paymaster:
  ├── Paymaster.sol        — base (sponsor gas)
  ├── PaymasterERC20       — pay gas in ERC20
  ├── PaymasterSigner      — signature-based
  └── PaymasterERC721Owner — NFT-gated

Utils:
  ├── ERC4337Utils         — UserOp hashing, packing
  ├── EIP7702Utils         — EIP-7702 delegation
  └── ERC7579Utils         — modular account utils
```

**Security considerations:**
```
⚠️ Signature validation is CRITICAL
   → Must implement _rawSignatureValidation correctly
   → Use SignerECDSA / SignerP256 / SignerRSA
   → Wrong implementation = full account takeover

⚠️ Nonce management
   → EntryPoint tracks nonces per (account, key)
   → Multiple keys = parallel UserOps
   → Wrong key management = replay attacks

⚠️ Paymaster = gas sponsor
   → Paymaster pays gas for users
   → Must validate UserOp before sponsoring
   → Or get drained by spam UserOps
```

### 3.6 Security Utilities

**ReentrancyGuardTransient (EIP-1153):**
```solidity
// Uses transient storage (tload/tstore) instead of regular storage
// Gas: ~100 gas vs ~20,000 gas for regular ReentrancyGuard
// Available: v5.1+
// Requires: EIP-1153 support (Cancun+)

modifier nonReentrant() {
    _nonReentrantBefore();  // tload + tstore(true)
    _;
    _nonReentrantAfter();   // tstore(false)
}

// Also has nonReentrantView() for view functions
// → Prevents reading inconsistent state during reentrancy
```

**StorageSlot:**
```solidity
// Type-safe access to arbitrary storage slots
// Used by ERC1967, ERC7201 (namespaced storage)
StorageSlot.getAddressSlot(slot).value = newImpl;
StorageSlot.getUint256Slot(slot).value = 42;
StorageSlot.getBooleanSlot(slot).value = true;
```

**ShortStrings:**
```solidity
// Store strings <= 31 bytes in a single storage slot
// Saves gas for name/symbol storage
// Falls back to regular string for longer values
```

### 3.7 Known CVEs & Security Advisories

```
1. ERC4626 Inflation Attack (2022)
   → First depositor can steal subsequent deposits
   → Fixed in v4.9 with virtual shares/assets
   → Severity: HIGH

2. GovernorCompatibilityBravo double voting (2022)
   → Could vote twice on same proposal
   → Fixed in v4.7.3
   → Severity: MEDIUM

3. ERC165Checker infinite loop (2022)
   → Malicious contract could cause infinite loop
   → Fixed in v4.8.1
   → Severity: LOW

4. TimelockController bypass (2023)
   → PROPOSER_ROLE could schedule arbitrary operations
   → Fixed: added CANCELLER_ROLE separation
   → Severity: MEDIUM

5. Initializable reinitializer (2023)
   → reinitializer(1) could be called multiple times
   → Fixed: version must be > current
   → Severity: LOW

6. ERC2771Context + multicall (2023)
   → _msgSender() could be spoofed via multicall
   → Fixed: check msg.sender in multicall
   → Severity: MEDIUM

7. Ownable2Step acceptOwnership (2024)
   → Pending owner could be frontrun
   → Not a bug, but design consideration
   → Severity: INFO
```

### 3.8 Common Integration Mistakes

```
1. Using OZ ERC4626 with rebasing tokens (AMPL, stETH)
   → totalAssets() = balanceOf() changes without deposits
   → Share price manipulation
   → FIX: Use wrapper (WAMPL) or override totalAssets()

2. Upgradeable contract with constructor logic
   → Constructor doesn't run in proxy context
   → State set in constructor is LOST
   → FIX: Move to initializer()

3. AccessControl without DEFAULT_ADMIN_ROLE management
   → Grant roles but can't revoke (admin lost)
   → FIX: Always keep DEFAULT_ADMIN_ROLE in multisig

4. Governor with votingDelay = 0
   → Flash loan governance attack
   → FIX: votingDelay >= 1 block

5. TransparentProxy + implementation has receive()
   → ETH sent to proxy gets stuck
   → FIX: Use UUPS or handle ETH explicitly

6. ERC20Permit + replay across chains
   → Same permit valid on all chains with same address
   → FIX: Add chainId to domain separator (OZ does this)
   → But: if chain forks, chainId might be same

7. Pausable but not pausing critical functions
   → Developer adds whenNotPaused to transfer but not approve
   → Attacker approves during "pause" then transfers after unpause
   → FIX: Pause ALL state-changing functions

8. Missing storage gap in upgradeable base contract
   → Derived contracts can't add variables safely
   → FIX: Always include uint256[50] private __gap;
```

---

## PART 4: AUDIT CHECKLIST (OZ-SPECIFIC)

### When auditing a contract that uses OZ:

```
□ Check OZ version — known CVEs for that version?
□ Check proxy pattern — Transparent/UUPS/Beacon?
□ Check _disableInitializers() in constructor
□ Check storage layout — gaps? appended only?
□ Check ERC4626 — virtual shares? _decimalsOffset()?
□ Check Governor — timelock? votingDelay? quorum?
□ Check AccessControl — who has DEFAULT_ADMIN_ROLE?
□ Check ReentrancyGuard — on ALL external write functions?
□ Check Pausable — on ALL state-changing functions?
□ Check totalAssets() — balanceOf() or custom accounting?
□ Check rounding direction — favors vault or user?
□ Check cross-chain — replay protection? gateway trust?
□ Check ERC-4337 — signature validation? nonce? paymaster?
```

---

*BOZAGENTIC · "Know the library, find the bug."*
*OZ is the most used Solidity library. Knowing its internals = knowing where developers go wrong.*
