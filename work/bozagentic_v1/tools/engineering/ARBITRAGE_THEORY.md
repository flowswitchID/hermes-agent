# 📚 TEORI ARBITRASE DeFi — LENGKAP SEMUA CHAIN
# Ditulis dari pengalaman nyata: $27 loss, 14 pitfalls, 11 kontrak arb
# BOZAGENTIC BOZAGENTIC · 2026-07-29

---

## 1. TIPE ARBITRASE

### 1.1 Spatial / Cross-DEX Arbitrage

**Konsep:** Harga token berbeda di 2 DEX pada chain yang sama.

```
Profit = (Price_sell - Price_buy) × Amount - Fees - Gas

Dimana:
  Price_buy  = harga di DEX A (beli murah)
  Price_sell = harga di DEX B (jual mahal)
  Fees       = swap_fee_A + swap_fee_B + flash_loan_premium
  Gas        = gas_cost × gas_price
```

**Minimum viable spread:**
```
Spread_min = Fee_A + Fee_B + FlashLoan_Premium + Gas/Amount

Contoh Base (gas $0.01, amount $1000):
  Uniswap V3 (0.05%) + Uniswap V3 (0.30%) + Aave (0.05%) + $0.01/$1000
  = 0.05% + 0.30% + 0.05% + 0.001%
  = 0.401% minimum spread
```

**Kenyataan di Base:**
- WETH/USDC spread antar fee tier: 0.02-0.4% → TIDAK PROFITABLE
- cbETH/WETH cross-DEX (QuickSwap vs PancakeSwap): 1.3-4.1% → PROFITABLE tapi liquidity tipis ($147k)
- Altcoin pairs: spread lebih besar tapi slippage juga besar

### 1.2 Triangular Arbitrage

**Konsep:** 3 swap membentuk loop: A→B→C→A, kalau hasil akhir > modal = profit.

```
Profit = Amount × Rate_AB × Rate_BC × Rate_CA - Amount - Fees

Contoh:
  USDC → WETH (di Uni V3 0.05%)
  WETH → AERO (di Aerodrome)
  AERO → USDC (di Uni V3 0.30%)

  Fees = 0.05% + 0.30% + 0.30% + flash_loan 0.05% = 0.70%
  Butuh: product of rates > 1.007
```

**Kenyataan:** Sangat jarang profit di L2. Spread antar 3 pair harus > 0.7% simultaneously. Window-nya < 1 block (2 detik di Base).

### 1.3 Cross-Chain Arbitrage

**Konsep:** Harga token berbeda di 2 chain berbeda.

```
Profit = (Price_chainB - Price_chainA) × Amount - Bridge_Fee - Gas_A - Gas_B

Risiko:
  - Bridge latency: 7 hari (optimistic), 10-30 min (fast bridges)
  - Price convergence: harga bisa berubah saat bridge belum selesai
  - NON-ATOMIC: nggak bisa flash loan cross-chain (kecuali pakai bridge yang support)
```

**Bridge types:**
| Bridge | Latency | Fee | Atomic? |
|--------|---------|-----|---------|
| Optimistic (Hop, Across) | 7 days dispute | 0.05-0.3% | ❌ |
| Fast (Stargate, Synapse) | 1-5 min | 0.05-0.1% | ❌ |
| Native (OP/Arb bridge) | 7 days | Gas only | ❌ |
| Intent-based (Across V3) | 10-60 sec | 0.05-0.2% | ❌ |

**Kenyataan:** Cross-chain arb butuh modal besar ($50k+) dan toleransi risiko tinggi. Bukan buat flash loan.

### 1.4 Flash Loan Arbitrage

**Konsep:** Pinjam → arb → bayar dalam 1 tx. Zero capital risk.

```
Profit = Arb_Profit - Flash_Loop_Premium - Gas

Premium:
  Aave V3:     0.05% (5 bps)
  Aave V2:     0.09% (9 bps)
  Uniswap V3:  0.30% (flash swap, fee tier dependent)
  dYdX:        FREE (tapi cuma ETH mainnet, deprecated)
  Balancer:    FREE (flash loan tanpa fee!)
```

**Best flash loan source per chain:**
| Chain | Best | Premium | Notes |
|-------|------|---------|-------|
| Base | Aave V3 | 0.05% | flashLoanSimple verified |
| Ethereum | Balancer | 0% | Free tapi vault liquidity limited |
| Arbitrum | Aave V3 | 0.05% | Same interface |
| Polygon | Aave V3 | 0.05% | Same interface |
| BSC | PancakeSwap | 0.25% | flashSwap di pair |

### 1.5 MEV / Sandwich Attack

**Konsep:** Front-run + back-run victim's swap.

```
Attacker:
  1. Lihat pending tx di mempool (victim mau swap $10k di Uni V3)
  2. Front-run: beli token sebelum victim (naikin harga)
  3. Victim swap execute (dapat harga lebih mahal)
  4. Back-run: jual token setelah victim (profit dari price impact)

Profit = Price_impact × Victim_amount - 2 × Gas - Priority_fee
```

**Kenyataan di Base:**
- Base pakai sequencer terpusat → mempool nggak publik
- MEV di Base SANGAT TERBATAS (nggak ada Flashbots, nggak ada public mempool)
- Kebanyakan swap route via aggregator → susah detect
- **Base bukan chain buat MEV. Ethereum mainnet = MEV playground.**

### 1.6 Statistical Arbitrage

**Konsep:** Model matematika predict price divergence, execute saat threshold tercapai.

```
Bukan on-chain pure — butuh:
  - Historical price data
  - Mean-reversion model
  - Execution engine (bot)
  - Risk management (stop-loss)
```

Ini lebih ke quant trading. Bukan fokus kita.

---

## 2. AMM MATH

### 2.1 Uniswap V2: Constant Product (x × y = k)

```
Reserves: (x, y) dimana x × y = k

Swap dx → dy:
  dy = (y × dx × 997) / (x × 1000 + dx × 997)
  
  997/1000 = 0.3% fee

Price impact:
  impact = dx / (x + dx)  (approximation untuk small dx)
  
  $1000 swap di pool $100k: impact ≈ 1%
  $1000 swap di pool $1M:  impact ≈ 0.1%
  $1000 swap di pool $10k: impact ≈ 10% ← SLIPPAGE GILA

Spot price:
  P = y / x (token1 per token0, sebelum fee)

Arb condition (2 pools):
  P_poolA ≠ P_poolB → arb exists
  Profit = Amount × |P_A - P_B| / P_avg - fees
```

### 2.2 Uniswap V3: Concentrated Liquidity

```
Tick-based liquidity:
  - Liquidity disediakan di range [tick_lower, tick_upper]
  - sqrtPriceX96 = sqrt(price) × 2^96
  
Price dari sqrtPriceX96:
  price = (sqrtPriceX96 / 2^96)²
  
  Untuk WETH/USDC (18 dec vs 6 dec):
  actual_price = price × 10^(18-6) = price × 10^12

Swap math:
  Untuk swap dalam 1 tick:
    amount0 = L × (1/√P_lower - 1/√P_upper)
    amount1 = L × (√P_upper - √P_lower)
  
  L = liquidity (dari pool.liquidity())

Fee tiers:
  0.01% (1 bps)   — stable pairs (USDC/USDT)
  0.05% (5 bps)   — correlated (WETH/cbETH)
  0.30% (30 bps)  — standard (WETH/USDC)
  1.00% (100 bps) — exotic/low-liq

Arb insight:
  Fee tier berbeda → harga berbeda (karena liquidity berbeda)
  TAPI: spread antar tier < fee difference → TIDAK PROFITABLE
  Verified di Base: WETH/USDC 0.05% vs 1.00% spread = 0.4%, fees = 1.05% → RUGI
```

### 2.3 Solidly / Aerodrome (Curve fork)

```
Stableswap invariant (untuk stable pools):
  A × n^n × Σx_i + D = A × D × n^n + D^(n+1) / (n^n × Πx_i)
  
  A = amplification coefficient
  n = number of tokens
  D = total value

Volatile pools (V2-like):
  x × y = k (sama kayak Uni V2)
  Fee: 0.30% typical (configurable per pool)

Quirks:
  - getReserves() REVERTS → pakai balanceOf()
  - factory() di router REVERTS → pakai defaultFactory()
  - 2 pool types: "volatile" (V2) dan "stable" (Curve)
  - Gauge system: liquidity mining rewards
```

### 2.4 Balancer (Weighted Pools)

```
Invariant: Π(B_i / W_i)^W_i = k

  B_i = balance token i
  W_i = weight token i (sum = 1)

Swap:
  amountOut = B_out × (1 - (B_in / (B_in + amountIn × (1 - fee)))^(W_in/W_out))

Flash loan: FREE (0% premium) — tapi vault liquidity limited.

Arb use case: Balancer ↔ Uni V3 price differences.
```

### 2.5 Curve Finance (Stableswap)

```
Same invariant as Solidly stable pools.
Fee: 0.04% (4 bps) — PALING MURAH buat stable arb.

Arb: Curve ↔ Uni V3 stable pairs (USDC/USDT/DAI)
  Spread biasanya < 0.01% → butuh $1M+ buat profit
  Gas di Ethereum: $5-50 → butuh spread > 0.005%
```

---

## 3. FEE STRUCTURE — SEMUA DEX

### 3.1 Per-DEX Fees

| DEX | Chain | Fee | Type |
|-----|-------|-----|------|
| Uniswap V2 | ETH | 0.30% | Fixed |
| Uniswap V3 | ETH/Base/Arb/OP/Polygon | 0.01/0.05/0.30/1.00% | Per pool |
| Aerodrome | Base | 0.01-1.00% | Per pool (gauge) |
| PancakeSwap V3 | BSC/Base/ETH | 0.01/0.05/0.25/1.00% | Per pool |
| QuickSwap | Polygon/Base | 0.01/0.05/0.30/1.00% | Per pool |
| SushiSwap | Multi | 0.30% | Fixed |
| Curve | ETH/Arb/OP | 0.04% | Stable pools |
| Balancer | ETH/Arb/OP | 0.01-1.00% | Per pool |
| Velodrome | OP | 0.01-1.00% | Per pool (gauge) |

### 3.2 Aggregator Fees

| Aggregator | Fee | Notes |
|-----------|-----|-------|
| ParaSwap | 0 (protocol) | Takes spread, positive slippage |
| 1inch | 0 (protocol) | API key required |
| 0x/Matcha | 0 (protocol) | API key required |
| CowSwap | 0 (protocol) | Batch auction, MEV protection |
| Odos | 0 (protocol) | API key required |
| OpenOcean | 0 (protocol) | API key required |
| Socket | 0 (protocol) | Cross-chain, API key required |

**Aggregator = free tapi butuh API key.** Tanpa key → 401/403.

### 3.3 Total Cost Formula

```
Total_Cost = Swap_Fee_Buy + Swap_Fee_Sell + Flash_Loan_Premium + Gas

Contoh realistic (Base, $1000 arb):
  Buy on Uni V3 0.05%:   $0.50
  Sell on Uni V3 0.30%:  $3.00
  Aave flash loan 0.05%: $0.50
  Gas (300k × 0.01 gwei): $0.01
  ─────────────────────────────
  Total:                  $4.01

  Butuh spread > 0.401% buat break even
  Butuh spread > 0.5% buat profit meaningful ($1+)
```

---

## 4. PROFITABILITY THRESHOLDS PER CHAIN

### 4.1 Minimum Spread (after all fees)

| Chain | Gas Cost | Min Spread ($1k) | Min Spread ($10k) | Min Spread ($100k) |
|-------|----------|-------------------|--------------------|--------------------|
| Base | $0.01-0.05 | 0.41% | 0.40% | 0.40% |
| Arbitrum | $0.05-0.20 | 0.42% | 0.40% | 0.40% |
| Optimism | $0.05-0.20 | 0.42% | 0.40% | 0.40% |
| Polygon | $0.01-0.05 | 0.41% | 0.40% | 0.40% |
| BSC | $0.10-0.30 | 0.43% | 0.40% | 0.40% |
| Ethereum | $5-50 | 0.90% | 0.45% | 0.41% |

**Insight:** Di L2, gas negligible. Bottleneck = DEX fees (0.40% minimum). Di Ethereum, gas dominates untuk small amounts.

### 4.2 Sweet Spot Amount

| Chain | Sweet Spot | Why |
|-------|-----------|-----|
| Base | $500-2000 | Above $2k, slippage kills (thin liq) |
| Arbitrum | $2000-10000 | Deeper liquidity than Base |
| Ethereum | $50k-500k | Gas fixed, need volume to amortize |
| BSC | $1000-5000 | PancakeSwap deep pools |

### 4.3 Verified Reality (Base, 2026-07-28)

```
WETH/USDC fee-tier arb:     SPREAD 0.02-0.4% < FEES 0.40% → ❌ NEVER PROFIT
cbETH/WETH cross-DEX:       SPREAD 1.3-4.1% > FEES 0.40% → ✅ BUT $147k liq cap
AERO/WETH:                  SPREAD 0.1-0.5% → ⚠️ MARGINAL
USDC/USDT stable:           SPREAD < 0.01% → ❌ DEAD
```

---

## 5. ROUTER & AGGREGATOR — SEMUA CHAIN

### 5.1 Ethereum Mainnet

| DEX/Router | Address | Interface | Status |
|-----------|---------|-----------|--------|
| Uniswap V2 Router | `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D` | V2 | ✅ Active |
| Uniswap V3 SwapRouter | `0xE592427A0AEce92De3Edee1F18E0157C05861564` | V3 | ✅ Active (REAL di ETH) |
| Uniswap Universal Router | `0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD` | Universal | ✅ Active |
| Uniswap V3 Factory | `0x1F98431c8aD98523631AE4a59f267346ea31F984` | Factory | ✅ |
| Uniswap V3 Quoter V2 | `0x61fFE014bA17989E743c5F6cB21bF9697530B21e` | Quoter | ✅ |
| 1inch V6 Router | `0x111111125421cA6dc452d289314280a0f8842A65` | Aggregator | ✅ (API key) |
| ParaSwap Augustus V6 | `0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57` | Aggregator | ✅ (REAL di ETH) |
| 0x Exchange Proxy | `0xDef1C0ded9bec7F1a1670819833240f027b25EfF` | Aggregator | ✅ |
| CowSwap GPv2 | `0x9008D19f58AAbD9eD0D60971565AA8510560ab41` | Batch auction | ✅ |
| SushiSwap Router | `0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F` | V2 | ✅ |
| Curve Registry | `0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d7f5` | Registry | ✅ |
| Balancer Vault | `0xBA12222222228d8Ba445958a75a0704d566BF2C8` | Vault | ✅ |

### 5.2 Base Chain

| DEX/Router | Address | Interface | Status |
|-----------|---------|-----------|--------|
| ⚠️ Uniswap V3 SwapRouter | `0xE592427A0AEce92De3Edee1F18E0157C05861564` | V3 | ❌ **STUB! 34k gas, no swap** |
| ✅ Uniswap Universal Router | `0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7` | Universal | ✅ REAL |
| Uniswap V3 Factory | `0x33128a8fC17869897dcE68Ed026d694621f6FDfD` | Factory | ✅ |
| Uniswap V3 Quoter V2 | `0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a` | Quoter | ✅ |
| Aerodrome Router | `0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43` | Solidly | ⚠️ Quirks |
| Aerodrome Factory | `0x420DD381b31aEf6683db6B902084cB0FFECe40Da` | Factory | ✅ (via defaultFactory) |
| ParaSwap Augustus V6 | `0x59C7C832e96D2568bea6db468C1aAdcbbDa08A52` | Aggregator | ✅ (API verified) |
| ParaSwap TokenTransferProxy | `0x93aAAe79a53759cD164340E4C8766E4Db5331cD7` | Proxy | ✅ |
| Aave V3 Pool | `0xA238Dd80C259a72e81d7e4664a9801593F98d1c5` | Flash loan | ✅ |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | Permit | ✅ |
| WETH | `0x4200000000000000000000000000000000000006` | Token | ✅ |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | Token | ✅ |
| AERO | `0x940181a94A35A4569E4529A3CDfB74e38FD98631` | Token | ✅ |
| cbETH | `0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22` | Token | ✅ |

### 5.3 Arbitrum One

| DEX/Router | Address | Interface | Status |
|-----------|---------|-----------|--------|
| Uniswap V3 SwapRouter | `0xE592427A0AEce92De3Edee1F18E0157C05861564` | V3 | ✅ REAL (beda sama Base!) |
| Uniswap Universal Router | `0x5E325eDA8064b456f4781070C0738d849c824258` | Universal | ✅ |
| Uniswap V3 Factory | `0x1F98431c8aD98523631AE4a59f267346ea31F984` | Factory | ✅ |
| GMX Router | `0xaBBc5F99639c9B6bCb58544ddf04EFA6802F4064` | Perp/Spot | ✅ |
| Camelot Router | `0xc873fEcbd354f5A56E00E710B90EF4201db2448d` | V2 | ✅ |
| Aave V3 Pool | `0x794a61358D6845594F94dc1DB02A252b5b4814aD` | Flash loan | ✅ |
| ParaSwap Augustus | `0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57` | Aggregator | ✅ |
| WETH | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` | Token | ✅ |
| USDC | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | Token | ✅ |

### 5.4 Optimism

| DEX/Router | Address | Interface | Status |
|-----------|---------|-----------|--------|
| Uniswap V3 SwapRouter | `0xE592427A0AEce92De3Edee1F18E0157C05861564` | V3 | ✅ REAL |
| Uniswap Universal Router | `0xCb1355ff08Ab38bBCE60111F1bb2B784bE25D7e8` | Universal | ✅ |
| Velodrome Router | `0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858` | Solidly | ✅ |
| Aave V3 Pool | `0x794a61358D6845594F94dc1DB02A252b5b4814aD` | Flash loan | ✅ |
| WETH | `0x4200000000000000000000000000000000000006` | Token | ✅ |
| USDC | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | Token | ✅ |

### 5.5 Polygon

| DEX/Router | Address | Interface | Status |
|-----------|---------|-----------|--------|
| Uniswap V3 SwapRouter | `0xE592427A0AEce92De3Edee1F18E0157C05861564` | V3 | ✅ REAL |
| QuickSwap Router | `0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff` | V2 | ✅ |
| QuickSwap V3 | Custom pools | V3-like | ⚠️ fee=750, non-standard |
| Aave V3 Pool | `0x794a61358D6845594F94dc1DB02A252b5b4814aD` | Flash loan | ✅ |
| WETH | `0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619` | Token | ✅ |
| USDC | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | Token | ✅ |

### 5.6 BSC (BNB Chain)

| DEX/Router | Address | Interface | Status |
|-----------|---------|-----------|--------|
| PancakeSwap V2 Router | `0x10ED43C718714eb63d5aA57B78B54704E256024E` | V2 | ✅ Dominant |
| PancakeSwap V3 Router | `0x13f4EA83D0bd40E75C8222255bc855a974568Dd4` | V3 | ✅ |
| PancakeSwap Factory | `0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73` | Factory | ✅ |
| Aave V3 Pool | N/A | — | ❌ Not on BSC |
| Venus (flash loan) | `0xfD36E2c2a6789Db23113685031d7F16329158384` | Flash loan | ✅ |
| WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` | Token | ✅ |
| USDC | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | Token | ✅ |

---

## 6. VERIFIKASI ROUTER ↔ POOL CONNECTIVITY

### 6.1 Pre-Flight Checklist (WAJIB sebelum coding arb)

```bash
# Step 1: Router punya code?
cast code $ROUTER --rpc-url $RPC | wc -c
# > 100 = ada code. 0x atau < 10 = STUB/DEAD

# Step 2: Function selector ada di bytecode?
cast code $ROUTER --rpc-url $RPC | grep -c "414bf389"
# exactInputSingle selector. 0 = TIDAK ADA → wrong router!

# Step 3: Factory return pool address?
cast call $FACTORY "getPool(address,address,uint24)(address)" $TOKEN_A $TOKEN_B $FEE --rpc-url $RPC
# 0x000...000 = NO POOL → nggak ada liquidity

# Step 4: Pool punya liquidity?
cast call $POOL "liquidity()(uint128)" --rpc-url $RPC
# 0 = DEAD POOL → nggak bisa swap

# Step 5: Pool punya reserves?
cast call $POOL "slot0()(uint160,int24,uint16,uint16,uint16,uint8,bool)" --rpc-url $RPC
# sqrtPriceX96 = 0 = UNINITIALIZED

# Step 6: Test swap TINY (0.0001 ETH)
cast send $ROUTER "exactInputSingle(...)" ... --value 100000000000000 --rpc-url $RPC
cast receipt $TX --rpc-url $RPC | grep gasUsed
# < 50k = NO-OP (stub). > 80k = REAL SWAP
```

### 6.2 Red Flags — Router Palsu/Stub

| Red Flag | Artinya |
|----------|---------|
| `cast code` return `0x` | Dead address, no contract |
| `cast code` return < 200 bytes | Proxy tanpa implementation |
| gasUsed < 50k on swap | **STUB** — function nggak execute |
| No Transfer events in receipt | Swap nggak terjadi |
| No Sync/Swap events | Pool nggak di-touch |
| `factory()` returns 0x0 | Router nggak connected ke factory |
| `getPool()` returns 0x0 | No pool exists for pair |
| `liquidity()` = 0 | Pool dead/empty |

### 6.3 Chain-Specific Verification

**Base:**
```bash
# ⚠️ JANGAN pakai 0xE592427A... — STUB di Base!
# ✅ Pakai Universal Router: 0xfdf682f5...
# ✅ Atau direct pool swap (bypass router entirely)

# Verify Universal Router:
cast code 0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7 --rpc-url https://mainnet.base.org | wc -c
# Should be > 10000 bytes

# Verify selector:
cast code 0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7 --rpc-url https://mainnet.base.org | grep -c "3593564c"
# execute(bytes,bytes[],uint256) — should be 1+
```

**Aerodrome (Base):**
```bash
# factory() REVERTS — pakai defaultFactory()
cast call 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43 "defaultFactory()(address)" --rpc-url $RPC
# Returns: 0x420DD381b31aEf6683db6B902084cB0FFECe40Da

# getReserves() REVERTS — pakai balanceOf
cast call $POOL "token0()(address)" --rpc-url $RPC
cast call $TOKEN0 "balanceOf(address)(uint256)" $POOL --rpc-url $RPC
```

**QuickSwap (Polygon/Base):**
```bash
# fee() return 750 (non-standard!)
cast call $POOL "fee()(uint24)" --rpc-url $RPC
# 750 = 0.075% — bukan standard Uni V3 (500/3000/10000)

# slot0() ada tapi format mungkin beda
# Verify swap selector:
cast code $POOL --rpc-url $RPC | grep -c "128acb08"
# 1 = standard V3 swap interface ✅
```

### 6.4 Callback Verification (Critical!)

```bash
# Sebelum direct pool swap, cek callback function:
cast code $POOL --rpc-url $RPC | grep -c "fa461e33"  # uniswapV3SwapCallback
cast code $POOL --rpc-url $RPC | grep -c "23a69e75"  # pancakeV3SwapCallback

# Kalau NEITHER = 0 → custom callback → perlu reverse engineer
```

| DEX | Callback | Selector |
|-----|----------|----------|
| Uniswap V3 | `uniswapV3SwapCallback(int256,int256,bytes)` | `0xfa461e33` |
| PancakeSwap V3 | `pancakeV3SwapCallback(int256,int256,bytes)` | `0x23a69e75` |
| QuickSwap | Unknown | Verify via bytecode |
| Aerodrome | N/A (V2-style, no callback) | — |

---

## 7. AGGREGATOR API REFERENCE

### 7.1 ParaSwap (FREE, no key)

```
Price:  GET https://api.paraswap.io/prices/?srcToken={}&destToken={}&amount={}&srcDecimals={}&destDecimals={}&side=SELL&network={chainId}&userAddress={}
Tx:     POST https://api.paraswap.io/transactions/{chainId}

Chain IDs: 1 (ETH), 8453 (Base), 42161 (Arb), 10 (OP), 137 (Polygon), 56 (BSC)

⚠️ LIMITATIONS:
  - /transactions/ does LIVE BALANCE CHECK → flash loan contracts fail (balance=0)
  - 500 errors ~30% of time → retry with fresh quote
  - Workaround: pre-fund contract with 1 wei
```

### 7.2 1inch (API key required)

```
Price:  GET https://api.1inch.dev/swap/v6.0/{chainId}/quote?src={}&dst={}&amount={}
Tx:     GET https://api.1inch.dev/swap/v6.0/{chainId}/swap?src={}&dst={}&amount={}&from={}&slippage={}

Auth: Bearer token (register at portal.1inch.dev)
Free tier: 1000 requests/day
```

### 7.3 0x Protocol (API key required)

```
Price:  GET https://api.0x.org/swap/v1/price?sellToken={}&buyToken={}&sellAmount={}
Tx:     GET https://api.0x.org/swap/v1/quote?sellToken={}&buyToken={}&sellAmount={}&takerAddress={}

Auth: API key in header
```

### 7.4 CowSwap (No key, batch auction)

```
Quote:  POST https://api.cow.fi/mainnet/api/v1/quote
Orders: POST https://api.cow.fi/mainnet/api/v1/orders

Unique: batch auction every ~5 seconds, MEV protection
No flash loan support (settlement is async)
```

---

## 8. GOLDEN RULES — LESSONS FROM $27 LOSS

### RULE #1: NEVER trust an address without `cast code`
```bash
cast code $ADDRESS --rpc-url $RPC | wc -c
# 0x = dead. < 100 = suspicious. > 1000 = probably real.
```

### RULE #2: NEVER send --value to a SwapRouter
```
Uniswap V3 SwapRouter does NOT wrap ETH.
WETH.deposit() → approve → swap as WETH. No --value.
```

### RULE #3: ALWAYS check gasUsed, not status
```
status: 1 + gasUsed < 50k = NO-OP (ETH LOST)
status: 1 + gasUsed > 80k = REAL SWAP
```

### RULE #4: ALWAYS test with 0.0001 ETH first
```
Cost of test: ~$0.001
Cost of mistake: ~$19+
Ratio: 19,000:1
```

### RULE #5: Same address ≠ same behavior across chains
```
0xE592427A... = REAL SwapRouter di Ethereum, Arbitrum, Optimism, Polygon
0xE592427A... = STUB di Base (34k gas, no swap, ETH LOST)

ALWAYS verify per-chain.
```

### RULE #6: Verify callback before direct pool swap
```
Different DEX = different callback name.
Wrong callback = silent revert = gas wasted.
```

### RULE #7: Track wallet balance before/after EVERY tx
```bash
cast nonce $WALLET --rpc-url $RPC  # before
cast send ...
cast nonce $WALLET --rpc-url $RPC  # after (should +1)
cast balance $WALLET --rpc-url $RPC  # track ETH erosion
```

### RULE #8: Fee tier arb is a DEAD END on L2
```
Spread between fee tiers: 0.02-0.4%
Combined fees: 0.40%+
Result: ALWAYS LOSS for deep pairs (WETH/USDC)
Only viable: cross-DEX altcoin pairs with real spread
```

---

## 9. ARB STRATEGY DECISION TREE

```
START: Mau arb?
│
├─ Chain apa?
│  ├─ Base → gas cheap, tapi spread tipis
│  │  └─ Only viable: cross-DEX altcoin (cbETH/WETH 1-4%)
│  │     └─ Cap: $147k liquidity → max $500-1000 per trade
│  │
│  ├─ Arbitrum → deeper liquidity, more DEXs
│  │  └─ GMX ↔ Uni V3, Camelot ↔ Uni V3
│  │
│  ├─ Ethereum → gas mahal, butuh $50k+
│  │  └─ MEV possible (Flashbots, private mempool)
│  │
│  └─ BSC → PancakeSwap dominant, less arb opportunity
│
├─ Tipe arb?
│  ├─ Same-chain cross-DEX → paling feasible
│  ├─ Triangular → jarang profit, butuh speed
│  ├─ Cross-chain → butuh modal besar, non-atomic
│  └─ MEV → butuh infra (Flashbots, private relay)
│
├─ Flash loan atau modal sendiri?
│  ├─ Flash loan → zero risk, tapi premium 0.05%
│  └─ Modal sendiri → no premium, tapi risk loss
│
└─ VERIFIED semua sebelum execute?
   ├─ Router: cast code ✅
   ├─ Pool: factory.getPool() ✅
   ├─ Liquidity: pool.liquidity() > 0 ✅
   ├─ Callback: bytecode grep ✅
   ├─ Test tiny: 0.0001 ETH ✅
   └─ Gas check: receipt gasUsed > 80k ✅
```

---

## 10. KENYATAAN PAHIT

```
Arb di L2 (Base, Arb, OP) untuk retail:
  - Spread < 0.5% untuk pair liquid
  - Setelah fees: profit $0-2 per trade
  - Setelah gas erosion dari testing: NET LOSS
  - Bot competition: pro bots execute dalam 1 block
  - Window: < 2 detik (Base block time)

Arb yang PROFITABLE:
  - Cross-DEX altcoin dengan spread > 1% (rare, thin liq)
  - Cross-chain saat volatility tinggi (bridge risk)
  - MEV di Ethereum (butuh infra $10k+/bulan)
  - Long-tail tokens di DEX kecil (rug risk)

Bug bounty > Arb untuk kita:
  - Basin bounty: potential $10-25k
  - Zero capital risk
  - Gue actually bagus di ini
  - Lo nggak rugi gas
```

---

*Ditulis oleh BOZAGENTIC · Dari $27 loss dan 14 pitfalls*
*"Learn the theory. Verify everything. Test tiny. Or just do bug bounty."*
