#!/bin/bash
# BOZAGENTIC PoC Project Generator v1.0
# Usage: ./generate_poc.sh <contract_name> <contract_address> <vuln_type>

NAME=${1:-"Target"}
ADDR=${2:-"0x0000000000000000000000000000000000000000"}
TYPE=${3:-"reentrancy"}

PROJECT_DIR="./poc_${NAME}"
mkdir -p "$PROJECT_DIR/src" "$PROJECT_DIR/test" "$PROJECT_DIR/script"

cat > "$PROJECT_DIR/foundry.toml" << TOMLEOF
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.23"
optimizer = true
optimizer_runs = 200

[fuzz]
runs = 10000
max_test_rejects = 65536

[invariant]
runs = 1000
depth = 100
TOMLEOF

cat > "$PROJECT_DIR/test/PoC.t.sol" << SOLEOF
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import "forge-std/Test.sol";

/// @title PoC: ${TYPE} on ${NAME}
/// @target ${ADDR}
contract PoC is Test {
    address constant TARGET = ${ADDR};
    address attacker = address(0xDEAD);
    
    function setUp() public {
        vm.deal(attacker, 1000 ether);
    }
    
    function test_${TYPE}() public {
        vm.startPrank(attacker);
        // Step 1: Setup attack conditions
        // Step 2: Execute attack
        // Step 3: Verify profit/impact
        vm.stopPrank();
    }
    
    function test_invariant() public {
        // Invariant that should hold but is violated
    }
}
SOLEOF

cat > "$PROJECT_DIR/echidna.yaml" << YAMLEOF
testMode: assertion
testLimit: 50000
seqLen: 100
corpusDir: "corpus"
coverage: true
YAMLEOF

cat > "$PROJECT_DIR/script/Attack.s.sol" << SCRIPTEOF
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
SCRIPTEOF

echo "PoC project generated: $PROJECT_DIR"
echo "  foundry.toml"
echo "  test/PoC.t.sol"
echo "  echidna.yaml"
echo "  script/Attack.s.sol"
echo ""
echo "Next steps:"
echo "  1. cd $PROJECT_DIR && forge install foundry-rs/forge-std"
echo "  2. Edit test/PoC.t.sol with actual attack logic"
echo "  3. forge test -vvv"
echo "  4. echidna test/PoC.t.sol --config echidna.yaml"
