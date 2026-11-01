// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "forge-std/Test.sol";

contract DeepBytecode is Test {
    address constant UACD = 0xb95712AC7Fbf54Ab3FD10C86FD1e9463C8461bf5;

    function setUp() public {
        vm.createSelectFork(vm.envString("ETH_RPC_URL"));
    }

    // Check: does deployed bytecode have any HIDDEN functions?
    function test_bytecode_analysis() public view {
        uint256 codeSize;
        assembly { codeSize := extcodesize(UACD) }
        console.log("Deployed bytecode size:", codeSize);

        // Get bytecode
        bytes memory code = new bytes(codeSize);
        assembly {
            extcodecopy(UACD, add(code, 32), 0, codeSize)
        }

        // Check for known function selectors
        // Standard ERC721 + custom functions
        bytes4[20] memory selectors = [
            bytes4(0x06fdde03), // name()
            bytes4(0x95d89b41), // symbol()
            bytes4(0xc87b56dd), // tokenURI(uint256)
            bytes4(0x70a08231), // balanceOf(address)
            bytes4(0x6352211e), // ownerOf(uint256)
            bytes4(0x42842e0e), // safeTransferFrom(address,address,uint256)
            bytes4(0xb88d4fde), // safeTransferFrom(address,address,uint256,bytes)
            bytes4(0x23b872dd), // transferFrom(address,address,uint256)
            bytes4(0x095ea7b3), // approve(address,uint256)
            bytes4(0xa22cb465), // setApprovalForAll(address,bool)
            bytes4(0x081812fc), // getApproved(uint256)
            bytes4(0xe985e9c5), // isApprovedForAll(address,address)
            bytes4(0x8da5cb5b), // owner()
            bytes4(0x715018a6), // renounceOwnership()
            bytes4(0xf2fde38b), // transferOwnership(address)
            bytes4(0x18160ddd), // totalSupply()
            bytes4(0xa0712d68), // mint(uint256) - standard mint selector
            bytes4(0x3ccfd60b), // withdraw()
            bytes4(0x5c975abb), // paused()
            bytes4(0xe8a3d485)  // contractURI()
        ];

        for (uint i = 0; i < selectors.length; i++) {
            bool found = false;
            for (uint j = 0; j < code.length - 4; j++) {
                if (code[j] == selectors[i][0] && code[j+1] == selectors[i][1] &&
                    code[j+2] == selectors[i][2] && code[j+3] == selectors[i][3]) {
                    found = true;
                    break;
                }
            }
            if (found) {
                console.log("Found selector:", vm.toString(selectors[i]));
            }
        }

        // Check for SELFDESTRUCT opcode (0xff)
        uint256 selfdestructCount = 0;
        for (uint j = 0; j < code.length; j++) {
            if (code[j] == 0xff) selfdestructCount++;
        }
        console.log("SELFDESTRUCT opcodes:", selfdestructCount);

        // Check for DELEGATECALL (0xf4) — could indicate hidden proxy
        uint256 delegatecallCount = 0;
        for (uint j = 0; j < code.length; j++) {
            if (code[j] == 0xf4) delegatecallCount++;
        }
        console.log("DELEGATECALL opcodes:", delegatecallCount);
    }

    // Check: any hidden storage slots?
    function test_storage_scan() public view {
        console.log("=== STORAGE SCAN ===");
        for (uint i = 0; i < 20; i++) {
            bytes32 val = vm.load(UACD, bytes32(i));
            if (uint256(val) != 0) {
                console.log("Slot", i);
                console.logBytes32(val);
            }
        }
    }

    // Check: constructor args from deployment
    function test_constructor_args() public view {
        // Read the last bytes of creation code for constructor args
        // The baseURI and contractURI are stored in storage
        // Slot 0-1: ERC721 name/symbol (packed)
        // Let's read storage to find URIs
        console.log("=== STORAGE VALUES ===");
        for (uint i = 0; i < 15; i++) {
            bytes32 val = vm.load(UACD, bytes32(i));
            if (uint256(val) != 0) {
                console.log("Slot", i);
                console.logBytes32(val);
            }
        }
    }
}
