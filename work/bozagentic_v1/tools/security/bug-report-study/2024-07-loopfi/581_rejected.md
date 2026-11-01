# #581: Upgraded Q -> 3 from #535 [1730296812865]
Labels: ['3 (High Risk)', 'satisfactory', 'duplicate-399']
Accepted: False

Judge has assessed an item in Issue #535 as 3 risk. The relevant finding follows:

 [Low-6] Shouldn’t here takeCollateral calculated after minusing penalty from repayAmount
According to my understanding During the liquidation process in the Loop protocol, penalties are applied to the position being liquidated to mitigate against profitable self-liquidations.

Here’s how the penalty is calculated and applied:

specific percentage deducted from the repay amount during liquidation
The penalty is calculated as a percentage of the amount the liquidator wants to repay. The specific percentage is defined in the LiquidationConfig of the CDPVault smart contract.
while deep diving i see that

takeCollateral, amount of collateral that will transfered to a Liquidator is calculated based on repayAmount
after that deltaDebt
after that penalty calculated
        uint256 takeCollateral = wdiv(repayAmount, discountedPrice);
        uint256 deltaDebt = wmul(repayAmount, liqConfig_.liquidationPenalty); 
        uint256 penalty = wmul(repayAmount, WAD - liqConfig_.liquidationPenalty);
https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L529-L531

So basically Token In here
poolUnderlying.safeTransferFrom(msg.sender, address(pool), repayAmount - penalty)
https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L539

poolUnderlying.safeTransferFrom(msg.sender, address(pool), penalty);
https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L568

Token Out here

token.safeTransfer(msg.sender, takeCollateral);
https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L565

According to my understanding here penlty has no effect on takeCollateral calculation. As it calculated after takeCollateral calculation and token send to contract in 2 step.

Liquidator getting collateral according to his entered repayAmount, so no penalty effect on colateral he receiving

Mitigation
I think takeCollateral should calculated after minusing penalty from repay amount like follow

+       uint256 penalty = wmul(repayAmount, WAD - liqConfig_.liquidationPenalty);
+       uint256 takeCollateral = wdiv(repayAmount - penalty, discountedPrice);