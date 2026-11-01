# #47: Maliciuos user can get free tokens from Well contract 
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L392
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L460
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352
https://github.com/code-423n4/2023-07-basin/blob/main/test/Well.Shift.t.sol#L19


# Vulnerability details

## Impact
A malicious user can steal other users tokens form the Well contract by playing with `addLiquidity()`, `shift()` and `removeLiquidity()` functions.

## Proof of Concept

After creating a Well contract users are able to add or remove liquidity from it. Also there is an unprotected `shift()` function that is suppose to be used during multi-step swaps as it is stated in the comments:

```
When using Wells for a multi-step swap, gas costs can be reduced by "shifting" tokens from one Well to another rather than returning them to a router (like Pipeline).
```

However the function can be called by any user anytime to get free tokens.

```
    function shift(
        IERC20 tokenOut,
        uint256 minAmountOut,
        address recipient
    ) external nonReentrant returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = new uint256[](_tokens.length);

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

Moreover `shift()` function relies on contract token balance, but on on the reserves as it required in other functions. Here is a comment in the code section about it:

```
        // Use the balances of the pool instead of the stored reserves.
        // If there is a change in token balances relative to the currently
        // stored reserves, the extra tokens can be shifted into `tokenOut`.
```

Also there is a Foundry test provided by the team in the Well.Shift.t.sol#testFuzz_shift() that proves that any user can get tokens from the unbalances pools.

```
    function testFuzz_shift(uint256 amount) public prank(user) {
        amount = bound(amount, 1, 1000e18);

        // Transfer `amount` of token0 to the Well
        tokens[0].transfer(address(well), amount);
        Balances memory wellBalanceBeforeShift = getBalances(address(well), well);
        assertEq(wellBalanceBeforeShift.tokens[0], 1000e18 + amount, "Well should have received token0");
        assertEq(wellBalanceBeforeShift.tokens[1], 1000e18, "Well should have NOT have received token1");

        // Get a user with a fresh address (no ERC20 tokens)
        address _user = users.getNextUserAddress();
        Balances memory userBalanceBeforeShift = getBalances(_user, well);

        // Verify that `_user` has no tokens
        assertEq(userBalanceBeforeShift.tokens[0], 0, "User should start with 0 of token0");
        assertEq(userBalanceBeforeShift.tokens[1], 0, "User should start with 0 of token1");

        well.sync();
        uint256 minAmountOut = well.getShiftOut(tokens[1]);
        uint256[] memory calcReservesAfter = new uint256[](2);
        calcReservesAfter[0] = well.getReserves()[0];
        calcReservesAfter[1] = well.getReserves()[1] - minAmountOut;

        vm.expectEmit(true, true, true, true);
        emit Shift(calcReservesAfter, tokens[1], minAmountOut, _user);
        uint256 amtOut = well.shift(tokens[1], minAmountOut, _user);

        uint256[] memory reserves = well.getReserves();
        Balances memory userBalanceAfterShift = getBalances(_user, well);
        Balances memory wellBalanceAfterShift = getBalances(address(well), well);

        // User should have gained token1
        assertEq(userBalanceAfterShift.tokens[0], 0, "User should NOT have gained token0");
        assertEq(userBalanceAfterShift.tokens[1], amtOut, "User should have gained token1");
        assertTrue(userBalanceAfterShift.tokens[1] >= userBalanceBeforeShift.tokens[1], "User should have more token1");

        // Reserves should now match balances
        assertEq(wellBalanceAfterShift.tokens[0], reserves[0], "Well should have correct token0 balance");
        assertEq(wellBalanceAfterShift.tokens[1], reserves[1], "Well should have correct token1 balance");

        // The difference has been sent to _user.
        assertEq(
            userBalanceAfterShift.tokens[1],
            wellBalanceBeforeShift.tokens[1] - wellBalanceAfterShift.tokens[1],
            "User should have correct token1 balance"
        );
        assertEq(
            userBalanceAfterShift.tokens[1],
            userBalanceBeforeShift.tokens[1] + amtOut,
            "User should have correct token1 balance"
        );
        checkInvariant(address(well));
    }
```

So imagine a situation with the next steps:

1. Maliciuos user adds liquidity to the well for the one specific token, for example. `token0` as it shown in the tests;
2. Later he calls a `shift()` function to get `token1` from the well contract based on contract token balance. He also doesn't need to burn his lp token to do it.
3. At the end he calls `removeLiquidity` to get his `token0` back. 

He can do it several times in a row and get as many free `token1` as he can.

## Tools Used
Manual review, Foundry test

## Recommended Mitigation Steps
It's better to allow only swap or other system functions use shift option, but not for regular users. 


## Assessed type

Access Control