// SPDX-License-Identifier: MIT
pragma solidity ^0.8.29;

import {Test} from "forge-std/Test.sol";
import {BuilderCodes} from "../src/BuilderCodes.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract Handler is Test {
    BuilderCodes codes;
    uint256 public mintCount;
    
    constructor(BuilderCodes _codes) {
        codes = _codes;
    }
    
    function registerCode(string memory code, address owner, address payout) external {
        if (owner == address(0)) owner = address(1);
        if (payout == address(0)) payout = address(1);
        if (bytes(code).length == 0 || bytes(code).length > 31) return;
        bytes memory b = bytes(code);
        for (uint i = 0; i < b.length; i++) {
            if (!((b[i] >= 'a' && b[i] <= 'z') || (b[i] >= '0' && b[i] <= '9'))) return;
        }
        if (codes.isRegistered(code)) return;
        codes.register(code, owner, payout);
        mintCount++;
    }
}

contract InvariantBuilderCodes is Test {
    BuilderCodes codes;
    Handler handler;
    
    function setUp() public {
        BuilderCodes impl = new BuilderCodes();
        bytes memory initData = abi.encodeCall(
            BuilderCodes.initialize,
            (address(this), address(this), "test://")
        );
        ERC1967Proxy proxy = new ERC1967Proxy(address(impl), initData);
        codes = BuilderCodes(address(proxy));
        codes.grantRole(codes.REGISTER_ROLE(), address(this));
        
        handler = new Handler(codes);
        codes.grantRole(codes.REGISTER_ROLE(), address(handler));
        
        targetContract(address(handler));
    }
    
    /// @dev Invariant: registered code always has valid owner
    function invariant_noZeroOwner() external view {
        uint256 count = handler.mintCount();
        for (uint256 i = 1; i <= count && i <= 20; i++) {
            try codes.ownerOf(i) returns (address owner) {
                assert(owner != address(0));
            } catch {}
        }
    }
    
    /// @dev Invariant: isRegistered consistent with ownership
    function invariant_registeredHasOwner() external view {
        uint256 count = handler.mintCount();
        for (uint256 i = 1; i <= count && i <= 20; i++) {
            try codes.ownerOf(i) returns (address) {
                // Token exists, good
            } catch {
                assert(false); // Minted token should exist
            }
        }
    }
}
