# #89: Permission roles of AuraVault.sol cannot be set
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', 'upgraded by judge', ':robot:_primary', ':robot:_93_group', 'duplicate-174']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/reward/EligibilityDataProvider.sol#L187-L191


# Vulnerability details


## Impact

Permission roles of AuraVault.sol cannot be set. There is a `VAULT_CONFIG_ROLE` and `VAULT_ADMIN_ROLE` role in the contract, but since no one has the `DEFAULT_ADMIN_ROLE`, it cannot be set.

## Bug Description

There is no admin to AuraVault contract, and no one can call `setParameter()` or `setVaultConfig()` to modify the parameters.

```solidity
    constructor(
        address rewardPool_,
        address asset_,
        address feed_,
        address auraPriceOracle_,
        uint32 maxClaimerIncentive_,
        uint32 maxLockerIncentive_,
        string memory tokenName_,
        string memory tokenSymbol_
    ) ERC4626(IERC20(asset_)) ERC20(tokenName_, tokenSymbol_) {
        rewardPool = rewardPool_;
        feed = feed_;
        auraPriceOracle = auraPriceOracle_;
        maxClaimerIncentive = maxClaimerIncentive_;
        maxLockerIncentive = maxLockerIncentive_;
    }

    /*//////////////////////////////////////////////////////////////
                             CONFIGURATION
    //////////////////////////////////////////////////////////////*/

    /// @notice Sets various variables for this contract
    /// @dev Sender has to be allowed to call this method
    /// @param parameter Name of the variable to set
    /// @param data New value to set for the variable [wad]
>   function setParameter(bytes32 parameter, uint256 data) external onlyRole(VAULT_CONFIG_ROLE) {
        if (parameter == "feed") feed = address(uint160(data));
        else if (parameter == "auraPriceOracle") auraPriceOracle = address(uint160(data));
        else revert AuraVault__setParameter_unrecognizedParameter();
        emit SetParameter(parameter, data);
    }

    function setVaultConfig(
        uint32 _claimerIncentive,
        uint32 _lockerIncentive,
        address _lockerRewards
>   ) public onlyRole(VAULT_ADMIN_ROLE) returns (bool) {
        if (_claimerIncentive > maxClaimerIncentive) revert AuraVault__setVaultConfig_invalidClaimerIncentive();
        if (_lockerIncentive > maxLockerIncentive) revert AuraVault__setVaultConfig_invalidLockerIncentive();
        if (_lockerRewards == address(0x0)) revert AuraVault__setVaultConfig_invalidLockerRewards();

        vaultConfig = VaultConfig({
            claimerIncentive: _claimerIncentive,
            lockerIncentive: _lockerIncentive,
            lockerRewards: _lockerRewards
        });

        return true;
    }
```

## Proof of Concept

N/A

## Tools Used

Manual Review

## Recommended Mitigation Steps

Grant the contract creator the admin role.


## Assessed type

Access Control