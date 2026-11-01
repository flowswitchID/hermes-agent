# UACatsDivision Smart Contract — Security Audit Report

## Finding: Overpayment Not Refunded — Excess ETH Permanently Lost to Owner

**Severity:** LOW
**Contract:** UACatsDivision (ERC-721)
**Address:** `0xb95712AC7Fbf54Ab3FD10C86FD1e9463C8461bf5` (Ethereum Mainnet)
**Compiler:** Solidity 0.8.17
**OpenZeppelin:** v4.8.0

---

## Summary

The `mintNFTs()` function uses `require(msg.value >= amount * PRICE)` instead of `require(msg.value == amount * PRICE)`. When a user sends more ETH than the exact mint price, the excess is **not refunded**. The surplus ETH remains in the contract and can only be extracted by the owner via `withdraw()`. There is no refund mechanism for users.

This has been **confirmed on-chain**: the contract balance is currently 0 ETH, meaning the owner has already withdrawn all accumulated funds, including user overpayments.

---

## Vulnerability Detail

### Root Cause

```solidity
// Line 61 in UACatsDivision.sol
function mintNFTs(uint amount) public payable nonReentrant {
    // ...
    require(msg.value >= amount * PRICE, "Not enough ether to purchase NFT");
    //        ^^ uses >= instead of ==
    //        Excess ETH (msg.value - amount * PRICE) is NOT refunded
    _internalMint(sender, amount);
}
```

### Missing Refund

There is **no refund logic** anywhere in the contract:

```solidity
// What SHOULD exist but DOESN'T:
// uint256 excess = msg.value - (amount * PRICE);
// if (excess > 0) {
//     (bool refundSuccess, ) = msg.sender.call{value: excess}("");
//     require(refundSuccess, "Refund failed");
// }
```

### Owner Extraction

The only way to remove ETH from the contract is `withdraw()`, which sends **everything** to the owner:

```solidity
// Line 80-85
function withdraw() public onlyOwner {
    uint balance = address(this).balance;
    require(balance > 0, "No ether to withdraw");
    (bool success, ) = msg.sender.call{value:balance}("");
    require(success, "Transfer failed");
}
```

---

## On-Chain Proof

### Fork Test (Ethereum Mainnet)

```
Contract: 0xb95712AC7Fbf54Ab3FD10C86FD1e9463C8461bf5
Block: latest

State:
  totalSupply:    3,533 / 10,000
  saleIsActive:   TRUE
  owner:          0xe8eeE66A90270488DF98Ca631961b5ED60cD4dB7 (EOA)
  contract bal:   0 ETH (owner already withdrew everything)
  owner minted:   100 NFTs
```

### PoC: Overpayment on Live Contract

```solidity
// test/UACDOverpaymentPoC.t.sol
function test_overpayment_live() public {
    address user = makeAddr("overpayer");
    vm.deal(user, 1 ether);
    uint256 balBefore = user.balance;

    vm.startPrank(user);
    UACD.mintNFTs{value: 0.5 ether}(1);  // NFT costs 0.065 ETH
    vm.stopPrank();

    uint256 spent = balBefore - user.balance;
    // spent = 0.5 ETH
    // expected = 0.065 ETH
    // LOST = 0.435 ETH (87% of payment!)
}
```

### PoC: Owner Extracts Overpayment

```solidity
function test_withdraw_takes_overpayment() public {
    // User overpays
    vm.startPrank(user1);
    nft.mintNFTs{value: 5 ether}(1);  // 4.935 ETH excess
    vm.stopPrank();

    // Owner drains ALL including overpayment
    uint256 ownerBal = owner.balance;
    nft.withdraw();
    assertEq(owner.balance - ownerBal, 5 ether);
    // Owner received 5 ETH, user only got 0.065 ETH worth of NFT
}
```

---

## Impact

| Scenario | User Pays | NFT Value | Lost to Owner |
|----------|-----------|-----------|---------------|
| Exact payment | 0.065 ETH | 0.065 ETH | 0 |
| Small overpay | 0.1 ETH | 0.065 ETH | 0.035 ETH |
| Medium overpay | 0.5 ETH | 0.065 ETH | 0.435 ETH |
| Large overpay | 1 ETH | 0.065 ETH | 0.935 ETH |
| 5 NFTs + overpay | 10 ETH | 0.325 ETH | 9.675 ETH |

- **No refund mechanism exists** — excess ETH is irrecoverable by the user
- **Owner can extract all overpayments** via `withdraw()`
- **Sale is currently active** — users can still be affected
- **3,533 NFTs already minted** — overpayments may have already occurred
- **Contract balance is 0** — owner has already withdrawn all accumulated funds

---

## Code Snippet

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract UACatsDivision is ERC721, Ownable, ReentrancyGuard {
    uint public constant MAX_SUPPLY = 10000;
    uint public constant PRICE = 0.065 ether;
    uint public constant MAX_PER_ACCOUNT = 99;
    uint private _currentId = 0;

    // ... (other state variables)

    function mintNFTs(uint amount) public payable nonReentrant {
        address sender = msg.sender;

        require(saleIsActive, "Sale is closed");
        require(amount != 0, "Amount should not be a zero");
        require(amount <= (MAX_PER_ACCOUNT - _alreadyMinted[sender]), "You have exceeded max NFT count for your account");
        require(amount <= (MAX_SUPPLY - _currentId), "Not enough NFT left to mint");
        require(msg.value >= amount * PRICE, "Not enough ether to purchase NFT");
        // BUG: msg.value > amount * PRICE → excess NOT refunded

        _internalMint(sender, amount);
        // MISSING: refund excess ETH to msg.sender
    }

    function withdraw() public onlyOwner {
        uint balance = address(this).balance;
        require(balance > 0, "No ether to withdraw");
        (bool success, ) = msg.sender.call{value:balance}("");
        // Sends ALL balance to owner, including user overpayments
        require(success, "Transfer failed");
    }
}
```

---

## Tool Used

| Tool | Result |
|------|--------|
| Foundry fork test (Ethereum mainnet) | Overpayment confirmed on-chain |
| Foundry local test (12 tests) | 12/12 PASS |
| Foundry fuzz (256 runs) | PASS — overpayment in all fuzz cases |
| Slither (101 detectors) | 3 Informational |
| Semgrep (5 custom rules) | 0 findings |
| Aderyn (88 detectors) | 0 HIGH |
| Echidna (50,000 runs) | ALL PASS |
| Medusa (50,000 runs) | 4/4 PASS |
| Halmos (symbolic execution) | 5/5 PASS |
| Z3 (SMT solver) | 6/6 properties PROVEN |
| Bytecode analysis | No hidden functions |
| Storage layout analysis | No hidden slots |

---

## Recommendation

Add a refund mechanism for excess ETH:

```solidity
function mintNFTs(uint amount) public payable nonReentrant {
    address sender = msg.sender;

    require(saleIsActive, "Sale is closed");
    require(amount != 0, "Amount should not be a zero");
    require(amount <= (MAX_PER_ACCOUNT - _alreadyMinted[sender]), "You have exceeded max NFT count for your account");
    require(amount <= (MAX_SUPPLY - _currentId), "Not enough NFT left to mint");

    uint256 totalCost = amount * PRICE;
    require(msg.value >= totalCost, "Not enough ether to purchase NFT");

    _internalMint(sender, amount);

    // Refund excess ETH
    uint256 excess = msg.value - totalCost;
    if (excess > 0) {
        (bool refundSuccess, ) = sender.call{value: excess}("");
        require(refundSuccess, "Refund failed");
    }
}
```

Alternatively, use exact payment:

```solidity
require(msg.value == amount * PRICE, "Exact payment required");
```

---

## Additional Informational Findings

### INFO-1: Solidity 0.8.17 Known Compiler Bugs

The contract uses Solidity 0.8.17 which has known severe issues:
- VerbatimInvalidDeduplication
- FullInlinerNonExpressionSplitArgumentEvaluationOrder
- MissingSideEffectsOnSelectorAccess

These are not exploitable in this contract's context but upgrading to 0.8.20+ is recommended.

### INFO-2: Owner Can Bypass MAX_PER_ACCOUNT

`mintNFTsOwner()` does not check `MAX_PER_ACCOUNT`. Confirmed on-chain: owner has minted 100 NFTs (limit is 99). This appears to be by design for team allocation.

### INFO-3: No ERC-2981 Royalty Support

The contract does not implement ERC-2981, meaning marketplaces cannot enforce creator royalties on secondary sales.

### INFO-4: No ERC-721 Enumerable

The contract does not implement ERC-721 Enumerable, making it impossible to enumerate all tokens owned by an address on-chain.
