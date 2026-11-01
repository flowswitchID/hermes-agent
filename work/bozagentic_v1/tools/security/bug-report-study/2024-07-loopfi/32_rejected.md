# #32: Wrong redeem accounting in `AuraVault.sol`
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', 'edited-by-warden', ':robot:_primary', ':robot:_03_group', 'duplicate-170']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/vendor/AuraVault.sol#L266


# Vulnerability details

## Impact
Users will never recieve the real value of their shares, which could even result in protocol insolvency or theft- High
## Proof of Concept
The Aura reward pool has the following rate: 1 asset = 1 share:
https://github.com/aurafinance/convex-platform/blob/e7c23cfeec5ef9beb4873d87069363ee458fc184/contracts/contracts/BaseRewardPool4626.sol#L129
However the AuraVault will have a different rate:
https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/vendor/AuraVault.sol#L190
So we can safely say that both rates are different. When a user deposits into the AuraVault, they are minted shares based on the AuraVault.sol rate. However when they call redeem the rate at which the shares will be redeemed is 1:1(rewardPool rate) as the following line will calculate the assets that will be sent to the user which will be equal to the shares:
https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/vendor/AuraVault.sol#L264
As a result the _withdraw function will transfer the wring value of assets:
https://github.com/OpenZeppelin/openzeppelin-contracts/blob/24a641d9c9e0137093592a466c5496315626d98d/contracts/token/ERC20/extensions/ERC4626.sol#L274

## Tools Used
Manual Review
## Recommended Mitigation Steps
The assets to transfer should be calculated using the `AuraVault.sol`:
https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/vendor/AuraVault.sol#L190

To use the correct rate rewrite the function:
```solidity
function redeem(uint256 shares, address receiver, address owner)
        public
        virtual
        override(IERC4626, ERC4626)
        returns (uint256)
    {
        require(shares <= maxRedeem(owner), "ERC4626: redeem more than max"); //should have enough shares
        uint256 assets = previewRedeem(shares, address(this), address(this));
        // Redeem assets from Aura reward pool and send to "receiver"
        IPool(rewardPool).redeem(assets, address(this), address(this)); //redeem from the pool

        _withdraw(_msgSender(), receiver, owner, assets, shares); //withdraw from the vault

        return assets; //return the assets
    }
```



## Assessed type

Other