// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "./TokenExchange.sol";

contract ExchangeHarness {
    TokenExchange public exchange;
    uint256 public initialK;
    bool public initialized;
    
    constructor() {
        exchange = new TokenExchange();
    }
    
    function seed(uint256 a, uint256 b) public {
        a = _bound(a, 10e18, 1000e18);
        b = _bound(b, 10e18, 1000e18);
        exchange.addLiquidity(a, b);
        if (!initialized) {
            initialK = exchange.reserveA() * exchange.reserveB();
            initialized = true;
        }
    }
    
    function addLiq(uint256 a, uint256 b) public {
        a = _bound(a, 1e18, 100e18);
        b = _bound(b, 1e18, 100e18);
        exchange.addLiquidity(a, b);
    }
    
    function swapAB(uint256 amt) public {
        amt = _bound(amt, 1e15, 50e18);
        uint256 kBefore = exchange.reserveA() * exchange.reserveB();
        try exchange.swapAToB(amt) {
            uint256 kAfter = exchange.reserveA() * exchange.reserveB();
            assert(kAfter >= kBefore); // k must not decrease
        } catch {}
    }
    
    function swapBA(uint256 amt) public {
        amt = _bound(amt, 1e15, 50e18);
        uint256 kBefore = exchange.reserveA() * exchange.reserveB();
        try exchange.swapBToA(amt) {
            uint256 kAfter = exchange.reserveA() * exchange.reserveB();
            assert(kAfter >= kBefore);
        } catch {}
    }
    
    function removeLiq(uint256 lp) public {
        uint256 bal = exchange.lpBalances(address(this));
        if (bal == 0) return;
        lp = _bound(lp, 1, bal);
        uint256 rA = exchange.reserveA();
        uint256 rB = exchange.reserveB();
        try exchange.removeLiquidity(lp) returns (uint256 amtA, uint256 amtB) {
            assert(amtA <= rA);
            assert(amtB <= rB);
        } catch {}
    }
    
    function echidna_kNeverDecreases() public view returns (bool) {
        if (!initialized) return true;
        uint256 currentK = exchange.reserveA() * exchange.reserveB();
        return currentK >= initialK;
    }
    
    function echidna_reservesPositive() public view returns (bool) {
        if (!initialized) return true;
        return exchange.reserveA() > 0 && exchange.reserveB() > 0;
    }
    
    function _bound(uint256 x, uint256 lo, uint256 hi) internal pure returns (uint256) {
        if (x < lo) return lo;
        if (x > hi) return hi;
        return x;
    }
}
