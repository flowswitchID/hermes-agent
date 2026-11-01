# #48: Positions are not liquidatable when `collateral * spotPrice * liquidationDiscount >= debt > collateral * spotPrice`
Labels: ['bug', '3 (High Risk)', 'sufficient quality report', 'unsatisfactory', ':robot:_24_group', 'duplicate-60']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L501-L632


# Vulnerability details

## Impact
Positions are not liquidatable when `collateral * spotPrice * liquidationDiscount >= debt > collateral * spotPrice`

## Proof of Concept
```solidity
    function liquidatePosition(address owner, uint256 repayAmount) external whenNotPaused {
        // ...
        uint256 spotPrice_ = spotPrice();
        uint256 discountedPrice = wmul(spotPrice_, liqConfig_.liquidationDiscount);
        if (spotPrice_ == 0) revert CDPVault__liquidatePosition_invalidSpotPrice();
        if (calcTotalDebt(debtData) > wmul(position.collateral, spotPrice_)) revert CDPVault__BadDebt(); // <===== Audit
        // ...
    }

    function liquidatePositionBadDebt(address owner, uint256 repayAmount) external whenNotPaused {
        // ...
        uint256 discountedPrice = wmul(spotPrice_, liqConfig_.liquidationDiscount);
        // Enusure that the debt is greater than the collateral at discounted price
        if (calcTotalDebt(debtData) <= wmul(position.collateral, discountedPrice)) revert CDPVault__noBadDebt(); // <===== Audit
        // ...
    }
```

`CDPVault@liquidatePosition` checks for bad debt using the spot price while `CDPVault@liquidatePositionBadDebt` checks for bad debt using the discounted price.

### Test
```solidity
    function test_position_not_liquidatable() public {
        CDPVault vault = createCDPVault(token, 150 ether, 0, 1.25 ether, 1 ether, 1.05 ether);
        createGaugeAndSetGauge(address(vault));

        _modifyCollateralAndDebt(vault, 100 ether, 80 ether);

        address position = address(this);
        uint256 repayAmount = 80 ether;
        mockWETH.mint(address(this), repayAmount);
        _updateSpot(0.78 ether); // Can be any value between (0.8 ether * 1 ether / 1.05 ether) + 1 and 0.8 ether - 1
        mockWETH.approve(address(vault), repayAmount);

        vm.expectRevert(CDPVault.CDPVault__noBadDebt.selector);
        vault.liquidatePositionBadDebt(position, repayAmount);

        vm.expectRevert(CDPVault.CDPVault__BadDebt.selector);
        vault.liquidatePosition(position, repayAmount);
    }
```

## Tools Used
Manual Review

## Recommended Mitigation Steps
Check for bad debt using the spot price in `CDPVault@liquidatePositionBadDebt`.


## Assessed type

Other