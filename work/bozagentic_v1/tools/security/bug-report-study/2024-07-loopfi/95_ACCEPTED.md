# #95: Debt position interest is compounded while pool interest is simple causing inconsistency b/w `expectedLiquidity_` and `availableLiquidity_`
Labels: ['bug', '3 (High Risk)', 'primary issue', 'satisfactory', 'selected for report', 'sponsor acknowledged', 'sufficient quality report', 'upgraded by judge', ':robot:_primary', ':robot:_130_group', 'H-10']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/CDPVault.sol#L478


# Vulnerability details

## Impact
Borrower's will mostly end up paying more than the required amount of interest. This can also lead to lowered borrowing interest rates and final withdrawals to revert due to the inconsistency b/w the expected interest amount and the actually paid interest amount

## Proof of Concept
The interest associated with a debt is calculated both in the pool and the user's debt position. But the used method for calculation leads to different values b/w the pool and the debt position, in the pool it is simple linear interest, while for the debt position, the interest gets compounded

In the pool the interest is calculated as `borrowed * interestRate * (elapsedTime/365 days)`

[link](https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/PoolV3.sol#L671-L673)
```solidity
    function _calcBaseInterestAccrued(uint256 timestamp) private view returns (uint256) {
        return (_totalDebt.borrowed * baseInterestRate().calcLinearGrowth(timestamp)) / RAY;
    }
```

In the CDP vault (ie. user's debt position), the interest is calculated as `debt * interestIndexNow / interestIndexPast - debt`.

[link](https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/CDPVault.sol#L478)
```solidity
    function _calcDebt(Position memory position) internal view returns (DebtData memory cdd) {
        
        ....

        cdd.accruedInterest = CreditLogic.calcAccruedInterest(cdd.debt, cdd.cumulativeIndexLastUpdate, index);
```

[link](https://github.com/Gearbox-protocol/core-v3/blob/832fe64d7194ad74b93543b1314da38aa6d413ea/contracts/libraries/CreditLogic.sol#L31-L38)
```solidity
    function calcAccruedInterest(uint256 amount, uint256 cumulativeIndexLastUpdate, uint256 cumulativeIndexNow)
        internal
        pure
        returns (uint256)
    {
        if (amount == 0) return 0;
        return (amount * cumulativeIndexNow) / cumulativeIndexLastUpdate - amount; // U:[CL-1]
    }
``` 

Where the `interestIndex` is updated as follows:

[link](https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/PoolV3.sol#L676-L678)
```solidity
    function _calcBaseInterestIndex(uint256 timestamp) private view returns (uint256) {
        return (_baseInterestIndexLU * (RAY + baseInterestRate().calcLinearGrowth(timestamp))) / RAY;
    }
```

Hence the `interestIndex` gets compounded with every invocation of `_calcBaseInterestIndex`, eventually causing a higher interest for the debt position when compared with the pool calculation. This also causes incorrectness b/w `expectedLiquidity_` and `availableLiquidity_` (ie. expectedLiquidity_ will be less than availableLiquidity_).

The correct relation b/w `expectedLiquidity_` and `availableLiquidity_` is required for `_updateBaseInterest` which is used throughout the contract for purposes like withdrawals

```solidity
    function _withdraw(
        address receiver,
        address owner,
        uint256 assetsSent,
        uint256 assetsReceived,
        uint256 amountToUser,
        uint256 shares
    ) internal {
        if (msg.sender != owner) _spendAllowance({owner: owner, spender: msg.sender, amount: shares}); // U:[LP-8,9]
        _burn(owner, shares); // U:[LP-8,9]


        _updateBaseInterest({
            expectedLiquidityDelta: -assetsSent.toInt256(),
            availableLiquidityDelta: -assetsSent.toInt256(),
            checkOptimalBorrowing: false
        }); // U:[LP-8,9]
```

If the associated shares with the excess interest are withdrawn, it will cause an underflow for `expectedLiquidity` during final withdrawals

### POC Code
Apply the following diff and run `forge test --mt testHash_CompoundingVsSimpleInterest`. It is asserted that the calculated interest in the position is more than in the pool and that final withdrawals can revert due to this. The `minRate == 0` check in GaugeV3 contract is commented out inorder to keep quotaInterest to 0 so that the only interest being accrued is the base interest, which will make it easier for displaying the difference in its calculation

```solidity
diff --git a/src/quotas/GaugeV3.sol b/src/quotas/GaugeV3.sol
index e16d6dc..00574a9 100644
--- a/src/quotas/GaugeV3.sol
+++ b/src/quotas/GaugeV3.sol
@@ -303,9 +303,9 @@ contract GaugeV3 is IGaugeV3, ACLNonReentrantTrait {
 
     /// @dev Checks that given min and max rate are correct (`0 < minRate <= maxRate`)
     function _checkParams(uint16 minRate, uint16 maxRate) internal pure {
-        if (minRate == 0 || minRate > maxRate) {
-            revert IncorrectParameterException(); // U:[GA-04]
-        }
+        // if (minRate == 0 || minRate > maxRate) {
+        //     revert IncorrectParameterException(); // U:[GA-04]
+        // }
     }
 
     /// @notice Whether token is added to the gauge as quoted
diff --git a/src/test/unit/CDPVault.t.sol b/src/test/unit/CDPVault.t.sol
index 85c82ca..6e324a1 100644
--- a/src/test/unit/CDPVault.t.sol
+++ b/src/test/unit/CDPVault.t.sol
@@ -166,6 +166,81 @@ contract CDPVaultTest is TestBase {
         assertEq(credit, 50 ether);
     }
 
+    function HashCreateGaugeAndSetGauge(address vault) internal virtual {
+        address token_ = address(CDPVault(vault).token());
+        HashCreateGaugeAndSetGauge(vault, token_);
+    }
+
+    function HashCreateGaugeAndSetGauge(address vault, address token_) internal virtual {
+        quotaKeeper.setCreditManager(address(token_), address(vault));
+        if (!gauge.isTokenAdded(address(token_))) {
+            gauge.addQuotaToken(address(token_), 0, 1);
+        }
+        gauge.setFrozenEpoch(false);
+        vm.warp(block.timestamp + 1 weeks);
+        vm.prank(address(gauge));
+        quotaKeeper.updateRates();
+    }
+
+    function testHash_CompoundingVsSimpleInterest() public {
+        CDPVault vault = createCDPVault(token, 100 ether, 10 ether, 1.25 ether, 1.0 ether, 0);
+        // the qouta interest is set to 0
+        HashCreateGaugeAndSetGauge(address(vault));
+        token.mint(address(this), 100 ether);
+        token.approve(address(vault), 100 ether);
+        address position = address(new PositionOwner(vault));
+        vault.deposit(position, 100 ether);
+
+        uint quotaRevenue = liquidityPool.quotaRevenue();
+        assert(quotaRevenue == 0);
+
+        uint initialExpectedAmount = liquidityPool.expectedLiquidity();
+
+        vault.borrow(address(this), position, 50 ether);
+
+        // first interest index update
+        vm.warp(block.timestamp + 1 days);
+        liquidityPool.deposit(0,address(this));
+        // second interest index update
+        vm.warp(block.timestamp + 1 days);
+        liquidityPool.deposit(0,address(this));
+
+        // quota revenue is 0
+        quotaRevenue = liquidityPool.quotaRevenue();
+        assert(quotaRevenue == 0);
+        
+        uint newExpectedAmount = liquidityPool.expectedLiquidity();
+        uint poolAccruedInterest = newExpectedAmount - initialExpectedAmount;
+
+        (uint256 debt, uint256 positionAccruedInterest, uint256 cumulativeQuotaInterest)=vault.getDebtInfo(position);
+        
+        assert(debt == 50 ether);
+        assert(cumulativeQuotaInterest == 0);
+        assert(positionAccruedInterest > poolAccruedInterest);
+
+        // this additional interest will is not accounted in the expected interest
+
+        mockWETH.mint(address(this), debt + positionAccruedInterest);
+        mockWETH.approve(address(vault), debt + positionAccruedInterest);
+        vault.repay(address(this),position,debt + positionAccruedInterest);
+
+        // attempt to withdraw all the tokens from the pool will revert since the expectedAmount will underflow
+        {
+        liquidityPool.setLock(false);
+        uint balTreasury = liquidityPool.balanceOf(treasury);
+        uint balThis = liquidityPool.balanceOf(address(this));
+        assert(balTreasury + balThis == liquidityPool.totalSupply());
+
+        vm.prank(treasury);
+        liquidityPool.withdraw(balTreasury,treasury,treasury);
+
+        vm.expectRevert("SafeCast: value must be positive");
+        liquidityPool.withdraw(balThis,address(this),address(this));
+        }
+        
+
+    }
+
     function test_modifyCollateralAndDebt_depositCollateralAndDrawDebt() public {
         CDPVault vault = createCDPVault(token, 150 ether, 0, 1.25 ether, 1.0 ether, 0);
         createGaugeAndSetGauge(address(vault));

```
## Tools Used
Manual Review

## Recommended Mitigation Steps
Change the index updation to align with the pool calculation ie. interestIndex = prevInterestIndex + baseInterest * timeElapsed


## Assessed type

Math