# #19: Wrong calculation of delinquent penalty time in `updateTimeDelinquentAndGetPenaltyTime` function
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_17_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-08-wildcat/blob/main/src/libraries/FeeMath.sol#L118


# Vulnerability details

## Impact
Because of the incorrect calculation of delinquent penalty time, a borrower gets charged much lower delinquency fee than intended.

## Proof of Concept
Over time, as market operations occur, borrowers accumulate fees. This process is managed by the `FeeMath.updateScaleFactorAndFees` function. While this function updates the scaleFactor and applies the protocolFee, it also implements the delinquency fee based on the market's delinquency status. The calculation is performed by the `updateDelinquency` function, which then utilizes the `updateTimeDelinquentAndGetPenaltyTime` function to determine the duration for which the `delinquencyFeeBips` should be applied.

When `state.isDelinquent` is false, indicating that the current market is healthy, the return value is calculated as follows:

```solidity
  function updateTimeDelinquentAndGetPenaltyTime(
    MarketState memory state,
    uint256 delinquencyGracePeriod,
    uint256 timeDelta
  ) internal pure returns (uint256 /* timeWithPenalty */) {
    // Seconds in delinquency at last update
    uint256 previousTimeDelinquent = state.timeDelinquent;

    if (state.isDelinquent) {
        ...
    }

    state.timeDelinquent = previousTimeDelinquent.satSub(timeDelta).toUint32();

    // Calculate the number of seconds the old timeDelinquent had remaining
    // outside the grace period, or zero if it was already in the grace period.
>>  uint256 secondsRemainingWithPenalty = previousTimeDelinquent.satSub(delinquencyGracePeriod);

    // Only apply penalties for the remaining time outside of the grace period.
    return MathUtils.min(secondsRemainingWithPenalty, timeDelta);
  }
```

In here, `secondsRemainingWithPenalty` is wrong because delinquent state remains active until `previousTimeDelinquent` drops down to zero.
It's also mentioned in wildcat doc: https://docs.wildcat.finance/using-wildcat/delinquency#how-delinquency-triggers
```
The penalty APR associated with a market activates once the grace tracker exceeds the grace period, and remains active until it drops below the same
```

Here's an example:

IF `previousTimeDelinquent = 3 days` and `delinquencyGracePeriod = 5 days`, then it should be: `secondsRemainingWithPenalty = 3 days`, but above code generates `0`.


#### (IMPORTANT NOTE: The `updateTimeDelinquentAndGetPenaltyTime` function has another critical flaw; it assumes that `state.isDelinquent` is up-to-date and has remained unchanged from the last update to the present. This assumption is incorrect and will be addressed as a separate issue submission.)

## Tools Used
Manual Review

## Recommended Mitigation Steps
Update the calculation as follows:
```diff
-    uint256 secondsRemainingWithPenalty = previousTimeDelinquent.satSub(delinquencyGracePeriod);
+    uint256 secondsRemainingWithPenalty = MathUtils.min(previousTimeDelinquent, delinquencyGracePeriod);
```


## Assessed type

Error