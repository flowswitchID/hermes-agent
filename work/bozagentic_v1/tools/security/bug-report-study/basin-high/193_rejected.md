# #193: A malicious user can steal a reserved token by using shift() function of Well.sol if the well was added liquidity unsafely with zero amount of the one of tokens.
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory', 'edited-by-warden', 'duplicate-291']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L413-L444
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377
https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L49-L54
https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L58-L67


# Vulnerability details

## Impact
A malicious user can steal a reserved token by using shift() function of Well.sol if the well was added liquidity unsafely with zero amount of the one of tokens.

## Proof of Concept
Let's assume the well with WETH and USDC tokens. Currently totalSupply() is zero.
A user will add liquidity with WETH token 1000 * 1e18 and USDC token 0 by calling addLiquidity() function.
```solidity
uint256[] memory amounts = new uint256[](2);
amounts[0] = 1000 * 1e18; // WETH amount
amounts[1] = 0; // USDC amount
uint256 lpAmountOut = well.addLiquidity(amounts, 0, user, type(uint256).max);
```
And then lpAmountOut will be zero, because amounts[1] is 0 when calculate lpTokenSupply in ConstantProduct2.sol.

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L413-L444
```solidity
    function _addLiquidity(
        uint256[] memory tokenAmountsIn,
        uint256 minLpAmountOut,
        address recipient,
        bool feeOnTransfer
    ) internal returns (uint256 lpAmountOut) {
        ...
        lpAmountOut = _calcLpTokenSupply(wellFunction(), reserves) - totalSupply();
        if (lpAmountOut < minLpAmountOut) {
            revert SlippageOut(lpAmountOut, minLpAmountOut);
        }

        _mint(recipient, lpAmountOut);
        _setReserves(_tokens, reserves);
        emit AddLiquidity(tokenAmountsIn, lpAmountOut, recipient);
    }
```
In above code, reserves[0] = 1000 * 1e18, reserves[1] = 0 from tokenAmountsIn argument(amounts).
https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L49-L54
```solidity
    function calcLpTokenSupply(
        uint256[] calldata reserves,
        bytes calldata
    ) external pure override returns (uint256 lpTokenSupply) {
        lpTokenSupply = (reserves[0] * reserves[1] * EXP_PRECISION).sqrt();
    }
```
And so lpAmountOut will be zero and will mint 0 LP in _addLiquidity() function, at all, totalSupply() is still 0 even though WETH token was reserved 1000 * 1e18.

A malicious user will manually transfer very small USDC (i.e. 1 USDC) to the well address to avoid division by zero and will call shift() function to transfer all WETH (1000 * 1e18) to his recipient address.
```solidity
IERC20(USDC).safeTransfer(well, 1e6);
well.shift(WETH, 1, recipient);
```
And then amountOut will be all WETH (1000 * 1e18) in shift() function because _calcReserve() will return 0 as totalSupply() is still 0 by calcReserve() function in ConstantProduct2.sol.

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377
```solidity
    function shift(
        IERC20 tokenOut,
        uint256 minAmountOut,
        address recipient
    ) external nonReentrant returns (uint256 amountOut) {
        ...
        for (uint256 i; i < _tokens.length; ++i) {
            reserves[i] = _tokens[i].balanceOf(address(this));
        }
        uint256 j = _getJ(_tokens, tokenOut);
        amountOut = reserves[j] - _calcReserve(wellFunction(), reserves, j, totalSupply());
        if (amountOut >= minAmountOut) {
            tokenOut.safeTransfer(recipient, amountOut);
            reserves[j] -= amountOut;
            _setReserves(_tokens, reserves);
            emit Shift(reserves, tokenOut, amountOut, recipient);
        } else {
            revert SlippageOut(amountOut, minAmountOut);
        }
    }
```
j = 0 and reserves[j] is 1000 * 1e18 as the balance of WETH token of the well, and _calcReserve() will return 0, because totalSupply() is 0, and so amountOut = 1000 * 1e18.
https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L58-L67
```solidity
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
At all, all WETH will be transferred to the malicious recipient address in shift() function.

## Tools Used
Manual

## Recommended Mitigation Steps
If totalSupply() is zero and the one of stored reserves is 0, it should be reverted in shift() function.
We can easily implement _isZeroOneReserved() internal function and define totalSupplyAndOneReservedZero() error in Well.sol.

```solidity
    function shift(
        IERC20 tokenOut,
        uint256 minAmountOut,
        address recipient
    ) external nonReentrant returns (uint256 amountOut) {

        if (totalSupply() == 0 && _isZeroOneReserved()) revert totalSupplyAndOneReservedZero();
        
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = new uint256[](_tokens.length);
        ...
    }
```














## Assessed type

Context