# Kiln V1 — Missing Zero-Address Validation in deactivateOperator / activateOperator

**Severity:** MEDIUM
**Contract:** StakingContract.sol
**Functions:** deactivateOperator(uint256, address), activateOperator(uint256, address)
**Submitted to:** Kiln Bug Bounty / Cantina / Code4rena

---

## Summary

The admin-only functions `deactivateOperator` and `activateOperator` accept an address parameter for the temporary / new fee recipient without calling the protocol's `_checkAddress()` validator. As a result, an admin (or a compromised admin) can set the operator's fee recipient to `address(0)`, after which every future `operatorFee` distribution is sent to a non-existent recipient and the ETH is permanently burned.

## Bug Details

### Vulnerable Code

File: `StakingContract.sol`

```solidity
// line 482 — deactivateOperator
function deactivateOperator(uint256 _operatorIndex, address _temporaryFeeRecipient) external onlyAdmin {
    StakingContractStorageLib.OperatorsSlot storage operators = StakingContractStorageLib.getOperators();
    operators.value[_operatorIndex].limit = 0;
    emit ChangedOperatorLimit(_operatorIndex, 0);
    operators.value[_operatorIndex].deactivated = true;
    emit DeactivatedOperator(_operatorIndex);
    operators.value[_operatorIndex].feeRecipient = _temporaryFeeRecipient;   // <-- no _checkAddress
    emit ChangedOperatorAddresses(_operatorIndex, operators.value[_operatorIndex].operator, _temporaryFeeRecipient);
    _updateAvailableValidatorCount(_operatorIndex);
}

// line 496 — activateOperator
function activateOperator(uint256 _operatorIndex, address _newFeeRecipient) external onlyAdmin {
    StakingContractStorageLib.OperatorsSlot storage operators = StakingContractStorageLib.getOperators();
    operators.value[_operatorIndex].deactivated = false;
    emit ActivatedOperator(_operatorIndex);
    operators.value[_operatorIndex].feeRecipient = _newFeeRecipient;       // <-- no _checkAddress
    emit ChangedOperatorAddresses(_operatorIndex, operators.value[_operatorIndex].operator, _newFeeRecipient);
}
```

### Reference (functions that DO validate)

```solidity
// line 412 — setOperatorAddresses HAS the check
function setOperatorAddresses(uint256 _operatorIndex, address _operatorAddress, address _feeRecipientAddress) external onlyActiveOperatorFeeRecipient(_operatorIndex) {
    _checkAddress(_operatorAddress);
    _checkAddress(_feeRecipientAddress);
    ...
}

// line 954 — _checkAddress implementation
function _checkAddress(address _address) internal pure {
    if (_address == address(0)) {
        revert InvalidZeroAddress();
    }
}
```

The protocol already has a `_checkAddress()` helper that reverts with `InvalidZeroAddress()` for `address(0)`. It is used in 7 other places (initialize_1, setOperatorAddresses, setWithdrawer), but `deactivateOperator` and `activateOperator` forget to call it. `setTreasury` has the same omission.

## Attack Path

Setup: an admin who is compromised, malicious, or simply makes a UI mistake.

1. Admin calls `deactivateOperator(0, address(0))`.
   - The `require(address(0) != 0)` is missing, so the tx does not revert.
   - `operators.value[0].feeRecipient` is now permanently set to `address(0)`.

2. Validators exit on the beacon chain. The CL FeeRecipient accumulates rewards and triggers `dispatch()`.

3. `ConsensusLayerFeeDispatcher.dispatch()` (and `ExecutionLayerFeeDispatcher.dispatch()`) compute:

   ```
   operatorFee = (globalFee * operatorFeeBPS) / 10000
   ...
   operator.call{value: operatorFee}("");
   ```

4. With `operator == address(0)`, the low-level `call` succeeds (the EVM treats the zero address as an EOA that accepts ETH) but the ETH is permanently locked. There is no private key for `address(0)`, so the funds are unrecoverable.

Result: every future withdrawal burns the operator's share of the fee. Over time the cumulative loss grows with rewards.

## Impact

- Loss vector: future operator fee revenue, permanently burned.
- Not a direct rug-pull (admin-only), but a permanent value sink.
- Misconfiguration by a well-meaning admin has the same outcome as a malicious admin — there is no revert at the call site to catch the error.
- The same pattern in `setTreasury` means a similar mistake there could brick all fee distribution (treasury gets burned, operator still paid).

## Proof of Concept

Foundry test, two proofs passing:

```solidity
[PASS] test_DeactivateOperator_WithZeroAddress_NotReverting()
[PASS] test_ActivateOperator_WithZeroAddress_NotReverting()
```

Test file: `audits/kiln-v1/test/ZeroAddressFeeRecipientPoC.t.sol`

Run:

```bash
forge test --match-contract ZeroAddressFeeRecipientPoC -vv
```

The PoC deploys the StakingContract via direct `initialize_1` (skipping the TUPProxy because the audit focus is the staking logic, not the proxy), then calls `deactivateOperator(0, address(0))` and asserts that:

- The tx does not revert (it should, per the protocol's input-validation policy).
- `operators.value[0].feeRecipient` is now `address(0)`.
- A subsequent fee distribution would send ETH to `address(0)`.

## Recommended Fix

Add `_checkAddress` to both functions:

```solidity
function deactivateOperator(uint256 _operatorIndex, address _temporaryFeeRecipient) external onlyAdmin {
    _checkAddress(_temporaryFeeRecipient);  // <-- add
    ...
}

function activateOperator(uint256 _operatorIndex, address _newFeeRecipient) external onlyAdmin {
    _checkAddress(_newFeeRecipient);        // <-- add
    ...
}
```

Same fix should be applied to `setTreasury` (line 214).

## Affected Files

- `StakingContract.sol` — 3 functions affected: `deactivateOperator`, `activateOperator`, `setTreasury`.
