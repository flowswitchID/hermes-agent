# #4: The recollateralization process isn't working properly
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', 'edited-by-warden', ':robot:_primary']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/p1/mixins/RecollateralizationLib.sol#L198


# Vulnerability details

## Impact

When the `basket` isn't fully `collateralized`, a `recollateralization` process takes place, which is crucial. 
The `basket` consists of several tokens, and during this process, surplus tokens are sold to buy those that are in deficit.
To determine the amounts to sell and buy, we first set a range of `baskets` that can be achieved after optimal trading, referred to as `[bottom, top]`. 
If a token has enough to cover the `top` of this range, the excess can be sold, but it should not fall below the `top`. 
Conversely, if a token does not have enough to cover the `bottom`, we need to buy more, with the amount based on the `bottom`.
However, there's an issue: the `bottom` calculation is incorrect. 
It's essential to fully `collateralize` the `baskets` as quickly as possible. 
Even if we could achieve full `collateralization` in one trade, the incorrect `bottom` calculation might prevent this, requiring manual adjustment of the `basketsNeeded`, which could lead to losses for depositors.
Alternatively, the trading could be split into several smaller trades, each taking time—potentially up to a week per trade.
## Proof of Concept
Below is the `basketRange` function, which determines the target `basket` range.
```
function basketRange(TradingContext memory ctx, Registry memory reg)
    internal
    view
    returns (BasketRange memory range)
{
    for (uint256 i = 0; i < reg.erc20s.length; ++i) {
143:       (uint192 low, uint192 high) = reg.assets[i].price(); // {UoA/tok}

        if (
148:            ctx.quantities[i] == 0 &&
149:            !TradeLib.isEnoughToSell(reg.assets[i], ctx.bals[i], low, ctx.minTradeVolume)
        ) {
            continue;
        }
        {

            uint192 anchor = ctx.quantities[i].mul(ctx.basketsHeld.top, CEIL);  
			 ...
        }

        {
185:            uint192 anchor = ctx.quantities[i].mul(ctx.basketsHeld.bottom, FLOOR);

189:            uint192 val = low.mul(ctx.bals[i] - anchor, FLOOR);

198:            uoaBottom += (val < ctx.minTradeVolume) ? 0 : val - ctx.minTradeVolume;

        }
    }
}
```
In `line 148`, if the `quantity` of a token is `0`, it means this token is not a `backing token` for the `basket`, so we can sell all of these tokens. However, the sale must meet the `minimum trading volume`. If a token's quantity is insufficient to satisfy this minimum, we skip it.

By the time we reach `line 198`, the token is either a `backing token` or a `non-backing token` with a quantity sufficient to exceed the `minimum trading volume`. At this point, all `backing tokens` should have enough quantity to cover the current `bottom`.
The idea is to sell all excess tokens at a `lower price`, buy `baskets` at a `higher price`, and see the final `bottom` we can achieve. 
It seems the reason for subtracting the `minimum trading volume` in `line 198` is to ensure we trade at least that volume.

However, if the token is not a `backing token` and its quantity is greater than the `minimum trading volume`, we could sell all of it. 
If the token is a `backing token` with less than the `minimum trading volume`, we didn’t actually sell these tokens, but they should still be included in the target `bottom` calculation.

```
For example, consider two backing tokens, A and B, and one non-backing token, C. 
All three tokens are priced at 1, with A having a quantity of 2, B having 1, and C having 2. 
The minimum trading volume is 2, and the current bottom is 1. 
We could sell 2 C to buy 2 B, increasing the bottom to 2. 
However, in line 198, the target bottom is still calculated as 1, so no trade is executed.
```
Therefore, there’s no need to subtract the `minimum trading volume` in `line 198`.

Let me clarify with a specific example:

Consider two tokens: `token0` and `token1`, where `token1` is a backing token and `token0` is not. Their prices and the basket's price are as follows. 
```
low price of token 0         =>   BigNumber { value: "990000000000000000" }
high price of token 0        =>   BigNumber { value: "1010000000000000000" }
low price of token 1         =>   BigNumber { value: "990000000000000000" }
high price of token 1        =>   BigNumber { value: "1010000000000000000" }
low price of basket          =>   BigNumber { value: "990000000000000000" }
high price of basket         =>   BigNumber { value: "1010000000000000000" }
```
Currently, there are no `token1` in the `backing manager`, and the current `basket bottom` and `basketsNeeded` are:
```
current basket bottom        =>   BigNumber { value: "0" }
baskets needed               =>   BigNumber { value: "100000000000000000000" }
```

To fully `collateralize`, we need to purchase `100000000000000000000 token1`, which requires selling `102020202020202020203 token0` (we're selling `token0` at a lower price and buying `token1` at a higher price). 
```
102020202020202020203 * 990000000000000000 / 1010000000000000000 = 100000000000000000000
```
The `minimum trading volume` is currently `20e18`, and this amount is subtracted from the `target bottom` calculation in `line 198`.

As a result, even though we have enough `token0` to buy the required `token1` and fully `collateralize`, the determined sell and buy amounts are insufficient, so the basket remains undercollateralized.
```
determined sell amount in rebalance   =>   BigNumber { value: "81818181818181818181" }
token 1 buy amount in rebalance       =>   BigNumber { value: "80198019801980198019" }
```

After this trade, there won’t be enough funds left to execute another trade because the remaining `token0` amount is just equal to the `minimum trading volume`, which won't allow the `target bottom` to increase. 
Consequently, the `compromiseBasketsNeeded` function will be called to manually decrease the `basketsNeeded`, leading to a loss for depositors

Please add below test to the `test/Recollateralization.test.ts`.
```
describe('Recollateralization test', function () {
  it('Should be fully collateralized', async () => {
    const [sellLow, sellHigh] = await collateral0.price();
    console.log('low price of token 0         =>  ', sellLow)
    console.log('high price of token 0        =>  ', sellHigh)
    
    const [buyLow, buyHigh] = await collateral1.price();
    console.log('low price of token 1         =>  ', buyLow)
    console.log('high price of token 1        =>  ', buyHigh)

    const issueAmount = bn('100e18')
    await basketHandler.connect(owner).setPrimeBasket([token0.address], [fp('1')])
    await basketHandler.connect(owner).refreshBasket()
  
    await token0.connect(addr1).approve(rToken.address, initialBal)
    await rToken.connect(addr1).issue(issueAmount)
    expect(await basketHandler.fullyCollateralized()).to.equal(true)  
    await basketHandler.connect(owner).setPrimeBasket([token1.address], [fp('1')])
    await basketHandler.connect(owner).refreshBasket() 
    expect(await basketHandler.fullyCollateralized()).to.equal(false)
    expect(await rToken.basketsNeeded()).to.equal(issueAmount)
    expect((await basketHandler.basketsHeldBy(backingManager.address)).bottom).to.equal(0)  
    
    await backingManager.connect(owner).setMinTradeVolume(bn('20e18'));
    await backingManager.connect(owner).setMaxTradeSlippage(0);  
    
    const [buPriceLow, buPriceHigh] = await basketHandler.price(false)
    console.log('low price of basket          =>  ', buPriceLow)
    console.log('high price of basket         =>  ', buPriceHigh)  
    console.log('current basket bottom        =>  ', (await basketHandler.basketsHeldBy(backingManager.address)).bottom)
    console.log('baskets needed               =>  ', await rToken.basketsNeeded())
    // sellAmount * sellLow / buPriceHigh >= issueAmount
    
    const excessAmount = issueAmount.mul(buPriceHigh).div(sellLow).sub(issueAmount).add(1)
    console.log('additional token 0 amount to buy enough token 1 for full collateralization :  ', excessAmount);  
    await token0.connect(owner).mint(backingManager.address, excessAmount)
    const token0Bal = await token0.balanceOf(backingManager.address)
    console.log('token 0 balance of BM        =>  ', token0Bal)  
    const SCALE_FACTOR = bn('1e18')
    
    /**
     * uint192 val = low.mul(ctx.bals[i] - anchor, FLOOR);
     * uoaBottom += (val < ctx.minTradeVolume) ? 0 : val - ctx.minTradeVolume;
     */
    const uoaBottom = sellLow.mul(token0Bal).div(SCALE_FACTOR).sub(await backingManager.minTradeVolume())

    /**
     * range.bottom =
     *     ctx.basketsHeld.bottom +
     *     uoaBottom.mulDiv(FIX_ONE.minus(ctx.maxTradeSlippage), buPriceHigh, FLOOR);
     */
    const bottom = uoaBottom.mul(SCALE_FACTOR.sub(await backingManager.maxTradeSlippage())).div(buPriceHigh)  

    // needed = range.bottom.mul(ctx.quantities[i], CEIL); // {buyTok};
    const minBuyAmount = bottom.mul(bn('1e18')).div(SCALE_FACTOR)
    const sellAmount = minBuyAmount.mul(buyHigh).div(sellLow)  
    console.log('determined sell amount in rebalance   =>  ', sellAmount)
    console.log('token 1 buy amount in rebalance       =>  ', minBuyAmount)  

    await backingManager.rebalance(TradeKind.DUTCH_AUCTION)
    const trade0 = await ethers.getContractAt(
      'DutchTrade',
      await backingManager.trades(token0.address)
    )
    expect(await trade0.sellAmount()).to.equal(sellAmount)
  })
});
```
## Tools Used

## Recommended Mitigation Steps
```
- uoaBottom += (val < ctx.minTradeVolume) ? 0 : val - ctx.minTradeVolume;
+ uoaBottom += val;
```





## Assessed type

Math