# #41: PositionAction4626._onDecreaseLever withdraws collateral from wrong position
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', 'upgraded by judge', 'edited-by-warden', ':robot:_primary', ':robot:_01_group', 'duplicate-116']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/proxy/PositionAction4626.sol#L136-L154


# Vulnerability details

## Impact
- `PositionAction4626.decreaseLever` will always revert as there is no collateral to withdraw from the wrong position.  
## Proof-of-Concept
Users can utilize `PositionAction4626.decreaseLever` to decrease or close their leveraged position using credit flashloan from **Flashlender** contract.  
**PositionAction4626(proxy)** validates input parameters and calls `creditFlashLoan` function on **Flashlender**  

**Flashlender** makes a callback to the **PositionAction4626(self)** `onCreditFlashLoan` function to perform key operations such as:
- Repaying debt with flashloan ETH
- Withdraw collateral from **CDPVault**  
- Swapping withdrawn collateral to ETH  
- Repaying the flashloan using ETH from swap  

However, in current implementation, `_onDecreaseLever` function incorrectly withdraws collateral from the **PositionAction4626**'s own position: `address(this)` instead of the user's position specified in `leverParams.position`. This is due to an incorrect assumption about execution context.  
In this execution flow, the context for `address(this)` while executing `_onDecreaseLever` is **PositionAction4626**'s address not **UserProxy** which is the actual position's owner.  

**Execution flow when users call `PositionAction4626.decreaseLever` on their proxy**  
```
UserProxy  
    --delegateCall--> (UserProxy) PositionAction4626.decreaseLever  
        --call--> Flashlender.creditFlashLoan  
            --call--> (Self) PositionAction4626.onCreditFlashLoan  
                --internalCall--> _onDecreaseLever   
                    --call--> CDPVault.withdraw
```

**_onDecreaseLever** implementation (See: [PositionAction4626.sol#L136-L154](https://github.com/code-423n4/2024-07-loopfi/blob/main/src/proxy/PositionAction4626.sol#L136-L154))
```solidity
function _onDecreaseLever(
    LeverParams memory leverParams,
    uint256 subCollateral
) internal override returns (uint256 tokenOut) {
    // withdraw collateral from vault
    uint256 withdrawnCollateral = ICDPVault(leverParams.vault).withdraw(address(this), subCollateral); <-- withdraw from wrong position address

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

Consequently, because `address(this)` in this context doesn't hold any collateral, the withdrawal will revert from insufficient funds.  

## Recommended Mitigations
It should withdraw from `leverParams.position` instead.  
### Suggested Fix
```
function _onDecreaseLever(
    LeverParams memory leverParams,
    uint256 subCollateral
) internal override returns (uint256 tokenOut) {
    // withdraw collateral from vault
    uint256 withdrawnCollateral = ICDPVault(leverParams.vault).withdraw(leverParams.position, subCollateral);

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





## Assessed type

Context