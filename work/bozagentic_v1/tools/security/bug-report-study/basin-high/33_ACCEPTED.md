# #33: check missed in the `_swapFrom` to prevent sending tokens to the reserves directly and cause bad cases happen
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L186-L196
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L215-L239


# Vulnerability details

## Impact

the function `swapFrom` in `Well.sol` contract make a swap between from and to token and sending the `amountOut` to the recipient address. this work fine and there is no problem with that but if the user set the `recipient` to the Well address or let's say the receive address then the user can set token to the reserve address and manipulate the reserves of the Well contract without doing necessary calculation for adding liquidity (that is implemented in `addLiquidty` functions) in this case the user can manipulate the reserve address as well.

note that the Well contract is the liquidity pool that holds the reserves of both token(from[i] and to[j]) and that's mean this contract is the reserve contract for both tokens(if not the attacker still can send token to the reserve address and cause manipulate in balances)

## Proof of Concept

in the function `swapFrom` we call the `_swapFrom` which make a swap and transferring the `amountOut` to the recipient address that we set it in the params:

```solidity
function swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountOut) {
        //audit-info send the amountIn to this contract and amountOut to our recipient address
        fromToken.safeTransferFrom(msg.sender, address(this), amountIn);
        amountOut = _swapFrom(fromToken, toToken, amountIn, minAmountOut, recipient);
    }
```

the `_swapFrom` function:

```solidity

 function _swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient
    ) internal returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _updatePumps(_tokens.length);
        (uint256 i, uint256 j) = _getIJ(_tokens, fromToken, toToken);

        reserves[i] += amountIn;
        uint256 reserveJBefore = reserves[j];
        reserves[j] = _calcReserve(wellFunction(), reserves, j, totalSupply());

        // Note: The rounding approach of the Well function determines whether
        // slippage from imprecision goes to the Well or to the User.
        amountOut = reserveJBefore - reserves[j];
        if (amountOut < minAmountOut) {
            revert SlippageOut(amountOut, minAmountOut);
        }
       //@audit what if we set the reserve/tokens address here !?
        toToken.safeTransfer(recipient, amountOut);
        emit Swap(fromToken, toToken, amountIn, amountOut, recipient);
        _setReserves(_tokens, reserves);
    }
```

the function `_swapFrom` will send the `amountOut` to the `recipient` address which can be the `fromToken` or `toToken` and sending token to the reserve directly without calling `addReserve` and cause many bad cases to happen(manipulate reserve balances for example)

## Tools Used

manual review / uniswap v2 codebase

## Recommended Mitigation Steps

recommend to add check to prevent the `recipient` to be the reserves address, check like these can be set in `_swapFrom`:

```solidity
require(recipient != fromToken && recipient != toToken, "invalid recipient addresss")
```

or if the reserves for the both token is Well contract, this check will help:

```solidity
require(recpient != address(this))
```



## Assessed type

Other