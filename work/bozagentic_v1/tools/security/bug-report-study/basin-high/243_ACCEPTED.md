# #243: Possible to stop trading
Labels: ['bug', '3 (High Risk)', 'disagree with severity', 'high quality report', 'primary issue', 'sponsor acknowledged', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L436-L439
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L460-L483
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L495-L517


# Vulnerability details

## Impact
It's possible to stop market due to division by 0 exception. So better to prevent this, because better to revert with missing `minAmountOut` than revert with some error, which might be complicated to detect.

## Proof of Concept
There is a change to withdraw all the liquidity for one of the tokens from the pool.
Let's consider a case: 
* `Well` deployed with two tokens -- A and B and `ConstantProduct2` as `wellFunction`;
* Someone provides liquidity: 1000 A and 1000 B, he got 2000 LP;
* Someone conduct swaps, A = 900, B = 1123, LP the same = 2000;
* Depositor may call `removeLiquidity` with all his LP (2000), and withdraw all reserves;
* Then if anyone wants to make a swap he gots an error -- (as you know division by 0 won't be printed at metamask or any other wallet, so user can't get well explanation about what happened);
* So better to lock a bit of tokens on the contract forever and in this case if user want to mint some token in case above he got well described error -- `revert SlippageOut(amountOut, minAmountOut);`.   


## Tools Used

Manual review

## Recommended Mitigation Steps

Block a bit of each tokens during first liquidity minting. 


## Assessed type

Uniswap