# #296: Funds added to reserves through `sync` are accidentally transferred out to users
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'duplicate-136']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L590


# Vulnerability details

## Impact
`Well`s have the ability to `shift` funds to other `Well`s as part of gas-efficient multi-pool swaps. [This natspec explanation of this can be find here](insert link). The `sync` function is intended to synchronize the underlying token amounts with the token reserves of the `Well`. But there is a bug which allows the next user calling `swapFrom`, with the target token set as the same as the token that was received, to receive all the funds added to the reserves from calling `sync`.  

When tokens are transferred into the `Well`, through `shift`'s from another `Well`, a call to `sync` should update the `reserves` for that specific token.  

[This code](https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L590) updates the reserves in `sync`:  
```  
    reserves[i] = _tokens[i].balanceOf(address(this));
```  

But a user may inadvertently transfer the received tokens out if they are swapping into the same token that was received by the `Well`.

The issue arises because `sync` does not update the `totalSupply` (i.e. it does not mint new LP tokens), so if the token the user is swapping to is the same token that was updated with `sync` (let's say `tokenA` was transferred and `reserve[tokenA]` was updated with `sync`), the `Well` can't account for the updated reserves of `tokenA` because the calculation for `reserves[tokenA]` in from [`calcReserve` in `ConstantProduct2.sol`](https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L58) uses the `lpTokenSupply ** 2` (which can't be updated via `sync`) and the `resesrves[tokenB]` (which wasn't affected by `sync` as no `tokenB` was received). 

This means that the incorrect calculation result from `calcReserve` (which derives the expected reserves from the `totalSupply` of LP Tokens and the `reserves[tokenB]`) gets subtracted from `reserveJBefore` (which holds the updated reserves). This effectively sweeps the `tokenA` received from direct transfers (or `shifts`) and accounted for with `sync` into the next `swapFrom`.  

As `shift` and `sync` are likely to be called as part of regular token swaps, this bug is very likely to occur in production and may cause the protocol in it's aggregate (due to the nature of `Well`'s shifting funds for gas-efficiency) to lose funds. For this reason it was submitted as high impact.

## Proof of Concept

The below code can be placed inside the `Well.AddLiquidity.t.sol` file, but it requires a slight modification to the `TestHelper.sol` file to mint 186000 `token0` and 100 `token1` to the `Well` when setting up liquidity - this is to simulate a `DAI-WETH` pair for this PoC. The PoC below shows a user exploiting the issue to receive `10 WETH` in exchange for `10 DAI`.  

```  
    function test_PoC_Sync_Interceptor() public prank(user) {
        IERC20[] memory _tokens = well.tokens();

        /// Let's send tokens to this address to keep the outputs clean
        address manipulationRecipient = address(0x30);

        /// Tokens get sent to the protocol directly, either via `shift` from another `Well` or through other means
        _tokens[1].transfer(address(well), 10 ether);
        /// `sync` is called to add these funds to the token reserves
        well.sync();

        /// A user calls a normal `swapFrom` for a small amount and recieves the amount that was transferred to the well directly.
        console.log("Attacker Captures Funds: ", well.swapFrom(_tokens[0], _tokens[1], 10 * 10**18, 0, manipulationRecipient, type(uint256).max));

        /// The user who had 0 WETH now has more than 10 WETH
        assertGt(_tokens[1].balanceOf(manipulationRecipient), 10 ether);
        }
```  

## Tools Used  
Manual code review. Foundry.

## Recommended Mitigation Steps  
It is recommended that `sync` be reworked to take into account the fact that `lpTokenSupply` should update in line with the token reserves.


## Assessed type

Math