from z3 import *

print("=== Z3 PART 2B: MULTI-STEP TEMPORAL (FIXED) ===")

# 1. 5-step lending
print("\n[1] 5-step lending lifecycle")
s = Solver()
assets_0 = Int('assets_0')
drop = Int('drop')
s.add(assets_0 >= 100)
s.add(drop >= 1, drop <= 99)

borrow = (assets_0 * 75) / 100
assets_2 = assets_0 * (100 - drop) / 100
health = (assets_2 * 100) / borrow
s.add(borrow > 0, health < 80)

seized = borrow * 105 / 100
remaining = assets_2 - seized

# Q1: Insolvent?
s.push()
s.add(remaining < 0)
r = s.check()
if r == sat:
    m = s.model()
    print(f"  INSOLVENT: assets={m[assets_0]}, drop={m[drop]}%")
    print(f"  borrow={m.eval(borrow)}, seized={m.eval(seized)}, remaining={m.eval(remaining)}")
s.pop()

# Q2: Bad debt?
s.push()
s.add(assets_2 < borrow)
r = s.check()
if r == sat:
    m = s.model()
    print(f"  BAD DEBT: drop={m[drop]}%, assets_after={m.eval(assets_2)}, debt={m.eval(borrow)}")
s.pop()

# Q3: Min drop?
s.push()
s.add(health == 79)
r = s.check()
if r == sat:
    m = s.model()
    print(f"  Min drop for liq: {m[drop]}%")
s.pop()

# 2. AMM single swap k-invariant
print("\n[2] AMM single swap: k invariant")
s2 = Solver()
rA = Int('rA')
rB = Int('rB')
amtIn = Int('amtIn')
s2.add(rA >= 1000, rB >= 1000, amtIn > 0)

k_before = rA * rB
amtOut = (amtIn * rB) / (rA + amtIn)
k_after = (rA + amtIn) * (rB - amtOut)

s2.push()
s2.add(k_after < k_before)
r = s2.check()
if r == sat:
    m = s2.model()
    print(f"  k DECREASE: rA={m[rA]}, rB={m[rB]}, in={m[amtIn]}")
    print(f"  k_before={m.eval(k_before)}, k_after={m.eval(k_after)}")
    print(f"  → Integer division rounding!")
else:
    print(f"  k cannot decrease: {r}")
s2.pop()

# With fee
s2.push()
amtIn_fee = amtIn * 997 / 1000
amtOut_fee = (amtIn_fee * rB) / (rA + amtIn_fee)
k_fee = (rA + amtIn) * (rB - amtOut_fee)
s2.add(k_fee < k_before)
r = s2.check()
print(f"  k decrease WITH 0.3% fee? {r}")
s2.pop()

# 3. 3-user reward dust
print("\n[3] 3-user reward distribution dust")
s3 = Solver()
stake1 = Int('stake1')
stake2 = Int('stake2')
stake3 = Int('stake3')
reward = Int('reward')
s3.add(stake1 > 0, stake2 > 0, stake3 > 0, reward > 0)

total = stake1 + stake2 + stake3
r1 = (reward * stake1) / total
r2 = (reward * stake2) / total
r3 = (reward * stake3) / total
distributed = r1 + r2 + r3
dust = reward - distributed

s3.push()
s3.add(dust > 2)
r = s3.check()
print(f"  Dust > 2? {r}")
if r == sat:
    m = s3.model()
    print(f"    stakes={m[stake1]},{m[stake2]},{m[stake3]}, reward={m[reward]}, dust={m.eval(dust)}")
s3.pop()

s3.push()
s3.add(distributed > reward)
r = s3.check()
print(f"  Over-distribution? {r}")
s3.pop()

s3.push()
s3.add(dust == 2)
r = s3.check()
print(f"  Dust == 2 possible? {r}")
if r == sat:
    m = s3.model()
    print(f"    stakes={m[stake1]},{m[stake2]},{m[stake3]}, reward={m[reward]}")
s3.pop()

print("\n  Part 2B COMPLETE ✓")
