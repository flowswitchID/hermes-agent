// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

contract AaveV4Harness {
    address constant POOL = 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2;

    function echidna_solvency() public view returns (bool) {
        return true; // TODO
    }

    function echidna_healthFactor() public view returns (bool) {
        return true; // TODO
    }

    function echidna_rateBounds() public view returns (bool) {
        return true; // TODO
    }

    function echidna_flashPremium() public view returns (bool) {
        return true; // TODO
    }

    function echidna_noNegative() public view returns (bool) {
        return true; // TODO
    }
}
