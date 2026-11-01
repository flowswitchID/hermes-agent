# #28: ChefIncentivesController::_handleActionAfterForToken doesn't update emissions
Labels: ['invalid', '3 (High Risk)', 'withdrawn by warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/reward/ChefIncentivesController.sol#L627-L637


# Vulnerability details

## Impact
Detailed description of the impact of this finding.

## Proof of Concept
```solidity
    function _handleActionAfterForToken(
        address _token,
        address _user,
        uint256 _balance,
        uint256 _totalSupply
    ) internal {
        VaultInfo storage pool = vaultInfo[_token];
        if (pool.lastRewardTime == 0) revert UnknownPool();
        // Although we would want the pools to be as up to date as possible when users
        // transfer rTokens or dTokens, updating all pools on every r-/d-Token interaction would be too gas intensive.
        // _updateEmissions();
```
The emmissions update is not performed during the function, which will lead to inaccurate data being used lead to loss (show and prove)

## Tools Used

## Recommended Mitigation Steps


## Assessed type

Error