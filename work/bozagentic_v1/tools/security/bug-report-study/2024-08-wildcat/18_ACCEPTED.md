# #18: Incorrect use of `state.isDelinquent` in `updateTimeDelinquentAndGetPenaltyTime` function - total misbehavior of applying delinquency fee
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_17_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-08-wildcat/blob/main/src/libraries/FeeMath.sol#L96
https://github.com/code-423n4/2024-08-wildcat/blob/main/src/market/WildcatMarketBase.sol#L406


# Vulnerability details

## Impact
Due to the incorrect value of `state.isDelinquent`, the `updateTimeDelinquentAndGetPenaltyTime` function malfunctions, causing significant disruptions in fee accumulation.

## Proof of Concept
Over time, as market operations occur, borrowers accumulate fees. This process is managed by the `FeeMath.updateScaleFactorAndFees` function. While this function updates the scaleFactor and applies the protocolFee, it also implements the delinquency fee based on the market's delinquency status. The calculation is performed by the `updateDelinquency` function, which then utilizes the `updateTimeDelinquentAndGetPenaltyTime` function to determine the duration for which the `delinquencyFeeBips` should be applied.

This function has a critical flaw by using incorrect `state.isDelinquent` value. It's assumed that:
1. `state.isDelinquent` is up-to-update
2. The delinqency state of market has been consistent (state.isDelinquent) since last update until current timestamp.

```solidity
  function updateTimeDelinquentAndGetPenaltyTime(
    MarketState memory state,
    uint256 delinquencyGracePeriod,
    uint256 timeDelta
  ) internal pure returns (uint256 /* timeWithPenalty */) {
    // Seconds in delinquency at last update
    uint256 previousTimeDelinquent = state.timeDelinquent;

>>   if (state.isDelinquent) {

    ...
  }
```

However, this is WRONG because
- `state.isDelinquent` is the delinquency status of last updated time (indicated by `state.lastInterestAccruedTimestamp`)
- It is only updated when calling `_writeState` function which is normally at the end of an action.

So the whole deliquent penalty time is calculated wrongly, which leads to incorrect accumulation of delinquency fee.

## Tools Used
Manual Review

## Recommended Mitigation Steps
Though we can't completely guarantee 2nd point (`The delinqency state of market has been consistent`) because delinquency state can be changed in-between by direct transfer-in of assets (either by borrower or whoever), we can mostly assume it's true for a specific duration between market operations.

We can have correct value of `state.isDelinquent`, so that `updateTimeDelinquentAndGetPenaltyTime` function could perform correctly. It can be done by making changes to `_getUpdatedState` function of `WildcatMarketBase` contract.

```diff
  function _getUpdatedState() internal returns (MarketState memory state) {
    state = _state;
+   bool isDelinquent = state.liquidityRequired() > totalAssets();
+   state.isDelinquent = isDelinquent;
    ...
  }
```


## Assessed type

Error