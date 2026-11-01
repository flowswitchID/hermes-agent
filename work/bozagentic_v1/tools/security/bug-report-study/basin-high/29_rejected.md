# #29: No any access control for some external functions in Well.sol
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'edited-by-warden', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L186-L196 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L203-L213 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L264-L290 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L392-L399 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L401-L408 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L460-L483 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L495-L517 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L548-L570 https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613


# Vulnerability details

## Impact
No any access control for some external functions in Well.sol and the tokens can be transfered to any address by attacker.

In Well.sol file, the following functions can be called by external without any access control.
And the input recipient address is not verified.

- Well::skim
- Well::swapFrom
- Well::swapFromFeeOnTransfer
- Well::swapTo
- Well::shift
- Well::addLiquidity
- Well::addLiquidityFeeOnTransfer
- Well::removeLiquidity
- Well::removeLiquidityOneToken
- Well::removeLiquidityImbalanced

So token's safeTransfer function is called arbitrarily by attacker.

Attacker can transfer all tokens of reserves by calling this functions.
So, the tokens of reserved can be transfered to any address by attacker.

## Proof of Concept
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L186-L196
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L203-L213
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L264-L290
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L392-L399
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L401-L408
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L460-L483
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L495-L517
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L548-L570
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613

## Tool used
Manual Review

## Recommended Mitigation Steps
Pleae consider to use "@openzeppelin/contracts/ownership/Ownable.sol" and restricts caller by adding modifier.







## Assessed type

Invalid Validation