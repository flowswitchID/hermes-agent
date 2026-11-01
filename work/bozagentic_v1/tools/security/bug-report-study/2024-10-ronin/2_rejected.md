# #2: Liquidity migrations from v2 to v3 for LPers will not work
Labels: ['invalid', '3 (High Risk)', 'withdrawn by warden']
Accepted: False

# Lines of code

https://github.com/ronin-chain/katana-v3-contracts/blob/03c80179e04f40d96f06c451ea494bb18f2a58fc/src/periphery/V3Migrator.sol#L41-L42


# Vulnerability details

## Proof of Concept
For migrations of Liquidity from the v2 katana pools contract to the v3 contracts, LPers can migrate such liquidity by executing the `migrate` function of the `V3Migrator` contract which burns the liquidity from the msg.sender by transferring it to the `V3Migrator` contract and then burning it before ultimately minting a new LP position to the user for v3 pools. However, due to a wrong recipient in the `safeTransferFrom` call argument, all liquidity migration calls from v2 to v3 will fail

```solidity
function migrate(MigrateParams calldata params) external override {
    require(params.percentageToMigrate > 0, "Percentage too small");
    require(params.percentageToMigrate <= 100, "Percentage too large");

    // burn v2 liquidity to this address
@>    TransferHelper.safeTransferFrom(params.pair, msg.sender, params.pair, params.liquidityToMigrate); // @audit recipient issue here

@>    (uint256 amount0V2, uint256 amount1V2) = IKatanaV2Pair(params.pair).burn(address(this)); // @audit issue here

    // calculate the amounts to migrate to v3
    uint256 amount0V2ToMigrate = amount0V2.mul(params.percentageToMigrate) / 100;
    uint256 amount1V2ToMigrate = amount1V2.mul(params.percentageToMigrate) / 100;

    // approve the position manager up to the maximum token amounts
    TransferHelper.safeApprove(params.token0, nonfungiblePositionManager, amount0V2ToMigrate);
    TransferHelper.safeApprove(params.token1, nonfungiblePositionManager, amount1V2ToMigrate);

    // mint v3 position
    (,, uint256 amount0V3, uint256 amount1V3) = INonfungiblePositionManager(nonfungiblePositionManager).mint(
      INonfungiblePositionManager.MintParams({
        token0: params.token0,
        token1: params.token1,
        fee: params.fee,
        tickLower: params.tickLower,
        tickUpper: params.tickUpper,
        amount0Desired: amount0V2ToMigrate,
        amount1Desired: amount1V2ToMigrate,
        amount0Min: params.amount0Min,
        amount1Min: params.amount1Min,
        recipient: params.recipient,
        deadline: params.deadline
      })
    );

    // if necessary, clear allowance and refund dust
    if (amount0V3 < amount0V2) {
      if (amount0V3 < amount0V2ToMigrate) {
        TransferHelper.safeApprove(params.token0, nonfungiblePositionManager, 0);
      }

      uint256 refund0 = amount0V2 - amount0V3;
      if (params.refundAsETH && params.token0 == WETH9) {
        IWETH9(WETH9).withdraw(refund0);
        TransferHelper.safeTransferETH(msg.sender, refund0);
      } else {
        TransferHelper.safeTransfer(params.token0, msg.sender, refund0);
      }
    }
    if (amount1V3 < amount1V2) {
      if (amount1V3 < amount1V2ToMigrate) {
        TransferHelper.safeApprove(params.token1, nonfungiblePositionManager, 0);
      }

      uint256 refund1 = amount1V2 - amount1V3;
      if (params.refundAsETH && params.token1 == WETH9) {
        IWETH9(WETH9).withdraw(refund1);
        TransferHelper.safeTransferETH(msg.sender, refund1);
      } else {
        TransferHelper.safeTransfer(params.token1, msg.sender, refund1);
      }
    }
  }
```

In the code snippet above:
1. During call to migrate, the intention is to transfer the position from the caller to the v3Migrator contract and then burn the position from the v3Migrator contract before minting a new position to the caller in the v3 pool
2. However, since the transfer of the position was from the caller to the v2 token pair address, the subsequent burn operation will fail and thus migration will not work
## Recommended Mitigation Steps
Replace the transfer logic with the below diff:

```diff
- TransferHelper.safeTransferFrom(params.pair, msg.sender, params.pair, params.liquidityToMigrate);

+ TransferHelper.safeTransferFrom(params.pair, msg.sender, address(this), params.liquidityToMigrate);
```






## Assessed type

ERC20