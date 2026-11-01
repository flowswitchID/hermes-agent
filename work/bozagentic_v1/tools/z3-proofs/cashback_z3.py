from z3 import *

# Model CashbackRewards._validatePaymentReward
# Prove that maxRewardBps cap can be bypassed

# Variables
distributed = Int('distributed')
allocated = Int('allocated')
send_amount = Int('send_amount')
allocate_amount = Int('allocate_amount')
paymentAmount = Int('paymentAmount')
maxRewardBps = Int('maxRewardBps')

# Constraints
s = Solver()
s.add(distributed >= 0, allocated >= 0)
s.add(send_amount > 0, allocate_amount > 0)
s.add(paymentAmount > 0)
s.add(maxRewardBps > 0, maxRewardBps <= 10000)

# maxAllowed = paymentAmount * maxRewardBps / 10000
maxAllowed = paymentAmount * maxRewardBps / 10000

# ALLOCATE path: previouslyRewarded = distributed + allocated
# Check: distributed + allocated + allocate_amount <= maxAllowed
allocate_passes = (distributed + allocated + allocate_amount <= maxAllowed)

# SEND path: previouslyRewarded = distributed (BUG: ignores allocated)
# Check: distributed + send_amount <= maxAllowed
send_passes = (distributed + send_amount <= maxAllowed)

# Total rewarded = allocated + send_amount (after allocate then send)
total_rewarded = allocated + send_amount

# Prove: both pass individually BUT total exceeds cap
s.add(allocate_passes)
s.add(send_passes)
s.add(total_rewarded > maxAllowed)

print("=== Z3 PROOF: maxRewardBps bypass ===")
result = s.check()
if result == sat:
    m = s.model()
    print(f"SAT — BYPASS CONFIRMED")
    print(f"  paymentAmount = {m[paymentAmount]}")
    print(f"  maxRewardBps = {m[maxRewardBps]}")
    print(f"  maxAllowed = {m[paymentAmount].as_long() * m[maxRewardBps].as_long() // 10000}")
    print(f"  allocated = {m[allocated]}")
    print(f"  distributed = {m[distributed]}")
    print(f"  allocate_amount = {m[allocate_amount]}")
    print(f"  send_amount = {m[send_amount]}")
    print(f"  total_rewarded = {m[allocated].as_long() + m[send_amount].as_long()}")
    print(f"  cap = {m[paymentAmount].as_long() * m[maxRewardBps].as_long() // 10000}")
else:
    print(f"UNSAT — no bypass possible")

# Proof 2: Correct implementation would prevent bypass
print("\n=== Z3 PROOF: Correct impl prevents bypass ===")
s2 = Solver()
s2.add(distributed >= 0, allocated >= 0)
s2.add(send_amount > 0, allocate_amount > 0)
s2.add(paymentAmount > 0)
s2.add(maxRewardBps > 0, maxRewardBps <= 10000)

maxAllowed2 = paymentAmount * maxRewardBps / 10000

# CORRECT: both paths count distributed + allocated
correct_allocate_passes = (distributed + allocated + allocate_amount <= maxAllowed2)
correct_send_passes = (distributed + allocated + send_amount <= maxAllowed2)

total2 = allocated + send_amount
s2.add(correct_allocate_passes)
s2.add(correct_send_passes)
s2.add(total2 > maxAllowed2)

result2 = s2.check()
if result2 == sat:
    print("SAT — bypass still possible (unexpected)")
else:
    print("UNSAT — correct impl PREVENTS bypass ✅")

# Proof 3: Concrete example
print("\n=== CONCRETE EXAMPLE ===")
pa = 10000  # payment amount
bps = 5000  # 50%
cap = pa * bps // 10000  # 5000
print(f"paymentAmount = {pa}, maxRewardBps = {bps}, cap = {cap}")
print(f"TX1: allocate(5000) → prev = 0+0 = 0, total = 0+5000 = 5000 ≤ {cap} ✅")
print(f"TX2: send(5000) → prev = 0 (ignores allocated!), total = 0+5000 = 5000 ≤ {cap} ✅")
print(f"TOTAL rewarded = 5000 + 5000 = 10000 > {cap} ← BYPASS!")
