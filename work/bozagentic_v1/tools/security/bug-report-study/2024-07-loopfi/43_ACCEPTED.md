# #43: CDPVault missing mechanism for handling $PENDLE incentive from PendleLP could lead to reward getting stuck in CDPVault forever
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor acknowledged', 'sufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_80_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L1-L762


# Vulnerability details

## Impact
**$PENDLE** incentive from **PendleLP** might get stuck in **CDPVault** forever.  
## Proof-of-Concept  
Per contest scope, **LoopFi** also intends to use **PendleLP** token as a collateral in **CDPVault**  
**PendleLP** holders are eligible for an incentive/reward in **$PENDLE** token. Reward claiming is triggerred by **PendleLP** token transfer or directly calling `redeemRewards` function on the contract (The function is permissionless, allowing anyone to claim rewards on behalf of other users).    

See: [PendleMarketV3.redeemRewards](https://github.com/pendle-finance/pendle-core-v2-public/blob/main/contracts/core/Market/v3/PendleMarketV3.sol#L235-L237)

The problem arises when users deposit **PendleLP** as collateral because then **CDPVault** contract becomes holder and is eligible for incentive and start accruing rewards. The reward is claimed and transferred to **CDPVault** every time there is a transfer of **PendleLP** (deposit, withdraw, liquidation).    

However, **CDPVault** contract lacks the mechanism to distribute or transfer **$PENDLE** incentive out of **CDPVault**, thus the reward might get stuck forever.  

## Rationale for Severity
Since **CDPVault** might not be upgradeable, the rewards might get stuck with no way for recovery. Hence, **High** severity from direct assets lost.  

## Recommended Mitigations  
Add this function in **CDPVault** to recover stuck token, in this case **$PENDLE**
```solidity
function recoverERC20(address tokenAddress, address to, uint256 tokenAmount) external onlyRole(DEFAULT_ADMIN_ROLE) {
    if( tokenAddress == address(token) ) revert Cannot_recover_collateral();
    IERC20(tokenAddress).safeTransfer(to, tokenAmount);
}
```


## Assessed type

Other