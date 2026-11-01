# #11: Price manipulation in the DEX
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_44_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-06-badger/blob/9173558ee1ac8a78a7ae0a39b97b50ff0dd9e0f8/ebtc-zap-router/src/EbtcLeverageZapRouter.sol#L403
https://github.com/code-423n4/2024-06-badger/blob/9173558ee1ac8a78a7ae0a39b97b50ff0dd9e0f8/ebtc-zap-router/src/EbtcLeverageZapRouter.sol#L397


# Vulnerability details

## Impact
when users want to add collateral by calling the `EbtcLeverageZapRouter::_adjustCdp` function, If users could repeatedly mint debt and swap it to stEth to repay the flash loan of activePool, then this number of swapping decreases the price of ebtc token and increases the price of stEth cause we keep buying it with the flash loan.
simply say, we add collateral with a flash loan to mint more debt to swap more ebtc to stEth to manipulate the price.

Users by calling the `_adjustCdp` function can provide a situation where they could Have the same CR but with different values of Collateral and Debt. for example, if a user has a valid CR of 130% with 17.5 collateral and 1 debt, they can have the same CR but with 175 coll and 10 debt. 
at first glance, this isn't an issue cause the CR is healthy but we did increase the demand for the stEth token in the stEth/eBTC pair with flash loan which led to a decrease in the eBTC token price, overall a price manipulation
with the `_adjustCdp` function, users can set the margin balance to 0 to don't pay anything.
another thing is if the CR of the accrued CDP goes underwater, the user can liquid himself with a flash loan of another protocol and enjoy the accrued collateral

## Proof of Concept
append this test to the `LeverageZaps.t.sol`:
```js
 
 function test_adjustCdp_debtIncrease_collIncrease_withoutMargin_stEth() public {
        seedActivePool();


        // debt = 1e3, marginAmount = 3.5 ether
        (address user, bytes32 cdpId) = createLeveragedPosition(MarginType.stETH);

        IEbtcZapRouter.PositionManagerPermit memory pmPermit = createPermit(user);

        uint256 debtChange = 2.24e18;
        uint256 marginIncrease = 0;
        uint256 collValue = 30e18;
        uint256 flAmount = 30e18;

        _before();
        vm.startPrank(user);
        leverageZapRouter.adjustCdp(
            cdpId,
            _getAdjustCdpParams(flAmount, int256(debtChange), int256(collValue), int256(marginIncrease), false),
            abi.encode(pmPermit),
            _getExactInDebtToCollateralTradeData(debtChange)
        );
        vm.stopPrank();
        _after();

        (, uint256 collShares) = cdpManager.getSyncedDebtAndCollShares(cdpId);

        assertGe(collateral.balanceOf(user), 10000e18 - 3.5e18); 
        // the user now has approximately 33.5 coll but only paid 3.5 stEth and increased the demand for the stEth
        assertGe(collShares, 3.5e18);   
        _checkZapStatusAfterOperation(user);
    }


```
this test uses `Mock1Inch` as DEX and the price is constantly equal to `1 ebtc = 13.46 stEth` and no slippage. you should consider that every ebtc swap for stEth increases the price of stEth and manipulates the price. since we can't do a one-time large swap due to the slippage, we can break a large trade into multiple smaller transactions which can help mitigate slippage

## Tools Used
manual

## Recommended Mitigation Steps
enforce and Provide margin balance for adding collateral in the `_adjustCdp` function


## Assessed type

Oracle