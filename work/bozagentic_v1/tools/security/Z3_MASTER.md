# Z3 MASTER — SMT Solver for Smart Contract Verification
# BOZAGENTIC | BitVec, Int, proofs, patterns

---

## BASICS

```python
from z3 import *

# Two modes:
# Int:     Mathematical integers (unbounded, fast for linear)
# BitVec:  Fixed-width bitvectors (bit-exact, slow for nonlinear)
```

## WHEN TO USE WHICH

```
USE Int WHEN:
  - Proving mathematical properties (cap <= payment)
  - Linear arithmetic (addition, comparison)
  - Quick proofs (< 1s)
  - Don't need bit-exact overflow behavior

USE BitVec WHEN:
  - Proving overflow/underflow behavior
  - Bit manipulation (shift, mask, pack)
  - Exact Solidity semantics (uint120, uint256)
  - Need to prove "this EXACT computation is safe"
```

## KEY PATTERNS

### 1. Prove bug exists (SAT)
```python
s = Solver()
s.add(alloc_passes)
s.add(send_passes)
s.add(total > cap)  # should be impossible
if s.check() == sat:
    print("BUG CONFIRMED — bypass exists")
    m = s.model()  # concrete counterexample
```

### 2. Prove fix works (UNSAT)
```python
s = Solver()
s.add(correct_alloc_passes)
s.add(correct_send_passes)
s.add(total > cap)
if s.check() == unsat:
    print("FIX VERIFIED — no bypass possible")
```

### 3. Bit-exact overflow check
```python
BV = 256
a = BitVec('a', BV)
b = BitVec('b', BV)
s.add(ULT(a, BitVecVal(2**120, BV)))  # uint120 range
s.add(ULT(b, BitVecVal(2**120, BV)))
# Can a + b overflow uint120?
s.add(UGT(a + b, BitVecVal(2**120 - 1, BV)))
if s.check() == sat:
    print("OVERFLOW POSSIBLE")
```

### 4. Monotonicity proof
```python
x1 = Int('x1')
x2 = Int('x2')
s.add(x1 <= x2)
s.add(f(x1) > f(x2))  # violate monotonicity
if s.check() == unsat:
    print("MONOTONIC — proven")
```

### 5. Rounding analysis
```python
amount = Int('amount')
bps = Int('bps')
s.add(amount > 0, bps > 0, bps <= 10000)
fee = (amount * bps) / 10000  # Int division = floor
# fee <= amount always?
s.add(fee > amount)
if s.check() == unsat:
    print("FEE BOUNDED — proven")
```

---

## PROOFS WRITTEN (COINBASE AUDIT)

```
PROOF                              | MODE   | RESULT
═══════════════════════════════════|════════|══════════
CashbackRewards bypass             | BitVec | SAT (bug confirmed)
CashbackRewards fix                | BitVec | UNSAT (fix works)
CashbackRewards max ratio          | BitVec | 2x (not 3x)
Commerce fee <= amount             | Int    | PROVEN ✅
Commerce no underflow              | Int    | PROVEN ✅
Commerce fee+net == amount         | Int    | PROVEN ✅
Commerce remainder < divisor       | Int    | PROVEN ✅
Flywheel allocate increases both   | Int    | PROVEN ✅
Flywheel deallocate decreases both | Int    | PROVEN ✅
Flywheel total >= individual       | Int    | PROVEN ✅
Flywheel distribute preserves sum  | Int    | PROVEN ✅
SpendPermission period overflow    | Int    | INFO (year 2106+)
SpendPermission realistic safe     | Int    | PROVEN ✅
Solady guard slot collision        | BitVec | SAT (theoretical)
Solady guard unlock sound          | BitVec | PROVEN ✅
_safePercent == naive (small)      | BitVec | PROVEN ✅
_safePercent no overflow           | BitVec | PROVEN ✅
_safePercent rounding max 1 wei    | BitVec | PROVEN ✅
```

---

## COMMON PITFALLS

```
1. BitVec nonlinear (mul + div) → TIMEOUT
   Fix: Use Int for math proofs, BitVec only for overflow

2. Forgetting range constraints
   Always add: s.add(UGT(x, 0), ULT(x, 2**120))

3. UGT vs > (unsigned vs signed)
   BitVec: use UGT, ULT, UGE, ULE (unsigned)
   Int:    use >, <, >=, <= (signed)

4. Division semantics
   Int:    floor division (Python semantics)
   BitVec: UDiv (unsigned floor division)

5. Model extraction
   m[x].as_long() → Python int from Z3 model
```

---

## LEVEL ASSESSMENT

```
BEFORE: 65% (basic Int proofs)
NOW:    82% (BitVec + Int, 18 proofs, bug confirmed)
EXPERT: 95% (quantifiers, arrays, custom tactics)
GAP:    forall/exists, Array theory, optimization
```
