# ZK CIRCUIT LANGUAGES — CIRCOM · NOIR · HALO2
# Complete reference for bug hunting in ZK protocols
# BOZAGENTIC · 2026-07-30

---

## 1. WHY ZK BUG HUNTING MATTERS

```
ZK protocols hold BILLIONS:
  - zkSync, Scroll, Linea (L2 rollups)
  - Aztec, Noir (private computation)
  - Tornado Cash, Semaphore (privacy)
  - Worldcoin, Sismo (identity)
  - zkBridge, Succinct (cross-chain)

ZK bugs are DIFFERENT from Solidity bugs:
  → Soundness bug = forge ANY proof
  → Completeness bug = valid proof rejected
  → Underconstrained circuit = accept invalid witness
  → Malleability = modify proof without detection

Bug bounty for ZK:
  → Usually $50K-$1M+ (higher than DeFi)
  → Fewer hunters (high barrier to entry)
  → Less competition = more opportunity
```

---

## 2. CIRCOM

### 2.1 What It Is
```
Circom = circuit compiler (Spain, iden3 team)
  → Write circuits in .circom files
  → Compiles to R1CS (Rank-1 Constraint System)
  → Prover: snarkjs (Groth16, PLONK, FFLONK)
  → Verifier: Solidity contract (auto-generated)
  → Used by: Tornado Cash, Semaphore, Worldcoin, Sismo

Language features:
  → Signals (wires): input, output, intermediate
  → Templates (reusable circuits)
  → Components (instantiated templates)
  → Constraints: === (must hold), <== (assign + constrain)
  --> (witness hint, NOT constrained)
```

### 2.2 Core Syntax
```circom
pragma circom 2.0.0;

// Template = reusable circuit
template Multiplier(n) {
    signal input in[n];      // private inputs
    signal output out;       // output signal
    
    // Constraint: product of all inputs
    var product = 1;
    for (var i = 0; i < n; i++) {
        product *= in[i];
    }
    out <== product;         // assign AND constrain
}

// Main component
component main {public [in]} = Multiplier(3);
```

### 2.3 Signal Operators (CRITICAL for security)
```
<==  Assign + Constrain (SAFE — creates R1CS constraint)
-->  Witness hint only (DANGEROUS — NO constraint!)
===  Constraint only (no assignment)
<--  Private computation (not constrained, not in witness)

⚠️ THE #1 CIRCOM BUG:
   Using --> instead of <==
   → Value computed but NOT constrained
   → Prover can use ANY value
   → Circuit accepts invalid witnesses
   
   Example:
     out --> in[0] * in[1];  // ❌ NOT CONSTRAINED
     out <== in[0] * in[1];  // ✅ CONSTRAINED
```

### 2.4 Key Circomlib Circuits (from source)
```
comparators.circom:
  IsZero()     — out = 1 if in == 0
  IsEqual()    — out = 1 if in[0] == in[1]
  LessThan(n)  — out = 1 if in[0] < in[1] (n bits)
  GreaterThan(n)
  LessEqThan(n)
  GreaterEqThan(n)

bitify.circom:
  Num2Bits(n)  — decompose number to n bits
  Bits2Num(n)  — compose bits to number
  Num2Bits_strict() — with AliasCheck (prevents overflow)

gates.circom:
  XOR()  — out = a + b - 2*a*b
  AND()  — out = a*b
  OR()   — out = a + b - a*b
  NOT()  — out = 1 - in (actually: 1 + in - 2*in)
  NAND() — out = 1 - a*b
  NOR()  — out = a*b + 1 - a - b

Other critical circuits:
  poseidon.circom    — ZK-friendly hash
  mimc.circom        — MiMC hash
  eddsa.circom       — EdDSA signature verification
  babyjub.circom     — BabyJubJub curve operations
  escalarmul.circom  — Scalar multiplication
  pedersen.circom    — Pedersen commitment
  mux1-4.circom      — Multiplexers
  binsum.circom      — Binary addition
```

### 2.5 IsZero Deep Dive (most used, most abused)
```circom
template IsZero() {
    signal input in;
    signal output out;
    signal inv;

    // Witness hint: inverse of in (or 0 if in == 0)
    inv <-- in!=0 ? 1/in : 0;

    // Constraint: out = -in*inv + 1
    // If in != 0: inv = 1/in, so out = -in*(1/in) + 1 = -1 + 1 = 0
    // If in == 0: inv = 0, so out = -0*0 + 1 = 1
    out <== -in*inv + 1;
    
    // Constraint: in*out === 0
    // If in != 0: out must be 0 (from above)
    // If in == 0: in*out = 0*out = 0 (always true)
    in*out === 0;
}

⚠️ SECURITY: The <-- for inv is SAFE here because:
   → The two constraints together force correct behavior
   → Even if prover lies about inv, constraints catch it
   → This is the CORRECT pattern for division in circuits
```

### 2.6 Num2Bits Deep Dive (range proof)
```circom
template Num2Bits(n) {
    signal input in;
    signal output out[n];
    var lc1 = 0;
    var e2 = 1;
    
    for (var i = 0; i < n; i++) {
        // Witness hint: extract bit i
        out[i] <-- (in >> i) & 1;
        
        // Constraint: each bit is 0 or 1
        out[i] * (out[i] - 1) === 0;
        
        // Accumulate: lc1 = sum(out[i] * 2^i)
        lc1 += out[i] * e2;
        e2 = e2 + e2;
    }
    
    // Constraint: reconstructed value == input
    lc1 === in;
}

⚠️ SECURITY: Without the final constraint (lc1 === in):
   → Prover could decompose ANY number into bits
   → Range proof would be meaningless
   
⚠️ SECURITY: Without bit constraint (out[i]*(out[i]-1) === 0):
   → Prover could use non-binary values
   → E.g., out[0] = 5, out[1] = -2 → still sums correctly
   → Breaks all downstream logic
```

---

## 3. NOIR

### 3.1 What It Is
```
Noir = ZK circuit language by Aztec Protocol
  → Rust-like syntax (familiar to Solidity/Rust devs)
  → Compiles to ACIR (Abstract Circuit IR)
  → Backend: Barretenberg (UltraPlonk + Honk)
  → Verifier: Solidity contract (auto-generated)
  → Used by: Aztec, Nocturne, various L2s

Key difference from Circom:
  → Higher level (types, structs, generics, traits)
  → Compiler handles constraint generation
  → Less manual constraint writing
  → But: compiler bugs = circuit bugs
```

### 3.2 Core Syntax
```rust
// Simple circuit: prove x != y
fn main(x: Field, y: pub Field) {
    assert(x != y);
}

// Types:
// Field — prime field element (bn254 scalar field)
// u8, u16, u32, u64, u128 — unsigned integers
// i8, i16, i32, i64 — signed integers
// bool — boolean
// [T; N] — fixed-size array
// pub — public input (visible to verifier)
// (no pub) — private input (hidden in proof)

// Structs
struct Point {
    x: Field,
    y: Field,
}

// Generics
fn sum<let N: u32>(arr: [Field; N]) -> Field {
    let mut total = 0;
    for i in 0..N {
        total += arr[i];
    }
    total
}

// Traits (like Rust)
trait Hash {
    fn hash<H>(self, state: &mut H) where H: Hasher;
}
```

### 3.3 Noir Stdlib (from source)
```
Hash functions:
  std::hash::poseidon2_permutation  — Poseidon2 hash
  std::hash::pedersen_hash          — Pedersen hash
  std::hash::pedersen_commitment    — Pedersen commitment
  sha256_compression               — SHA-256 (foreign)
  keccakf1600                      — Keccak (foreign)
  blake2s, blake3                   — Blake hashes

Signature verification:
  std::ecdsa_secp256k1::verify_signature
  std::ecdsa_secp256r1::verify_signature

Curve operations:
  std::embedded_curve_ops — BabyJubJub / embedded curve
  multi_scalar_mul        — MSM operations

Collections:
  std::collections::BoundedVec — bounded vector
  std::collections::UMap      — unordered map

Other:
  std::aes128            — AES encryption
  std::array::quicksort  — sorting in-circuit
  std::cmp               — comparisons
```

### 3.4 Noir Security Considerations
```
1. ASSERT vs IF:
   assert(x == y);     // Creates constraint — PROVEN
   if x == y { ... }   // Control flow — may NOT constrain
   
   ⚠️ In unconstrained functions, if/else doesn't create constraints
   → Must use assert for security-critical checks

2. UNCONSTRAINED functions:
   unconstrained fn helper(x: Field) -> Field {
       // Computed outside circuit (like <-- in Circom)
       // Result NOT constrained unless explicitly asserted
   }
   
   ⚠️ Same danger as Circom's -->
   → Return value is a HINT, not a proof
   → Must constrain result in constrained context

3. INTEGER OVERFLOW:
   → Noir integers are RANGE-CHECKED by default
   → u8 + u8 that overflows → compile error or runtime constraint
   → But: Field arithmetic wraps (no overflow check)
   → Field(2^254 - 1) + Field(1) = Field(0) (modular)

4. PUBLIC vs PRIVATE:
   pub Field x    — verifier sees this value
   Field x        — hidden in proof
   
   ⚠️ Forgetting pub = verifier can't check
   ⚠️ Adding pub = leaks information

5. COMPILE-TIME vs RUNTIME:
   comptime fn — evaluated at compile time (like templates)
   fn — evaluated at proving time
   
   ⚠️ comptime values are FIXED in circuit
   → Can't be changed per-proof
```

---

## 4. HALO2

### 4.1 What It Is
```
Halo2 = ZK proving system by Zcash/ECC
  → Written in Rust (not a language, a FRAMEWORK)
  → PLONKish arithmetization (custom gates + lookups)
  → No trusted setup (IPA polynomial commitment)
  → Used by: Zcash, Scroll, PSE (Privacy & Scaling)
  → Fork: halo2-ce (Chinese community, PSE)

Key difference:
  → NOT a high-level language
  → You write circuits in Rust directly
  → Full control over gates, columns, constraints
  → Most powerful but most complex
```

### 4.2 PLONKish Arithmetization (from book)
```
Circuit = rectangular matrix of values

Column types:
  Fixed    — constants (set at circuit definition)
  Advice   — witness values (prover fills in)
  Instance — public inputs (shared with verifier)

Constraints:
  → Multivariate polynomials over F
  → Must evaluate to ZERO for each row
  → Can reference cells in current/adjacent rows
  → Controlled by selectors (fixed columns)

Gate example (multiplication):
  | a0  | a1  | s_mul |
  | lhs | rhs |   1   |  → lhs * rhs - out = 0
  | out |     |       |

  Polynomial: s_mul * (a0 * a1 - a0_next) = 0
  When s_mul = 1: enforces a0 * a1 = a0_next
  When s_mul = 0: no constraint (gate disabled)

Lookup arguments:
  → Prove that a tuple of values exists in a table
  → Used for: range checks, bitwise ops, S-boxes
  → More efficient than polynomial constraints for some ops
```

### 4.3 Halo2 Circuit Structure (from simple-example.rs)
```rust
// 1. Define Config (columns + selectors)
#[derive(Clone, Debug)]
struct FieldConfig {
    advice: [Column<Advice>; 2],   // witness columns
    instance: Column<Instance>,     // public input
    s_mul: Selector,               // multiplication gate
}

// 2. Configure (define gates + constraints)
fn configure(meta: &mut ConstraintSystem<F>) -> FieldConfig {
    let advice = [meta.advice_column(), meta.advice_column()];
    let instance = meta.instance_column();
    let s_mul = meta.selector();
    
    // Enable equality for copy constraints
    meta.enable_equality(instance);
    for col in &advice { meta.enable_equality(*col); }
    
    // Define multiplication gate
    meta.create_gate("mul", |meta| {
        let lhs = meta.query_advice(advice[0], Rotation::cur());
        let rhs = meta.query_advice(advice[1], Rotation::cur());
        let out = meta.query_advice(advice[0], Rotation::next());
        let s = meta.query_selector(s_mul);
        vec![s * (lhs * rhs - out)]  // constraint = 0
    });
    
    FieldConfig { advice, instance, s_mul }
}

// 3. Synthesize (fill in witness)
fn synthesize(&self, config: FieldConfig, mut layouter: impl Layouter<F>) {
    let chip = FieldChip::construct(config);
    
    // Load private inputs
    let a = chip.load_private(layouter.namespace(|| "a"), self.a)?;
    let b = chip.load_private(layouter.namespace(|| "b"), self.b)?;
    
    // Compute: c = constant * a^2 * b^2
    let ab = chip.mul(layouter.namespace(|| "a*b"), a, b)?;
    let absq = chip.mul(layouter.namespace(|| "ab*ab"), ab.clone(), ab)?;
    let c = chip.mul(layouter.namespace(|| "const*absq"), constant, absq)?;
    
    // Expose public output
    chip.expose_public(layouter.namespace(|| "expose"), c, 0)?;
}

// 4. Test with MockProver
let prover = MockProver::run(k, &circuit, vec![public_inputs]).unwrap();
assert_eq!(prover.verify(), Ok(()));
```

### 4.4 Halo2 Key Concepts
```
Chip:
  → Modular component of a circuit
  → Owns its config (columns + selectors)
  → Implements Instructions trait
  → Composable (multiple chips in one circuit)

Region:
  → Section of the circuit layout
  → Where cells are assigned
  → Copy constraints link cells across regions

Rotation:
  → Rotation::cur()  — current row
  → Rotation::next() — next row
  → Rotation::prev() — previous row
  → Gates can reference multiple rows

Copy Constraint:
  → Enforces equality between two cells
  → copy_advice() creates copy constraint
  → Essential for wiring chips together

Lookup:
  → Prove value exists in a table
  → meta.lookup("name", |meta| { ... })
  → Used for: range checks, S-boxes, bitwise
```

---

## 5. COMPARISON TABLE

| | Circom | Noir | Halo2 |
|---|---|---|---|
| Level | Low (manual constraints) | High (compiler) | Lowest (Rust framework) |
| Syntax | Custom (.circom) | Rust-like (.nr) | Rust (.rs) |
| Arithmetization | R1CS | ACIR → UltraPlonk | PLONKish |
| Prover | snarkjs | Barretenberg | halo2_proofs |
| Trusted setup | Yes (Groth16) / No (PLONK) | No | No (IPA) |
| Verifier | Solidity (auto) | Solidity (auto) | Custom |
| Learning curve | Medium | Low (if know Rust) | HIGH |
| Bug surface | Manual constraints | Compiler bugs | Gate design |
| Used by | Tornado, Semaphore | Aztec, Nocturne | Zcash, Scroll |
| Audit difficulty | Medium | Low-Medium | HIGH |

---

## 6. ZK BUG TAXONOMY (For Hunting)

### 6.1 Underconstrained Circuits (MOST COMMON)
```
Bug: Circuit doesn't fully constrain the witness
  → Prover can use invalid witness that still satisfies constraints
  → Proof verifies but statement is FALSE

Examples:
  1. Missing range check:
     → Signal claimed to be 256-bit but not constrained
     → Prover uses value > 2^256
     → Overflow in downstream computation

  2. Missing bit decomposition constraint:
     → Num2Bits without lc1 === in
     → Prover decomposes wrong number

  3. Unconstrained division:
     → inv <-- 1/x without x*inv === 1
     → Prover uses inv = 0 for any x

  4. Missing uniqueness check:
     → Merkle proof without index binding
     → Prover uses same leaf at different positions

How to find:
  → For every --> or unconstrained fn: is result constrained?
  → For every division: is denominator != 0 checked?
  → For every range claim: is Num2Bits/AliasCheck used?
  → For every hash: are inputs fully constrained?
```

### 6.2 Arithmetic Bugs
```
1. Field overflow:
   → a + b where a, b near field modulus
   → Result wraps around (modular arithmetic)
   → Missing: assert(a + b < field_modulus)

2. Integer overflow in bit operations:
   → Num2Bits(254) but input can be 255 bits
   → Missing: AliasCheck (strict version)

3. Sign errors:
   → Subtraction without borrow handling
   → Negative values in unsigned context

4. Precision loss:
   → Division in field (exact) vs integer (truncated)
   → Mixing field and integer semantics
```

### 6.3 Logic Bugs
```
1. Wrong comparison:
   → LessThan(n) with n too small
   → Input > 2^n → comparison wraps

2. Missing edge cases:
   → IsZero for field element near modulus
   → Empty array handling
   → Zero-length proof

3. Incorrect gate design (Halo2):
   → Selector not enabled for all rows
   → Rotation offset wrong
   → Copy constraint missing between chips

4. Lookup table errors:
   → Table doesn't cover all valid values
   → Table has duplicate entries
   → Input expression doesn't match table format
```

### 6.4 Protocol-Level Bugs
```
1. Malleability:
   → Proof can be modified without detection
   → Missing: proof binding to public inputs
   → Example: Groth16 without proof-of-knowledge

2. Replay:
   → Same proof valid for different statements
   → Missing: bind proof to specific public inputs
   → Missing: nonce/timestamp in circuit

3. Front-running:
   → Proof submitted → frontrun with same proof
   → Missing: commit-reveal or proof binding

4. Verifier bugs (Solidity):
   → Auto-generated verifier has bugs
   → Wrong ABI encoding
   → Missing public input validation
   → Gas griefing in verifier
```

### 6.5 Implementation Bugs
```
1. Trusted setup compromise:
   → Toxic waste not destroyed
   → Forge arbitrary proofs
   → Check: ceremony transcript, multi-party

2. Prover/Verifier mismatch:
   → Circuit updated but verifier not redeployed
   → Different circuit versions

3. Witness generation bugs:
   → C++/Rust witness calculator differs from circuit
   → Integer overflow in witness gen (not in circuit)

4. Serialization bugs:
   → Proof format mismatch
   → Field element encoding (big-endian vs little-endian)
```

---

## 7. AUDIT CHECKLIST FOR ZK CIRCUITS

### Circom:
```
□ Every <-- has corresponding constraint?
□ Every division has denominator != 0 check?
□ Every range claim uses Num2Bits + AliasCheck?
□ Every comparison uses correct bit width?
□ Every hash input is fully constrained?
□ Every Merkle proof binds index + path?
□ No signal used before constrained?
□ Template parameters validated (n > 0, n <= 254)?
□ Public inputs correctly marked?
□ Verifier contract matches circuit version?
```

### Noir:
```
□ Every unconstrained fn result is asserted?
□ Every assert is in constrained context?
□ Integer types correct (u8 vs Field)?
□ Public inputs marked with pub?
□ No Field overflow in critical paths?
□ Array bounds checked?
□ Signature verification uses correct curve?
□ Hash function appropriate for use case?
□ No information leakage via public inputs?
□ Verifier contract matches circuit version?
```

### Halo2:
```
□ Every gate has correct selector?
□ Every rotation offset correct?
□ Every copy constraint between chips?
□ Every lookup table complete?
□ Every advice column enabled for equality?
□ MockProver passes with wrong inputs? (should FAIL)
□ No unconstrained cells in critical path?
□ Fixed columns correct?
□ Constraint degree within limit?
□ Region layout doesn't overlap?
```

---

## 8. TOOLS FOR ZK BUG HUNTING

```
Circom:
  circom compiler     — compile .circom to R1CS
  snarkjs             — prove/verify + generate Solidity verifier
  circomspect         — static analysis for Circom (by Trail of Bits!)
  picus               — constraint analysis
  ecne                — constraint verification

Noir:
  nargo               — Noir compiler + prover
  noir-inspector      — debug circuit constraints
  bb (barretenberg)   — proving backend

Halo2:
  MockProver          — test circuits without full proof
  halo2_gadgets       — pre-built gadgets (ECC, Poseidon, etc.)
  halo2_wrong         — community gadgets

General:
  ZK bug bounty programs:
    → Immunefi (zkSync, Scroll, Linea)
    → Code4rena (ZK contests)
    → Sherlock (ZK audits)
    → Hats Finance (ZK bounties)
```

---

## 9. REAL ZK BUGS (Case Studies)

```
1. Tornado Cash — Governance Attack (2023)
   → Attacker deployed malicious proposal
   → Gained ownership of governance contract
   → Bug: insufficient validation in proposal execution
   → NOT a circuit bug — Solidity bug in governance

2. Tornado Cash — Proof Malleability
   → Same nullifier could be reused
   → Missing: nullifier uniqueness check in circuit
   → Impact: double-spend of shielded notes

3. ZKSync — Verifier Bug (2023)
   → Incorrect public input handling
   → Could forge proofs for specific cases
   → Bug: Solidity verifier didn't validate all inputs

4. Semaphore — Signal Malleability
   → External nullifier not bound to proof
   → Could replay signals across groups
   → Fix: bind external nullifier in circuit

5. Common Circom Bug Pattern:
   template Vulnerable() {
       signal input a;
       signal input b;
       signal output out;
       
       out <-- a / b;  // ❌ UNCONSTRAINED
       // Missing: out * b === a
       // Missing: b !== 0 check
   }
   
   → Prover can set out to ANYTHING
   → Fix: out <== a / b; (constrains) + b !== 0
```

---

## 10. YOUR ZK HUNTING STRATEGY

```
START HERE (lowest barrier):
  1. Audit Solidity VERIFIERS (not circuits)
     → Auto-generated verifiers often have bugs
     → You already know Solidity auditing
     → Check: public input validation, ABI encoding
     
  2. Audit CIRCUIT-SOLIDITY interface
     → How proofs are submitted on-chain
     → How public inputs are passed
     → How verification results are used
     
  3. Audit ACCESS CONTROL around ZK
     → Who can update verifier?
     → Who can change circuit parameters?
     → Governance of ZK protocol

THEN (medium barrier):
  4. Audit Circom circuits
     → Check underconstrained signals
     → Use circomspect (ToB's tool)
     → Focus on: division, range, comparison
     
  5. Audit Noir circuits
     → Check unconstrained functions
     → Focus on: assert vs if, pub vs private

ADVANCED (high barrier):
  6. Audit Halo2 circuits
     → Gate design, selector logic
     → Copy constraints, lookup tables
     → Requires deep understanding of PLONKish

HIGHEST VALUE:
  → L2 rollup verifier contracts (zkSync, Scroll, Linea)
  → Bridge circuits (zkBridge, Succinct)
  → Privacy protocol circuits (Aztec, Nocturne)
  → Identity circuits (Worldcoin, Sismo)
```

---

*BOZAGENTIC · "ZK: where the math is the attack surface."*
*Fewer hunters, bigger bounties, higher barrier. That's the edge.*
