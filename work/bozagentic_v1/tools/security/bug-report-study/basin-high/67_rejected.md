# #67: ATTACKER CAN DRAIN THE POOL REMOVING LIQUDITY DUE CROSS FUNCTION REENTRENCY 
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L477-L478


# Vulnerability details

The Well contract is implementing ReentrancyGuardUpgradeable to prevent reentrancy (this is in case that the token was a bad token implementation, a ERC777 , even someone that just want make a rugpull ) but this doesn´t prevent cross function reentrancy. The contract is not following the CEI pattern open the door for attacker.

## Impact
A malicius user or attacker can get more lptokens that he should receive due the contract is not following the CEI patterns draining the pool repeting the attack(check Proof of Concept) multiples times.

## Proof of Concept
We can start analizing the removeLiquidity function:
```
file:src/Well.sol
function removeLiquidity(
        uint256 lpAmountIn,
        uint256[] calldata minTokenAmountsOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256[] memory tokenAmountsOut) {
        ...
       _burn(msg.sender, lpAmountIn); //@reducing the totalsupply
        tokenAmountsOut = _calcLPTokenUnderlying(wellFunction(), lpAmountIn, reserves, lpTokenSupply);
        for (uint256 i; i < _tokens.length; ++i) {
            if (tokenAmountsOut[i] < minTokenAmountsOut[i]) {
                revert SlippageOut(tokenAmountsOut[i], minTokenAmountsOut[i]);
            }
            _tokens[i].safeTransfer(recipient, tokenAmountsOut[i]); //@audit  its no following the cei, this can 
            reserves[i] = reserves[i] - tokenAmountsOut[i];
        }
        ...
    }
```
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L459C1-L483C6

As we can see the contract is burning the lpAmountIn reducing the totalsupply, the contract calculate the tokenAmountOut and then make the transfer, we can notice that the resever its not already reduced letting the contract in a not complety state.

At this point we have less totalSupply but with the same reserve letting the contract in a bad position in case that the token was an erc777 or a bad token (the contract can not make sure that the token is an ERC20 or doesn´t have some hooks implementation) a malicius user can call addLiquidity and get more lptoken.

see the addLiquidty function:

```
file:src/Well.sol
function _addLiquidity(
        uint256[] memory tokenAmountsIn,
        uint256 minLpAmountOut,
        address recipient,
        bool feeOnTransfer
    ) internal returns (uint256 lpAmountOut) {
            ...
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
        ...
    }
```
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L413C5-L444C6

let´s start to analize _addLiquidity function, as we can see the contract is taking the token from the user and calculating the lpAmountOut, let´s analize the calculation:

```
file:src/Well.sol
function _calcLpTokenSupply(
        Call memory _wellFunction,
        uint256[] memory reserves
    ) internal view returns (uint256 lpTokenSupply) {
        lpTokenSupply = IWellFunction(_wellFunction.target).calcLpTokenSupply(reserves, _wellFunction.data);
    }
```
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L681C5-L686C6

```
file:src/functions/ConstantProduct2.sol
function calcLpTokenSupply(
        uint256[] calldata reserves,
        bytes calldata
    ) external pure override returns (uint256 lpTokenSupply) {
        lpTokenSupply = (reserves[0] * reserves[1] * EXP_PRECISION).sqrt();
    }
```
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/functions/ConstantProduct2.sol#L49-L54

Firts thing that we can see is that te calculation of the new lpTokenSupply is made it with the reseves that are not complete updated due the reentrancy attack. 

The amount of lp token to the user is made by the previus calculation (which is major that it should be) minus the tokensupply which has already been decrease by the burn in the remove liquidity function.

```
function _addLiquidity(...){
   ...
   lpAmountOut = _calcLpTokenSupply(wellFunction(), reserves) - totalSupply();
   ...
   _mint(recipient, lpAmountOut);
   ...}
   
```
In Resume:
1. attacker can removeLiquidity and let the contract in a state where the tokenSupply is already decrease by the burn function but the reserves are no already decrease.
2. attacker can addLiquidity getting more lp token that it should receive due that the calculation is made with the resever that are no already update but the totalSupply is already update :

```
   lpAmountOut = _calcLpTokenSupply(wellFunction(), reserves) - totalSupply(); //@audit the reserve is no already decrease but the totalSupply it is.
 
```
Just to clarify that addliquidity is not the only function that the maliciuse user can reenter, A malicus user can reenter calling swapFromFeeOnTransfer or swapFrom , both function work with _swapFrom function, let´s analize quickly: 
```
file:src/Well.sol
function _swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient
    ) internal returns (uint256 amountOut) {
        ...
        reserves[i] += amountIn;
        uint256 reserveJBefore = reserves[j];
        reserves[j] = _calcReserve(wellFunction(), reserves, j, totalSupply());

        amountOut = reserveJBefore - reserves[j];
        ...

        toToken.safeTransfer(recipient, amountOut);
        ...
    }

```
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L215C5-L241C1

Following the same logic, in this case the contract is calculating the reserve with a reserve that is no already update and with the totalsupply already decrease, let´s analize the calculation:

```
/file: src/functions/ConstantProduct2.sol
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
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/functions/ConstantProduct2.sol#L58C4-L67C6

In this case the reserve its gonna be less than the it should be (just make it sure that the from token corresponds with the reserve that is not already update) that is becase the calculation is made by diving the totalSupply^2 (which is already decreasy by the burn function in the removeLiquidity function) and the reserve that is no update yet (it´s major that it should be because is not already reduced in the removeLiquidity function)


## Tools Used
manual

## Recommended Mitigation Steps
follow the CEI pattern even when you have reentrancyGuard, update the reserve firts and then make the transfer.

```
function removeLiquidity(
        uint256 lpAmountIn,
        uint256[] calldata minTokenAmountsOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256[] memory tokenAmountsOut) {
        ...
        reserves[i] = reserves[i] - tokenAmountsOut[i];
       _tokens[i].safeTransfer(recipient, tokenAmountsOut[i]); 
        ...
}
       
```


## Assessed type

Reentrancy