# COINBASE ONSHAIN ECOSYSTEM — Complete Audit Reference
# BOZAGENTIC | All contracts, interactions, findings
# Last updated: 2026-08-01

---

## TIER 0 (max $5M)

### Base L2
- L2 and L1 mainnet addresses (OP Stack)
- Not directly audited in this session

### cbBTC (0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf)
- FiatTokenProxy (Circle proxy pattern)
- Implementation: FiatTokenV2_1
- Multi-chain: Base, Ethereum, Solana, Arbitrum

### cbETH
- StakedTokenV1 (Lido-style)
- Ethereum mainnet only

## TIER 1 (max $500K)

### Smart Wallet Stack
- CoinbaseSmartWallet (ERC-4337) + MultiOwnable + ERC1271 + Factory
- Tests: 80/80 PASS, Halmos 2/3, Mythril 0 issues
- Verdict: SAFE

### SpendPermissionManager
- Periodic allowance, CEI verified, EIP-712 with chainId
- Echidna 50K PASS
- Verdict: SAFE

### Commerce Payments
- AuthCaptureEscrow + TokenStore + 5 Collectors
- Z3: 4 fee proofs PROVEN
- Verdict: SAFE

### Flywheel Protocol
- Flywheel + Campaign + CashbackRewards + AdConversion + BridgeReferralFees
- BUG FOUND: CashbackRewards maxRewardBps bypass (MEDIUM)
- Confirmed by: Z3 SAT, Echidna FAIL, Semgrep DETECTED
- Status: SUBMITTED to Cantina

### BuilderCodes
- ERC721 NFT registry, toTokenId injective (10K fuzz + Z3)
- 142/142 tests, Echidna 100K, Medusa 100K
- Verdict: SAFE

### ExtendedOptimismMintableToken, LinearUnlocker, MultiChainWithdrawer
### ERC20FundingConduit, RecoverySigner
- All SAFE

---

## FINDINGS

### CashbackRewards maxRewardBps Bypass (MEDIUM)
- File: src/hooks/CashbackRewards.sol, line 325
- Bug: SEND/DISTRIBUTE ignore allocated in cap check
- Attack: allocate(cap) + send(cap) = 2x cap
- Confirmed by: Z3 SAT, Echidna FAIL, Semgrep DETECTED
- Status: SUBMITTED

### Solady Guard Slot Collision (INFO)
- Theoretical only, requires keccak256 preimage
- NOT submitted

### SpendPermission uint32 Period Overflow (INFO)
- Requires year 2106+ with 1s period
- NOT submitted

---

## CROSS-PROTOCOL: 15 pairs analyzed, 1 bug, 14 safe

## TOOLS: Slither, Semgrep, Aderyn, Mythril, Foundry, Echidna, Medusa, Halmos, Z3, Blockscout
