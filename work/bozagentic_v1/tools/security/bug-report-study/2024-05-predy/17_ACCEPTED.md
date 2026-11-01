# #17: signature replay to steal traders' fund via permit2
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', 'edited-by-warden', ':robot:_primary']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/a9246db5f874a91fb71c296aac6a66902289306a/src/markets/perp/PerpMarketV1.sol#L327-L338


# Vulnerability details

## Impact
Hackers can make use of trader' signed signature to transfer traders' tokens to hack themselves.

## Proof of Concept
Predy protocol makes use of permit2 to support gas-free trading. Traders will hash their order and sign one signature to the filler. The filler role will trigger the trade and transfer traders' token via permit2 with the correct signatures.

Considering that fillers get traders' signature off-chain, and predy protocol will be deployed on Layer2 chain, hackers cannot receive the correct and unused signature information on-chain before the signature is used.

However, there are some scenarios that hackers can get one correct and unused signature.
1. When the filler triggers the trade, and the trade transaction is reverted because of some unexpected condition, for example, current price doesn't match the limited price and so on.
2. Predy protocol will be deployed in several Layer2 chains. Hackers can make cross-chain signature replay. For example, hackers can find one valid signature in Arb chain and try to use it on Op chain.

In permit2, function `permitWitnessTransferFrom` does not limit the transfer's destination. Because the `to` address does not belong to one part of hash. Once hackers get one valid and unused and not-expired signature, hackers can transfer tokens directly via `permitWitnessTransferFrom`.
```javascript
    struct SignatureTransferDetails {
        // recipient address
        address to;
        // spender requested amount
        uint256 requestedAmount;
    }
    function permitWitnessTransferFrom(
        PermitTransferFrom memory permit,
        SignatureTransferDetails calldata transferDetails,
        address owner,
        bytes32 witness,
        string calldata witnessTypeString,
        bytes calldata signature
    ) external {
        _permitTransferFrom(
            permit, transferDetails, owner, permit.hashWithWitness(witness, witnessTypeString), signature
        );
    }
```

## Tools Used
Manual

## Recommended Mitigation Steps
Consider to use permit2's permit()/transferFrom() function. 



## Assessed type

Error