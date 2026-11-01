# #17: Malicious proposals can be executed in the Governance
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_02_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/p1/StRSR.sol#L452
https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/plugins/governance/Governance.sol#L131


# Vulnerability details

## Impact

In governance systems, there’s always a risk of malicious users creating harmful `proposals`. 
It’s crucial to prevent these `proposals` from being executed, which is the primary role of the governor.
For a malicious `proposal` to succeed, the malicious user must have enough (e.x. `51%` of) `votes` at the time the `vote` begins. 
The governor takes a `snapshot` of all users' `votes` at that moment. 

When a malicious `proposal` is made, honest users will work to gather more `votes` than the malicious party.
To help with this, a `voting delay` exists. 
In the `Reserve Governor`, the `minimum voting delay` is set to `1 day`. 
However, there are situations where this `delay` might not be effective, allowing malicious users to still gather enough `votes` to pass their harmful `proposals`. 
This is really dangerous.
## Proof of Concept

Let's say the `current era` in `StRSR` is `2`, and a malicious user has enough `votes` to create any `proposal` they want. 
They create a malicious `proposal` at `time T`. 
If the `voting delay` is `D`, the `vote` will begin at `T + D`, and the `snapshot` of `votes` for this `proposal` will be `T + D` (`line 290, 295`).
```
function propose(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    string memory description
) public virtual override returns (uint256) {
    uint256 currentTimepoint = clock();  // T
290:    uint256 snapshot = currentTimepoint + votingDelay();  // T + D
    uint256 deadline = snapshot + votingPeriod();
    
    _proposals[proposalId] = ProposalCore({
        proposer: proposer,
295:        voteStart: SafeCast.toUint64(snapshot), // T + D
        voteEnd: SafeCast.toUint64(deadline),
        executed: false,
        canceled: false,
        __gap_unused0: 0,
        __gap_unused1: 0
    });
}
```
Honest users have enough `votes` to defeat this `proposal` or to gather more `votes` than the malicious user. 

However, if the `StRSR` moves to the `next era` (`era 3`) at `T + D - 1` (or any time close to the `vote start`), all users' `votes` from `era 2` will disappear (`line 452`).
```
function seizeRSR(uint256 rsrAmount) external {
    if (stakeRSR == 0 || stakeRate > MAX_STAKE_RATE) {
        seizedRSR += stakeRSR;
452:        beginEra();
    }
}
```

The malicious user can then quickly `stake` some `RSR` to get new `votes`, while the honest users don’t have enough time to gather sufficient `votes`. 
In this case, the actual `voting delay` might act as short as `1 second`, for example.

When the `vote` begins, the malicious user has enough `votes` to pass their `proposal`. 

The `proposalSnapshot` function returns the `vote start time`, which is `T + D`. 
```
function proposalSnapshot(uint256 proposalId) public view virtual override returns (uint256) {
    return _proposals[proposalId].voteStart;  // T + D
}
```
Since `era 3` has just begun at `T + D - 1`, the `quorum` will be small, mostly consisting of the malicious users' `votes`.
```
function quorum(uint256 timepoint) public view virtual override returns (uint256) {
    return (token.getPastTotalSupply(timepoint) * quorumNumerator(timepoint)) / quorumDenominator();  // timepoint = T + D
}
```
If the malicious users cast their `votes` for their own `proposal`, the `quorum` will be reached.
```
function _quorumReached(uint256 proposalId) internal view virtual override returns (bool) {
    ProposalVote storage proposalVote = _proposalVotes[proposalId];

    return quorum(proposalSnapshot(proposalId)) <= proposalVote.forVotes + proposalVote.abstainVotes;
}
```
And the `proposal` will be marked as successful.
```
function _voteSucceeded(uint256 proposalId) internal view virtual override returns (bool) {
    ProposalVote storage proposalVote = _proposalVotes[proposalId];
  
    return proposalVote.forVotes > proposalVote.againstVotes;
}
```

At this point, the `_cancel` function will revert because the `era` at `T + D` (when the `vote` starts) is now `3`, matching the `current era` (`line 131`). 
```
function cancel(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    bytes32 descriptionHash
) public override(Governor, IGovernor) returns (uint256) {
    uint256 proposalId = _cancel(targets, values, calldatas, descriptionHash);
131:    require(!startedInSameEra(proposalId), "same era");
  
    return proposalId;
}

function startedInSameEra(uint256 proposalId) private view returns (bool) {
    uint256 startTimepoint = proposalSnapshot(proposalId); // T + D
    uint256 pastEra = IStRSRVotes(address(token)).getPastEra(startTimepoint); // 3
    uint256 currentEra = IStRSRVotes(address(token)).currentEra(); // 3
    return currentEra == pastEra; // 3 = 3
}
```
Even the owner cannot cancel these `proposals`.
## Tools Used

## Recommended Mitigation Steps

- Use the `proposal creation time` instead of the `vote start time` in the `startedInSameEra` function.
- Alternatively, allow the `owner` to cancel any `proposal`.


## Assessed type

Invalid Validation