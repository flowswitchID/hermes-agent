# YUL & INLINE ASSEMBLY — COMPLETE MASTER REFERENCE
# Low-level EVM programming inside Solidity
# BOZAGENTIC · 2026-07-30

---

## 1. WHAT IS YUL

```
Yul = intermediate language for EVM
  → Low-level but with structure (functions, loops, variables)
  → Used in: inline assembly (Solidity), Solidity compiler IR, Huff
  → Compiles to raw EVM bytecode
  → No type safety (everything is 256-bit word)

Two contexts:
  1. Inline Assembly: assembly { ... } inside Solidity
  2. Standalone Yul: .yul files (rare, mostly compiler internal)

Why developers use it:
  → Gas optimization (skip Solidity overhead)
  → Access opcodes not exposed by Solidity (tload, tstore, mcopy)
  → Direct memory/storage manipulation
  → Custom proxy bytecode (Clones, ERC1967)
  → Return data handling (SafeERC20)

Why it's DANGEROUS:
  → No type checking
  → No bounds checking
  → No overflow protection
  → Compiler doesn't verify correctness
  → "memory-safe" annotation is a PROMISE, not a guarantee
```

---

## 2. YUL SYNTAX

### 2.1 Variables & Assignment
```yul
assembly {
    let x := 42              // declare + assign
    let y := add(x, 1)      // x + 1
    let z                    // declare (default 0)
    z := mul(x, y)          // reassign
    
    // Multiple return values
    let success, data := call(gas(), addr, 0, 0, 0, 0, 0)
}
```

### 2.2 Arithmetic & Comparison
```yul
assembly {
    // Arithmetic (all mod 2^256, NO overflow check!)
    let a := add(x, y)      // x + y
    let b := sub(x, y)      // x - y
    let c := mul(x, y)      // x * y
    let d := div(x, y)      // x / y (0 if y == 0!)
    let e := sdiv(x, y)     // signed division
    let f := mod(x, y)      // x % y (0 if y == 0!)
    let g := exp(x, y)      // x ** y
    let h := addmod(x, y, m) // (x + y) % m
    let i := mulmod(x, y, m) // (x * y) % m
    
    // Comparison
    let eq1 := eq(x, y)     // x == y → 1 or 0
    let lt1 := lt(x, y)     // x < y (unsigned)
    let gt1 := gt(x, y)     // x > y (unsigned)
    let slt1 := slt(x, y)   // x < y (signed)
    let sgt1 := sgt(x, y)   // x > y (signed)
    let iz := iszero(x)     // x == 0 → 1
    
    // Bitwise
    let and1 := and(x, y)   // x & y
    let or1 := or(x, y)     // x | y
    let xor1 := xor(x, y)   // x ^ y
    let not1 := not(x)      // ~x (bitwise NOT)
    let byte1 := byte(i, x) // ith byte of x
    let shl1 := shl(s, x)   // x << s
    let shr1 := shr(s, x)   // x >> s
    let sar1 := sar(s, x)   // arithmetic shift right
}
```

### 2.3 Memory Operations
```yul
assembly {
    // Memory layout:
    // 0x00 - 0x3f: Scratch space (64 bytes) — KECCAK uses this!
    // 0x40 - 0x5f: Free memory pointer (points to next free slot)
    // 0x60+:       Free memory
    
    let fmp := mload(0x40)       // Load free memory pointer
    mstore(0x40, add(fmp, 0x20)) // Allocate 32 bytes
    
    mstore(ptr, value)           // Store 32 bytes at ptr
    mstore8(ptr, byte_val)       // Store 1 byte at ptr
    let val := mload(ptr)        // Load 32 bytes from ptr
    let size := msize()          // Current memory size
    
    // Copy operations
    mcopy(dst, src, len)         // Memory copy (Cancun+)
    calldatacopy(dst, offset, len) // Copy calldata to memory
    codecopy(dst, offset, len)   // Copy code to memory
    extcodecopy(addr, dst, offset, len) // Copy external code
    returndatacopy(dst, offset, len)    // Copy return data
}
```

### 2.4 Storage Operations
```yul
assembly {
    // Direct storage access
    let val := sload(slot)       // Read storage slot
    sstore(slot, value)          // Write storage slot
    
    // Transient storage (EIP-1153, Cancun+)
    let tval := tload(slot)      // Read transient slot
    tstore(slot, value)          // Write transient slot
    
    // Storage slot of a variable
    let slot := var.slot         // Storage slot of Solidity var
    let offset := var.offset     // Byte offset within slot (packed)
}
```

### 2.5 Control Flow
```yul
assembly {
    // If (no else!)
    if iszero(x) {
        revert(0, 0)
    }
    
    // For loop
    for { let i := 0 } lt(i, 10) { i := add(i, 1) } {
        // body
    }
    
    // Switch (like C)
    switch x
    case 0 { result := 1 }
    case 1 { result := 2 }
    default { result := 0 }
    
    // Functions
    function square(x) -> y {
        y := mul(x, x)
    }
    let sq := square(5)  // 25
    
    // Leave (return from function)
    function abs(x) -> y {
        if slt(x, 0) {
            y := sub(0, x)
            leave
        }
        y := x
    }
    
    // Break / Continue
    for { let i := 0 } lt(i, 100) { i := add(i, 1) } {
        if eq(i, 50) { break }
        if lt(i, 10) { continue }
    }
}
```

### 2.6 External Calls
```yul
assembly {
    // CALL: call(gas, to, value, inOff, inSize, outOff, outSize)
    let success := call(gas(), addr, 0, inPtr, inSize, outPtr, outSize)
    
    // STATICCALL: no state modification
    let ok := staticcall(gas(), addr, inPtr, inSize, outPtr, outSize)
    
    // DELEGATECALL: execute in context of current contract
    let ok2 := delegatecall(gas(), addr, inPtr, inSize, outPtr, outSize)
    
    // CALLCODE: deprecated, don't use
    
    // Return data
    let rdsize := returndatasize()
    returndatacopy(dst, 0, rdsize)
    
    // CREATE / CREATE2
    let newAddr := create(value, offset, size)
    let newAddr2 := create2(value, offset, size, salt)
    
    // Self info
    let self := address()
    let bal := balance(addr)
    let selfBal := selfbalance()
    let codeSize := extcodesize(addr)
    let codeHash := extcodehash(addr)
}
```

### 2.7 Logging & Return
```yul
assembly {
    // Events (LOG0-LOG4)
    log0(offset, size)                          // no topics
    log1(offset, size, topic1)                  // 1 topic
    log2(offset, size, topic1, topic2)          // 2 topics
    log3(offset, size, topic1, topic2, topic3)  // 3 topics
    log4(offset, size, t1, t2, t3, t4)         // 4 topics
    
    // Return / Revert / Stop
    return(offset, size)     // Return data
    revert(offset, size)     // Revert with data
    stop()                   // Halt, no data
    invalid()                // Invalid opcode (burns all gas)
    
    // Other
    let pc_val := pc()       // Program counter
    let gasLeft := gas()     // Remaining gas
    let chainId := chainid() // Chain ID
    let blockNum := number() // Block number
    let ts := timestamp()    // Block timestamp
    let coinbase := coinbase() // Block coinbase
    let diff := difficulty()   // Block difficulty (prevrandao post-merge)
    let gasLimit := gaslimit() // Block gas limit
    let baseFee := basefee()   // Base fee (EIP-3198)
    let blobBaseFee := blobbasefee() // Blob base fee (EIP-7516)
}
```

---

## 3. REAL-WORLD PATTERNS (From OZ Source)

### 3.1 StorageSlot — Arbitrary Slot Access
```solidity
// OZ StorageSlot.sol
function getAddressSlot(bytes32 slot) internal pure returns (AddressSlot storage r) {
    assembly ("memory-safe") {
        r.slot := slot  // Point storage reference to arbitrary slot
    }
}

// Usage: ERC1967 proxy slots
bytes32 constant IMPL_SLOT = 0x360894a1...;
StorageSlot.getAddressSlot(IMPL_SLOT).value = newImpl;

// SECURITY: This bypasses Solidity's storage layout
// → Can read/write ANY storage slot
// → Used for proxy patterns (ERC1967, ERC7201)
// → Bug if slot calculation is wrong → storage collision
```

### 3.2 SafeERC20 — Return Value Handling
```solidity
// OZ SafeERC20.sol — _safeTransfer
assembly ("memory-safe") {
    let fmp := mload(0x40)           // Save free memory pointer
    mstore(0x00, selector)           // Function selector at 0x00
    mstore(0x04, and(to, shr(96, not(0))))  // Address (cleaned)
    mstore(0x24, value)              // Amount
    success := call(gas(), token, 0, 0x00, 0x44, 0x00, 0x20)
    
    // Check: success AND return == true
    if iszero(and(success, eq(mload(0x00), 1))) {
        // If call failed and bubble enabled → revert with reason
        if and(iszero(success), bubble) {
            returndatacopy(fmp, 0x00, returndatasize())
            revert(fmp, returndatasize())
        }
        // Success if: call succeeded + empty return + has code
        success := and(success, and(iszero(returndatasize()), gt(extcodesize(token), 0)))
    }
    mstore(0x40, fmp)                // Restore free memory pointer
}

// WHY: USDT doesn't return bool from transfer()
// Solidity would revert on missing return value
// Assembly handles: no return = OK (if contract has code)
// false return = FAIL

// SECURITY IMPLICATIONS:
// → extcodesize check: prevents "success" on EOA (no code)
// → returndatasize check: empty return = OK
// → But: if token returns random 32 bytes ≠ 1 → treated as failure
```

### 3.3 Clones — EIP-1167 Minimal Proxy
```solidity
// OZ Clones.sol — clone()
assembly ("memory-safe") {
    // Build bytecode in memory:
    // 3d602d80600a3d3981f3  (creation code)
    // 363d3d373d3d3d363d73  (runtime prefix)
    // <20-byte address>     (implementation)
    // 5af43d82803e903d91602b57fd5bf3  (runtime suffix)
    
    mstore(0x00, or(shr(232, shl(96, implementation)), 
               0x3d602d80600a3d3981f3363d3d373d3d3d363d73000000))
    mstore(0x20, or(shl(120, implementation), 
               0x5af43d82803e903d91602b57fd5bf3))
    instance := create(value, 0x09, 0x37)
}

// Runtime bytecode (45 bytes):
// 363d3d373d3d3d363d73<address>5af43d82803e903d91602b57fd5bf3
//
// Disassembled:
// CALLDATASIZE RETURNDATASIZE RETURNDATASIZE CALLDATACOPY
// RETURNDATASIZE RETURNDATASIZE RETURNDATASIZE CALLDATASIZE
// RETURNDATASIZE PUSH20 <address> GAS DELEGATECALL
// RETURNDATASIZE RETURNDATASIZE RETURNDATASIZE RETURNDATASIZE
// RETURNDATASIZE PUSH1 0x2b JUMPI REVERT JUMPDEST STOP

// SECURITY:
// → DELEGATECALL to hardcoded address (immutable)
// → No admin, no upgrade path
// → If implementation has no code → clone is uninitialized
// → OZ warns: "does not check if implementation has code"
```

### 3.4 tryGetDecimals — Static Call Pattern
```solidity
// OZ SafeERC20.sol
assembly ("memory-safe") {
    mstore(0x00, selector)                    // decimals() selector
    success := staticcall(gas(), token, 0x00, 4, 0x00, 0x20)
    success := and(and(success, gt(returndatasize(), 0x1f)), 
                   lt(mload(0x00), 0x100))
    decimals := mul(success, mload(0x00))
}

// Pattern: safe external call with validation
// 1. staticcall (no state change)
// 2. Check success
// 3. Check returndatasize >= 32 (valid uint8 encoding)
// 4. Check value < 256 (valid uint8 range)
// 5. Return 0 if any check fails (mul by success=0)
```

### 3.5 Governor — Unsafe Memory Read
```solidity
// OZ Governor.sol — _unsafeReadBytesOffset
function _unsafeReadBytesOffset(bytes memory buffer, uint256 offset) 
    private pure returns (bytes32 value) {
    assembly ("memory-safe") {
        value := mload(add(add(buffer, 0x20), offset))
    }
}

// SECURITY:
// → "memory-safe" but reads beyond buffer bounds!
// → Comment says: "all calls are within bounds"
// → If offset > buffer.length → reads garbage memory
// → Used for #proposer= suffix parsing
// → Safe ONLY because caller validates length >= 52 first
```

---

## 4. MEMORY LAYOUT (Critical for Security)

```
EVM Memory Layout:
┌─────────────────────────────────────────┐
│ 0x00 - 0x3f │ Scratch Space (64 bytes) │ ← keccak256 uses this!
├─────────────────────────────────────────┤
│ 0x40 - 0x5f │ Free Memory Pointer      │ ← mload(0x40)
├─────────────────────────────────────────┤
│ 0x60+       │ Free Memory              │ ← grows upward
├─────────────────────────────────────────┤
│ ...         │ Solidity variables       │
├─────────────────────────────────────────┤
│ 0x...       │ Stack (1024 items max)   │ ← grows downward
└─────────────────────────────────────────┘

RULES:
  1. NEVER store data at 0x00-0x3f (scratch space)
     → keccak256, sha3, log operations overwrite this
     → OZ SafeERC20 uses 0x00 for selector (safe because
       it's consumed before any keccak)
     
  2. ALWAYS save/restore free memory pointer
     → let fmp := mload(0x40)
     → ... do stuff ...
     → mstore(0x40, fmp)
     
  3. Memory expansion costs gas
     → First 724 bytes: cheap
     → Beyond: quadratic cost
     → MSIZE tracks highest accessed word

  4. Memory is NOT zeroed between calls
     → After external call, memory may contain stale data
     → Must explicitly zero sensitive data
```

---

## 5. SECURITY VULNERABILITIES IN ASSEMBLY

### 5.1 Memory Corruption
```solidity
// BUG: Writing to scratch space
assembly {
    mstore(0x00, importantValue)  // Store at scratch space
    let hash := keccak256(0x00, 0x20)  // keccak OVERWRITES 0x00!
    // importantValue is GONE
}

// FIX: Use memory after free pointer
assembly {
    let ptr := mload(0x40)
    mstore(ptr, importantValue)
    let hash := keccak256(ptr, 0x20)
}
```

### 5.2 Unchecked Return Data
```solidity
// BUG: Assuming return data exists
assembly {
    success := call(gas(), addr, 0, 0, 0, 0, 0x20)
    let result := mload(0x00)  // May be garbage if call returned nothing!
}

// FIX: Check returndatasize
assembly {
    success := call(gas(), addr, 0, 0, 0, 0, 0x20)
    if and(success, gt(returndatasize(), 0x1f)) {
        let result := mload(0x00)
    }
}
```

### 5.3 Missing Address Cleaning
```solidity
// BUG: Address with dirty upper bits
assembly {
    mstore(0x04, addr)  // addr may have garbage in upper 96 bits!
    // calldata now has wrong address
}

// FIX: Clean upper bits
assembly {
    mstore(0x04, and(addr, shr(96, not(0))))  // Mask to 160 bits
    // OZ does this: and(to, shr(96, not(0)))
}
```

### 5.4 Division by Zero
```solidity
// BUG: No zero check
assembly {
    let result := div(x, y)  // If y == 0, result = 0 (NOT revert!)
}

// FIX: Check before divide
assembly {
    if iszero(y) { revert(0, 0) }
    let result := div(x, y)
}

// NOTE: Solidity checks division by zero. Assembly does NOT.
// div(x, 0) = 0 in EVM (not revert)
// mod(x, 0) = 0 in EVM (not revert)
```

### 5.5 Overflow/Underflow
```solidity
// BUG: No overflow check
assembly {
    let result := add(x, y)  // Wraps mod 2^256!
    // If x = 2^256 - 1, y = 1 → result = 0
}

// FIX: Check before add
assembly {
    let result := add(x, y)
    if lt(result, x) { revert(0, 0) }  // Overflow if result < x
}

// NOTE: Solidity 0.8+ checks overflow. Assembly does NOT.
```

### 5.6 Storage Collision
```solidity
// BUG: Wrong slot calculation
assembly {
    // Trying to access mapping(address => uint256) at slot 5
    // Correct: keccak256(abi.encode(key, 5))
    mstore(0x00, key)
    mstore(0x20, 5)
    let slot := keccak256(0x00, 0x40)
    let balance := sload(slot)
}

// BUG: Off-by-one in slot
assembly {
    mstore(0x20, 6)  // Wrong! Should be 5
    let slot := keccak256(0x00, 0x40)
    let balance := sload(slot)  // Reads WRONG storage!
}
```

### 5.7 Reentrancy via Assembly Call
```solidity
// BUG: External call without reentrancy guard
assembly {
    // State update AFTER call = reentrancy window
    success := call(gas(), addr, 0, inPtr, inSize, 0, 0)
    sstore(slot, newValue)  // Can be re-entered before this!
}

// FIX: Update state BEFORE call (CEI)
assembly {
    sstore(slot, newValue)  // State first
    success := call(gas(), addr, 0, inPtr, inSize, 0, 0)
}
```

### 5.8 Delegatecall to Untrusted
```solidity
// BUG: delegatecall to user-controlled address
assembly {
    success := delegatecall(gas(), userAddr, inPtr, inSize, 0, 0)
}
// Attacker's code runs in YOUR storage context!
// Can modify ANY storage slot

// FIX: Never delegatecall to untrusted addresses
// Only delegatecall to verified implementations
```

### 5.9 "memory-safe" Lie
```solidity
// BUG: Annotated "memory-safe" but isn't
assembly ("memory-safe") {
    // This writes beyond allocated memory!
    mstore(add(ptr, 0x100), value)  // ptr + 256 bytes
    // If ptr was near free memory pointer, this corrupts
    // other variables
}

// "memory-safe" tells compiler:
//   "I promise this doesn't corrupt memory"
// Compiler then SKIPS memory safety checks
// If you lie → undefined behavior

// RULE: Only use "memory-safe" if you ACTUALLY
// save/restore free memory pointer and stay within bounds
```

---

## 6. COMMON ASSEMBLY PATTERNS

### 6.1 Efficient ABI Encoding
```solidity
// Encode transfer(address,uint256) call
assembly {
    let fmp := mload(0x40)
    mstore(0x00, 0xa9059cbb)           // transfer selector
    mstore(0x04, and(to, shr(96, not(0))))  // address (cleaned)
    mstore(0x24, amount)               // uint256
    // Total: 4 + 32 + 32 = 68 bytes (0x44)
}
```

### 6.2 Efficient Storage Packing
```solidity
// Pack uint128 + uint128 in one slot
assembly {
    let packed := sload(slot)
    let lower := and(packed, 0xffffffffffffffffffffffffffffffff)
    let upper := shr(128, packed)
    
    // Update lower half
    packed := or(and(packed, shl(128, not(0))), newLower)
    sstore(slot, packed)
}
```

### 6.3 Minimal Proxy Detection
```solidity
// Check if address is EIP-1167 clone
assembly {
    let size := extcodesize(addr)
    if eq(size, 45) {  // Clone is exactly 45 bytes
        extcodecopy(addr, 0, 0, 45)
        let prefix := mload(0)
        // Check runtime bytecode prefix
        if eq(and(prefix, 0xffffffffffffffffffffffffffffffffffff),
              0x363d3d373d3d3d363d73) {
            // It's a clone! Extract implementation address
            let impl := and(shr(96, mload(10)), 
                           0xffffffffffffffffffffffffffffffffffffffff)
        }
    }
}
```

### 6.4 Transient Storage (EIP-1153)
```solidity
// OZ ReentrancyGuardTransient.sol
assembly {
    // Read transient slot
    let locked := tload(REENTRANCY_SLOT)
    if locked { revert(0, 0) }  // Already entered
    
    // Set lock
    tstore(REENTRANCY_SLOT, 1)
    
    // ... function body ...
    
    // Clear lock
    tstore(REENTRANCY_SLOT, 0)
}

// Advantages over regular storage:
// → ~100 gas vs ~20,000 gas (200x cheaper!)
// → Automatically cleared at end of transaction
// → No need to manually reset
// → Available: Cancun hardfork+
```

### 6.5 Return Data Forwarding
```solidity
// Forward revert reason from failed call
assembly {
    let fmp := mload(0x40)
    success := call(gas(), addr, 0, inPtr, inSize, 0, 0)
    if iszero(success) {
        returndatacopy(fmp, 0, returndatasize())
        revert(fmp, returndatasize())
    }
}
```

---

## 7. AUDIT CHECKLIST FOR ASSEMBLY

```
For every assembly { } block:

MEMORY:
  □ Free memory pointer saved/restored?
  □ No writes to 0x00-0x3f (scratch space)?
  □ No reads beyond allocated memory?
  □ "memory-safe" annotation is truthful?
  □ Memory zeroed after sensitive operations?

ARITHMETIC:
  □ Division by zero checked? (div/mod return 0, not revert)
  □ Overflow/underflow checked? (add/sub/mul wrap mod 2^256)
  □ Signed vs unsigned comparison correct? (slt vs lt)

CALLS:
  □ Return value checked?
  □ returndatasize validated before mload?
  □ Address cleaned (upper 96 bits zeroed)?
  □ Reentrancy guarded for state-changing calls?
  □ delegatecall only to trusted addresses?
  □ Value transfer handled correctly?

STORAGE:
  □ Slot calculation correct?
  □ No collision with Solidity storage layout?
  □ Packed storage read/write correct?
  □ Transient storage used correctly (Cancun+)?

CONTROL FLOW:
  □ All paths terminate (return/revert/stop)?
  □ No fall-through to unintended code?
  □ Loop bounds correct?
  □ Switch covers all cases?

ENCODING:
  □ Function selector correct?
  □ ABI encoding matches expected layout?
  □ Dynamic types (bytes, string) handled correctly?
  □ Offset calculations correct?

GAS:
  □ Gas forwarded correctly for external calls?
  □ No unbounded loops (gas DoS)?
  □ Memory expansion cost considered?
```

---

## 8. YUL vs SOLIDITY vs HUFF

```
Level:     Solidity > Yul > Huff > Raw Bytecode
Safety:    Solidity > Yul > Huff > Raw Bytecode
Gas:       Raw < Huff < Yul < Solidity
Audit:     Solidity easiest, Yul medium, Huff hard

When to use Yul:
  ✅ Gas-critical hot paths (DEX swaps, token transfers)
  ✅ Access to new opcodes (tload, tstore, mcopy)
  ✅ Custom proxy bytecode
  ✅ Return data handling (non-standard tokens)
  ✅ Storage slot manipulation (ERC1967, ERC7201)

When NOT to use Yul:
  ❌ Business logic (use Solidity)
  ❌ Access control (use Solidity modifiers)
  ❌ Complex state machines (use Solidity)
  ❌ Anything that doesn't need gas optimization

Audit priority:
  1. Assembly in token transfers (SafeERC20 pattern)
  2. Assembly in proxy contracts (Clones, ERC1967)
  3. Assembly in cryptographic operations (ECDSA, P256)
  4. Assembly in data structures (Checkpoints, EnumerableSet)
  5. Custom assembly in protocol-specific code
```

---

## 9. QUICK REFERENCE: OPCODE CHEAT SHEET

```
STACK:     PUSH1-32, POP, DUP1-16, SWAP1-16
MATH:      ADD, SUB, MUL, DIV, SDIV, MOD, SMOD, EXP
           ADDMOD, MULMOD, SIGNEXTEND
COMPARE:   LT, GT, SLT, SGT, EQ, ISZERO
BITWISE:   AND, OR, XOR, NOT, BYTE, SHL, SHR, SAR
KECCAK:    KECCAK256(offset, size) → hash
ENV:       ADDRESS, BALANCE, ORIGIN, CALLER, CALLVALUE
           CALLDATALOAD, CALLDATASIZE, CALLDATACOPY
           CODESIZE, CODECOPY, GASPRICE, EXTCODESIZE
           EXTCODECOPY, RETURNDATASIZE, RETURNDATACOPY
           EXTCODEHASH, BLOCKHASH, COINBASE, TIMESTAMP
           NUMBER, DIFFICULTY, GASLIMIT, CHAINID
           SELFBALANCE, BASEFEE, BLOBBASEFEE
MEMORY:    MLOAD, MSTORE, MSTORE8, MSIZE, MCOPY
STORAGE:   SLOAD, SSTORE, TLOAD, TSTORE
FLOW:      JUMP, JUMPI, PC, JUMPDEST, STOP
CALLS:     CALL, CALLCODE, RETURN, DELEGATECALL
           CREATE, CREATE2, STATICCALL
LOG:       LOG0, LOG1, LOG2, LOG3, LOG4
REVERT:    REVERT, INVALID, SELFDESTRUCT
```

---

*BOZAGENTIC · "Assembly: where Solidity's training wheels come off."*
*Every assembly block is a potential bug. Audit them FIRST.*
