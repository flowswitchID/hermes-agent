# #50: Tokens can stuck in the contract if user will supply only one token type for initial call "addLiquidity"
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L413
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L436
https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L49
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L471


# Vulnerability details

## Impact
Tokens can stuck in the Well contract if a user will call `addLiquidity` with only one token type for the first ever deposit.

## Proof of Concept

After a Well contract is created we can call `addLiquidity` to deposit tokens and get lp tokens in exchange. Also there is a possibility in the contract to make a depost only for one token type for each `addLiquidity` call.

So if a user is new to the protocol and might not know what is `minLpAmountOut`, he could leave `0` value for it. I believe on the website initial value for the javascript field will be 0 as well, so the situation is quite real. 

And there is no check for the `minLpAmountOut` to be more than zero. 

```
function _addLiquidity(
        uint256[] memory tokenAmountsIn,
        uint256 minLpAmountOut,
        address recipient,
        bool feeOnTransfer
    ) internal returns (uint256 lpAmountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _updatePumps(_tokens.length);

        if (feeOnTransfer) {
            for (uint256 i; i < _tokens.length; ++i) {
                if (tokenAmountsIn[i] == 0) continue;
                tokenAmountsIn[i] = _safeTransferFromFeeOnTransfer(_tokens[i], msg.sender, tokenAmountsIn[i]);
                reserves[i] = reserves[i] + tokenAmountsIn[i];
            }
        } else {
            for (uint256 i; i < _tokens.length; ++i) {
                if (tokenAmountsIn[i] == 0) continue;
                _tokens[i].safeTransferFrom(msg.sender, address(this), tokenAmountsIn[i]);
                reserves[i] = reserves[i] + tokenAmountsIn[i];
            }
        }

        lpAmountOut = _calcLpTokenSupply(wellFunction(), reserves) - totalSupply();
        if (lpAmountOut < minLpAmountOut) {
            revert SlippageOut(lpAmountOut, minLpAmountOut);
        }

        _mint(recipient, lpAmountOut);
        _setReserves(_tokens, reserves);
        emit AddLiquidity(tokenAmountsIn, lpAmountOut, recipient);
    }
```

So for the initial deposit, reserve[0] and reserve[1] for both tokens will be 0 as well. 

A user depost an amount for one token. After token transfer and `_updatePumps()` call, reserve[token0] will be equal for the deposit amount, and the second will still be 0. Due to calculations in the ConstantProduct2 contract a user receives `0 lp tokens`.

```
    function calcLpTokenSupply(
        uint256[] calldata reserves,
        bytes calldata
    ) external pure override returns (uint256 lpTokenSupply) {
        lpTokenSupply = (reserves[0] * reserves[1] * EXP_PRECISION).sqrt();
    }
```

And with 0 for received lp tokens and same value for `minLpAmountOut` the check `if (lpAmountOut < minLpAmountOut) {}` will be passed. 

Later on when a user will want to get his tokens back he will need to call `removeLiquidity`, but it will fail because he has no lp tokens to burn:

```
...
 tokenAmountsOut = new uint256[](_tokens.length);
 _burn(msg.sender, lpAmountIn);
...
```

So the first deposited token will stuck in the contract. 

If you slightly modify the test in the `WellAddLiquidityTest` you can see the proof:

```
    function test_addLiquidity_oneSided() public prank(user) {
        uint256[] memory amounts = new uint256[](2);
        amounts[0] = 10 * 1e18;
        amounts[1] = 0;

        Snapshot memory before;
        AddLiquidityAction memory action;
        action.amounts = amounts;
        action.lpAmountOut = 0;
        action.recipient = user;
        action.fees = new uint256[](2);
        console.log(well.balanceOf(user));
        well.addLiquidity(amounts, 0, user, type(uint256).max);
        console.log(well.balanceOf(user));
    }
```  

## Tools Used
Manual review, Foundry test

## Recommended Mitigation Steps

For the first depost you should provide a check to restrict `minLpAmountOut` be equal to 0, like this:
`require(minLpAmountOut > 0, "fail lp");`


## Assessed type

Token-Transfer