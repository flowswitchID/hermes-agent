# UACatsDivision Smart Contract — Audit Submission

## Finding: Overpayment Not Refunded (LOW)

**Contract:** `0xb95712AC7Fbf54Ab3FD10C86FD1e9463C8461bf5` (Ethereum)
**Platform:** HackenProof — UACatsDivision Smart Contracts

## How to Run PoC

```bash
# Clone and setup
forge init --no-git uacd-poc && cd uacd-poc
forge install OpenZeppelin/openzeppelin-contracts@v4.8.0 --no-git

# Copy source + tests
cp source/UACatsDivision.sol src/
cp poc/*.sol test/

# Add remappings
echo "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/" > remappings.txt

# Run local tests (12/12 PASS)
forge test --match-contract UACDLocal -vvv

# Run fork tests (requires ETH RPC)
ETH_RPC_URL="https://ethereum-rpc.publicnode.com" forge test --match-contract UACDDeep -vvv

# Run all deep tests
forge test -vvv
```

## Folder Structure

```
report/          — Full audit report (paste into HackenProof)
poc/             — All test files (57+ tests)
source/          — Contract source code (from Blockscout)
tools-output/    — Slither + Aderyn results
```

## Tools Used

| Tool | Runs | Result |
|------|------|--------|
| Foundry fork test | 11 tests | 11/11 PASS |
| Foundry local test | 12 tests | 12/12 PASS |
| Foundry deep attacks | 10 tests | 9/10 PASS |
| Foundry deep economic | 10 tests | 10/10 PASS |
| Foundry deep storage | 7 tests | 7/7 PASS |
| Foundry deep bytecode | 3 tests | 3/3 PASS |
| Foundry fuzz | 256 runs | PASS |
| Slither | 101 detectors | 3 INFO |
| Semgrep | 5 rules | 0 findings |
| Aderyn | 88 detectors | 0 HIGH |
| Echidna | 50,000 runs | ALL PASS |
| Medusa | 50,000 runs | 4/4 PASS |
| Halmos | symbolic | 5/5 PASS |
| Z3 | SMT solver | 6/6 PROVEN |

## Severity Assessment

- **LOW**: Overpayment not refunded (on-chain confirmed)
- **INFO**: solc 0.8.17, owner bypass, no royalties, no enumerable
- **NO HIGH/CRITICAL**: Contract is 86 lines, standard OZ ERC721
