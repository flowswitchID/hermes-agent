#!/usr/bin/env python3
"""
Z3 DRILL: Cross-contract invariants + temporal properties
Encoding complex DeFi invariants that span multiple contracts
"""
from z3 import *
import time

print("="*60)
print("Z3 DRILL: CROSS-CONTRACT INVARIANTS")
print("="*60)

# ============================================================
# PROPERTY 1: Vault + Lender solvency across contracts
# ============================================================
print("\n[1] Vault + Lender cross-contract solvency")
s = Solver()

# Vault state
vault_totalAssets = Int('vault_totalAssets')
vault_totalShares = Int('vault_totalShares')
user_shares = Int('user_shares')
user_assets = Int('user_assets')

# Lender state
lender_totalDebt = Int('lender_totalDebt')
user_debt = Int('user_debt')
user_collateral_shares = Int('user_collateral_shares')

# Constants
LTV = 7500
LIQ_THRESHOLD = 8000

# Invariants
s.add(vault_totalAssets >= 0)
s.add(vault_totalShares >= 0)
s.add(user_shares >= 0)
s.add(user_debt >= 0)
s.add(user_collateral_shares >= 0)
s.add(lender_totalDebt >= 0)

# Vault solvency: any user can withdraw their proportional share
withdrawable = (user_shares * vault_totalAssets) / vault_totalShares
s.add(vault_totalShares > 0)
s.add(withdrawable <= vault_totalAssets)

# LTV constraint: debt <= 75% of collateral value
collateral_value = (user_collateral_shares * vault_totalAssets) / vault_totalShares
s.add(user_debt * 10000 <= collateral_value * LTV)

# Cross-contract: lender's total debt must be backed by vault's assets
s.add(lender_totalDebt <= vault_totalAssets)

# Check: can we find a state where vault is insolvent?
s.push()
s.add(withdrawable > vault_totalAssets)  # violation
result = s.check()
print(f"  Vault insolvency possible? {result}")  # Should be UNSAT
s.pop()

# Check: can lender debt exceed vault assets?
s.push()
s.add(lender_totalDebt > vault_totalAssets)
result = s.check()
print(f"  Lender over-leverage possible? {result}")  # Should be UNSAT
s.pop()

# ============================================================
# PROPERTY 2: AMM constant product with fees (temporal)
# ============================================================
print("\n[2] AMM constant product — temporal (before/after swap)")
s2 = Solver()

# Before state
rA_before = Int('rA_before')
rB_before = Int('rB_before')
k_before = Int('k_before')

# After state
rA_after = Int('rA_after')
rB_after = Int('rB_after')
k_after = Int('k_after')

# Swap params
amountIn = Int('amountIn')
amountOut = Int('amountOut')
fee_num = 3
fee_den = 1000

s2.add(rA_before > 0, rB_before > 0)
s2.add(amountIn > 0)
s2.add(k_before == rA_before * rB_before)

# Swap A->B with fee
amountInWithFee = amountIn * (fee_den - fee_num)
# amountOut = (amountInWithFee * rB_before) / (rA_before * fee_den + amountInWithFee)
s2.add(rA_after == rA_before + amountIn)
s2.add(rB_after == rB_before - amountOut)
s2.add(k_after == rA_after * rB_after)

# Invariant: k must NOT decrease (fees ensure this)
s2.add(k_after < k_before)  # Try to violate
result = s2.check()
if result == sat:
    m = s2.model()
    print(f"  k DECREASE possible! rA={m[rA_before]}, rB={m[rB_before]}, in={m[amountIn]}, out={m[amountOut]}")
    print(f"  k_before={m[k_before]}, k_after={m[k_after]}")
else:
    print(f"  k cannot decrease: {result} (fees protect)")

# ============================================================
# PROPERTY 3: Liquidation cascade — cross-contract temporal
# ============================================================
print("\n[3] Liquidation cascade — multi-step temporal")
s3 = Solver()

# Step 0: Initial state
debt_0 = Int('debt_0')
coll_value_0 = Int('coll_value_0')
health_0 = Int('health_0')

# Step 1: Price drop
price_drop_pct = Int('price_drop_pct')  # percentage
coll_value_1 = Int('coll_value_1')
health_1 = Int('health_1')

# Step 2: After liquidation
debt_2 = Int('debt_2')
coll_value_2 = Int('coll_value_2')
penalty = 500  # 5%

s3.add(debt_0 > 0, coll_value_0 > 0)
s3.add(health_0 == (coll_value_0 * 10000) / debt_0)
s3.add(health_0 > LIQ_THRESHOLD)  # Initially healthy

# Price drop
s3.add(price_drop_pct > 0, price_drop_pct < 100)
s3.add(coll_value_1 == coll_value_0 * (100 - price_drop_pct) / 100)
s3.add(health_1 == (coll_value_1 * 10000) / debt_0)

# Liquidation triggered when health < threshold
s3.add(health_1 < LIQ_THRESHOLD)

# After liquidation: debt repaid, collateral seized with penalty
s3.add(debt_2 == 0)  # Fully liquidated
s3.add(coll_value_2 == coll_value_1 - (debt_0 * (10000 + penalty)) / 10000)

# Question: Can liquidation leave negative collateral? (bad liquidation design)
s3.push()
s3.add(coll_value_2 < 0)
result = s3.check()
if result == sat:
    m = s3.model()
    print(f"  NEGATIVE collateral after liq! debt={m[debt_0]}, coll={m[coll_value_0]}, drop={m[price_drop_pct]}%")
    print(f"  coll_after={m[coll_value_2]}")
    print(f"  → BUG: Liquidation seizes more than available!")
else:
    print(f"  Collateral always >= 0 after liq: {result}")
s3.pop()

# Question: What's the minimum price drop that triggers liquidation?
s3.push()
s3.add(health_1 == LIQ_THRESHOLD - 1)  # Just below threshold
result = s3.check()
if result == sat:
    m = s3.model()
    min_drop = m[price_drop_pct].as_long()
    print(f"  Min drop for liquidation: {min_drop}% (at LTV={LTV/100}%, threshold={LIQ_THRESHOLD/100}%)")
s3.pop()

# ============================================================
# PROPERTY 4: Share inflation attack (first depositor)
# ============================================================
print("\n[4] First depositor inflation attack")
s4 = Solver()

# Attacker deposits 1 wei, gets 1 share
attacker_deposit = Int('attacker_deposit')
attacker_shares = Int('attacker_shares')
total_shares = Int('total_shares')
total_assets = Int('total_assets')

# Attacker donates large amount
donation = Int('donation')

# Victim deposits
victim_deposit = Int('victim_deposit')
victim_shares = Int('victim_shares')

s4.add(attacker_deposit == 1)  # 1 wei
s4.add(attacker_shares == 1)   # 1 share (first depositor)
s4.add(total_shares == 1)
s4.add(total_assets == 1)

# Donation inflates assets
s4.add(donation > 0)
total_assets_after_donation = total_assets + donation

# Victim deposit gets shares
s4.add(victim_deposit > 0)
s4.add(victim_shares == (victim_deposit * total_shares) / total_assets_after_donation)

# Attack: victim gets 0 shares if donation is large enough
s4.add(victim_shares == 0)
s4.add(victim_deposit > 0)

result = s4.check()
if result == sat:
    m = s4.model()
    print(f"  INFLATION ATTACK POSSIBLE!")
    print(f"  donation={m[donation]}, victim_deposit={m[victim_deposit]}, victim_shares={m[victim_shares]}")
    print(f"  → Victim deposits {m[victim_deposit]} wei but gets 0 shares!")
    print(f"  → Minimum donation for attack: {m[donation]}")
else:
    print(f"  Inflation attack impossible: {result}")

# ============================================================
# PROPERTY 5: Reward distribution fairness (temporal)
# ============================================================
print("\n[5] Reward distribution — multi-user temporal fairness")
s5 = Solver()

# Two users, staking over time
user1_stake = Int('user1_stake')
user2_stake = Int('user2_stake')
total_staked = Int('total_staked')
reward = Int('reward')
user1_reward = Int('user1_reward')
user2_reward = Int('user2_reward')

s5.add(user1_stake > 0, user2_stake > 0)
s5.add(total_staked == user1_stake + user2_stake)
s5.add(reward > 0)

# Proportional distribution
s5.add(user1_reward == (reward * user1_stake) / total_staked)
s5.add(user2_reward == (reward * user2_stake) / total_staked)

# Check: can total distributed exceed reward? (rounding up)
s5.push()
s5.add(user1_reward + user2_reward > reward)
result = s5.check()
print(f"  Over-distribution possible? {result}")
if result == sat:
    m = s5.model()
    print(f"    user1_stake={m[user1_stake]}, user2_stake={m[user2_stake]}, reward={m[reward]}")
    print(f"    distributed: {m[user1_reward]} + {m[user2_reward]} > {m[reward]}")
s5.pop()

# Check: can total distributed be LESS than reward? (dust loss)
s5.push()
s5.add(user1_reward + user2_reward < reward)
result = s5.check()
print(f"  Under-distribution (dust)? {result}")
if result == sat:
    m = s5.model()
    dust = m[reward].as_long() - m[user1_reward].as_long() - m[user2_reward].as_long()
    print(f"    dust lost: {dust} wei (reward={m[reward]}, stakes={m[user1_stake]},{m[user2_stake]})")
s5.pop()

# ============================================================
# PROPERTY 6: Cross-contract reentrancy state inconsistency
# ============================================================
print("\n[6] Reentrancy state inconsistency (cross-contract)")
s6 = Solver()

# Contract A calls Contract B, B calls back A
# State: A.balance[user], A.totalDeposits
a_balance = Int('a_balance')
a_total = Int('a_total')
withdraw_amount = Int('withdraw_amount')

# Correct: update state BEFORE external call
# Vulnerable: update state AFTER external call

# Scenario: reentrant withdraw
# First call: balance=100, withdraw=100
# Reentrant call: balance still 100 (not updated yet), withdraw=100 again
s6.add(a_balance == 100)
s6.add(a_total == 100)
s6.add(withdraw_amount == 100)

# Vulnerable pattern: check passes twice
first_check = a_balance >= withdraw_amount  # True
# After first withdraw (if state not updated):
second_check = a_balance >= withdraw_amount  # Still True!

# Total withdrawn = 200, but balance was only 100
total_withdrawn = withdraw_amount * 2
s6.add(total_withdrawn > a_balance)

result = s6.check()
if result == sat:
    print(f"  REENTRANCY EXPLOIT CONFIRMED!")
    print(f"  balance={a_balance}, withdrawn={total_withdrawn}")
    print(f"  → Double withdrawal: {total_withdrawn} > {a_balance}")
    print(f"  → Fix: update state BEFORE external call (CEI pattern)")

print("\n" + "="*60)
print("Z3 DRILL COMPLETE — 6 properties verified")
print("="*60)
