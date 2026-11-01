// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import {Multicallable} from "solady/utils/Multicallable.sol";
import {EIP712} from "solady/utils/EIP712.sol";
import {SignatureCheckerLib} from "solady/utils/SignatureCheckerLib.sol";
import {MultiOwnable} from "smart-wallet/src/MultiOwnable.sol";

contract RecoverySigner is Multicallable, EIP712 {
    error AlreadyInitialized();
    error InvalidNonce(uint256 expectedNonce, uint256 actualNonce);
    error InvalidSignature();
    error SelfRemoval();

    bytes32 constant MESSAGE_TYPEHASH = keccak256("RecoverySigner(bytes4 selector,bytes data,uint256 nonce)");
    address public guardian;
    MultiOwnable public account;
    uint256 public nextNonce;

    /// @dev Disables initialization of the implementation contract.
    constructor() {
        guardian = address(1);
    }

    function initialize(MultiOwnable account_, address guardian_) external {
        if (guardian != address(0)) {
            revert AlreadyInitialized();
        }
        guardian = guardian_;
        account = account_;
    }

    function addOwnerAddress(address owner, uint256 nonce, bytes calldata signature) external {
        _checkSignature({
            selector: MultiOwnable.addOwnerAddress.selector,
            data: abi.encode(owner),
            nonce: nonce,
            signature: signature
        });

        account.addOwnerAddress(owner);
    }

    function addOwnerPublicKey(bytes32 x, bytes32 y, uint256 nonce, bytes calldata signature) external {
        _checkSignature({
            selector: MultiOwnable.addOwnerPublicKey.selector,
            data: abi.encode(x, y),
            nonce: nonce,
            signature: signature
        });

        account.addOwnerPublicKey(x, y);
    }

    function removeOwnerAtIndex(uint256 index, bytes calldata ownerBytes, uint256 nonce, bytes calldata signature)
        external
    {
        _checkSignature({
            selector: MultiOwnable.removeOwnerAtIndex.selector,
            data: abi.encode(index, ownerBytes),
            nonce: nonce,
            signature: signature
        });

        if (ownerBytes.length == 32 && address(uint160(uint256(bytes32(ownerBytes)))) == address(this)) {
            revert SelfRemoval();
        }

        account.removeOwnerAtIndex(index, ownerBytes);
    }

    function removeSelfAsOwner(uint256 index, uint256 nonce, bytes calldata signature) external {
        bytes memory ownerBytes = abi.encode(address(this));

        _checkSignature({
            selector: MultiOwnable.removeOwnerAtIndex.selector,
            data: abi.encode(index, ownerBytes),
            nonce: nonce,
            signature: signature
        });

        account.removeOwnerAtIndex(index, ownerBytes);
    }

    /// @dev EIP-712 hashStruct
    function hashStruct(bytes4 selector, bytes memory data, uint256 nonce) public view returns (bytes32) {
        return _hashTypedData(keccak256(abi.encode(MESSAGE_TYPEHASH, selector, keccak256(data), nonce)));
    }

    function _checkSignature(bytes4 selector, bytes memory data, uint256 nonce, bytes calldata signature) internal {
        bytes32 hash = hashStruct(selector, data, nonce);
        if (nextNonce != nonce) {
            revert InvalidNonce(nextNonce, nonce);
        }
        nextNonce += 1;
        if (!SignatureCheckerLib.isValidSignatureNowCalldata(guardian, hash, signature)) {
            revert InvalidSignature();
        }
    }

    function _domainNameAndVersion() internal pure override returns (string memory name, string memory version) {
        name = "Coinbase Smart Wallet Recovery Signer";
        version = "1";
    }
}
