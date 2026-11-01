# #82: `PositionAction4626.sol#_onDecreaseLever` should withdraw from `leverParams.position` CDPVault position instead of `address(this)`.
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', 'upgraded by judge', ':robot:_primary', ':robot:_38_group', 'duplicate-116']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/proxy/PositionAction4626.sol#L62


# Vulnerability details


## Impact

`PositionAction4626.sol#_onDecreaseLever` should withdraw from `leverParams.position` CDPVault position instead of `address(this)`.

## Bug Description

In `PositionAction4626`, the `_onDecreaseLever` should withdraw the token from `leverParams.position` CDPVault position. However, currently it withdraws from `address(this)`.

This does not work, because `_onDecreaseLever` is called in the `PositionAction` contract (which is called by flashlender callback `onCreditFlashLoan()`). This means the `address(this)` here means the `PositionAction` contract, which does not make sense at all, because it should be a stateless contract used for processing flashloans.

Also, in contrast, we can check the `PositionAction20` contract, it withdraws from the `leverParams.position` address.

PositionAction4626.sol
```solidity
    function _onDecreaseLever(
        LeverParams memory leverParams,
        uint256 subCollateral
    ) internal override returns (uint256 tokenOut) {
        // withdraw collateral from vault
>       uint256 withdrawnCollateral = ICDPVault(leverParams.vault).withdraw(address(this), subCollateral);

        // withdraw collateral from the ERC4626 vault and return underlying assets
        tokenOut = IERC4626(leverParams.collateralToken).redeem(withdrawnCollateral, address(this), address(this));

        if (leverParams.auxAction.args.length != 0) {
            bytes memory exitData = _delegateCall(
                address(poolAction),
                abi.encodeWithSelector(poolAction.exit.selector, leverParams.auxAction)
            );

            tokenOut = abi.decode(exitData, (uint256));
        }
    }
```

PositionAction20.sol
```solidity
    function _onDecreaseLever(
        LeverParams memory leverParams,
        uint256 subCollateral
    ) internal override returns (uint256) {
>       return _onWithdraw(leverParams.vault, leverParams.position, address(0), subCollateral);
    }
```

PositionAction.sol
```solidity
struct LeverParams {
    // position to lever
>   address position;
    // the vault to lever
    address vault;
    // the vault's token
    address collateralToken;
    // the swap parameters to swap collateral to underlying token or vice versa
    SwapParams primarySwap;
    // optional swap parameters to swap an arbitrary token to the collateral token or vice versa
    SwapParams auxSwap;
    // optional action parameters
    PoolActionParams auxAction;
}
```

## Proof of Concept

N/A

## Tools Used

Manual Review

## Recommended Mitigation Steps

```diff
-       uint256 withdrawnCollateral = ICDPVault(leverParams.vault).withdraw(address(this), subCollateral);
+       uint256 withdrawnCollateral = ICDPVault(leverParams.vault).withdraw(leverParams.position, subCollateral);
```


## Assessed type

Other