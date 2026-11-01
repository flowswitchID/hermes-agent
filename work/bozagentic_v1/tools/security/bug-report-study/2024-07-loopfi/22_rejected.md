# #22: CDPVault::liquidatePosition compared two different prices, USD vs token
Labels: ['invalid', '3 (High Risk)', 'withdrawn by warden', ':robot:_primary']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L526


# Vulnerability details

## Impact
Detailed description of the impact of this finding.

## Proof of Concept
```solidity
    function liquidatePosition(address owner, uint256 repayAmount) external whenNotPaused {
        // validate params
        if (owner == address(0) || repayAmount == 0) revert CDPVault__liquidatePosition_invalidParameters();

        // load configs
        VaultConfig memory config = vaultConfig;
        LiquidationConfig memory liqConfig_ = liquidationConfig;

        // load liquidated position
        Position memory position = positions[owner];
        DebtData memory debtData = _calcDebt(position);

        // load price and calculate discounted price
        uint256 spotPrice_ = spotPrice();
        uint256 discountedPrice = wmul(spotPrice_, liqConfig_.liquidationDiscount);
        if (spotPrice_ == 0) revert CDPVault__liquidatePosition_invalidSpotPrice();
        // Enusure that there's no bad debt
        if (calcTotalDebt(debtData) > wmul(position.collateral, spotPrice_)) revert CDPVault__BadDebt();
```
The bad debt check compared the spot price of the collateral in USD, and compares this value to the debt amount in token amounts.

Check what oracle is used and what the returned spot price is returned for USD, or some token conversion?

## Tools Used

## Recommended Mitigation Steps


## Assessed type

Math