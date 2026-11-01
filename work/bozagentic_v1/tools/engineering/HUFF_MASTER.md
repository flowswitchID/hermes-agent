# HUFF LANGUAGE — COMPLETE MASTER REFERENCE
# Low-level EVM assembly language · huffmate library
# BOZAGENTIC · 2026-07-30

---

## 1. WHAT IS HUFF

```
Huff = low-level EVM language
  → No types, no structs, no inheritance
  → Direct stack manipulation (PUSH, POP, DUP, SWAP)
  → Macros instead of functions
  → Compiles to raw EVM bytecode
  → GAS OPTIMIZED (no Solidity overhead)

Created by: Aztec Protocol (for Weierstrudel — elliptic curve math)
Maintained by: huff-language community
Compiler: huffc (Rust) — huff-rs (legacy) / huff2 (new)
Library: huffmate (like OZ/Solmate but for Huff)

WHY HUFF:
  → 30-50% less gas than Solidity for simple operations
  → Full control over bytecode
  → No hidden compiler behavior
  → Used by: Sudoswap, NonfungiblePositionManager, Pentagon

WHY NOT HUFF:
  → Extremely error-prone (manual stack management)
  → No type safety
  → No overflow checks (unless manual)
  → Hard to audit (read assembly, not logic)
  → Small ecosystem
```

---

## 2. SYNTAX BASICS

### 2.1 Function Signatures
```huff
// Define external interface
#define function transfer(address,uint256) nonpayable returns (bool)
#define function balanceOf(address) view returns (uint256)
#define function owner() view returns (address)

// Events
#define event Transfer(address indexed, address indexed, uint256)
#define event Approval(address indexed, address indexed, uint256)

// Errors (custom)
#define error InsufficientBalance()
#define error Unauthorized()
```

### 2.2 Constants & Storage
```huff
// Storage slots (auto-incrementing)
#define constant TOTAL_SUPPLY_SLOT = FREE_STORAGE_POINTER()  // slot 0
#define constant BALANCE_SLOT = FREE_STORAGE_POINTER()       // slot 1
#define constant APPROVAL_SLOT = FREE_STORAGE_POINTER()      // slot 2

// Fixed constants
#define constant UINT_256_MAX = 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
#define constant ZERO_ADDRESS = 0x0000000000000000000000000000000000000000

// Function selectors (auto-computed)
__FUNC_SIG(transfer)    // → 0xa9059cbb
__EVENT_HASH(Transfer)  // → keccak256("Transfer(address,address,uint256)")
```

### 2.3 Macros (Functions)
```huff
// Macro = block of bytecode
// takes(N) = expects N items on stack
// returns(M) = leaves M items on stack
#define macro TRANSFER() = takes (0) returns (0) {
    // Stack notation: [item1, item2, ...] (top first)
    
    0x04 calldataload       // [to]          — load 1st arg
    caller                  // [from, to]     — msg.sender
    0x24 calldataload       // [value, from, to] — load 2nd arg
    
    // ... logic ...
    
    0x01 0x00 mstore        // []            — store return value
    0x20 0x00 return        // []            — return 32 bytes
}
```

### 2.4 The Dispatcher (MAIN)
```huff
#define macro MAIN() = takes (0) returns (0) {
    // Extract function selector from calldata
    pc calldataload 0xE0 shr    // [selector]
    // pc = 0, calldataload(0) = first 32 bytes of calldata
    // shr 0xE0 = shift right 224 bits = extract first 4 bytes
    
    // Route to function
    dup1 __FUNC_SIG(transfer) eq transfer_jump jumpi
    dup1 __FUNC_SIG(balanceOf) eq balance_jump jumpi
    dup1 __FUNC_SIG(approve) eq approve_jump jumpi
    
    // No match → revert
    0x00 dup1 revert
    
    transfer_jump:
        TRANSFER()
    balance_jump:
        BALANCE_OF()
    approve_jump:
        APPROVE()
}
```

### 2.5 Constructor
```huff
#define macro CONSTRUCTOR() = takes (0) returns (0) {
    // Store initial state
    caller [OWNER_SLOT] sstore   // owner = msg.sender
    
    // Return runtime bytecode
    __codesize(CONSTRUCTOR)      // [constructor_size]
    dup1                         // [size, size]
    codesize                     // [total, size, size]
    sub                          // [runtime_size, size]
    dup1                         // [runtime_size, runtime_size, size]
    swap2                        // [size, runtime_size, runtime_size]
    0x00                         // [0, size, runtime_size, runtime_size]
    codecopy                     // [runtime_size]
    0x00                         // [0, runtime_size]
    return                       // []
}
```

---

## 3. STACK OPERATIONS (Core EVM)

```
PUSH1-PUSH32:  Push N bytes onto stack
POP:           Remove top item
DUP1-DUP16:    Duplicate Nth item from top
SWAP1-SWAP16:  Swap top with Nth item

ARITHMETIC:
  ADD, SUB, MUL, DIV, SDIV, MOD, SMOD
  ADDMOD, MULMOD, EXP, SIGNEXTEND

COMPARISON:
  LT, GT, SLT, SGT, EQ, ISZERO

BITWISE:
  AND, OR, XOR, NOT, BYTE, SHL, SHR, SAR

MEMORY:
  MLOAD(offset) → value
  MSTORE(offset, value)
  MSTORE8(offset, byte)
  MSIZE → current memory size

STORAGE:
  SLOAD(slot) → value
  SSTORE(slot, value)

CALLDATA:
  CALLDATALOAD(offset) → 32 bytes
  CALLDATASIZE → size
  CALLDATACOPY(dest, offset, size)

CONTROL:
  JUMP(dest)
  JUMPI(dest, condition)  — jump if condition != 0
  PC → program counter
  JUMPDEST — valid jump target

LOGGING:
  LOG0(offset, size)
  LOG1(offset, size, topic1)
  LOG2(offset, size, topic1, topic2)
  LOG3(offset, size, topic1, topic2, topic3)
  LOG4(offset, size, topic1, topic2, topic3, topic4)

CALLS:
  CALL(gas, to, value, inOff, inSize, outOff, outSize)
  STATICCALL(gas, to, inOff, inSize, outOff, outSize)
  DELEGATECALL(gas, to, inOff, inSize, outOff, outSize)

RETURN/REVERT:
  RETURN(offset, size)
  REVERT(offset, size)
  STOP
  INVALID
```

---

## 4. HUFFMATE LIBRARY (OZ/Solmate equivalent)

### 4.1 Available Modules
```
tokens/
  ERC20.huff       — ERC20 + EIP-2612 Permit (604 lines)
  ERC721.huff      — NFT
  ERC1155.huff     — Multi-token
  ERC4626.huff     — Tokenized Vault

auth/
  Owned.huff       — Single owner
  Auth.huff        — Authority-based
  NonPayable.huff  — Reject ETH
  OnlyContract.huff — Only contracts
  RolesAuthority.huff — Role-based

data-structures/
  Hashmap.huff     — Storage mapping (1D, 2D, 3D)
  Arrays.huff      — Dynamic arrays
  Bytes.huff       — Byte manipulation

math/
  Math.huff        — Basic math
  SafeMath.huff    — Overflow checks
  FixedPointMath.huff — WAD/RAY math
  Trigonometry.huff — Sin/Cos/Tan (!)

utils/
  ReentrancyGuard.huff — Lock/unlock pattern
  SafeTransferLib.huff — Safe ERC20 transfers
  ECDSA.huff       — Signature verification
  MerkleProofLib.huff — Merkle proof
  CREATE3.huff     — Deterministic deployment
  Pausable.huff    — Pause mechanism
  Multicallable.huff — Batch calls
  SSTORE2.huff     — Storage as code
  LibBit.huff      — Bit operations

proxies/
  ERC1967Proxy.huff
  ERC1967Upgrade.huff
  Proxy.huff
  Clones.huff      — EIP-1167 minimal proxy

mechanisms/
  huff-clones/     — Clone factory
  huff-vrgda/      — Variable Rate Gradual Dutch Auction
```

### 4.2 Storage Pattern (Hashmap)
```huff
// Solidity: mapping(address => uint256) balances;
// Huff: manual slot computation

// 1D mapping: slot = keccak256(key . SLOT)
#define macro LOAD_ELEMENT_FROM_KEYS(mem_ptr) = takes(2) returns(1) {
    // [slot, key]
    GET_SLOT_FROM_KEYS(<mem_ptr>)  // [computed_slot]
    sload                          // [value]
}

// 2D mapping: slot = keccak256(key2 . keccak256(key1 . SLOT))
#define macro LOAD_ELEMENT_FROM_KEYS_2D(mem_ptr) = takes(3) returns(1) {
    // [slot, key1, key2]
    GET_SLOT_FROM_KEYS_2D(<mem_ptr>)  // [computed_slot]
    sload                              // [value]
}

// This is EXACTLY what Solidity does internally
// But in Huff you SEE it and CONTROL it
```

### 4.3 Reentrancy Guard Pattern
```huff
#define constant LOCKED_SLOT = FREE_STORAGE_POINTER()
#define constant _UNLOCKED = 0x01
#define constant _LOCKED = 0x02

#define macro LOCK() = takes (0) returns (0) {
    [_LOCKED]              // [2]
    dup1                   // [2, 2]
    [LOCKED_SLOT] sload   // [current, 2, 2]
    lt                     // [current < 2, 2]
    lock jumpi             // jump if unlocked
    
    // Reentrancy detected → revert
    0x00 0x00 revert
    
    lock:
        [LOCKED_SLOT] sstore  // set locked
}

#define macro UNLOCK() = takes (0) returns (0) {
    [_UNLOCKED] [LOCKED_SLOT] sstore  // set unlocked
}

// Usage:
#define macro WITHDRAW() = takes (0) returns (0) {
    LOCK()
    // ... external calls ...
    UNLOCK()
    stop
}
```

---

## 5. SECURITY IMPLICATIONS (For Auditing)

### 5.1 What Makes Huff DANGEROUS
```
1. NO TYPE SAFETY
   → Stack items are just 256-bit words
   → address, uint256, bytes32 all look the same
   → Wrong interpretation = silent bug
   
   Example:
     0x04 calldataload  // Is this address or uint256?
     → Developer must KNOW, compiler doesn't check

2. NO OVERFLOW PROTECTION
   → ADD wraps around silently (mod 2^256)
   → Must manually check with LT/GT before arithmetic
   → SafeMath.huff exists but must be EXPLICITLY used
   
   Example:
     balance value sub  // balance - value
     → If value > balance: UNDERFLOW → huge number
     → Must check: dup2 dup2 lt iszero valid jumpi

3. MANUAL STACK MANAGEMENT
   → Every DUP, SWAP, POP must be correct
   → Off-by-one in stack position = wrong variable
   → EXTREMELY hard to verify by reading
   
   Example:
     dup3  // Is this 'from' or 'to' or 'value'?
     → Must trace entire stack from function entry

4. NO BOUNDS CHECKING
   → calldataload doesn't check length
   → Reading beyond calldata returns 0 (not revert)
   → Must manually validate calldatasize

5. MEMORY IS UNSAFE
   → No memory allocator
   → Overlapping writes corrupt data
   → Must manually track memory layout
   → Scratch space: 0x00-0x3f (64 bytes) — KECCAK uses this!

6. NO COMPILER OPTIMIZATIONS TO RELY ON
   → Solidity: compiler handles dead code, constant folding
   → Huff: what you write is what you get
   → Forgotten POP = stack leak = wrong behavior
```

### 5.2 Common Huff Bugs
```
1. STACK IMBALANCE
   → Macro says takes(0) returns(0) but leaves items
   → Next macro reads wrong values
   → Silent corruption

2. WRONG STORAGE SLOT
   → FREE_STORAGE_POINTER() collision
   → Two variables share same slot
   → Overwrite each other

3. MISSING CALLDATA VALIDATION
   → No check: calldatasize >= expected
   → Short calldata → reads zeros
   → Unexpected behavior

4. MEMORY CORRUPTION
   → Using 0x00-0x3f for storage (scratch space!)
   → keccak256 overwrites your data
   → Must start at 0x40+

5. MISSING RETURN/STOP
   → Execution falls through to next macro
   → Unintended code execution
   → Must explicitly stop/return/revert

6. REENTRANCY WITHOUT GUARD
   → External call (CALL/STATICCALL) without LOCK()
   → Re-enter and drain

7. WRONG SELECTOR ROUTING
   → dup1 __FUNC_SIG(x) eq label jumpi
   → Forgot dup1 → selector consumed → next check fails
   → Function unreachable
```

### 5.3 Auditing Huff Contracts
```
STEP 1: Map the dispatcher
  → What functions exist?
  → What selectors route where?
  → Any unreachable code?

STEP 2: Trace stack for EVERY macro
  → Write stack state at each line
  → Verify takes(N)/returns(M) matches reality
  → Check: no leftover items

STEP 3: Verify storage layout
  → List all FREE_STORAGE_POINTER() slots
  → Check for collisions
  → Verify immutables offsets don't overlap

STEP 4: Check arithmetic
  → Every SUB: is underflow checked?
  → Every ADD: is overflow checked?
  → Every DIV: is division-by-zero handled?

STEP 5: Check external calls
  → Is return value checked?
  → Is reentrancy guarded?
  → Is gas forwarded correctly?

STEP 6: Check calldata handling
  → Is calldatasize validated?
  → Are offsets correct? (0x04, 0x24, 0x44...)
  → Can short calldata cause issues?

STEP 7: Check memory safety
  → Is scratch space (0x00-0x3f) avoided for storage?
  → Do memory writes overlap?
  → Is memory layout documented?

STEP 8: Compare with Solidity equivalent
  → What would OZ/Solmate do?
  → What's MISSING in the Huff version?
  → What's DIFFERENT?
```

---

## 6. HUFF vs SOLIDITY — GAS COMPARISON

```
Operation              Solidity    Huff      Savings
─────────────────────────────────────────────────────
Simple storage read    ~2100 gas   ~2100     0%
Simple storage write   ~5000 gas   ~5000     0%
ERC20 transfer         ~51000 gas  ~34000    33%
ERC20 approve          ~46000 gas  ~29000    37%
Function dispatch      ~200 gas    ~100      50%
Reentrancy guard       ~4200 gas   ~2100     50%
Owner check            ~2200 gas   ~2100     5%

WHY SAVINGS:
  → No ABI encoding overhead
  → No unnecessary memory expansion
  → No redundant stack operations
  → No Solidity's "safety" checks you don't need
  → Direct jump table (no binary search)

WHEN HUFF MATTERS:
  → High-frequency operations (DEX swaps, NFT mints)
  → Gas-critical protocols (perps, options)
  → Minimal proxies / factories
  → When every gas unit counts

WHEN HUFF DOESN'T MATTER:
  → Admin functions (called rarely)
  → Governance (not gas-sensitive)
  → Complex business logic (readability > gas)
```

---

## 7. HUFF IN THE WILD

```
Protocols using Huff:
  - Sudoswap (NFT AMM) — all core contracts
  - Pentagon (DeFi primitives)
  - NonfungiblePositionManager variants
  - Various MEV bots (undisclosed)
  - Gas-optimized ERC20 deployments

Why they chose Huff:
  → 30-50% gas savings on hot paths
  → Predictable bytecode (no compiler surprises)
  → Minimal attack surface (less code = less bugs)
  → Full control over execution

Why most DON'T use Huff:
  → Audit cost higher (fewer Huff auditors)
  → Development speed slower
  → Maintenance harder
  → Bug probability higher per line
```

---

## 8. QUICK REFERENCE: READING HUFF

```
// Calldata offsets for function args:
// selector:  bytes 0-3   (4 bytes)
// arg1:      bytes 4-35  (offset 0x04)
// arg2:      bytes 36-67 (offset 0x24)
// arg3:      bytes 68-99 (offset 0x44)

// Common patterns:
0x04 calldataload     // Load first argument
0x24 calldataload     // Load second argument
caller                // msg.sender
address               // address(this)
chainid               // block.chainid
timestamp             // block.timestamp
number                // block.number
gas                   // gasleft()
returndatasize        // 0 (at start)

// Storage:
[SLOT] sload          // Read storage slot
[SLOT] sstore         // Write storage slot (value must be below on stack)

// Events:
__EVENT_HASH(Name)    // topic0
0x20 0x00 log3        // emit with 3 topics, 32 bytes data

// Return:
0x00 mstore           // Store value at memory[0]
0x20 0x00 return      // Return 32 bytes from memory[0]

// Revert:
0x00 0x00 revert      // Revert with no data
0x00 dup1 revert      // Same (stack trick)

// Stop:
stop                  // Halt execution, no return data
```

---

## 9. WRITING YOUR FIRST HUFF CONTRACT

```huff
// SPDX-License-Identifier: MIT
// SimpleStorage.huff

#define function get() view returns (uint256)
#define function set(uint256) nonpayable returns ()
#define event ValueChanged(uint256 indexed newValue)

#define constant VALUE_SLOT = FREE_STORAGE_POINTER()

#define macro MAIN() = takes (0) returns (0) {
    pc calldataload 0xE0 shr
    
    dup1 __FUNC_SIG(get) eq get jumpi
    dup1 __FUNC_SIG(set) eq set jumpi
    0x00 dup1 revert

    get:
        [VALUE_SLOT] sload
        0x00 mstore
        0x20 0x00 return

    set:
        0x04 calldataload           // [value]
        dup1 [VALUE_SLOT] sstore   // [value]
        
        // Emit event
        __EVENT_HASH(ValueChanged)  // [sig, value]
        0x00 0x00                   // [0, 0, sig, value]
        log2                        // []
        
        stop
}
```

---

*BOZAGENTIC · "Huff: where every byte is your responsibility."*
*If Solidity is C, Huff is assembly. Power + danger in equal measure.*
