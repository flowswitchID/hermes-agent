// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract TokenExchange {
    uint256 public reserveA;
    uint256 public reserveB;
    uint256 public totalLPTokens;
    mapping(address => uint256) public lpBalances;
    mapping(address => uint256) public tokenABalance;
    mapping(address => uint256) public tokenBBalance;
    
    uint256 public feeNumerator = 3;
    uint256 public feeDenominator = 1000;
    
    function addLiquidity(uint256 amountA, uint256 amountB) external returns (uint256 lpMinted) {
        require(amountA > 0 && amountB > 0, "zero");
        
        if (totalLPTokens == 0) {
            lpMinted = _sqrt(amountA * amountB);
            require(lpMinted > 0, "zero lp");
        } else {
            uint256 lpA = (amountA * totalLPTokens) / reserveA;
            uint256 lpB = (amountB * totalLPTokens) / reserveB;
            lpMinted = lpA < lpB ? lpA : lpB;
        }
        
        require(lpMinted > 0, "zero lp");
        tokenABalance[msg.sender] += amountA;
        tokenBBalance[msg.sender] += amountB;
        reserveA += amountA;
        reserveB += amountB;
        lpBalances[msg.sender] += lpMinted;
        totalLPTokens += lpMinted;
    }
    
    function removeLiquidity(uint256 lpAmount) external returns (uint256 amountA, uint256 amountB) {
        require(lpAmount > 0 && lpAmount <= lpBalances[msg.sender], "bad");
        amountA = (lpAmount * reserveA) / totalLPTokens;
        amountB = (lpAmount * reserveB) / totalLPTokens;
        require(amountA > 0 && amountB > 0, "zero out");
        
        lpBalances[msg.sender] -= lpAmount;
        totalLPTokens -= lpAmount;
        reserveA -= amountA;
        reserveB -= amountB;
        tokenABalance[msg.sender] -= amountA;
        tokenBBalance[msg.sender] -= amountB;
    }
    
    function swapAToB(uint256 amountIn) external returns (uint256 amountOut) {
        require(amountIn > 0, "zero");
        require(tokenABalance[msg.sender] >= amountIn, "insufficient");
        require(reserveA > 0 && reserveB > 0, "no liquidity");
        
        uint256 amountInWithFee = amountIn * (feeDenominator - feeNumerator);
        amountOut = (amountInWithFee * reserveB) / (reserveA * feeDenominator + amountInWithFee);
        require(amountOut > 0 && amountOut < reserveB, "bad swap");
        
        tokenABalance[msg.sender] -= amountIn;
        tokenBBalance[msg.sender] += amountOut;
        reserveA += amountIn;
        reserveB -= amountOut;
    }
    
    function swapBToA(uint256 amountIn) external returns (uint256 amountOut) {
        require(amountIn > 0, "zero");
        require(tokenBBalance[msg.sender] >= amountIn, "insufficient");
        require(reserveA > 0 && reserveB > 0, "no liquidity");
        
        uint256 amountInWithFee = amountIn * (feeDenominator - feeNumerator);
        amountOut = (amountInWithFee * reserveA) / (reserveB * feeDenominator + amountInWithFee);
        require(amountOut > 0 && amountOut < reserveA, "bad swap");
        
        tokenBBalance[msg.sender] -= amountIn;
        tokenABalance[msg.sender] += amountOut;
        reserveB += amountIn;
        reserveA -= amountOut;
    }
    
    function _sqrt(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        uint256 y = x;
        while (z < y) { y = z; z = (x / z + z) / 2; }
        return y;
    }
}
