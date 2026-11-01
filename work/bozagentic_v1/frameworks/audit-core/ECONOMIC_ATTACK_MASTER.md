# ECONOMIC ATTACK MASTER — DeFi Exploit Patterns
# BOZAGENTIC | 2026-08-01
# Tujuan: Economic intuition — "KENAPA orang mau exploit ini?"

---

## 1. BEANSTALK (2022) — $182M

### Economic Incentive
```
Profit: $182M dalam 1 tx
Cost:   ~$100 gas
ROI:    ∞ (flash loan = 0 capital)
```

### Cross-Protocol Interaction
```
Aave (flash loan) → Beanstalk (governance) → Curve (liquidity)
```

### Attack Flow
```
1. Flash loan $1B dari Aave
2. Beli BEAN/LP tokens di Curve
3. Submit BIP-18 (malicious proposal)
4. Vote dengan tokens yang baru dibeli
5. Proposal pass → drain treasury
6. Jual LP tokens, repay flash loan
7. Profit $182M
```

### Invariant yang Dilanggar
```
"Governance voting power harus berdasarkan STAKED tokens
 yang sudah ada SEBELUM proposal, bukan tokens yang baru
 dibeli dalam tx yang sama."
```

### Cara Detect saat Audit
```
❌ Tanya: "Bisa ga seseorang flash loan → vote → drain dalam 1 tx?"
❌ Cek: Apakah ada time-delay antara acquire tokens dan vote?
❌ Cek: Apakah snapshot voting power di block SEBELUM proposal?
✅ Pattern: Governance + flash loan + no snapshot = CRITICAL
```

### Lesson
```
Governance tanpa snapshot = flash loan attack vector.
SELALU cek: "Bisa ga voting power di-manipulate dalam 1 tx?"
```

---

## 2. EULER FINANCE (2023) — $197M

### Economic Incentive
```
Profit: $197M (later returned via negotiation)
Method: Self-liquidation dengan inflated collateral
```

### Cross-Protocol Interaction
```
Euler (lending) → Euler (liquidation) → external DEX (price)
```

### Attack Flow
```
1. Deposit 10 DAI ke Euler
2. Borrow 10x → 100 DAI (undercollateralized via eToken)
3. Transfer eToken ke account ke-2
4. Donate DAI ke Euler → inflate eToken value
5. Account 2 sekarang "overcollateralized"
6. Self-liquidate account 1 → extract collateral
7. Profit dari selisih
```

### Invariant yang Dilanggar
```
"eToken value harus berdasarkan UNDERLYING ASSET balance,
 bukan total supply yang bisa di-inflate via donation."
```

### Cara Detect saat Audit
```
❌ Tanya: "Bisa ga seseorang inflate share price via donation?"
❌ Cek: Apakah balanceOf() dipakai untuk pricing?
❌ Cek: Apakah ada sync() atau equivalent yang bisa di-trigger?
✅ Pattern: balanceOf-based pricing + public sync = inflation attack
```

### Lesson
```
INI SAMA PERSIS dengan Basin/Beanstalk bug lo yang PAID HIGH!
Donation → inflate share → extract. Pattern yang sama.
Lo udah punya insting ini. Sekarang generalize ke semua lending.
```

---

## 3. MANGO MARKETS (2022) — $114M

### Economic Incentive
```
Profit: $114M
Method: Oracle manipulation → borrow → dump
```

### Attack Flow
```
1. Beli MANGO tokens (thin orderbook)
2. Pump price via market orders (low liquidity)
3. Deposit inflated MANGO sebagai collateral
4. Borrow $114M dalam stablecoins
5. Dump MANGO → price crash
6. Walk away dengan $114M stablecoins
```

### Invariant yang Dilanggar
```
"Oracle price harus resisten terhadap manipulasi di
 low-liquidity markets. Mid-price dari orderbook tipis
 bukan true price."
```

### Cara Detect saat Audit
```
❌ Tanya: "Berapa cost untuk move oracle price 10%?"
❌ Cek: Apakah oracle pakai TWAP atau spot price?
❌ Cek: Berapa liquidity di market yang mendasari oracle?
✅ Pattern: Spot oracle + thin liquidity = manipulation
```

---

## 4. BONQDAO (2023) — $120M

### Economic Incentive
```
Profit: $120M
Method: Oracle manipulation via TellorFlex
```

### Attack Flow
```
1. Stake minimum di TellorFlex oracle
2. Submit fake price report (WALBT = $0.01 instead of $1)
3. BonqDAO reads fake price → thinks collateral worthless
4. Attacker liquidates ALL positions at discount
5. Submit correct price → positions restored but damage done
6. Profit dari liquidation discount
```

### Invariant yang Dilanggar
```
"Oracle report harus punya dispute period SEBELUM
 dikonsumsi oleh protocol. No instant consumption."
```

### Cara Detect saat Audit
```
❌ Tanya: "Bisa ga oracle di-manipulate dalam 1-2 tx?"
❌ Cek: Apakah ada dispute/delay mechanism?
❌ Cek: Berapa cost untuk submit fake report vs profit?
✅ Pattern: Push oracle + no delay + high TVL = target
```

---

## 5. CURVE VYPER (2023) — $70M

### Economic Incentive
```
Profit: $70M across multiple pools
Method: Compiler bug → reentrancy
```

### Attack Flow
```
1. Vyper compiler bug: reentrancy lock tidak di-set correctly
2. remove_liquidity() → callback → remove_liquidity() lagi
3. Double-spend LP tokens
4. Drain pool
```

### Invariant yang Dilanggar
```
"Compiler harus generate reentrancy guard yang benar.
 Vyper 0.2.15-0.3.0 punya bug di reentrancy lock."
```

### Cara Detect saat Audit
```
❌ Cek: Versi compiler yang dipakai
❌ Cek: Apakah reentrancy guard di-compile correctly?
❌ Decompile dan verify bytecode vs source
✅ Pattern: Known compiler version + reentrancy = verify bytecode
```

### Lesson
```
COMPILER BUG. Bukan Solidity/Vyper code yang salah.
Selalu cek compiler version against known CVEs.
```

---

## 6. MULTICHAIN (2023) — $126M

### Economic Incentive
```
Profit: $126M
Method: Private key compromise (MPC threshold)
```

### Attack Flow
```
1. MPC key shares dikontrol oleh 1 entity (CEO)
2. Key compromise → sign arbitrary transfers
3. Drain all bridged assets
```

### Invariant yang Dilanggar
```
"MPC threshold harus truly distributed.
 1 entity tidak boleh bisa sign sendiri."
```

### Cara Detect saat Audit
```
❌ Tanya: "Berapa orang yang needed untuk sign?"
❌ Cek: Apakah threshold truly enforced on-chain?
❌ Cek: Apakah ada single point of failure?
✅ Pattern: Bridge + centralized key = rug risk
```

---

## 7. LEVEL FINANCE (2023) — $1M

### Economic Incentive
```
Profit: $1M
Method: Oracle manipulation + leverage
```

### Attack Flow
```
1. Manipulate price oracle (low liquidity pair)
2. Open leveraged position dengan fake price
3. Close position dengan real price
4. Profit dari selisih
```

### Lesson
```
Leverage + manipulable oracle = guaranteed profit.
Cek: "Berapa cost manipulate oracle vs max leverage profit?"
```

---

## 8. ORBIT CHAIN (2024) — $82M

### Economic Incentive
```
Profit: $82M
Method: Private key extraction from validator
```

### Lesson
```
Key management > smart contract security.
Tapi sebagai auditor: cek apakah on-chain ada safeguard
(multisig, timelock, withdrawal limits).
```

---

## 9. PENPIE (2024) — $27M

### Economic Incentive
```
Profit: $27M
Method: Flash loan + reward manipulation
```

### Attack Flow
```
1. Flash loan Pendle LP tokens
2. Deposit ke Penpie → receive receipt tokens
3. Claim rewards (based on deposit amount)
4. Withdraw LP tokens
5. Repay flash loan
6. Keep rewards (disproportionate to actual staking time)
```

### Invariant yang Dilanggar
```
"Rewards harus proportional ke TIME staked, bukan
 AMOUNT staked dalam 1 block."
```

### Cara Detect saat Audit
```
❌ Tanya: "Bisa ga flash loan → deposit → claim → withdraw dalam 1 tx?"
❌ Cek: Apakah rewards based on time-weighted balance?
❌ Cek: Apakah ada minimum staking period?
✅ Pattern: Reward claim + no time lock = flash loan target
```

---

## 10. COMPROMISED KEY ATTACKS (2024-2025)

### Pattern
```
WazirX ($235M), DMM Bitcoin ($305M), Radiant Capital ($50M)
→ Semua via compromised private keys / insider
```

### Cara Detect saat Audit
```
❌ Cek: Admin functions — bisa drain semua funds?
❌ Cek: Multisig threshold — berapa dari total?
❌ Cek: Timelock — ada delay sebelum execute?
❌ Cek: Withdrawal limits — ada cap per tx/day?
✅ Pattern: Unlimited admin + no timelock = rug vector
```

---

## META-PATTERNS: 10 Economic Attack Categories

```
# | PATTERN                    | DETECT QUESTION
══|════════════════════════════|══════════════════════════════════════
1 | Flash loan + governance    | "Bisa vote dalam 1 tx?"
2 | Flash loan + reward claim  | "Bisa claim tanpa time lock?"
3 | Donation/inflation attack  | "balanceOf() dipakai untuk pricing?"
4 | Oracle manipulation        | "Berapa cost move price 10%?"
5 | Reentrancy (compiler bug)  | "Compiler version known CVE?"
6 | Key compromise             | "Admin bisa drain tanpa limit?"
7 | Cross-protocol arb         | "Protocol A + B = inconsistent state?"
8 | Sandwich/frontrun          | "User tx bisa di-sandwich?"
9 | Governance attack          | "Proposal bisa di-push dalam 1 tx?"
10| Economic griefing          | "Bisa rug liquidity tanpa penalty?"
```

## AUDIT CHECKLIST: Economic Lens

```
Setiap audit, WAJIB tanya:

1. "Kalau gue flash loan $1B, apa yang bisa gue exploit?"
2. "Kalau gue manipulate oracle 50%, profit berapa?"
3. "Kalau gue admin yang jahat, berapa yang bisa gue drain?"
4. "Kalau gue user pertama di pool, bisa gue rug yang lain?"
5. "Kalau gue front-run setiap tx, profit berapa per tx?"
6. "Kalau gue donate 1 wei ke contract, apa yang berubah?"
7. "Kalau gue call sync()/skim()/update() publik, apa efeknya?"
8. "Kalau gue governance attack, berapa cost vs profit?"
9. "Kalau gue sandwich user, berapa max extractable?"
10. "Kalau gue jadi protocol B yang interact, bisa gue exploit A?"
```
