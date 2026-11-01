// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "forge-std/Test.sol";

contract DeepStorage is Test {
    address constant UACD = 0xb95712AC7Fbf54Ab3FD10C86FD1e9463C8461bf5;

    function setUp() public {
        vm.createSelectFork(vm.envString("ETH_RPC_URL"));
    }

    // Full storage dump — understand exact layout
    function test_storage_layout() public view {
        console.log("=== FULL STORAGE DUMP ===");
        // UACatsDivision storage layout:
        // Inherited from ERC721:
        //   slot 0: _name (string)
        //   slot 1: _symbol (string)
        //   slot 2: _owners mapping
        //   slot 3: _balances mapping
        //   slot 4: _tokenApprovals mapping
        //   slot 5: _operatorApprovals mapping
        // Inherited from Ownable:
        //   slot 6: _owner
        // Inherited from ReentrancyGuard:
        //   slot 7: _status
        // UACatsDivision:
        //   slot 8: _currentId
        //   slot 9: baseURI (string)
        //   slot 10: _contractURI (string)
        //   slot 11: saleIsActive (bool)
        //   slot 12: _alreadyMinted mapping

        for (uint i = 0; i < 15; i++) {
            bytes32 val = vm.load(address(UACD), bytes32(uint256(i)));
            if (uint256(val) != 0) {
                console.log("Slot", i);
                console.logBytes32(val);
            }
        }
    }

    // Check: is _currentId consistent with totalSupply?
    function test_currentId_consistency() public view {
        bytes32 slot8 = vm.load(address(UACD), bytes32(uint256(8)));
        uint256 currentId = uint256(slot8);
        console.log("_currentId from storage:", currentId);

        // Call totalSupply()
        (bool ok, bytes memory ret) = UACD.staticcall(abi.encodeWithSignature("totalSupply()"));
        if (ok && ret.length >= 32) {
            uint256 supply = abi.decode(ret, (uint256));
            console.log("totalSupply():", supply);
            console.log("Match:", currentId == supply);
        }
    }

    // Check: owner in storage matches owner()
    function test_owner_storage() public view {
        bytes32 slot6 = vm.load(address(UACD), bytes32(uint256(6)));
        address storageOwner = address(uint160(uint256(slot6)));
        console.log("Owner from storage:", storageOwner);

        (bool ok, bytes memory ret) = UACD.staticcall(abi.encodeWithSignature("owner()"));
        if (ok && ret.length >= 32) {
            address fnOwner = abi.decode(ret, (address));
            console.log("owner():", fnOwner);
            console.log("Match:", storageOwner == fnOwner);
        }
    }

    // Check: saleIsActive in storage
    function test_sale_storage() public view {
        bytes32 slot11 = vm.load(address(UACD), bytes32(uint256(11)));
        console.log("saleIsActive raw:", uint256(slot11));
        // bool is stored as 0 or 1 in the lowest byte
    }

    // Check: baseURI string storage
    function test_baseURI_storage() public view {
        // Solidity strings: if length < 32, stored in slot directly
        // If length >= 32, slot stores length*2+1, data at keccak256(slot)
        bytes32 slot9 = vm.load(address(UACD), bytes32(uint256(9)));
        uint256 raw = uint256(slot9);

        if (raw % 2 == 0) {
            // Short string: length = raw / 2, data in high bytes
            uint256 len = raw / 2;
            console.log("baseURI length:", len);
        } else {
            // Long string: length = (raw - 1) / 2
            uint256 len = (raw - 1) / 2;
            console.log("baseURI length:", len);
            // Data starts at keccak256(9)
            bytes32 dataSlot = keccak256(abi.encode(uint256(9)));
            for (uint i = 0; i < (len + 31) / 32; i++) {
                bytes32 chunk = vm.load(address(UACD), bytes32(uint256(dataSlot) + i));
                console.logBytes32(chunk);
            }
        }
    }

    // Check: can we find any HIDDEN storage beyond expected layout?
    function test_hidden_storage() public view {
        console.log("=== HIDDEN STORAGE SCAN ===");
        for (uint i = 15; i < 50; i++) {
            bytes32 val = vm.load(address(UACD), bytes32(uint256(i)));
            if (uint256(val) != 0) {
                console.log("UNEXPECTED slot", i);
                console.logBytes32(val);
            }
        }
        console.log("Scan complete (slots 15-49)");
    }

    // Check: _alreadyMinted for known addresses
    function test_alreadyMinted_mapping() public view {
        // _alreadyMinted is at slot 12
        // mapping(address => uint) at slot 12
        // value for address A = keccak256(abi.encode(A, 12))

        address owner = 0xe8eeE66A90270488DF98Ca631961b5ED60cD4dB7;
        bytes32 ownerSlot = keccak256(abi.encode(owner, uint256(12)));
        bytes32 ownerMinted = vm.load(address(UACD), ownerSlot);
        console.log("Owner alreadyMinted:", uint256(ownerMinted));

        // Check a few more addresses
        address zero = address(0);
        bytes32 zeroSlot = keccak256(abi.encode(zero, uint256(12)));
        bytes32 zeroMinted = vm.load(address(UACD), zeroSlot);
        console.log("address(0) alreadyMinted:", uint256(zeroMinted));
    }
}
