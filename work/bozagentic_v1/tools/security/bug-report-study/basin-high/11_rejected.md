# #11: Skim() is susceptible to MEV bot attack.
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'edited-by-warden', 'duplicate-291']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L603


# Vulnerability details

## Impact
In the well.sol contract, the `external` function `skim()` can be called by anyone to transfer excess tokens in the contract to a `recipient`. This call is vulnerable to `frontrunning` attack as the caller can be frontrun to skim the funds before the callers transaction gets approved by miners.
This can lead to a serious loss of funds by the users.
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
## Proof of Concept
Consider a situation, whereby Alice instead of calling the `addLiquidity` function, mistakenly transfers her tokens directly into the well. Now, Alice wants to get her tokens back which is possible by calling the `skim()` function which calculates the `skimamount` by subtracting `reserves` of the token from the total balance of the token in the contract, which gives the excess token amount. Alice then calls the `skim()` function but while the transaction is still in the memory pool, if a `mev` `bot` sees this transaction, it can frrontrun the transaction, passing in a higher gas than Alice thereby effectively stealing the funds.

## Tools Used
Manaul review
## Recommended Mitigation Steps





## Assessed type

MEV