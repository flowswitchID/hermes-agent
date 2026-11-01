# #186: `Well.shift` could suffer from front-running attack 
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-291']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603


# Vulnerability details

## Impact

The usage of `Well.shift` is described in the comment:
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L344
```solidity
     * 2. Using a router with {shift}:
     *  WETH.transfer(sender=0xUSER, recipient=Well1)                        [1]
     *  Call the router, which performs:
     *      Well1.shift(tokenOut=DAI, recipient=Well2)
     *          DAI.transfer(sender=Well1, recipient=Well2)                  [2]
     *      Well2.shift(tokenOut=USDC, recipient=0xUSER)
     *          USDC.transfer(sender=Well2, recipient=0xUSER)                [3]
```

The user first transfers the token to the well, then calls the router to perform the shift actions. An attacker can launch a front-run attack to call `Well.skim`before the user calls the router. Therefore, the attacker can steal the token from the user.


## Proof of Concept

To perform `Well.shift`, the user needs to transfer the token first, so the extra tokens can be shifted into `tokenOut`.
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352
```solidity
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

However, an attacker can launch a front-running attack to call `Well.skim` and steal the funds. 
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603
```solidity
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

The benign order of transactions should be:
* WETH.transfer(sender=0xUSER, recipient=Well1)
* Call the router, which performs `Well.shift` and token transferals

The attacker can inject the malicious transaction to steal the funds:
* WETH.transfer(sender=0xUSER, recipient=Well1)
* Well1.skim(recipient=attacker)
* Call the router, which performs `Well.shift` and token transferals


## Tools Used

Manual Review

## Recommended Mitigation Steps

`Well.shift` should be re-implemented to mitigate front-run attack.



## Assessed type

Other