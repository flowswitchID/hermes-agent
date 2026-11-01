// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import {EIP712} from "solady/utils/EIP712.sol";
import {LibClone} from "solady/utils/LibClone.sol";
import {MultiOwnable} from "smart-wallet/src/MultiOwnable.sol";
import {SignatureCheckerLib} from "solady/utils/SignatureCheckerLib.sol";

import {RecoverySigner} from "./RecoverySigner.sol";

contract RecoverySignerFactory is EIP712 {
    error RecoverySignerMustBeOwner();
    error InvalidSignature();

    event RecoverySignerDeployed(MultiOwnable account, address guardian);

    bytes32 constant MESSAGE_TYPEHASH = keccak256("RecoverySignerFactory(address account)");
    RecoverySigner immutable implementation;

    constructor(RecoverySigner implementation_) {
        implementation = implementation_;
    }

    function createRecoverySigner(MultiOwnable account, address guardian, bytes calldata guardianSignature) external returns (address) {
        return _deploy(account, guardian, guardianSignature);
    }

    function createRecoverySignerAndCall(MultiOwnable account, address guardian, bytes calldata guardianSignature, bytes calldata data)
        external
        returns (bytes memory)
    {
        address signer = _deploy(account, guardian, guardianSignature);
        (bool success, bytes memory result) = signer.call(data);
        if (!success) {
            assembly ("memory-safe") {
                revert(add(result, 32), mload(result))
            }
        }
        return result;
    }

    function getRecoverySignerAddress(address guardian) external view returns (address) {
        return LibClone.predictDeterministicAddress({
            implementation: address(implementation),
            salt: _computeSalt(guardian),
            deployer: address(this)
        });
    }

    /// @dev EIP-712 hashStruct
    function hashStruct(address account) public view returns (bytes32) {
        return _hashTypedData(keccak256(abi.encode(MESSAGE_TYPEHASH, account)));
    }

    function _deploy(MultiOwnable account, address guardian, bytes calldata guardianSignature) internal returns (address signer) {
        signer = LibClone.cloneDeterministic({implementation: address(implementation), salt: _computeSalt(guardian)});

        if (!account.isOwnerAddress(signer)) {
            revert RecoverySignerMustBeOwner();
        }

        bytes32 hash = hashStruct(address(account));

        // Ensure guardian intends to serve this account
        if (!SignatureCheckerLib.isValidSignatureNowCalldata(guardian, hash, guardianSignature)) {
            revert InvalidSignature();
        }

        RecoverySigner(signer).initialize(account, guardian);

        emit RecoverySignerDeployed(account, guardian);
    }

    function _computeSalt(address guardian) internal pure returns (bytes32) {
        return keccak256(abi.encode(guardian));
    }

    function _domainNameAndVersion() internal view override returns (string memory name, string memory version) {
        name = "Coinbase Smart Wallet Recovery Signer Factory";
        version = "1";
    }
}
