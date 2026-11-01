# #61: attacker can swap zero amount of token A to get some amount of token B
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L215-L240
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L695-L702
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/functions/ConstantProduct2.sol#L58-L75


# Vulnerability details

## Impact

an attacker can make a call to the function `_swapFrom` to swap token A --> B, but the attacker can set `amountIn` to zero for the token A and receive token B. this attack is possible because the function `_swapFrom` did not check the `amountIn` value to not be equal to zero, if the attacker make a call with zero amount to swap then s/he would get token B because the ` amountOut` is calculated using the reserve of B before the swap and the calculation of the reserve B after the swap. more details in POC

## Proof of Concept

let's say Alice want to swap token A to get token B by calling `swapFrom` which it made call to the `_swapFrom` function:

```solidity
 function swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountOut) {
        fromToken.safeTransferFrom(msg.sender, address(this), amountIn);
        amountOut = _swapFrom(fromToken, toToken, amountIn, minAmountOut, recipient);
    }
```

first we send `amountIn` to the address(this) and we can set the `amountIn` to zero because there is no check for zero value in `safeTransferFrom` function in `safeERC20`

```solidity
 function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeWithSelector(token.transferFrom.selector, from, to, value));
    }

   //audit the _callOptionalReturn function is the code below
    function _callOptionalReturn(IERC20 token, bytes memory data) private {
        // We need to perform a low level call here, to bypass Solidity's return data size checking mechanism, since
        // we're implementing it ourselves. We use {Address-functionCall} to perform this call, which verifies that
        // the target address contains contract code and also asserts for success in the low-level call.

        bytes memory returndata = address(token).functionCall(data, "SafeERC20: low-level call failed");
        require(returndata.length == 0 || abi.decode(returndata, (bool)), "SafeERC20: ERC20 operation did not succeed");
    }
```

and in this way if Alice decide to set the `amountIn` to zero then the function `_swapFrom` will be called using Alice input value. the `_swapFrom` function:

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
        //@audit we increase reserve[i] or the reserve for the A token by zero !
        reserves[i] += amountIn;
        //@audit here we return the reserve[j] or B token value before swap and after swap(calculating)
        uint256 reserveJBefore = reserves[j];
        //@audit we use all reserves(both i and j) to make the calculate
        reserves[j] = _calcReserve(wellFunction(), reserves, j, totalSupply());

        // Note: The rounding approach of the Well function determines whether
        // slippage from imprecision goes to the Well or to the User.

        //@audit we set amountOut to be equal to =  reserveJBefore - reserves[j] --> reserve[j] before and the reserve[j] calculated using all reserves.
        amountOut = reserveJBefore - reserves[j];
        if (amountOut < minAmountOut) {
            revert SlippageOut(amountOut, minAmountOut);
        }

        toToken.safeTransfer(recipient, amountOut);
        emit Swap(fromToken, toToken, amountIn, amountOut, recipient);
        _setReserves(_tokens, reserves);
    }

```

if you read the //@audit tag then its clear that Alice can send zero amount to increase a LP for the reserve[i] and then she get the reserve[j] minus the calculated reserve[j] as `amountOut` which it can be more than zero. the function `_calcReserve` will call the `calcReserve`:

```solidity
function _calcReserve(
        Call memory _wellFunction,
        uint256[] memory reserves,
        uint256 j,
        uint256 lpTokenSupply
    ) internal view returns (uint256 reserve) {
        reserve = IWellFunction(_wellFunction.target).calcReserve(reserves, j, lpTokenSupply, _wellFunction.data);
    }

    // the function calcReserve in the constantProduct.sol lib

    function calcReserve(
        uint256[] calldata reserves,
        uint256 j,
        uint256 lpTokenSupply,
        bytes calldata
    ) external pure override returns (uint256 reserve) {
        // Note: potential optimization is to use unchecked math here
        reserve = lpTokenSupply ** 2;
        reserve = LibMath.roundUpDiv(reserve, reserves[j == 1 ? 0 : 1] * EXP_PRECISION);
    }
```

if we see the calculation above then the `amountOut` will be more than zero and this amount will be send to Alice without swapping any tokens because the `calcReserve` will take the `totalSupply` as parameter and if the liquidity contains tokens(A and B) then its possible to Alice to swap zero amount and get some token to herself.

## Tools Used

manual review

## Recommended Mitigation Steps

I recommend to prevent swapping of zero amount by check the `amountIn` in `_swapFrom` function:

```solidity
require(amountIn > 0, "invalid amountIn")
```

Uniswap v2 implemented this check too and it can be helpful to check their mechanism, at the end all AMM will have some similarity in some points:
https://github.com/Uniswap/v2-core/blob/ee547b17853e71ed4e0101ccfd52e70d5acded58/contracts/UniswapV2Pair.sol#L178

and maybe setting a min value for swapping from A--> B will help too.



## Assessed type

Other