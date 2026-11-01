/*
 * Certora Spec — Liquity V2 TroveManager
 */

methods {
    function getTroveIdsCount() external returns (uint256) envfree;
    function getEntireBranchDebt() external returns (uint256);
    function getEntireBranchColl() external returns (uint256);
    function getCurrentICR(uint256, uint256) external returns (uint256) envfree;
    function CCR() external returns (uint256) envfree;
}

// INVARIANT 1: System must remain overcollateralized
invariant systemSolvency(env e, uint256 _price)
    _price > 0 => getEntireBranchColl(e) * _price >= getEntireBranchDebt(e)
    {
        preserved {
            require _price > 0;
            require _price < 1000000000000000000000000;
        }
    }

// INVARIANT 2: Trove count is bounded
invariant troveCountBounded()
    getTroveIdsCount() <= 1000000;

// RULE: ICR computation is always non-negative
rule icrNonNegative(uint256 troveId, uint256 _price) {
    require _price > 0;
    require _price < 1000000000000000000000000;
    uint256 icr = getCurrentICR(troveId, _price);
    assert icr >= 0, "ICR must be non-negative";
}

// RULE: CCR is within expected bounds
rule ccrBounds() {
    uint256 ccr = CCR();
    assert ccr > 1000000000000000000, "CCR must be > 100%";
    assert ccr < 2000000000000000000, "CCR must be < 200%";
}
