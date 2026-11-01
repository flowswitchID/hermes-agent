from z3 import *

print("="*60)
print("Z3 PART 1: QUANTIFIED + ARRAY THEORY")
print("="*60)

# === 1. ForAll: ALL users solvent ===
print("\n[1] ForAll: all users solvent after operations")
s = Solver()
balances = Array('balances', IntSort(), IntSort())
user = Int('user')
deposit_user = Int('deposit_user')
deposit_amt = Int('deposit_amt')

s.add(deposit_amt > 0)
s.add(ForAll([user], Select(balances, user) >= 0))

balances_after = Store(balances, deposit_user, Select(balances, deposit_user) + deposit_amt)

# Violation: exists user with negative balance
s.push()
s.add(Exists([user], Select(balances_after, user) < 0))
r = s.check()
print(f"  Negative balance after deposit? {r}")
s.pop()

# === 2. Over-withdraw without check ===
print("\n[2] Over-withdraw (no require)")
s2 = Solver()
bal = Array('bal', IntSort(), IntSort())
wd_user = Int('wd_user')
wd_amt = Int('wd_amt')

s2.add(Select(bal, wd_user) >= 0)
s2.add(wd_amt > Select(bal, wd_user))  # withdraw MORE than balance

bal_after = Store(bal, wd_user, Select(bal, wd_user) - wd_amt)
s2.add(Select(bal_after, wd_user) < 0)
r = s2.check()
if r == sat:
    m = s2.model()
    print(f"  OVER-WITHDRAW: balance={m.eval(Select(bal, wd_user))}, withdraw={m[wd_amt]}")
    print(f"  → Missing require(balance >= amount)!")

# === 3. Allowance mapping (nested Array) ===
print("\n[3] Nested Array: allowances[owner][spender]")
s3 = Solver()
allowances = Array('allowances', IntSort(), ArraySort(IntSort(), IntSort()))
owner = Int('owner')
spender = Int('spender')
approve_amt = Int('approve_amt')
spend_amt = Int('spend_amt')

s3.add(approve_amt >= 0, spend_amt > 0)

# Approve
allowances_1 = Store(allowances, owner, Store(Select(allowances, owner), spender, approve_amt))
current = Select(Select(allowances_1, owner), spender)

# Spend (must be <= allowance)
s3.add(spend_amt <= current)
allowances_2 = Store(allowances_1, owner, Store(Select(allowances_1, owner), spender, current - spend_amt))
remaining = Select(Select(allowances_2, owner), spender)

s3.add(remaining < 0)
r = s3.check()
print(f"  Allowance underflow (guarded)? {r}")

# === 4. Approve race condition ===
print("\n[4] ERC20 approve race condition")
s4 = Solver()
old_allow = Int('old_allow')
new_allow = Int('new_allow')
frontrun_spend = Int('frontrun_spend')

s4.add(old_allow == 100)
s4.add(new_allow == 50)
s4.add(frontrun_spend > 0, frontrun_spend <= old_allow)

total_spent = frontrun_spend + new_allow
s4.add(total_spent > old_allow)
r = s4.check()
if r == sat:
    m = s4.model()
    print(f"  RACE: old={m[old_allow]}, new={m[new_allow]}, frontrun={m[frontrun_spend]}")
    print(f"  total_spent={m.eval(total_spent)} > intended={m[old_allow]}")
    print(f"  → Fix: increaseAllowance/decreaseAllowance")

# === 5. ForAll + temporal: no user can profit from fee ===
print("\n[5] ForAll: no profit after fee")
s5 = Solver()
dep = Int('dep')
wd = Int('wd')
fee_bps = 30

s5.add(dep > 0)
net = wd * (10000 - fee_bps) / 10000

# Can anyone withdraw more than deposited?
s5.add(wd == dep)
s5.add(net > dep)
r = s5.check()
print(f"  Profit after 0.3% fee? {r}")

print("\n  Part 1 COMPLETE ✓")
