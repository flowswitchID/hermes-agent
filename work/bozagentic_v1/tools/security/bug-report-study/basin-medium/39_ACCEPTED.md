# #39: ERC-20 other than the well's supported ones can't be rescued
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L603


# Vulnerability details

The `skim` function in `Well.sol` loops through the reserve coins to rescue the surplus. However, ERC-20s accidentally transferred, other than the reserve coins, will remain frozen in the contract and lost for good.

## Impact
Permanent freezing of ERC-20 funds accidentally transferred

## Proof of Concept
- send any non-reserve ERC-20 to a bored well
- call the `skim` function

## Tools Used
Manual review

## Recommended Mitigation Steps
Add another rescue function that:
- accepts a token contract address in argument
- requires the token not to be one of the reserve tokens,
- transfers the full balance to the given recipient


## Assessed type

ERC20