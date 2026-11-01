# EVM BYTECODE & YUL/ASSEMBLY MASTER
# BOZAGENTIC | 2026-08-01
# Tujuan: Baca bytecode langsung, audit assembly, detect compiler bugs

---

## 1. EVM FUNDAMENTALS — Stack Machine

```
EVM = Stack-based virtual machine
Stack: max 1024 items, each 256-bit (32 bytes)
Memory: byte-addressable, ephemeral (per-tx)
Storage: key-value 32-byte slots, persistent (per-contract)

SETIAP OPCODE = 1 byte
Operand = 0-32 bytes (tergantung opcode)
```

### Opcodes yang WAJIB dihafal:

```
OPCODE | HEX  | STACK EFFECT    | KEGUNAAN
═══════|══════|═════════════════|══════════════════════════
STOP   | 0x00 |                 | End execution
ADD    | 0x01 | [a,b] → [a+b]  | Arithmetic
MUL    | 0x02 | [a,b] → [a*b]  | Arithmetic
SUB    | 0x03 | [a,b] → [a-b]  | Arithmetic
DIV    | 0x04 | [a,b] → [a/b]  | Division (0 if b=0)
SDIV   | 0x05 | signed div      | Signed division
MOD    | 0x06 | [a,b] → [a%b]  | Modulo
ADDMOD | 0x08 | [a,b,N] → [(a+b)%N] | Safe modular add
MULMOD | 0x09 | [a,b,N] → [(a*b)%N] | Safe modular mul
EXP    | 0x0a | [a,b] → [a^b]  | Exponentiation
LT     | 0x10 | [a,b] → [a<b]  | Unsigned compare
GT     | 0x11 | [a,b] → [a>b]  | Unsigned compare
SLT    | 0x12 | signed <        | Signed compare
SGT    | 0x13 | signed >        | Signed compare
EQ     | 0x14 | [a,b] → [a==b] | Equality
ISZERO | 0x15 | [a] → [a==0]   | Zero check
AND    | 0x16 | bitwise AND     | Bit manipulation
OR     | 0x17 | bitwise OR      | Bit manipulation
XOR    | 0x18 | bitwise XOR     | Bit manipulation
NOT    | 0x19 | bitwise NOT     | Bit flip
BYTE   | 0x1a | extract byte    | Byte extraction
SHL    | 0x1b | shift left      | Bit shift
SHR    | 0x1c | shift right     | Bit shift
SAR    | 0x1d | arithmetic SHR  | Signed shift
KECCAK | 0x20 | hash            | keccak256
ADDRESS| 0x30 | [this.addr]     | Current contract
BALANCE| 0x31 | [addr] → [bal]  | ETH balance
ORIGIN | 0x32 | [tx.origin]     | Transaction origin
CALLER | 0x33 | [msg.sender]    | Message sender
CALLVALUE|0x34| [msg.value]     | ETH sent
CALLDATALOAD|0x35| load 32 bytes| Input data
CALLDATASIZE|0x36| [size]       | Input size
CALLDATACOPY|0x37| copy to mem  | Copy input
CODESIZE|0x38 | [size]          | Code size
CODECOPY|0x39 | copy code       | Copy code
GASPRICE|0x3a | [gasprice]      | Gas price
EXTCODESIZE|0x3b| [addr]→[size] | External code size
EXTCODECOPY|0x3c| copy ext code | Copy external code
RETURNDATASIZE|0x3d| [size]     | Return data size
RETURNDATACOPY|0x3e| copy ret   | Copy return data
EXTCODEHASH|0x3f| [addr]→[hash] | Code hash
BLOCKHASH|0x40| [num]→[hash]   | Block hash
COINBASE|0x41 | [miner]         | Block miner
TIMESTAMP|0x42| [time]          | Block timestamp
NUMBER | 0x43 | [blocknum]      | Block number
PREVRANDAO|0x44| [random]       | Random (post-merge)
GASLIMIT|0x45 | [gaslimit]      | Block gas limit
CHAINID| 0x46 | [chainid]       | Chain ID
SELFBALANCE|0x47| [this.balance]| Self balance
BASEFEE| 0x48 | [basefee]       | Base fee
BLOBHASH|0x49 | [hash]          | Blob hash (EIP-4844)
BLOBBASEFEE|0x4a| [fee]         | Blob base fee
POP    | 0x50 | [a] → []        | Remove top
MLOAD  | 0x51 | [off] → [val]   | Load from memory
MSTORE | 0x52 | [off,val]       | Store to memory
MSTORE8| 0x53 | [off,val]       | Store 1 byte
SLOAD  | 0x54 | [key] → [val]   | Load storage
SSTORE | 0x55 | [key,val]       | Store storage
JUMP   | 0x56 | [dest]          | Jump
JUMPI  | 0x57 | [dest,cond]     | Conditional jump
PC     | 0x58 | [pc]            | Program counter
MSIZE  | 0x59 | [size]          | Memory size
GAS    | 0x5a | [gas]           | Remaining gas
JUMPDEST|0x5b|                  | Jump destination
TLOAD  | 0x5c | [key] → [val]   | Transient load (EIP-1153)
TSTORE | 0x5d | [key,val]       | Transient store (EIP-1153)
MCOPY  | 0x5e | copy memory     | Memory copy (EIP-5656)
PUSH0  | 0x5f | [0]             | Push zero (EIP-3855)
PUSH1-32|0x60-7f| [val]         | Push N bytes
DUP1-16| 0x80-8f| duplicate     | Duplicate stack item
SWAP1-16|0x90-9f| swap          | Swap stack items
LOG0-4 | 0xa0-a4| emit event    | Event log
CREATE | 0xf0 | deploy contract | Create contract
CALL   | 0xf1 | external call   | Call contract
CALLCODE|0xf2 | delegatecall v1 | Legacy delegatecall
RETURN | 0xf3 | return data     | Return
DELEGATECALL|0xf4| delegatecall | Delegate call
CREATE2| 0xf5 | deterministic   | Create2
STATICCALL|0xfa| read-only call | Static call
REVERT | 0xfd | revert          | Revert
INVALID| 0xfe | invalid opcode  | Consume all gas
SELFDESTRUCT|0xff| destroy      | Self destruct
```

---

## 2. STORAGE LAYOUT — Critical untuk Audit

### Solidity Storage Rules:
```
Slot 0: first state variable
Slot 1: second state variable
...

Struct: each field gets its own slot (unless packed)
Mapping: keccak256(key . slot) → value
Array:   keccak256(slot) → element[0], +1 → element[1]

Packing: variables < 32 bytes BISA share slot
  uint128 a; // slot 0, bytes 0-15
  uint128 b; // slot 0, bytes 16-31
  uint256 c; // slot 1 (too big to pack)
```

### Proxy Storage (EIP-1967):
```
Implementation slot:
  bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1)
  = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc

Admin slot:
  bytes32(uint256(keccak256("eip1967.proxy.admin")) - 1)
  = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103

Beacon slot:
  bytes32(uint256(keccak256("eip1967.proxy.beacon")) - 1)
  = 0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50
```

### Storage Collision Bug Pattern:
```
// DANGER: Implementation dan Proxy share storage!
// Kalau implementation punya state variable di slot 0,
// dan proxy juga punya sesuatu di slot 0 → COLLISION

// Safe: pakai ERC-7201 namespaced storage
// bytes32 constant STORAGE_SLOT = keccak256("my.protocol.v1") & ~0xff;
```

---

## 3. ASSEMBLY PATTERNS IN DeFi

### Pattern 1: Transient Storage Reentrancy Guard (EIP-1153)
```solidity
// Solady ReentrancyGuardTransient
uint256 private constant _REENTRANCY_GUARD_STORAGE =
    0x929eee149b4bd21268;

modifier nonReentrant() {
    assembly {
        if tload(_REENTRANCY_GUARD_STORAGE) {
            mstore(0x00, 0xab143c06) // Reentrancy()
            revert(0x1c, 0x04)
        }
        tstore(_REENTRANCY_GUARD_STORAGE, 1)
    }
    _;
    assembly {
        tstore(_REENTRANCY_GUARD_STORAGE, 0)
    }
}

// AUDIT CHECK:
// ✅ tload/tstore = transient (reset per tx)
// ✅ Gas efficient (no SSTORE)
// ⚠️ Cross-function reentrancy: guard per-contract, not per-function
// ⚠️ Multi-chain: TSTORE only on Cancun+ (EIP-1153)
```

### Pattern 2: Minimal Proxy (EIP-1167)
```
Bytecode:
363d3d373d3d3d363d73<address>5af43d82803e903d91602b57fd5bf3

Decode:
36      CALLDATASIZE
3d      RETURNDATASIZE
3d      RETURNDATASIZE
37      CALLDATACOPY      // copy calldata to memory
3d      RETURNDATASIZE
3d      RETURNDATASIZE
3d      RETURNDATASIZE
36      CALLDATASIZE
3d      RETURNDATASIZE
73<addr> PUSH20 <address>  // implementation address
5a      GAS
f4      DELEGATECALL      // delegate to implementation
3d      RETURNDATASIZE
82      DUP3
80      DUP1
3e      RETURNDATACOPY
90      SWAP1
3d      RETURNDATASIZE
91      SWAP2
602b    PUSH1 0x2b
57      JUMPI             // if success, jump to return
fd      REVERT
5b      JUMPDEST
f3      RETURN

// AUDIT CHECK:
// ⚠️ Implementation address HARDCODED in bytecode
// ⚠️ No upgrade mechanism
// ⚠️ If implementation selfdestructs → ALL clones dead
```

### Pattern 3: Custom Error in Assembly
```solidity
assembly {
    mstore(0x00, 0xab143c06) // selector for Reentrancy()
    revert(0x1c, 0x04)       // revert with 4-byte selector
}

// 0x1c = 28 = 32 - 4 (offset to last 4 bytes of 32-byte word)
// 0x04 = 4 bytes (just the selector)

// AUDIT CHECK:
// ⚠️ Wrong selector = wrong error message (not security issue)
// ⚠️ Wrong offset/size = revert with garbage data
```

### Pattern 4: Bit Masking for Packing
```solidity
// Pack multiple values into one slot
assembly {
    // Read slot
    let packed := sload(slot)
    
    // Extract uint128 from lower 128 bits
    let lower := and(packed, 0xffffffffffffffffffffffffffffffff)
    
    // Extract uint128 from upper 128 bits
    let upper := shr(128, packed)
    
    // Write new lower value
    let newPacked := or(and(packed, not(0xffffffffffffffffffffffffffffffff)), newValue)
    sstore(slot, newPacked)
}

// AUDIT CHECK:
// ⚠️ Wrong mask = read/write wrong bits
// ⚠️ Off-by-one in shift = data corruption
// ⚠️ Missing mask on write = overwrite adjacent data
```

---

## 4. REAL BUGS IN ASSEMBLY

### Bug 1: Storage Collision (Parity Wallet, 2017, $150M)
```
Library contract punya state variable di slot 0.
Wallet contracts delegatecall ke library.
Someone called initWallet() on library directly → became owner.
Then called kill() → SELFDESTRUCT → all wallets dead.

Lesson: Library contracts MUST NOT have state variables
        that overlap with calling contract's storage.
```

### Bug 2: Incorrect Bit Shift (various)
```
// WRONG:
let tokenId := shr(mul(leadingZeroBytes, 8), rawTokenId)
// If leadingZeroBytes overflows uint8 → wrong shift

// CORRECT:
let tokenId := shr(mul(and(leadingZeroBytes, 0xff), 8), rawTokenId)
```

### Bug 3: Delegatecall to User-Controlled Address
```
// DANGER:
function execute(address target, bytes calldata data) external {
    (bool success,) = target.delegatecall(data);
    // If target is attacker's contract → arbitrary storage write
}

// SAFE:
// Only delegatecall to KNOWN, IMMUTABLE implementation
```

### Bug 4: Transient Storage Cross-Chain
```
// EIP-1153 (TSTORE/TLOAD) only available on Cancun+
// If contract deployed on pre-Cancun chain → TSTORE = INVALID opcode
// Solady handles this: _useTransientReentrancyGuardOnlyOnMainnet()

// AUDIT CHECK:
// ⚠️ Is the chain running Cancun?
// ⚠️ What happens if TSTORE is not available?
// ⚠️ Fallback to SSTORE or no guard?
```

---

## 5. PRACTICAL EXERCISES

### Exercise 1: Decode Deployed Contract
```bash
# Get bytecode from Blockscout
cast code 0x00000f14ad09382841db481403d1775adee1179f --rpc-url https://mainnet.base.org

# Disassemble
cast disassemble <bytecode>

# Or use forge inspect
forge inspect Flywheel bytecode
forge inspect Flywheel deployedBytecode
forge inspect Flywheel storageLayout
forge inspect Flywheel methodIdentifiers
```

### Exercise 2: Find Storage Slots
```bash
# Read specific storage slot
cast storage 0xCONTRACT 0 --rpc-url https://mainnet.base.org

# EIP-1967 implementation slot
cast storage 0xPROXY 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc

# Calculate mapping slot
# mapping(address => uint256) at slot 3
# slot = keccak256(abi.encode(key, 3))
cast keccak $(cast abi-encode "f(address,uint256)" 0xUSER 3)
```

### Exercise 3: Trace Delegatecall
```bash
# Trace a transaction
cast run 0xTXHASH --rpc-url https://mainnet.base.org

# Look for DELEGATECALL in trace
# Verify: target == expected implementation
# Verify: storage context == proxy (not implementation)
```

### Exercise 4: Audit Yul Reentrancy Guard
```solidity
// Read this and find the bug:
assembly {
    if tload(0x929eee149b4bd21268) {
        mstore(0x00, 0xab143c06)
        revert(0x1c, 0x04)
    }
    tstore(0x929eee149b4bd21268, 1)
}
_;
// BUG: Missing tstore(0x929eee149b4bd21268, 0) after _;
// → Guard never resets → ALL subsequent calls revert!
```

### Exercise 5: Audit Transient Storage Implementation
```solidity
// Check CashbackRewards/Flywheel:
// 1. Is TSTORE used for reentrancy guard?
// 2. Is the guard reset in ALL exit paths (return, revert)?
// 3. What happens on chains without EIP-1153?
// 4. Can cross-function reentrancy bypass the guard?

// Flywheel uses Solady ReentrancyGuardTransient:
// - Line 6: import ReentrancyGuardTransient
// - Line 17: contract Flywheel is ReentrancyGuardTransient
// - Line 686: _useTransientReentrancyGuardOnlyOnMainnet()
//   → returns true (uses transient on ALL chains, not just mainnet)
//   → SAFE if chain supports Cancun
//   → DANGER if chain doesn't support TSTORE
```

---

## 6. TOOLS

```
TOOL              | COMMAND
══════════════════|══════════════════════════════════════
forge inspect     | forge inspect Contract storageLayout
cast disassemble  | cast disassemble 0x<bytecode>
cast storage      | cast storage 0xADDR SLOT --rpc-url URL
cast code         | cast code 0xADDR --rpc-url URL
cast run          | cast run 0xTXHASH --rpc-url URL
evm.codes         | https://evm.codes (opcode reference)
tenderly          | https://tenderly.co (tx debugger)
```

---

## 7. AUDIT CHECKLIST: Assembly/Bytecode

```
Setiap contract yang pakai assembly:

1. □ Storage slot calculation correct?
2. □ Bit masking/shifting correct?
3. □ Delegatecall target is IMMUTABLE/KNOWN?
4. □ Reentrancy guard resets on ALL paths?
5. □ Transient storage available on target chain?
6. □ Return data size checked after external call?
7. □ Memory doesn't overlap with free memory pointer?
8. □ No SELFDESTRUCT in delegatecall target?
9. □ Compiler version has no known bugs?
10. □ Storage layout matches between proxy and impl?
```
