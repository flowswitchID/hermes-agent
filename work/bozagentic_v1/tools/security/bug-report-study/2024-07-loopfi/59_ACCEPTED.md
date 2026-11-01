# #59: BalancerOracle calculates BPT price incorrectly
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_06_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/oracle/BalancerOracle.sol#L114


# Vulnerability details


## Impact

BalancerOracle calculates BPT price incorrectly.

## Bug Description

First let's see how the BPT price is calculated: https://docs.balancer.fi/concepts/advanced/valuing-bpt/valuing-bpt.html#informational-price-evaluation.

The formula is mainly correct, however, the issue is when handling WAD decimals, there is an issue.

- wdiv(A, B) is A * WAD / B.
- wmul(A, B) is A * B / WAD.
- wpow(A, B) is `A**B` but A, B, and result are all in WAD. Example: `wpow(4e18, 4e18) == 256e18`.

Now, the issue is when calculating `totalPi`, it uses wmul for each token. This means if there are 3 tokens, then WAD is divided 3 times. However, since the total sum of weights[i] is 1e18, this means only one WAD is multiplied in total for `val` and `indivPi`.

This means only 1 WAD is multiplied, but 3 WAD is divided. This is obviously incorrect.

```solidity
    function update() external virtual onlyRole(KEEPER_ROLE) returns (uint256 safePrice_) {
        if (block.timestamp - lastUpdate < updateWaitWindow) revert BalancerOracle__update_InUpdateWaitWindow();
        // update the safe price first
        safePrice = safePrice_ = currentPrice;
        lastUpdate = block.timestamp;

        uint256[] memory weights = IWeightedPool(pool).getNormalizedWeights();
        uint256 totalSupply = IWeightedPool(pool).totalSupply();

        uint256 totalPi = WAD;
        uint256[] memory prices = new uint256[](weights.length);
        // update balances in 18 decimals
        for (uint256 i = 0; i < weights.length; i++) {
            // reverts if the price is invalid or stale
            prices[i] = _getTokenPrice(i);
>           uint256 val = wdiv(prices[i], weights[i]);
            uint256 indivPi = uint256(wpow(int256(val), int256(weights[i])));

>           totalPi = wmul(totalPi, indivPi);
        }

        currentPrice = wdiv(wmul(totalPi, IWeightedPool(pool).getInvariant()), totalSupply);
    }
```

## Proof of Concept

Presented above.

## Tools Used

Manual Review

## Recommended Mitigation Steps

Don't use `wmul` for `totalPi = wmul(totalPi, indivPi)`. Use normal multiplication instead, and divide WAD once in the end.


## Assessed type

Math