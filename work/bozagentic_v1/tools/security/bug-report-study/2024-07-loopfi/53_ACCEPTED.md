# #53: `PoolV3.sol` withdraw fees are sent to `StakingLPEth.sol` contract as WETH, which is not accessible.
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_156_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/reward/EligibilityDataProvider.sol#L187-L191


# Vulnerability details


## Impact

`PoolV3.sol` withdraw fees are sent to `StakingLPEth.sol` contract as WETH, which is not accessible. This would be equivalent to loss of funds because the fees would be completely trapped.

## Bug Description

First let's see how `PoolV3.sol` works in LoopFi. Users can deposit WETH as assets and receive lpETH as shares. However, holding these lpETH does not accumulate any interest. Users must stake their lpETH in the `StakingLPEth.sol` contract, and receive the interest as lpETH, and the base interest and quota interest are minted as lpETH to the `StakingLPEth.sol` contract. Users can then use the lpETH they earned, and come back to `PoolV3.sol` to redeem their WETH.

The `treasury` address of `PoolV3.sol` is set to `StakingLPEth.sol` contract.

The issue here is, there is a withdrawl fee in `PoolV3.sol`, it takes a small portion of the user tokens when they withdraw their WETH from `PoolV3.sol`. The fees is then sent to the `treasury` (which is the `StakingLPEth.sol`) as WETH token. However, in `StakingLPEth.sol`, the asset is lpETH, so no one can receive these fees. Also, since there isn't a rescue function in `StakingLPEth.sol`, these fees are stuck their forever.

Note that this code is forked from GearboxV3, but since GearboxV3's treasury is a multisig wallet, this wouldn't be an issue.

```solidity
    function withdraw(
        uint256 assets,
        address receiver,
        address owner
    )
        public
        override(ERC4626, IERC4626)
        whenNotPaused // U:[LP-2A]
        whenNotLocked
        nonReentrant // U:[LP-2B]
        nonZeroAddress(receiver) // U:[LP-5]
        returns (uint256 shares)
    {
        uint256 assetsToUser = _amountWithFee(assets);
>       uint256 assetsSent = _amountWithWithdrawalFee(assetsToUser); // U:[LP-8]
        shares = _convertToShares(assetsSent); // U:[LP-8]
>       _withdraw(receiver, owner, assetsSent, assets, assetsToUser, shares); // U:[LP-8]
    }

    function _withdraw(
        address receiver,
        address owner,
        uint256 assetsSent,
        uint256 assetsReceived,
        uint256 amountToUser,
        uint256 shares
    ) internal {
        ...
        IERC20(underlyingToken).safeTransfer({to: receiver, value: amountToUser}); // U:[LP-8,9]
        if (assetsSent > amountToUser) {
            unchecked {
>               IERC20(underlyingToken).safeTransfer({to: treasury, value: assetsSent - amountToUser}); // U:[LP-8,9]
            }
        }
    }
```

## Proof of Concept

N/A

## Tools Used

Manual Review

## Recommended Mitigation Steps

Send the withdrawl fees to `treasury` by minting shares (lpETH) instead of transferring underlying token (WETH) directly.


## Assessed type

Other