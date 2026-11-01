# #5: The protocol has not charged the protocol fee.
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_20_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-08-wildcat/blob/fe746cc0fbedc4447a981a50e6ba4c95f98b9fe1/src/libraries/MarketState.sol#L15


# Vulnerability details

## Proof of Concept
The protocol has set `accruedProtocolFees` to represent the current protocol fees and `protocolFeeBips` to represent the protocol fee rate. 
```solidity
struct MarketState {
  bool isClosed;
  uint128 maxTotalSupply;
  uint128 accruedProtocolFees;
  // Underlying assets reserved for withdrawals which have been paid
  // by the borrower but not yet executed.
  uint128 normalizedUnclaimedWithdrawals;
  // Scaled token supply (divided by scaleFactor)
  uint104 scaledTotalSupply;
  // Scaled token amount in withdrawal batches that have not been
  // paid by borrower yet.
  uint104 scaledPendingWithdrawals;
  uint32 pendingWithdrawalExpiry;
  // Whether market is currently delinquent (liquidity under requirement)
  bool isDelinquent;
  // Seconds borrower has been delinquent
  uint32 timeDelinquent;
  // Fee charged to borrowers as a fraction of the annual interest rate
  uint16 protocolFeeBips;
  // Annual interest rate accrued to lenders, in basis points
  uint16 annualInterestBips;
  // Percentage of outstanding balance that must be held in liquid reserves
  uint16 reserveRatioBips;
  // Ratio between internal balances and underlying token amounts
  uint112 scaleFactor;
  uint32 lastInterestAccruedTimestamp;
}
```
It also has related functions set up to update protocolFeeBips and collet protocol fee
github:[https://github.com/code-423n4/2024-08-wildcat/blob/fe746cc0fbedc4447a981a50e6ba4c95f98b9fe1/src/market/WildcatMarketConfig.sol#L164](https://github.com/code-423n4/2024-08-wildcat/blob/fe746cc0fbedc4447a981a50e6ba4c95f98b9fe1/src/market/WildcatMarketConfig.sol#L164)
```solidity
  function setProtocolFeeBips(
    uint16 _protocolFeeBips
  ) external nonReentrant sphereXGuardExternal {
    if (msg.sender != factory) revert_NotFactory();
    if (_protocolFeeBips > 1_000) revert_ProtocolFeeTooHigh();
    MarketState memory state = _getUpdatedState();
    if (state.isClosed) revert_ProtocolFeeChangeOnClosedMarket();
    if (_protocolFeeBips == state.protocolFeeBips) revert_ProtocolFeeNotChanged();
    hooks.onSetProtocolFeeBips(_protocolFeeBips, state);
    state.protocolFeeBips = _protocolFeeBips;
    emit ProtocolFeeBipsUpdated(_protocolFeeBips);
    _writeState(state);
  }

```
```solidity
  /**
   * @dev Withdraw available protocol fees to the fee recipient.
   */
  function collectFees() external nonReentrant sphereXGuardExternal {
    MarketState memory state = _getUpdatedState();
    if (state.accruedProtocolFees == 0) revert_NullFeeAmount();

    uint128 withdrawableFees = state.withdrawableProtocolFees(totalAssets());
    if (withdrawableFees == 0) revert_InsufficientReservesForFeeWithdrawal();

    state.accruedProtocolFees -= withdrawableFees;
    asset.safeTransfer(feeRecipient, withdrawableFees);
    _writeState(state);
    emit_FeesCollected(withdrawableFees);
  }
```
However, there is no part of the protocol execution where the protocol fees are calculated, which will result in the protocol never being able to collect any fees.
## Recommended Mitigation Steps
Update the calculation of the protocol fee.



## Assessed type

Other