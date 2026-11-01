// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract OptTarget {
    uint256 public maxValue;
    uint256 public callCount;
    
    // Medusa optimization: try to maximize this
    function optimizeMe(uint256 x, uint256 y) public {
        callCount++;
        uint256 result = (x * y) / (x + y + 1); // harmonic-like
        if (result > maxValue) {
            maxValue = result;
        }
    }
    
    // Complex function with branches
    function complexPath(uint256 a, uint256 b, uint256 c) public {
        callCount++;
        uint256 score = 0;
        
        if (a > 100) score += 10;
        if (b > 200) score += 20;
        if (c > 300) score += 30;
        if (a + b > 500) score += 50;
        if (a * b > 100000) score += 100;
        if (a > b && b > c) score += 200;
        if (a % 7 == 0) score += 7;
        if (b % 13 == 0) score += 13;
        
        if (score > maxValue) {
            maxValue = score;
        }
    }
    
    function echidna_maxValueBounded() public view returns (bool) {
        return maxValue < 1000; // should this fail?
    }
}
