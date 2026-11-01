from z3 import *

print("=== Z3 PART 2A: BITVECTOR ===")

# 1. uint256 overflow
print("\n[1] uint256 overflow")
s = Solver()
a = BitVec('a', 256)
b = BitVec('b', 256)
s.add(a > 0, b > 0)
s.add(ULT(a * b, a))
r = s.check()
if r == sat:
    m = s.model()
    av, bv = m[a].as_long(), m[b].as_long()
    print(f"  a={av}, b={bv}, wrapped={(av*bv)%(2**256)}")

# 2. div-before-mul
print("\n[2] div-before-mul")
s2 = Solver()
x = BitVec('x', 256)
y = BitVec('y', 256)
z = BitVec('z', 256)
s2.add(x > 0, y > 1, z > 1, ULT(y, x))
bad = UDiv(x, y) * z
good = UDiv(x * z, y)
s2.add(ULT(bad, good))
r = s2.check()
if r == sat:
    m = s2.model()
    xv, yv, zv = m[x].as_long(), m[y].as_long(), m[z].as_long()
    print(f"  x={xv}, y={yv}, z={zv}")
    print(f"  (x/y)*z={(xv//yv)*zv}, (x*z)/y={(xv*zv)//yv}")
    print(f"  loss={(xv*zv)//yv - (xv//yv)*zv}")

# 3. uint128 truncation
print("\n[3] uint128 truncation")
s3 = Solver()
val = BitVec('val', 256)
s3.add(UGT(val, BitVecVal(2**128 - 1, 256)))
trunc = ZeroExt(128, Extract(127, 0, val))
s3.add(ULT(trunc, val))
r = s3.check()
if r == sat:
    m = s3.model()
    v = m[val].as_long()
    print(f"  val={v}, uint128={v%(2**128)}, lost={v - v%(2**128)}")

# 4. SafeCast check
print("\n[4] SafeCast: when is uint256→uint128 safe?")
s4 = Solver()
v = BitVec('v', 256)
s4.add(ULE(v, BitVecVal(2**128 - 1, 256)))
# If v <= max_uint128, truncation is identity
trunc4 = ZeroExt(128, Extract(127, 0, v))
s4.add(trunc4 != v)
r = s4.check()
print(f"  Truncation loss when v <= max128? {r}")  # UNSAT

print("\n  Part 2A COMPLETE ✓")
