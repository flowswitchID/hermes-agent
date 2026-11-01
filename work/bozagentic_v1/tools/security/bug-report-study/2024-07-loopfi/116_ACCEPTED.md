# #116: `decreaseLever` uses incorrect position address when withdrawing
Labels: ['bug', '3 (High Risk)', 'primary issue', 'satisfactory', 'selected for report', 'sponsor confirmed', 'sufficient quality report', 'upgraded by judge', ':robot:_01_group', 'H-09']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/proxy/PositionAction4626.sol#L61-L62


# Vulnerability details

## Impact
`decreaseLever` will always revert for Position4626 associated vaults

## Proof of Concept
When decreasing lever, the control is passed over to the actual implementation contract for the flashLoan execution

```solidity
    function decreaseLever(
        LeverParams calldata leverParams,
        uint256 subCollateral,
        address residualRecipient
    ) external onlyDelegatecall {
       
       ....

        // @audit execution passed to the implementation contract by setting it as the callback 
        // take out credit flash loan
        IPermission(leverParams.vault).modifyPermission(leverParams.position, self, true);
        uint loanAmount = leverParams.primarySwap.amount;
        flashlender.creditFlashLoan(
            ICreditFlashBorrower(self),
            loanAmount,
            abi.encode(leverParams, subCollateral, residualRecipient)
        );
        IPermission(leverParams.vault).modifyPermission(leverParams.position, self, false);       
```

Inside the `onCreditFlashLoan` call it attempts to withdraw the collateral of the passed in position by the passed in subCollateral amount
```solidity
    function onCreditFlashLoan(
        address /*initiator*/,
        uint256 /*amount*/,
        uint256 /*fee*/,
        bytes calldata data
    ) external returns (bytes32) {
        

        // sub collateral and debt
        ICDPVault(leverParams.vault).modifyCollateralAndDebt(
            leverParams.position,
            address(this),
            address(this),
            0,
            -toInt256(subDebt)
        );

        // withdraw collateral and handle any CDP specific actions
        // @audit should withdraw `subCollateral` amount from `leverParams.position`
=>      uint256 withdrawnCollateral = _onDecreaseLever(leverParams, subCollateral);
```

But the `_onDecreaseLever` function of the Position4626 contract is flawed as it attempts to withdraw the collateral from its own address intead of the passed in `position`
```solidity
    function _onDecreaseLever(
        LeverParams memory leverParams,
        uint256 subCollateral
    ) internal override returns (uint256 tokenOut) {
        // @audit attempts to withdraw from address(this) rather than leverParams.position
=>      uint256 withdrawnCollateral = ICDPVault(leverParams.vault).withdraw(address(this), subCollateral);
```

Since the collateral is actually present in the passed in position, this attempt to withdraw will  cause the call to revert

## Tools Used
Manual review

## Recommended Mitigation Steps
Inside `_onDecreaseLever`, withdraw from `leverParams.position` instead


## Assessed type

Other