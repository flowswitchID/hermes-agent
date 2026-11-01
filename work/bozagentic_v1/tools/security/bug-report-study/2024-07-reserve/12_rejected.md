# #12: Incorrect buying asset calculation in `nextTradePair`
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_13_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/p1/mixins/RecollateralizationLib.sol#L332-L353


# Vulnerability details

## Impact
Invalid assets(e.g. assets not in current basket) can be bought which will make collateralization worse.

## Proof of Concept
When the protocol becomes under-collateralized, trading events happen to sell over-collateralized tokens and to buy tokens with deficient supply.

The logic to choose what tokens to buy and sell are done via `nextTradePair` function:
```solidity
if (ctx.bals[i].gt(needed)) {
    // Choose token to sell
} else {
    // needed(Bottom): token balance needed at bottom of the basket range
    needed = range.bottom.mul(ctx.quantities[i], CEIL); // {buyTok};

    if (ctx.bals[i].lt(needed)) {
        uint192 amtShort = needed.minus(ctx.bals[i]); // {buyTok}
        (uint192 low, uint192 high) = reg.assets[i].price(); // {UoA/buyTok}

        // {UoA} = {buyTok} * {UoA/buyTok}
        uint192 delta = amtShort.mul(high, CEIL);

        // The best asset to buy is whichever asset has the largest deficit
        if (delta.gt(maxes.deficit)) {
            trade.buy = reg.assets[i];
            trade.buyAmount = amtShort;
            trade.prices.buyLow = low;
            trade.prices.buyHigh = high;

            maxes.deficit = delta;
        }
    }
}
```

If current balance is greater than needed collateral amount, it is considered to be chosen as token to sell. Otherwise, the asset is considered to be bought based on the deficiency.

However, when choosing token to buy, it does not check if the asset exists in current basket.
This exposes a vulnerability for invalid tokens to be bought using surplus, and this will make collateralization of protocol worse.

## Tools Used
Manual Review

## Recommended Mitigation Steps
When choosing a token to buy, it should only look in tokens in current basket.


## Assessed type

Context