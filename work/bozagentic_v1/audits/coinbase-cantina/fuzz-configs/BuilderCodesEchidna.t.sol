// SPDX-License-Identifier: MIT
pragma solidity ^0.8.29;

import {BuilderCodes} from "../../src/BuilderCodes.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract BuilderCodesEchidna {
    BuilderCodes public codes;
    uint256 public mintCount;
    
    constructor() {
        BuilderCodes impl = new BuilderCodes();
        bytes memory initData = abi.encodeCall(
            BuilderCodes.initialize,
            (address(this), address(this), "test://")
        );
        ERC1967Proxy proxy = new ERC1967Proxy(address(impl), initData);
        codes = BuilderCodes(address(proxy));
        codes.grantRole(codes.REGISTER_ROLE(), address(this));
    }
    
    function registerAndCheck(string memory code, address owner, address payout) external {
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
        
        uint256 tokenId = codes.toTokenId(code);
        assert(codes.ownerOf(tokenId) == owner);
        assert(codes.payoutAddress(tokenId) == payout);
        assert(codes.isRegistered(code));
    }
    
    function echidna_no_zero_owner() external view returns (bool) {
        for (uint256 i = 1; i <= mintCount && i <= 10; i++) {
            try codes.ownerOf(i) returns (address owner) {
                if (owner == address(0)) return false;
            } catch {}
        }
        return true;
    }
}
