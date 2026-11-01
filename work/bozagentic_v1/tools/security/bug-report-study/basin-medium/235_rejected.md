# #235: Wherever possible, _safeMint() should be used rather than _mint()
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/mocks/tokens/MockToken.sol#L22, https://github.com/code-423n4/2023-07-basin/blob/main/mocks/tokens/MockTokenFeeOnTransfer.sol#L27, https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L441


# Vulnerability details

## Impact
_mint() is not recommended in favour of _safeMint(), which guarantees that the recipient is either an EOA. 

## Proof of Concept
https://github.com/code-423n4/2023-07-basin/blob/main/mocks/tokens/MockToken.sol#L22, 
https://github.com/code-423n4/2023-07-basin/blob/main/mocks/tokens/MockTokenFeeOnTransfer.sol#L27, https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L441

## Tools Used

Vscode
use _safeMint() instead of _mint().


## Assessed type

Upgradable