# OPENZEPPOLIN v5.6.1 — MASTER REFERENCE
# Dibaca dari source. 368 kontrak. 13 module.
# BOZAGENTIC · 2026-07-29

---

## 1. TOKEN STANDARDS

### 1.1 ERC20 (token/ERC20/ERC20.sol)

**Arsitektur:**
```
abstract contract ERC20 is Context, IERC20, IERC20Metadata, IERC20Errors
```

**Storage:**
```solidity
mapping(address => uint256) private _balances;
mapping(address => mapping(address => uint256)) private _allowances;
uint256 private _totalSupply;
string private _name;
string private _symbol;
```

**Core pattern — _update():**
Semua transfer/mint/burn flow melalui 1 fungsi internal:
```solidity
function _update(address from, address to, uint256 value) internal virtual {
    if (from == address(0)) _totalSupply += value;     // mint
    else _balances[from] -= value;                      // debit
    if (to == address(0)) _totalSupply -= value;        // burn
    else _balances[to] += value;                        // credit
    emit Transfer(from, to, value);
}
```
→ Override `_update()` buat custom logic (fees, hooks, voting). JANGAN override `_transfer()`.

**Allowance — infinite approval optimization:**
```solidity
function _spendAllowance(address owner, address spender, uint256 value) internal {
    uint256 currentAllowance = allowance(owner, spender);
    if (currentAllowance < type(uint256).max) {  // skip kalau max
        _approve(owner, spender, currentAllowance - value, false);
    }
}
```
→ `type(uint256).max` = infinite approve, nggak dikurangin. Gas saving.

**Security notes:**
- Revert on failure (bukan return false) — custom errors (ERC20InsufficientBalance, dll)
- Zero address checks di semua entry point
- `_approve()` punya variant `emitEvent` bool — skip Approval event di transferFrom (gas saving)

### 1.2 ERC20 Extensions

| Extension | Fungsi | Security Note |
|-----------|--------|---------------|
| **ERC20Permit** | Approve via EIP-712 signature (gasless) | Nonce per-owner, deadline check, ECDSA recover |
| **ERC20Votes** | Checkpoint-based voting power | Max supply 2^208-1, delegate pattern |
| **ERC4626** | Tokenized vault (shares ↔ assets) | ⚠️ DONATION ATTACK RISK — virtual shares mitigation |
| **ERC20FlashMint** | ERC-3156 flash loans | ⚠️ JANGAN combine dengan ERC4626 (inflates supply) |
| **ERC20Capped** | Supply cap | Override `_update()` |
| **ERC20Pausable** | Emergency stop | Override `_update()`, check `whenNotPaused` |
| **ERC20Burnable** | Public burn | Wrapper around `_burn()` |
| **ERC20Wrapper** | Wrap underlying token | deposit/withdraw pattern |
| **ERC1363** | Transfer-and-call | ERC20 + callback to receiver |

### 1.3 ERC4626 — Vault Standard (CRITICAL FOR AUDIT)

**Donation/Inflation Attack:**
```
1. Attacker deposit 1 wei → dapat 1 share
2. Attacker donate 1000 ETH langsung ke vault
3. totalAssets naik, tapi totalSupply tetap 1
4. 1 share = 1000 ETH sekarang
5. Victim deposit 1000 ETH → dapat 0 share (rounding)
6. Attacker redeem 1 share → dapat 2000 ETH
```

**OZ mitigation — virtual shares:**
```solidity
function _convertToShares(uint256 assets, Math.Rounding rounding) internal view {
    return assets.mulDiv(totalSupply() + 10**_decimalsOffset(), totalAssets() + 1, rounding);
}
```
→ `+1` di totalAssets dan `+10^offset` di totalSupply bikin attack non-profitable.

**Reentrancy protection:**
```solidity
function _deposit(...) internal {
    _transferIn(caller, assets);  // transfer DULU
    _mint(receiver, shares);       // mint KEMUDIAN
}
function _withdraw(...) internal {
    _burn(owner, shares);          // burn DULU
    _transferOut(receiver, assets); // transfer KEMUDIAN
}
```
→ CEI pattern (Checks-Effects-Interactions). Transfer before mint, burn before transfer.

### 1.4 ERC721, ERC1155, ERC6909

- **ERC721**: NFT, `_update()` pattern sama kayak ERC20, `safeTransfer` checks ERC721Receiver
- **ERC1155**: Multi-token, batch operations, URI storage
- **ERC6909**: Minimal multi-token (baru), content URI, token supply tracking

### 1.5 SafeERC20 (WAJIB DIPAKE)

```solidity
using SafeERC20 for IERC20;
token.safeTransfer(to, amount);
token.safeTransferFrom(from, to, amount);
token.forceApprove(spender, amount);  // USDT-compatible (approve 0 dulu)
```

**Kenapa butuh:** Beberapa token (USDT) nggak return bool dari transfer(). SafeERC20 handle itu via low-level call + returndata check.

**Assembly-level implementation:**
```solidity
success := call(gas(), token, 0, 0x00, 0x44, 0x00, 0x20)
// Check: success AND (return == true OR returndata empty AND token has code)
success := and(success, and(iszero(returndatasize()), gt(extcodesize(token), 0)))
```

---

## 2. ACCESS CONTROL

### 2.1 Ownable

```solidity
abstract contract Ownable is Context {
    address private _owner;
    modifier onlyOwner() { _checkOwner(); _; }
    function transferOwnership(address newOwner) public onlyOwner;
    function renounceOwnership() public onlyOwner;  // → address(0), IRREVERSIBLE
}
```

**Audit checklist:**
- ✅ Constructor set owner? (v5: explicit `constructor(address initialOwner)`)
- ✅ Zero address check? (v5: yes, revert OwnableInvalidOwner)
- ⚠️ renounceOwnership() = no more admin. Pastikan nggak ada fungsi critical yang butuh owner.

### 2.2 Ownable2Step

```solidity
function transferOwnership(address newOwner) public onlyOwner;  // step 1: propose
function acceptOwnership() public;  // step 2: new owner accepts
```
→ Lebih aman dari Ownable. Nggak bisa accidentally transfer ke wrong address.

### 2.3 AccessControl (Role-Based)

```solidity
bytes32 public constant MY_ROLE = keccak256("MY_ROLE");
modifier onlyRole(bytes32 role);
function grantRole(bytes32 role, address account) onlyRole(getRoleAdmin(role));
function revokeRole(bytes32 role, address account) onlyRole(getRoleAdmin(role));
function renounceRole(bytes32 role, address callerConfirmation);
```

**Pattern:**
- DEFAULT_ADMIN_ROLE (0x00) = admin of all roles by default
- `_setRoleAdmin()` buat custom hierarchy
- `renounceRole()` butuh `callerConfirmation == msg.sender` (anti-phishing)

**Extensions:**
- `AccessControlEnumerable` — on-chain role member enumeration
- `AccessControlDefaultAdminRules` — delay + 2-step for admin transfer

### 2.4 AccessManager (v5 NEW)

Full permission system:
```
AccessManager (central authority)
  → defines operations (target + selector)
  → assigns roles to operations
  → sets execution delays per role
  → supports scheduled operations (timelock built-in)
```

---

## 3. PROXY PATTERNS (CRITICAL FOR AUDIT)

### 3.1 ERC1967 Storage Slots

```
Implementation: 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc
Admin:          0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
Beacon:         0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50
```
→ `cast storage $PROXY 0x360894...` = implementation address

### 3.2 Transparent Proxy

```
User calls proxy → fallback → delegatecall to implementation
Admin calls proxy → upgradeToAndCall() ONLY (can't call implementation)
```

**Security:**
- Admin = immutable (set di constructor, nggak bisa diubah)
- ProxyAdmin contract deployed automatically
- Selector clashing prevented: admin can ONLY upgrade, user can ONLY call implementation

### 3.3 UUPS Proxy

```solidity
abstract contract UUPSUpgradeable is IERC1822Proxiable {
    address private immutable __self = address(this);
    modifier onlyProxy();      // must be called via delegatecall
    modifier notDelegated();   // must NOT be called via delegatecall
    function _authorizeUpgrade(address) internal virtual;  // OVERRIDE THIS
}
```

**Security:**
- `_checkProxy()`: `address(this) != __self` AND `ERC1967Utils.getImplementation() == __self`
- `proxiableUUID()` punya `notDelegated` — prevent proxy pointing to another proxy (infinite loop)
- `_authorizeUpgrade()` MUST be overridden with access control (e.g., `onlyOwner`)

**Audit checklist:**
- ⚠️ Implementation contract punya `_authorizeUpgrade()` with proper access control?
- ⚠️ Implementation contract punya `UUPSUpgradeable` in inheritance?
- ⚠️ Storage layout compatible between versions?

### 3.4 Beacon Proxy

```
BeaconProxy → reads implementation from UpgradeableBeacon
UpgradeableBeacon → owner can upgrade ALL proxies at once
```
→ 1 upgrade = all proxies updated. Efficient tapi centralized risk.

### 3.5 Clones (EIP-1167)

```solidity
library Clones {
    function clone(address implementation) internal returns (address);
    function cloneDeterministic(address implementation, bytes32 salt) internal returns (address);
    function predictDeterministicAddress(address implementation, bytes32 salt) internal view returns (address);
}
```
→ Minimal proxy (45 bytes). No upgradeability. Cheap deployment.

### 3.6 Initializable

```solidity
abstract contract Initializable {
    modifier initializer();       // first init
    modifier reinitializer(uint8 version);  // subsequent upgrades
    function _disableInitializers() internal;  // lock implementation contract
}
```

**Audit checklist:**
- ⚠️ Implementation contract call `_disableInitializers()` in constructor?
- ⚠️ `initializer` modifier on init function?
- ⚠️ Version incremented on re-initialization?

---

## 4. SECURITY UTILITIES

### 4.1 ReentrancyGuard

```solidity
uint256 private constant NOT_ENTERED = 1;
uint256 private constant ENTERED = 2;

modifier nonReentrant() {
    _nonReentrantBefore();  // check + set ENTERED
    _;
    _nonReentrantAfter();   // set NOT_ENTERED
}
```

**v5 changes:**
- Storage slot: `0x9b779b17422d0df92223018b32b4d1fa46e071723d6817e2486d003becc55f00`
- `nonReentrantView` modifier — block view functions during reentrancy
- **DEPRECATED** — v6 will use `ReentrancyGuardTransient` (EIP-1153 transient storage)

**ReentrancyGuardTransient (EIP-1153):**
```solidity
// Uses transient storage (TSTORE/TLOAD) — cheaper, auto-cleared per tx
modifier nonReentrant() {
    // tload(slot) check → tstore(slot, 1) → execute → tstore(slot, 0)
}
```

### 4.2 Pausable

```solidity
bool private _paused;
modifier whenNotPaused();
modifier whenPaused();
function _pause() internal whenNotPaused;
function _unpause() internal whenPaused;
```
→ Combine dengan `Ownable` atau `AccessControl` buat access-restricted pause.

### 4.3 Create2

```solidity
library Create2 {
    function deploy(uint256 amount, bytes32 salt, bytes memory bytecode) internal returns (address);
    function computeAddress(bytes32 salt, bytes32 bytecodeHash) internal view returns (address);
    function computeAddress(bytes32 salt, bytes32 bytecodeHash, address deployer) internal pure returns (address);
}
```
→ `address = keccak256(0xff ++ deployer ++ salt ++ keccak256(bytecode))`

**Security:** Salt reuse with same bytecode = revert (address already occupied).

### 4.4 Create3

Deploy to deterministic address WITHOUT bytecode dependency:
```
address = f(deployer, salt)  // independent of bytecode
```
→ Useful for counterfactual deployments.

---

## 5. CRYPTOGRAPHY

### 5.1 ECDSA

```solidity
library ECDSA {
    function recover(bytes32 hash, bytes memory signature) internal pure returns (address);
    function tryRecover(bytes32 hash, bytes memory signature) internal pure returns (address, RecoverError, bytes32);
}
```

**Security:**
- Rejects malleable signatures (s must be in lower half order)
- Only 65-byte signatures (v, r, s)
- `hash` MUST be hashed data — never pass raw data to recover

### 5.2 EIP712

```solidity
abstract contract EIP712 {
    constructor(string memory name, string memory version);
    function _domainSeparatorV4() internal view returns (bytes32);
    function _hashTypedDataV4(bytes32 structHash) internal view returns (bytes32);
}
```
→ Domain: `keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")`

### 5.3 MerkleProof

```solidity
library MerkleProof {
    function verify(bytes32[] memory proof, bytes32 root, bytes32 leaf) internal pure returns (bool);
    function multiProofVerify(...) internal pure returns (bool);
    function processMultiProof(...) internal pure returns (bytes32);
}
```
→ Sorted pairs (commutative hashing) — prevents second preimage attacks.

### 5.4 SignatureChecker

```solidity
library SignatureChecker {
    function isValidSignatureNow(address signer, bytes32 hash, bytes memory signature) internal view returns (bool);
}
```
→ Supports both EOA (ECDSA) and contract (ERC-1271) signers.

### 5.5 New in v5: P256, RSA, WebAuthn

- **P256**: secp256r1 signature verification (passkeys)
- **RSA**: PKCS#1 v1.5 verification
- **WebAuthn**: FIDO2/WebAuthn authentication
- **ERC7913**: Multi-signer framework (ECDSA, P256, RSA, WebAuthn signers)

---

## 6. GOVERNANCE

### 6.1 Governor

```solidity
abstract contract Governor is Context, ERC165, EIP712, Nonces, IGovernor {
    struct ProposalCore {
        address proposer;
        uint48 voteStart;
        uint32 voteDuration;
        bool executed;
        bool canceled;
        uint48 etaSeconds;
    }
}
```

**Lifecycle:** Pending → Active → Defeated/Succeeded → Queued → Executed/Canceled

**Required overrides:**
- `_quorumReached()` — counting module
- `_voteSucceeded()` — counting module
- `_countVote()` — counting module
- `_getVotes()` — voting module
- `votingPeriod()`, `votingDelay()`, `quorum()`

**Extensions:**
| Extension | Purpose |
|-----------|---------|
| GovernorCountingSimple | For/Against/Abstain |
| GovernorCountingFractional | Fractional voting |
| GovernorVotes | ERC20Votes/ERC721Votes integration |
| GovernorVotesQuorumFraction | Quorum as % of supply |
| GovernorTimelockControl | Timelock integration |
| GovernorPreventLateQuorum | Extend voting if quorum reached late |
| GovernorSettings | Configurable parameters |
| GovernorStorage | On-chain proposal storage |
| GovernorCrosschain | Cross-chain governance |

### 6.2 TimelockController

```solidity
contract TimelockController is AccessControl, ERC721Holder, ERC1155Holder {
    bytes32 PROPOSER_ROLE;
    bytes32 EXECUTOR_ROLE;
    bytes32 CANCELLER_ROLE;
    uint256 private _minDelay;
}
```

**Flow:** schedule() → wait(delay) → execute()
**Security:** Operations have unique ID (hash of params). Can't execute before delay. Predecessor support for ordering.

---

## 7. FINANCE

### 7.1 VestingWallet

```solidity
contract VestingWallet is Context, Ownable {
    uint64 private immutable _start;
    uint64 private immutable _duration;
    // Linear vesting: vested = total * (now - start) / duration
}
```

**Security notes:**
- ⚠️ Ownership transferable → can sell unvested tokens
- ⚠️ Rebase tokens break vesting math
- ⚠️ Native ERC20 chains: double-withdraw risk (ERC20 + native)
- VestingWalletCliff: adds cliff period before vesting starts

---

## 8. CROSSCHAIN (v5 NEW)

### 8.1 Bridge Contracts

```
BridgeERC20   — lock/mint pattern for fungible tokens
BridgeERC721  — lock/mint for NFTs
BridgeERC1155 — lock/mint for multi-tokens
BridgeERC7802 — crosschain fungible token standard
```

### 8.2 CrosschainLinked

```solidity
abstract contract CrosschainLinked {
    // Links remote contracts across chains
    // Uses CAIP-2 (chain ID) and CAIP-10 (account ID) standards
}
```

---

## 9. ACCOUNT ABSTRACTION (v5 NEW)

### 9.1 ERC-4337 Support

```
Account.sol          — Base smart account
ERC4337Utils.sol     — UserOperation helpers
Paymaster.sol        — Gas sponsorship
PaymasterERC20.sol   — Pay gas in ERC20
```

### 9.2 ERC-7579 (Modular Accounts)

```
draft-AccountERC7579.sol      — Modular account standard
draft-AccountERC7579Hooked.sol — With hook support
draft-ERC7579Utils.sol        — Execution helpers
```

### 9.3 ERC-7821 (Batch Execution)

```
draft-ERC7821.sol — Minimal batch execution for smart accounts
```

---

## 10. METATX

### 10.1 ERC-2771

```solidity
abstract contract ERC2771Context is Context {
    // Trusted forwarder can relay transactions
    // _msgSender() returns original sender from calldata
    function isTrustedForwarder(address forwarder) public view virtual returns (bool);
}
```

### 10.2 ERC2771Forwarder

```solidity
contract ERC2771Forwarder is EIP712 {
    // Batch relay with nonce management
    // execute() and executeBatch()
}
```

---

## 11. UTILS — DATA STRUCTURES

| Struct | Use Case |
|--------|----------|
| **EnumerableSet** | Set with O(1) add/remove/contains + enumeration |
| **EnumerableMap** | Map with O(1) operations + enumeration |
| **Checkpoints** | Historical value tracking (voting, vesting) |
| **BitMaps** | Compact boolean storage |
| **DoubleEndedQueue** | FIFO/LIFO queue |
| **CircularBuffer** | Fixed-size ring buffer |
| **Heap** | Min/max heap |
| **MerkleTree** | On-chain incremental Merkle tree |
| **Accumulators** | Running sum/product |

---

## 12. UTILS — MATH & CRYPTO

| Library | Key Functions |
|---------|---------------|
| **Math** | `mulDiv()` (overflow-safe), `log2()`, `average()`, `ceilDiv()` |
| **SafeCast** | `toUint128()`, `toInt64()`, etc. — revert on overflow |
| **SignedMath** | `abs()`, `min()`, `max()` for int256 |
| **Strings** | `toString()`, `toHexString()`, `equal()` |
| **Base64** | `encode()` |
| **RLP** | `encode()` for RLP encoding |
| **Packing** | `pack()`, `extract()` for storage packing |
| **SlotDerivation** | Derive storage slots (ERC-7201 namespaced storage) |
| **StorageSlot** | Typed storage slot access |
| **TransientSlot** | EIP-1153 transient storage |

---

## 13. AUDIT CHECKLIST — OZ PATTERNS

### Token Audit
- [ ] Uses `_update()` override pattern (not `_transfer()`)?
- [ ] SafeERC20 for external token interactions?
- [ ] Zero address checks?
- [ ] Infinite allowance handled (`type(uint256).max`)?
- [ ] ERC4626: virtual shares for donation attack mitigation?
- [ ] ERC4626: NOT combined with ERC20FlashMint?
- [ ] ERC20Permit: nonce + deadline + ECDSA?

### Access Control Audit
- [ ] Ownable: constructor sets owner explicitly?
- [ ] Ownable2Step for critical contracts?
- [ ] AccessControl: DEFAULT_ADMIN_ROLE secured?
- [ ] No missing `onlyOwner`/`onlyRole` on privileged functions?
- [ ] renounceOwnership() implications understood?

### Proxy Audit
- [ ] ERC-1967 storage slots correct?
- [ ] Implementation has `_disableInitializers()` in constructor?
- [ ] UUPS: `_authorizeUpgrade()` has access control?
- [ ] Transparent: admin ≠ user (no selector clashing)?
- [ ] Storage layout compatible across upgrades?
- [ ] Beacon: single point of failure understood?

### Security Audit
- [ ] ReentrancyGuard on external call functions?
- [ ] CEI pattern (Checks-Effects-Interactions)?
- [ ] Pausable for emergency stop?
- [ ] ECDSA: hash before recover?
- [ ] EIP-712: domain separator includes chainId?
- [ ] MerkleProof: sorted pairs?
- [ ] Create2: salt collision handled?

### Governance Audit
- [ ] Timelock delay sufficient?
- [ ] Quorum threshold reasonable?
- [ ] Voting period adequate?
- [ ] Proposer/Executor roles separated?
- [ ] Guardian/cancel mechanism exists?

---

## 14. V5 vs V4 BREAKING CHANGES

| Change | V4 | V5 |
|--------|----|----|
| Ownable constructor | `Ownable()` (msg.sender) | `Ownable(address initialOwner)` |
| Errors | `require("string")` | Custom errors (`revert ERC20InsufficientBalance()`) |
| SafeMath | Required | Removed (Solidity 0.8+ built-in) |
| `_setupRole()` | Exists | Removed → use `_grantRole()` |
| ERC1155 `_setURI()` | Exists | Removed → use `ERC1155URIStorage` |
| Proxy admin | Mutable storage | Immutable (TransparentProxy) |
| ReentrancyGuard | Regular storage | Deprecated → TransientStorage in v6 |

---

*Dibaca dari source OpenZeppelin Contracts v5.6.1*
*368 contracts · 13 modules · 0 mocks/vendor*
*BOZAGENTIC · "Learn the standard. Find the deviation."*
