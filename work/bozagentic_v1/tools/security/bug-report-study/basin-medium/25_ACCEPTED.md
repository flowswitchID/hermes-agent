# #25: Users have the ability to transfer excess tokens to their own account.
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377


# Vulnerability details

## Impact
Users have the freedom to transfer excess tokens to any destination of their choice.

## Proof of Concept
The purpose of the `skim` and `shift` functions in the `Well` contract is to transfer any excess tokens held by the Well to a designated recipient address.

It is important to note that there are no modifiers implemented to restrict access to the `skim` and `shift` functions within the Well contract.
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613
```
    function skim(address recipient) external nonReentrant returns (uint256[] memory skimAmounts) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _getReserves(_tokens.length);
        skimAmounts = new uint256[](_tokens.length);
        for (uint256 i; i < _tokens.length; ++i) {
            skimAmounts[i] = _tokens[i].balanceOf(address(this)) - reserves[i];
            if (skimAmounts[i] > 0) {
                _tokens[i].safeTransfer(recipient, skimAmounts[i]);
            }
        }
    }
```
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377
```
    function shift(
        IERC20 tokenOut,
        uint256 minAmountOut,
        address recipient
    ) external nonReentrant returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = new uint256[](_tokens.length);

        // Use the balances of the pool instead of the stored reserves.
        // If there is a change in token balances relative to the currently
        // stored reserves, the extra tokens can be shifted into `tokenOut`.
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

As a result, if there are no access restrictions or modifiers implemented in the `skim` and `shift` functions of the `Well` contract, it means that anyone can indeed call these functions and specify the recipient address as a parameter.
Consequently, anyone would be able to obtain the excess tokens from the `Well` by calling the `skim` and `shift` functions.

From the this code, anyone can call this function and set the recipient as a parameter, so anyone can get the excess token.
## Tools Used

## Recommended Mitigation Steps
Absolutely, by utilizing a modifier, we can effectively limit access to the `skim` and `shift` functions within the `Well.sol`. 

Modifiers serve as a tool to impose certain conditions or permissions before executing a function.

By implementing a modifier, we can carefully control who is granted permission to call the `skim` and `shift` functions and consequently restrict unauthorized access to the transfer of excess tokens.


## Assessed type

Access Control