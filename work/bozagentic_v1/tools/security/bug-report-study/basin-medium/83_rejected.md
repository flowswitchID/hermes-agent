# #83: Recommended use of the shift function leads to loss of funds by front running attacks
Labels: ['bug', '2 (Med Risk)', 'unsatisfactory', 'edited-by-warden', 'duplicate-291']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L323-L377


# Vulnerability details

## Impact
The shift function use the balances of the pool instead of the stored reserves. If there is a change in token balances relative to the currently stored reserves, the extra tokens can be shifted into tokenOut. The comment above the shift function describes the way of using it as followed:

```solidity
* 2. Using a router with {shift}:
*  WETH.transfer(sender=0xUSER, recipient=Well1)                        [1]
*  Call the router, which performs:
*      Well1.shift(tokenOut=DAI, recipient=Well2)
*          DAI.transfer(sender=Well1, recipient=Well2)                  [2]
*      Well2.shift(tokenOut=USDC, recipient=0xUSER) 
*          USDC.transfer(sender=Well2, recipient=0xUSER)                [3]
```

If using the function in the recommended way an attacker can front run the user after the transfer to the first Well and execute the shift function himself to steal the users funds.

## Proof of Concept
1. User transfers tokens to Well implementation
2. User calls shift function
3. Attacker front runs the user to call the shift function first and steals the extra tokens on the Well implementation

## Tools Used
Manual Review, Foundry, VSCode

## Recommended Mitigation Steps
If the suggested router does all the calls, it would not be possible to front run it as it would all be executed in one transaction. Therefore updating the comment could be enough to prevent users from using the function in a dangerous way. Providing a router contract and allow the shift function to be only callable by a trusted router would be more secure.





## Assessed type

MEV