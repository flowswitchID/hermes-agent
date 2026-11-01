# #288: NO ACCESS CONTROL IN THE `Well.skim()` EXTERNAL FUNCTION
Labels: ['bug', '2 (Med Risk)', 'unsatisfactory', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613


# Vulnerability details

## Impact
 The `Well.skim()` external function is used to transfer the excess tokens held by the Well to `recipient`. But there is no access control in this function and hence anyone can call this function. Therefore this function allows any arbitory user recieve the excessive tokens in the `Well` contract by calling this `skim()` function.

## Proof of Concept

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

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613

## Tools Used
VSCode and Manaul Review

## Recommended Mitigation Steps
Hence it is recommended to add access control to this function so that only the admin of the protocol can call this function and send the excessive tokens to the treasury of the protocol.


## Assessed type

Access Control