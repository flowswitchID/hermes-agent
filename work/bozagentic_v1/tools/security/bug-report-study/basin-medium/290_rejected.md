# #290: Inflation attack in well
Labels: ['bug', '2 (Med Risk)', 'unsatisfactory', 'duplicate-274']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L413


# Vulnerability details

## Impact
The `Well.sol` contract is vulnerable to a first depositor attack allowing someone to directly send funds to the pool in order to obfuscate the `totalSupply()` and steal funds from the subsequent depositor.



## Proof of Concept
Below is how the attack can be carried out.

// 1. The well is empty
// 2. Alice deposits 1 token (1e18 units) into well
// 3. Bob front-runs it, depositing 1 unit
// 4. Bob donates 1 token (1e18 units) into the well using ERC20 transfer
// 5. Alice's deposit is executed

With an empty vault, the shares are being minted at a 1:1 rate with the amount. After Bob deposits 1 unit, the rate is 1:1 unit:shares.

Then, Bob donates another 1e18 units. This will make `totalAssets = 1e18 + 1`.

Finally, Alice's transaction is completed and she gets:

(1e18*1) / (1e18 + 1) = 0.99999.. shares. This will round down and cause Alice to receive 0 shares.

When Bob then withdraws he will take half of Alices shares.

## Tools Used

Manual review

## Recommended Mitigation Steps

Check if the total supply of the LP token is zero and if it is mint 1000 WEI worth of LP tokens and send it to the 0 address.

```
    /// THE FIX
    if (totalSupply == 0) {
        totalSupply = 1000;
        transfer(address(0),1000);
    }
```



## Assessed type

Other