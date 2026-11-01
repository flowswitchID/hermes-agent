// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import "forge-std/Script.sol";

contract AttackScript is Script {
    function run() external {
        vm.startBroadcast();
        // Attack execution
        vm.stopBroadcast();
    }
}
