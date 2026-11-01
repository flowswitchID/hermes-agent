# #578: Upgraded Q -> 2 from #545 [1730294682585]
Labels: ['3 (High Risk)', 'satisfactory', 'upgraded by judge', 'duplicate-401']
Accepted: False

Judge has assessed an item in Issue #545 as 2 risk. The relevant finding follows:

 [L-01] Potential over-distribution of rewards in claim function
The claim function in the AuraVault contract may lead to over-distribution of rewards due to incorrect handling of incentives. The function calculates amountIn using _previewReward(amounts[0], amounts[1], _config), which already considers the incentives. However, when distributing the rewards, the incentives are applied again, leading to potential over-distribution.

Relevant code:


function claim(uint256[] memory amounts, uint256 maxAmountIn) external returns (uint256 amountIn) {
    // Claim rewards from Aura reward pool
    IPool(rewardPool).getReward();

    // Compute assets amount to be sent to the Vault
    VaultConfig memory _config = vaultConfig;
    amountIn = _previewReward(amounts[0], amounts[1], _config);

    // Transfer assets to Vault
    require(amountIn <= maxAmountIn, "!Slippage");
    IERC20(asset()).safeTransferFrom(msg.sender, address(this), amountIn);

    // Compound assets into "asset" balance
    IERC20(asset()).safeApprove(rewardPool, amountIn);
    IPool(rewardPool).deposit(amountIn, address(this));

    // Distribute BAL rewards
    IERC20(BAL).safeTransfer(_config.lockerRewards, (amounts[0] * _config.lockerIncentive) / INCENTIVE_BASIS);
    IERC20(BAL).safeTransfer(msg.sender, amounts[0]);

    // Distribute AURA rewards
    if (block.timestamp <= INFLATION_PROTECTION_TIME) {
        IERC20(AURA).safeTransfer(_config.lockerRewards, (amounts[1] * _config.lockerIncentive) / INCENTIVE_BASIS);
        IERC20(AURA).safeTransfer(msg.sender, amounts[1]);
    } else {
        // after INFLATION_PROTECTION_TIME
        IERC20(AURA).safeTransfer(_config.lockerRewards, IERC20(AURA).balanceOf(address(this)));
    }

    emit Claimed(msg.sender, amounts[0], amounts[1], amountIn);
}
Recommendation: