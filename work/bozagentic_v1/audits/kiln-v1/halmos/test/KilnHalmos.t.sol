// SPDX-License-Identifier: MIT
pragma solidity >=0.8.10;

contract KilnFeeProps {
    uint256 constant BP = 10_000;

    function check_feeNeverExceedsBalance(uint16 bal, uint16 g) public pure {
        require(g <= BP);
        require(bal > 0);
        uint256 fee = (uint256(bal) * g) / BP;
        assert(fee <= bal);
    }

    function check_operatorFeeLeq(uint16 bal, uint16 g, uint16 o) public pure {
        require(g <= BP);
        require(o <= BP);
        uint256 gFee = (uint256(bal) * g) / BP;
        uint256 oFee = (gFee * o) / BP;
        assert(oFee <= gFee);
    }

    function check_exemptionSafe(uint128 bal) public pure {
        require(bal >= 31 ether);
        uint256 exemption = bal > 32 ether ? 32 ether : uint256(bal);
        assert(exemption <= bal);
        assert(exemption <= 32 ether);
    }

    function check_feeSplitConservation(uint16 bal, uint16 g, uint16 o) public pure {
        require(g <= BP);
        require(o <= BP);
        uint256 gFee = (uint256(bal) * g) / BP;
        uint256 oFee = (gFee * o) / BP;
        uint256 tFee = gFee - oFee;
        uint256 wGet = uint256(bal) - gFee;
        assert(wGet + tFee + oFee <= bal);
        assert(uint256(bal) - (wGet + tFee + oFee) <= 1);
    }
}
