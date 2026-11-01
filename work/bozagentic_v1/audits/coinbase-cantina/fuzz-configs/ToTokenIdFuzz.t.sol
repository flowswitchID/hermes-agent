// SPDX-License-Identifier: MIT
pragma solidity ^0.8.29;

import {Test} from "forge-std/Test.sol";
import {BuilderCodes} from "../src/BuilderCodes.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract ToTokenIdFuzz is Test {
    BuilderCodes codes;
    
    function setUp() public {
        BuilderCodes impl = new BuilderCodes();
        bytes memory initData = abi.encodeCall(
            BuilderCodes.initialize,
            (address(this), address(this), "test://")
        );
        ERC1967Proxy proxy = new ERC1967Proxy(address(impl), initData);
        codes = BuilderCodes(address(proxy));
    }
    
    // Generate valid alphanumeric code from seed
    function _validCode(uint256 seed) internal pure returns (string memory) {
        uint256 len = (seed % 30) + 1; // 1-30 chars
        bytes memory b = new bytes(len);
        for (uint i = 0; i < len; i++) {
            uint8 c = uint8((seed >> (i * 8)) % 36);
            if (c < 10) b[i] = bytes1(c + 48); // 0-9
            else b[i] = bytes1(c - 10 + 97);   // a-z
        }
        return string(b);
    }
    
    /// @dev Fuzz: toTokenId and toCode roundtrip for valid codes
    function testFuzz_roundtrip(uint256 seed) public view {
        string memory code = _validCode(seed);
        uint256 tokenId = codes.toTokenId(code);
        string memory recovered = codes.toCode(tokenId);
        assertEq(keccak256(bytes(code)), keccak256(bytes(recovered)));
    }
    
    /// @dev Fuzz: different valid codes → different tokenIds
    function testFuzz_no_collision(uint256 seed1, uint256 seed2) public view {
        string memory code1 = _validCode(seed1);
        string memory code2 = _validCode(seed2);
        if (keccak256(bytes(code1)) == keccak256(bytes(code2))) return;
        
        uint256 id1 = codes.toTokenId(code1);
        uint256 id2 = codes.toTokenId(code2);
        assertTrue(id1 != id2, "COLLISION!");
    }
    
    /// @dev Fuzz: tokenId always non-zero
    function testFuzz_nonzero(uint256 seed) public view {
        string memory code = _validCode(seed);
        assertTrue(codes.toTokenId(code) != 0);
    }
    
    /// @dev Fuzz: isValidCode accepts all alphanumeric
    function testFuzz_isValid(uint256 seed) public view {
        string memory code = _validCode(seed);
        assertTrue(codes.isValidCode(code));
    }
    
    /// @dev Edge case: trailing zeros in bytes
    function test_trailing_zeros() public view {
        // "a" vs "a\x00" — but \x00 is invalid, so skip
        // Instead test: "ab" vs "ba" — must be different
        uint256 id1 = codes.toTokenId("ab");
        uint256 id2 = codes.toTokenId("ba");
        assertTrue(id1 != id2);
        
        // "a" vs "aa" — must be different
        uint256 id3 = codes.toTokenId("a");
        uint256 id4 = codes.toTokenId("aa");
        assertTrue(id3 != id4);
    }
}
