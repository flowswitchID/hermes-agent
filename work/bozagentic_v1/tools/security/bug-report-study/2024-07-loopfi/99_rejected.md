# #99: Flash lending fee is not added to expectedAmount effectively making it non-withdrawable
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', ':robot:_189_group', 'duplicate-55']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/Flashlender.sol#L106


# Vulnerability details

## Impact
Withdrawing of the accumulated fees will not be handled correctly and will cause the final withdrawals to revert

## Proof of Concept
The fees associated with a flash loan are accounted in pool by calling the `repayCreditAccount` function with the fee passed in as profit

[link](https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/Flashlender.sol#L106)
```solidity
    function flashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) external override nonReentrant returns (bool) {
        
        ...

        underlyingToken.transferFrom(address(receiver), address(pool), total);
        pool.repayCreditAccount(total - fee, fee, 0);
```

The `repayCreditAccount` function doesn't add the profit amount to the `expectedLiquidity` since it is meant to repay the credit for which the corresponding interests are already added to the `expectedLiquidity`

[link](https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/PoolV3.sol#L548-L570)
```solidity
    function repayCreditAccount(
        uint256 repaidAmount,
        uint256 profit,
        uint256 loss
    )
        external
        override
        creditManagerOnly // U:[LP-2C]
        whenNotPaused // U:[LP-2A]
        nonReentrant // U:[LP-2B]
    {
        
        ....

        if (profit > 0) {
            // @audit shares are minted for profit
            _mint(treasury, convertToShares(profit)); // U:[LP-14B]
        } else if (loss > 0) {
            
        ....

        // @audit but expectedLiquidityDelta is not updated in case of profit since it expects the profit amount to be already present in the expectedLiquidity
        _updateBaseInterest({
           expectedLiquidityDelta: -loss.toInt256(),
            availableLiquidityDelta: 0,
            checkOptimalBorrowing: false
        }); // U:[LP-14B,14C,14D]
```

This will cause the expectedLiquidity to be less than the actual underlying assets which can lower the interest rates and also disable final withdrawals

[link](https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/PoolV3.sol#L401-L416)
```solidity
    function _withdraw(
        address receiver,
        address owner,
        uint256 assetsSent,
        uint256 assetsReceived,
        uint256 amountToUser,
        uint256 shares
    ) internal {
        if (msg.sender != owner) _spendAllowance({owner: owner, spender: msg.sender, amount: shares}); // U:[LP-8,9]
        _burn(owner, shares); // U:[LP-8,9]


        _updateBaseInterest({
=>          expectedLiquidityDelta: -assetsSent.toInt256(),
            availableLiquidityDelta: -assetsSent.toInt256(),
            checkOptimalBorrowing: false
        }); // U:[LP-8,9]
```



Eg:
underlying assets of pool == 100
shares of pool == 100
expectedLiquidity == 100
flashloan of 100 with 5 as fee
now total underlying assets == 105
shares == 105
but expectedLiquidity == 100

hence only 100 assets can be withdrawn from the pool as further withdrawals will cause underflow in expectedLiquidity

## Tools Used
Manual review

## Recommended Mitigation Steps
Use the mintProfit function instead to account the fees which also adjusts the expectedLiquidity

```solidity
    function mintProfit(uint256 amount) external creditManagerOnly {
        _mint(treasury, amount);


        _updateBaseInterest({
            expectedLiquidityDelta: amount.toInt256(),
            availableLiquidityDelta: 0,
            checkOptimalBorrowing: false
        }); // U:[LP-14B,14C,14D]
```


## Assessed type

Context