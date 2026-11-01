# OZ GOVERNANCE — COMPLETE MASTER REFERENCE
# OpenZeppelin Contracts v5.6.1 · 23 contracts · 4308 lines
# BOZAGENTIC · 2026-07-30

---

## 1. ARCHITECTURE OVERVIEW

```
Governor.sol (825 lines) — CORE, abstract
├── IGovernor.sol — interface + ProposalState enum
├── TimelockController.sol (470 lines) — execution delay
│
├── Extensions (16):
│   ├── COUNTING:
│   │   ├── GovernorCountingSimple — For/Against/Abstain
│   │   ├── GovernorCountingFractional — split votes (ERC-6947)
│   │   └── GovernorCountingOverridable — token holders override delegate
│   │
│   ├── VOTING POWER:
│   │   ├── GovernorVotes — token-based voting (ERC-5805)
│   │   ├── GovernorVotesQuorumFraction — quorum = % of supply
│   │   └── GovernorVotesSuperQuorumFraction — super quorum = %
│   │
│   ├── TIMELOCK:
│   │   ├── GovernorTimelockControl — OZ TimelockController
│   │   ├── GovernorTimelockCompound — Compound Timelock
│   │   └── GovernorTimelockAccess — AccessManager integration
│   │
│   ├── SETTINGS:
│   │   ├── GovernorSettings — configurable delay/period/threshold
│   │   ├── GovernorPreventLateQuorum — extend deadline on late quorum
│   │   └── GovernorSuperQuorum — early pass if super quorum reached
│   │
│   ├── STORAGE & ID:
│   │   ├── GovernorStorage — on-chain proposal enumeration
│   │   ├── GovernorSequentialProposalId — sequential IDs
│   │   └── GovernorNoncesKeyed — parallel vote signing
│   │
│   ├── ADMIN:
│   │   └── GovernorProposalGuardian — cancel any proposal
│   │
│   └── CROSS-CHAIN:
│       └── GovernorCrosschain — execute on remote chains
│
└── Utils:
    ├── Votes.sol (245 lines) — delegation + checkpoints
    ├── VotesExtended.sol — delegation history tracking
    └── IVotes.sol — interface
```

---

## 2. PROPOSAL LIFECYCLE (State Machine)

```
                    ┌──────────┐
                    │ Pending  │  (voteStart > currentBlock)
                    └────┬─────┘
                         │ votingDelay passes
                    ┌────▼─────┐
         ┌─────────│  Active  │─────────┐
         │         └────┬─────┘         │
         │              │ votingPeriod   │
         │              │ ends           │
         │         ┌────▼──────────┐     │
         │         │ Check quorum  │     │
         │         │ + votes       │     │
         │         └──┬────────┬───┘     │
         │            │        │         │
    ┌────▼────┐  ┌────▼───┐  ┌▼────┐    │
    │Canceled │  │Defeated│  │Succ.│    │
    └─────────┘  └────────┘  └──┬──┘    │
                                │        │
                           ┌────▼────┐   │
                           │ Queued  │   │ (if timelock)
                           └────┬────┘   │
                                │ delay  │
                           ┌────▼────┐   │
                           │Executed │   │
                           └─────────┘   │
                                         │
                                    ┌────▼────┐
                                    │ Expired │ (timelock expired)
                                    └─────────┘
```

**ProposalState enum:**
```
0 = Pending     — created, voting not started
1 = Active      — voting in progress
2 = Canceled    — canceled by proposer/guardian
3 = Defeated    — quorum not reached OR votes failed
4 = Succeeded   — passed, no timelock needed
5 = Queued      — passed, in timelock waiting
6 = Expired     — timelock window passed without execution
7 = Executed    — executed successfully
```

---

## 3. CORE FUNCTIONS (Governor.sol)

### 3.1 propose()
```solidity
function propose(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    string memory description
) public virtual returns (uint256 proposalId)
```
```
Checks:
  1. _isValidDescriptionForProposer() — frontrunning protection
  2. proposalThreshold() — proposer needs enough votes
  3. _propose() — creates ProposalCore struct

ProposalCore:
  - proposer: address
  - voteStart: uint48 (block number)
  - voteDuration: uint32
  - executed: bool
  - canceled: bool
  - etaSeconds: uint48 (timelock ETA)

ProposalId = keccak256(targets, values, calldatas, descriptionHash)
  ⚠️ NO chainId, NO governor address
  → Same proposal on different chains = SAME ID
  → Must change description for re-submission
```

### 3.2 castVote() / castVoteBySig()
```solidity
// Direct vote
castVote(proposalId, support)  // support: 0=Against, 1=For, 2=Abstain

// Meta-transaction vote (gasless)
castVoteBySig(proposalId, support, voter, signature)

// Extended vote with reason + params
castVoteWithReasonAndParams(proposalId, support, reason, params)
```
```
Vote validation:
  1. State must be Active
  2. _getVotes(account, snapshot, params) — voting weight at snapshot
  3. _countVote() — module-specific counting
  4. _tallyUpdated() — hook for late quorum extension

Signature: EIP-712 typed data
  BALLOT_TYPEHASH = keccak256("Ballot(uint256 proposalId,uint8 support,address voter,uint256 nonce)")
  → Nonce prevents replay
  → SignatureChecker supports ERC-1271 (contract wallets)
```

### 3.3 execute()
```solidity
function execute(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    bytes32 descriptionHash
) public payable virtual returns (uint256)
```
```
CRITICAL SECURITY:
  1. executed = true BEFORE external calls (CEI pattern)
  2. If executor != governor (timelock):
     → Push calldata hashes to _governanceCall queue
     → onlyGovernance modifier pops from queue
     → Queue cleared after execution
  3. _executeOperations() — calls targets with calldata
  4. Anyone can call execute() once ready
```

### 3.4 cancel()
```solidity
function cancel(targets, values, calldatas, descriptionHash) public
```
```
Default: only proposer can cancel, only during Pending state
Override: GovernorProposalGuardian allows guardian to cancel ANY state
```

### 3.5 onlyGovernance modifier
```solidity
modifier onlyGovernance() {
    _checkGovernance();
    _;
}

function _checkGovernance() internal virtual {
    // 1. msg.sender must be executor (governor or timelock)
    if (_executor() != _msgSender()) revert;
    
    // 2. If executor is timelock, calldata must be whitelisted
    if (_executor() != address(this)) {
        bytes32 msgDataHash = keccak256(_msgData());
        while (_governanceCall.popFront() != msgDataHash) {}
    }
}
```
```
This prevents:
  - Timelock proposers from directly calling governor setters
  - Must go through full governance proposal flow
  - Queue is populated during execute(), consumed by modifier
```

---

## 4. TIMELOCK CONTROLLER (470 lines)

### 4.1 Roles
```
DEFAULT_ADMIN_ROLE — grant/revoke other roles (self-administered)
PROPOSER_ROLE      — schedule operations
EXECUTOR_ROLE      — execute ready operations
CANCELLER_ROLE     — cancel pending operations

⚠️ Granting role to address(0) = OPEN ROLE (anyone can do it)
   onlyRoleOrOpenRole(EXECUTOR_ROLE) checks this
```

### 4.2 Operation Flow
```
schedule(target, value, data, predecessor, salt, delay)
  → id = keccak256(target, value, data, predecessor, salt)
  → timestamps[id] = block.timestamp + delay
  → delay must be >= minDelay

execute(target, value, payload, predecessor, salt)
  → _beforeCall: check Ready + predecessor Done
  → _execute: target.call{value}(payload)
  → _afterCall: timestamps[id] = DONE_TIMESTAMP (1)

cancel(id)
  → delete timestamps[id]
```

### 4.3 Operation States
```
Unset   (timestamp = 0)  — never scheduled
Waiting (timestamp > now) — scheduled, not yet ready
Ready   (timestamp <= now) — can be executed
Done    (timestamp = 1)   — already executed
```

### 4.4 Security Notes
```
⚠️ updateDelay() — ONLY callable by timelock itself
   → Must schedule + execute through timelock
   → Cannot be called directly by admin

⚠️ execute() has NO reentrancy guard
   → Comment says: "_afterCall checks proposal is pending"
   → Reentrancy during execute could re-enter but _afterCall
     would fail because operation is no longer Ready
   → Safe by design, but worth auditing in context

⚠️ Batch execution is ATOMIC
   → If one call fails, entire batch reverts
   → predecessor dependency: operation B waits for A

⚠️ minDelay can be set to 0
   → Operations execute immediately
   → Defeats purpose of timelock
   → Audit: check deployed minDelay value
```

---

## 5. COUNTING MODULES

### 5.1 GovernorCountingSimple (96 lines)
```
3 options: Against (0), For (1), Abstain (2)

_quorumReached: forVotes + abstainVotes >= quorum
_voteSucceeded: forVotes > againstVotes

⚠️ Abstain counts toward quorum but NOT toward success
   → Large abstain can help reach quorum but not pass
```

### 5.2 GovernorCountingFractional (190 lines)
```
ERC-6947: Split voting weight across options

Voter can vote:
  - 100 For + 50 Against + 30 Abstain (if weight >= 180)
  - Uses params to encode per-option weights

⚠️ GovernorExceedRemainingWeight if total > weight
⚠️ Support field encodes: 0=Against, 1=For, 2=Abstain, 255=Fractional
```

### 5.3 GovernorCountingOverridable (226 lines)
```
Token holders can OVERRIDE their delegate's vote

Flow:
  1. Delegate votes For with 1000 weight
  2. Token holder who delegated 200 votes Against
  3. Override: delegate's For reduced by 200, Against += 200

⚠️ Override only possible AFTER delegate votes
⚠️ Each token holder can override only ONCE
⚠️ Interacts with GovernorSuperQuorum — early closure
   may prevent overrides
```

---

## 6. VOTING POWER

### 6.1 GovernorVotes (64 lines)
```
Connects Governor to ERC-5805 token (Votes)

_getVotes(account, timepoint, params):
  → token.getPastVotes(account, timepoint)

⚠️ Snapshot = proposal creation block
   → Votes counted at snapshot, NOT at vote time
   → Prevents flash loan governance attacks
   → But: delegate AFTER snapshot = votes not counted
```

### 6.2 GovernorVotesQuorumFraction (113 lines)
```
quorum(timepoint) = getPastTotalSupply(timepoint) * numerator / denominator

Default denominator = 100
Example: numerator = 4 → quorum = 4% of total supply

updateQuorumNumerator() — onlyGovernance
  → Must go through proposal
  → Uses checkpoints for historical quorum

⚠️ If token supply is manipulated (burn/mint), quorum changes
   → Burn tokens → lower quorum → easier to pass
   → Checkpoint mitigates: uses PAST supply at snapshot
```

### 6.3 GovernorSuperQuorum (59 lines)
```
If forVotes >= superQuorum → proposal passes EARLY
  → state() returns Succeeded even during Active period
  → No need to wait for votingPeriod to end

⚠️ Interacts badly with GovernorCountingOverridable
   → Super quorum closes voting early
   → Token holders can't override after closure
```

---

## 7. TIMELOCK EXTENSIONS

### 7.1 GovernorTimelockControl (167 lines)
```
Connects Governor to OZ TimelockController

state() override:
  → If governor says Succeeded but timelock says Done → Executed
  → If governor says Queued but timelock expired → Expired

_executor() → address(timelock)
  → All execution goes through timelock
  → Governor can't execute directly

_queueOperations():
  → timelock.scheduleBatch(targets, values, calldatas, 0, salt, delay)

_executeOperations():
  → timelock.executeBatch(targets, values, calldatas, 0, salt)

⚠️ updateTimelock() — onlyGovernance
   → Changing timelock requires governance proposal
   → Old timelock operations may be orphaned
```

### 7.2 GovernorTimelockAccess (346 lines)
```
Integrates with AccessManager (ERC-7579 style)

More granular than TimelockController:
  → Per-function delay configuration
  → AccessManager controls who can call what
  → Governor proposals can be subject to additional delays

baseDelaySeconds — minimum delay for all operations
  → Some functions may have LONGER delays via AccessManager

⚠️ setBaseDelaySeconds() — onlyGovernance
⚠️ setAccessManagerIgnored() — bypass AccessManager for specific functions
   → GovernorLockedIgnore: some functions can't be ignored
```

---

## 8. SETTINGS & PROTECTIONS

### 8.1 GovernorSettings (106 lines)
```
Configurable via governance:
  - votingDelay: uint48 (blocks before voting starts)
  - votingPeriod: uint32 (blocks voting is open)
  - proposalThreshold: uint256 (min votes to propose)

All setters: onlyGovernance
  → Must go through proposal to change

⚠️ votingDelay = 0 → propose + vote same block
   → Flash loan governance attack possible
   → RECOMMENDED: votingDelay >= 1

⚠️ votingPeriod too short → not enough time for voters
⚠️ proposalThreshold = 0 → anyone can propose (spam)
```

### 8.2 GovernorPreventLateQuorum (116 lines)
```
Extends deadline if quorum reached late

_tallyUpdated(proposalId):
  → If quorum just reached AND deadline is close
  → Extend deadline by lateQuorumVoteExtension

proposalDeadline() override:
  → max(originalDeadline, extendedDeadline)

⚠️ Prevents "last-minute quorum sniping"
   → Attacker can't rush quorum at deadline
   → Gives opponents time to react

⚠️ setLateQuorumVoteExtension() — onlyGovernance
   → Extension too large → proposals never end
   → Bounded by _maxLateQuorumVoteExtension()
```

### 8.3 GovernorProposalGuardian (59 lines)
```
Adds a guardian who can cancel ANY proposal in ANY state

_validateCancel() override:
  → Original: proposer can cancel during Pending
  → Guardian: can cancel during Pending OR Active

⚠️ Centralization risk: guardian can censor proposals
⚠️ setProposalGuardian() — onlyGovernance
⚠️ Use case: emergency cancellation of malicious proposals
```

---

## 9. STORAGE & UTILITIES

### 9.1 GovernorStorage (134 lines)
```
Stores proposal data on-chain for enumeration

Adds:
  - proposalCount() — total proposals
  - proposalDetails(id) — full proposal data
  - proposalDetailsAt(index) — by index
  - queue(proposalId) — simplified (no params needed)
  - execute(proposalId) — simplified
  - cancel(proposalId) — simplified

⚠️ Extra gas cost for on-chain storage
⚠️ Useful for UIs that don't index events
```

### 9.2 GovernorSequentialProposalId (75 lines)
```
Proposal IDs are sequential (1, 2, 3...) instead of hash-based

getProposalId() override:
  → Returns latestProposalId + 1
  → NOT keccak256 hash

⚠️ Breaks compatibility with hash-based proposal lookup
⚠️ _initializeLatestProposalId() for migration
```

### 9.3 GovernorNoncesKeyed (91 lines)
```
Multiple nonce keys for parallel vote signing

Standard: single nonce per voter (sequential)
Keyed: nonce per (voter, key) pair

⚠️ Allows signing multiple votes offline simultaneously
⚠️ Different keys = independent nonce sequences
```

### 9.4 GovernorCrosschain (30 lines)
```
Execute governance actions on remote chains

relayCrosschain(chain, target, data):
  → Uses ERC-7786 gateway
  → _crosschainExecute() — override for chain-specific logic

⚠️ Cross-chain replay: same calldata on different chains
⚠️ Gateway trust: compromised gateway = arbitrary execution
```

---

## 10. VOTES SYSTEM (Votes.sol, 245 lines)

### 10.1 Delegation
```
delegate(delegatee) — delegate voting power
delegateBySig(delegatee, nonce, expiry, v, r, s) — gasless

⚠️ MUST delegate to self to vote directly
   → New token holders have 0 voting power until delegation
   → Common UX mistake

⚠️ Delegation is ALL-OR-NOTHING per token
   → Can't delegate 50% to A, 50% to B
   → GovernorCountingFractional splits at VOTE level, not delegation
```

### 10.2 Checkpoints
```
Uses Checkpoints.Trace208 for historical tracking

Each delegation/transfer pushes checkpoint:
  (blockNumber, voteBalance)

getPastVotes(account, timepoint):
  → Binary search through checkpoints
  → upperLookupRecent: optimized for recent lookups

⚠️ uint208 max = 2^208 - 1
   → Voting power capped at ~4.6 × 10^62
   → Sufficient for any realistic token supply

⚠️ Clock modes:
   → blockNumber (default) — ERC-6372
   → timestamp — override clock() + CLOCK_MODE()
```

### 10.3 VotesExtended (85 lines)
```
Tracks delegation HISTORY (not just current)

delegateHistory(account, index) → past delegatees
  → Useful for governance analytics
  → Extra gas cost per delegation change
```

---

## 11. ATTACK VECTORS & AUDIT CHECKLIST

### 11.1 Flash Loan Governance Attack
```
Attack:
  1. Flash loan voting tokens
  2. Delegate to self
  3. Propose malicious proposal
  4. Vote on it
  5. Return flash loan

MITIGATION (built-in):
  ✅ Snapshot mechanism — votes counted at proposal creation block
  ✅ votingDelay > 0 — can't vote immediately
  ✅ proposalThreshold — need votes BEFORE proposing

AUDIT CHECK:
  □ votingDelay > 0?
  □ proposalThreshold > 0?
  □ Snapshot uses PAST votes (getPastVotes)?
  □ Token has flash mint capability? (ERC20FlashMint)
```

### 11.2 Proposal Frontrunning
```
Attack:
  1. See propose() in mempool
  2. Frontrun with same proposal (different description)
  3. Original proposer's proposal becomes "duplicate"

MITIGATION (built-in):
  ✅ #proposer=0x... suffix in description
  ✅ _isValidDescriptionForProposer() checks suffix
  ✅ Different description = different proposalId

AUDIT CHECK:
  □ Does protocol use #proposer= suffix?
  □ Is _isValidDescriptionForProposer() overridden?
```

### 11.3 Timelock Bypass
```
Attack:
  1. Governor without timelock → execute() is immediate
  2. Governance can drain treasury in one tx

MITIGATION:
  ✅ GovernorTimelockControl — adds delay
  ✅ TimelockController.minDelay > 0

AUDIT CHECK:
  □ Is timelock configured?
  □ minDelay > 0? (check on-chain)
  □ EXECUTOR_ROLE granted to address(0)? (open execution)
  □ PROPOSER_ROLE too broad?
```

### 11.4 Quorum Manipulation
```
Attack:
  1. GovernorVotesQuorumFraction: quorum = % of supply
  2. Attacker burns tokens → lower total supply → lower quorum
  3. Easier to pass proposals with fewer votes

MITIGATION:
  ✅ Checkpoints use PAST total supply at snapshot
  ✅ GovernorPreventLateQuorum — extends deadline

AUDIT CHECK:
  □ Quorum uses getPastTotalSupply (not current)?
  □ Token has burn mechanism?
  □ Large holders can manipulate supply?
```

### 11.5 Governance Parameter Manipulation
```
Attack:
  1. Pass proposal to set votingDelay = 0
  2. Pass proposal to set proposalThreshold = 0
  3. Now: instant proposals, no threshold, flash loan attacks

MITIGATION:
  ✅ GovernorSettings setters are onlyGovernance
  ✅ Timelock delays parameter changes
  ✅ Guardian can cancel malicious proposals

AUDIT CHECK:
  □ Are setters protected by onlyGovernance?
  □ Is there a timelock on parameter changes?
  □ Is there a guardian?
  □ Are there bounds on parameters?
```

### 11.6 Reentrancy in Execution
```
Attack:
  1. Proposal targets a malicious contract
  2. Malicious contract re-enters governor during execute()
  3. Could re-execute or manipulate state

MITIGATION (built-in):
  ✅ executed = true BEFORE external calls (line 410)
  ✅ _governanceCall queue prevents unauthorized calls
  ✅ TimelockController._afterCall checks Ready state

AUDIT CHECK:
  □ Is executed flag set before calls?
  □ Is _governanceCall queue properly managed?
  □ Can proposal target the governor itself?
```

### 11.7 Cross-Chain Replay
```
Attack:
  1. GovernorCrosschain executes on remote chain
  2. Same calldata replayed on another chain
  3. Unauthorized execution

MITIGATION:
  ✅ ERC-7786 gateway verification
  ✅ Counterpart registration (onlyOwner)

AUDIT CHECK:
  □ Is gateway trusted?
  □ Are counterparts properly registered?
  □ Is there nonce/replay protection?
```

---

## 12. COMMON DEPLOYMENT CONFIGURATIONS

### 12.1 Standard DAO (most common)
```solidity
contract MyGovernor is
    Governor,
    GovernorSettings,          // configurable params
    GovernorCountingSimple,    // For/Against/Abstain
    GovernorVotes,             // token voting
    GovernorVotesQuorumFraction, // quorum = 4% supply
    GovernorTimelockControl    // 24h timelock
{
    constructor(IVotes token, TimelockController timelock)
        Governor("MyDAO", "1")
        GovernorSettings(1 days, 1 weeks, 100_000e18)
        GovernorVotes(token)
        GovernorVotesQuorumFraction(4)
        GovernorTimelockControl(timelock)
    {}
}
```

### 12.2 Advanced DAO (fractional + override + late quorum)
```solidity
contract AdvancedGovernor is
    Governor,
    GovernorSettings,
    GovernorCountingFractional,     // split votes
    GovernorCountingOverridable,    // override delegate
    GovernorVotes,
    GovernorVotesQuorumFraction,
    GovernorPreventLateQuorum,      // extend on late quorum
    GovernorProposalGuardian,       // emergency cancel
    GovernorTimelockControl
{
    // ...
}
```

### 12.3 ⚠️ DANGEROUS Configuration
```solidity
// DON'T DO THIS:
contract BadGovernor is
    Governor,
    GovernorCountingSimple,
    GovernorVotes
{
    function votingDelay() public pure override returns (uint256) { return 0; }
    function votingPeriod() public pure override returns (uint256) { return 1; }
    function quorum(uint256) public pure override returns (uint256) { return 0; }
    // NO timelock, NO threshold, NO settings protection
    // → Flash loan governance attack trivial
}
```

---

## 13. GAS CONSIDERATIONS

```
propose():     ~150K gas (depends on targets count)
castVote():    ~80K gas (checkpoint lookup + write)
execute():     ~100K + target call gas
queue():       ~50K (timelock schedule)

GovernorStorage: +20K per proposal (on-chain storage)
GovernorPreventLateQuorum: +5K per vote (deadline check)
GovernorCountingFractional: +10K per vote (multi-option)
Votes delegation: ~50K (checkpoint push)
```

---

*BOZAGENTIC · "Governance is the attack surface nobody watches."*
*Most DAOs deploy Governor with default settings and never audit the config.*
