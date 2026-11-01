# #282: Potential token duplication validation bypass
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L36


# Vulnerability details

## Impact
Potential token duplication validation bypass

## Proof of Concept
The loop statement in `init()` function will check if there is duplicated token for a Well.
```solidity
    function init(string memory name, string memory symbol) public initializer {
        __ERC20Permit_init(name);
        __ERC20_init(name, symbol);

        IERC20[] memory _tokens = tokens();
        for (uint256 i; i < _tokens.length - 1; ++i) {
            for (uint256 j = i + 1; j < _tokens.length; ++j) {
                if (_tokens[i] == _tokens[j]) {
                    revert DuplicateTokens(_tokens[i]);
                }
            }
        }
    }
```
However, some proxied tokens may have more than one address, which would bypass the duplicate check above. If a Well has duplicate tokens, an attack path shown below exists, and there can be more.
1. Let us say tokens[0]=tokens[1].
2. An honest LP calls addLiquidity([1 ether,1 ether], 200
ether, address), and the reserves will be (1 ether, 1 ether).
3. Anyone can call skim() and take 1 ether out.
This is because skimAmounts relies on the balanceOf(), which will return 2 ether for the first loop.
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

## Tools Used

## Recommended Mitigation Steps
Adding check for token metadata in the `init()` function.


## Assessed type

Other