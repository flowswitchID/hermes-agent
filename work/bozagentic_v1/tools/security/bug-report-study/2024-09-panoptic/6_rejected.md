# #6: Collateral Trackers can be made for tokens without code.
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', ':robot:_06_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-09-panoptic/blob/881a306eeb3764a2553eeb74c69bf85f4b6ce438/contracts/PanopticFactory.sol#L171-L243


# Vulnerability details


Panoptic uses the safeTransferLib adapted from solady for the safe transfers of tokens to and fro the core components like 
- collateralTrackers
- Panoptic Pool
- Panoptic Factory

The safe transfer lib uses assembly for low level calls to the token addresses, this allows for an issue that can be exploited where calls to tokens without code will not revert.
meaning calling transfer or transferForm on such addresses will return success.
before we look at the attack another thing to consider is that during the deployment of new pools, the check that's supposed to prevent this can be bypassed given anyone can create a uniswap V3 pool
```solidity
 /// @notice Create a new Panoptic Pool linked to the given Uniswap pool identified uniquely by the incoming parameters.
    /// @dev Pool deployment is restricted to the factory owner until transferred to the zero address.
    /// @dev There is a 1:1 mapping between a Panoptic Pool and a Uniswap Pool.
    /// @dev A Uniswap pool is uniquely identified by its tokens and the fee.
    /// @param token0 Address of token0 for the underlying Uniswap v3 pool
    /// @param token1 Address of token1 for the underlying Uniswap v3 pool
    /// @param fee The fee tier of the underlying Uniswap v3 pool, denominated in hundredths of bips
    /// @param salt User-defined salt used in CREATE2 for the PanopticPool (must contain caller addr as first 20 bytes)
    /// @return newPoolContract The address of the newly deployed Panoptic pool
    function deployNewPool(
        address token0,
        address token1,
        uint24 fee,
        bytes32 salt
    ) external returns (PanopticPool newPoolContract) {
// more code
//@audit checks if pool has been created
        IUniswapV3Pool v3Pool = IUniswapV3Pool(UNIV3_FACTORY.getPool(token0, token1, fee));
        if (address(v3Pool) == address(0)) revert Errors.UniswapPoolNotInitialized();

        if (address(s_getPanopticPool[v3Pool]) != address(0))
            revert Errors.PoolAlreadyInitialized();
// more code
        newPoolContract = PanopticPool(POOL_REFERENCE.cloneDeterministic(salt));

        // Deploy collateral token proxies
        CollateralTracker collateralTracker0 = CollateralTracker(
            Clones.clone(COLLATERAL_REFERENCE)
        );
        CollateralTracker collateralTracker1 = CollateralTracker(
            Clones.clone(COLLATERAL_REFERENCE)//reorgs
        );

        // Run state initialization sequence for pool and collateral tokens
        collateralTracker0.startToken(true, token0, token1, fee, newPoolContract);
        collateralTracker1.startToken(false, token0, token1, fee, newPoolContract);
// some code

        // Mints the full-range initial deposit
        // which is why the deployer becomes also a "donor" of full-range liquidity
        // The SFPM will `safeTransferFrom` tokens from the donor during the mint callback
        (uint256 amount0, uint256 amount1) = _mintFullRange(v3Pool, token0, token1, fee);

// more code

```
Given 

`Some protocols deploy their token across multiple networks, and when they do so, a common practice is to deploy the token contract from the same deployer address and with the same nonce so that the token address can be the same for all the networks.`

Example 1inch [etheruem](https://etherscan.io/token/0x111111111117dC0aa78b770fA6A738034120C302), [bsc](https://bscscan.com/address/0x111111111117dc0aa78b770fa6a738034120c302), Gelato [ethereum, fanthom, polygon](https://docs.gelato.network/gelato-dao/gel-token-contracts).

and also 
Apart from tokens on multiple chains, another form of tokens that have pre-determined addresses are tokens created from factory contracts.

`LP tokens of pools can be predetermined before the pool is created, supposing we expect a new uniswap pool to be created from 2 credible tokens, an attacker can create a pool using the lp tokens of the pool that doesn't exist yet,usi pairing it up with a credible token to create a uniswapV3 pool`.

Given such tokens an attacker can create uniswapV3 pools, pairing such tokens with other credible tokens.
https://etherscan.io/address/0x1F98431c8aD98523631AE4a59f267346ea31F984#code#F1#L34

this will allow bypass of this check
```solidity
        IUniswapV3Pool v3Pool = IUniswapV3Pool(UNIV3_FACTORY.getPool(token0, token1, fee));
        if (address(v3Pool) == address(0)) revert Errors.UniswapPoolNotInitialized();
```

given this predeterminants.

This is an example of how this can be exploited to steal a user funds.

- Alice takes a token without a code yet(for instance, 1inch), pairs it up with another credible token (eg, LINK)to form a uniswap pool.
- deploys a new panoptic pool using the 2 tokens(1inch/LINK), with the pool having collateral trackers of the 2 tokens each being the underlying token in its tracker.
- attacker then deposits into the tracker any amount of `1inch`, since the tokens has no code, the deposit using `safeTransferFrom()` will be successful with the attacker now having a balance and shares inside the tracker of such token.
- later on the token actual gets a code and it valid.
- seeing a panoptic pool has been created for such a tokens tokens Bob intends to get shares from the `1inch` collateral tracker, and makes a deposit to gain shares.
- Alice having had shares already in the collateral tracker before hand without actual making any real deposit of 1inc, siphons bobs funds on the call to `withdraw()` or `redeem`
- this transfer Alice the balance in the contract and that is Bob's balance.



**Similar issue valid with POC to gain more context**
- https://github.com/MiloTruck/audits/blob/main/contests/2023-12-morpho-blue.md#h-01-markets-can-be-created-for-tokens-without-code
## Recommended Mitigation Steps
The `panopticfactory::deployNewPool()` should be changed to this

```diff
    function deployNewPool(
        address token0,
        address token1,
        uint24 fee,
        bytes32 salt
    ) external returns (PanopticPool newPoolContract) {
        // sensure the token has code.
+     require(token0.length != 0, "no code in token0");
+     require(token1.length != 0, "no code in token1");
```



## Assessed type

Other