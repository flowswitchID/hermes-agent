/**
 * ETHERS.JS EXPERT DRILL 1: Decompiler Patterns + Advanced Security
 */
const { ethers } = require("ethers");

async function main() {
    // Use multiple RPCs for resilience
    const RPCS = ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com"];
    let provider;
    for (const rpc of RPCS) {
        try {
            provider = new ethers.JsonRpcProvider(rpc);
            await provider.getBlockNumber();
            console.log(`Connected: ${rpc}`);
            break;
        } catch { continue; }
    }
    if (!provider) { console.log("No RPC available"); return; }

    const latest = await provider.getBlockNumber();

    // === 1. BYTECODE DECOMPILER PATTERNS ===
    console.log("\n=== 1. DECOMPILER PATTERNS ===");
    const KILN = "0x0A7272e8573aea8359FEC143ac02AED90F822bD0";
    const code = await provider.getCode(KILN);
    const bytes = Buffer.from(code.slice(2), 'hex');

    // Pattern: Function dispatcher (PUSH4 + EQ + PUSH2 + JUMPI)
    const functions = [];
    for (let i = 0; i < bytes.length - 10; i++) {
        if (bytes[i] === 0x63) { // PUSH4
            const sel = '0x' + bytes.slice(i+1, i+5).toString('hex');
            // Look for EQ within next 3 bytes
            for (let j = i+5; j < Math.min(i+8, bytes.length); j++) {
                if (bytes[j] === 0x14) { // EQ
                    // Look for PUSH1/PUSH2 + JUMPI
                    for (let k = j+1; k < Math.min(j+5, bytes.length); k++) {
                        if (bytes[k] === 0x61 || bytes[k] === 0x60) { // PUSH2 or PUSH1
                            const n = bytes[k] - 0x5f;
                            const target = parseInt(bytes.slice(k+1, k+1+n).toString('hex'), 16);
                            functions.push({ selector: sel, target });
                            break;
                        }
                    }
                    break;
                }
            }
        }
    }
    console.log(`  Function dispatcher entries: ${functions.length}`);
    console.log(`  First 10:`);
    for (const f of functions.slice(0, 10)) {
        console.log(`    ${f.selector} -> offset ${f.target}`);
    }

    // Pattern: REVERT with error selector
    const errors = [];
    for (let i = 0; i < bytes.length - 5; i++) {
        if (bytes[i] === 0xfd) { // REVERT
            // Check if preceded by PUSH4 (error selector)
            if (i >= 5 && bytes[i-5] === 0x63) {
                const errSel = '0x' + bytes.slice(i-4, i).toString('hex');
                if (!errors.includes(errSel)) errors.push(errSel);
            }
        }
    }
    console.log(`\n  Custom errors found: ${errors.length}`);
    // Match against known Kiln errors
    const knownErrors = {
        '0x82b42900': 'Unauthorized()',
        '0x0dc149f0': 'InvalidFee()',
        '0x5fc483c5': 'Deactivated()',
        '0xa1209a28': 'NoOperators()',
        '0x1cf44e10': 'InvalidCall()',
        '0x2f27a35c': 'DepositFailure()',
        '0x5b24ea5e': 'DepositsStopped()',
        '0x5698b35a': 'InvalidArgument()',
        '0x34c7ed5a': 'UnsortedIndexes()',
        '0x28e2a0a0': 'InvalidPublicKeys()',
        '0x0b62ad1c': 'InvalidSignatures()',
        '0xa8391174': 'InvalidWithdrawer()',
        '0xf8e54a07': 'InvalidZeroAddress()',
        '0x9e87fac8': 'AlreadyInitialized()',
        '0x2c1fb1dd': 'InvalidDepositValue()',
        '0x71a67920': 'NotEnoughValidators()',
        '0x67e3691e': 'InvalidValidatorCount()',
        '0x4e487b71': 'Panic(uint256)',
        '0x08c379a0': 'Error(string)',
    };
    for (const sel of errors) {
        console.log(`    ${sel} = ${knownErrors[sel] || 'UNKNOWN'}`);
    }

    // Pattern: Events (LOG1-LOG4 with topic0)
    const eventTopics = [];
    for (let i = 0; i < bytes.length - 33; i++) {
        if (bytes[i] >= 0xa0 && bytes[i] <= 0xa4) { // LOG0-LOG4
            // Topic0 is usually PUSH32 before LOG
            if (i >= 33 && bytes[i-33] === 0x7f) { // PUSH32
                const topic = '0x' + bytes.slice(i-32, i).toString('hex');
                if (!eventTopics.includes(topic)) eventTopics.push(topic);
            }
        }
    }
    console.log(`\n  Event topics in bytecode: ${eventTopics.length}`);
    const knownEvents = {
        '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef': 'Transfer',
        '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925': 'Approval',
    };
    for (const t of eventTopics.slice(0, 10)) {
        console.log(`    ${t.slice(0, 18)}... = ${knownEvents[t] || 'Kiln event'}`);
    }

    // === 2. STORAGE LAYOUT COLLISION CHECK ===
    console.log("\n=== 2. STORAGE COLLISION CHECK ===");
    // Compute all Kiln storage slots and check for collisions with proxy slots
    const kilnLabels = [
        "StakingContract.version", "StakingContract.admin", "StakingContract.pendingAdmin",
        "StakingContract.treasury", "StakingContract.depositContract",
        "StakingContract.operators", "StakingContract.validatorsFundingInfo",
        "StakingContract.totalAvailableValidators", "StakingContract.withdrawers",
        "StakingContract.operatorIndexPerValidator", "StakingContract.globalFee",
        "StakingContract.operatorFee", "StakingContract.executionLayerDispatcher",
        "StakingContract.consensusLayerDispatcher", "StakingContract.feeRecipientImplementation",
        "StakingContract.withdrawerCustomizationEnabled", "StakingContract.exitRequest",
        "StakingContract.withdrawn", "StakingContract.globalCommissionLimit",
        "StakingContract.operatorCommissionLimit", "StakingContract.depositStopped",
        "StakingContract.lastValidatorsEdit",
    ];

    const kilnSlots = kilnLabels.map(l => ({
        label: l,
        slot: BigInt(ethers.keccak256(ethers.toUtf8Bytes(l)))
    }));

    // EIP-1967 slots
    const proxySlots = {
        "EIP-1967 impl": BigInt("0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"),
        "EIP-1967 admin": BigInt("0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"),
        "EIP-1967 beacon": BigInt("0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"),
        "TUPProxy pause": BigInt(ethers.keccak256(ethers.toUtf8Bytes("eip1967.proxy.pause"))) - 1n,
    };

    let collisions = 0;
    for (const ks of kilnSlots) {
        for (const [pname, pslot] of Object.entries(proxySlots)) {
            if (ks.slot === pslot) {
                console.log(`  ⚠️ COLLISION: ${ks.label} == ${pname}`);
                collisions++;
            }
            // Also check ±1 (some slots use keccak-1 pattern)
            if (ks.slot === pslot + 1n || ks.slot === pslot - 1n) {
                console.log(`  ⚠️ ADJACENT: ${ks.label} ~= ${pname}`);
            }
        }
    }
    if (collisions === 0) {
        console.log(`  No collisions between Kiln slots and proxy slots ✓`);
        console.log(`  Kiln uses keccak-based slots, proxy uses EIP-1967 → safe`);
    }

    // === 3. ADVANCED: Signature Analysis ===
    console.log("\n=== 3. SIGNATURE ANALYSIS ===");
    // Analyze a real tx signature
    const block = await provider.getBlock(latest - 1, true);
    const txs = block.prefetchedTransactions || [];
    if (txs.length > 0) {
        const tx = txs[0];
        console.log(`  TX: ${tx.hash.slice(0, 18)}...`);
        console.log(`  Type: ${tx.type} (${tx.type === 2 ? "EIP-1559" : tx.type === 0 ? "Legacy" : "EIP-2930"})`);
        console.log(`  From: ${tx.from}`);
        console.log(`  Nonce: ${tx.nonce}`);
        console.log(`  Chain ID: ${tx.chainId}`);
        if (tx.signature) {
            console.log(`  v: ${tx.signature.v}`);
            console.log(`  r: ${tx.signature.r.slice(0, 20)}...`);
            console.log(`  s: ${tx.signature.s.slice(0, 20)}...`);
            // Check malleability
            const secp256k1n = BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141");
            const s = BigInt(tx.signature.s);
            console.log(`  Low-s: ${s <= secp256k1n / 2n ? "✓" : "⚠️ MALLEABLE"}`);
        }
    }

    // === 4. ADVANCED: Contract Size Analysis ===
    console.log("\n=== 4. CONTRACT SIZE ANALYSIS ===");
    const contracts = {
        "Kiln Staking": KILN,
        "USDT": ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7"),
        "WETH": ethers.getAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"),
        "Multicall3": "0xcA11bde05977b3631167028862bE2a173976CA11",
    };
    const EIP170_LIMIT = 24576; // max contract size
    for (const [name, addr] of Object.entries(contracts)) {
        const code = await provider.getCode(addr);
        const size = (code.length - 2) / 2;
        const pct = (size / EIP170_LIMIT * 100).toFixed(1);
        console.log(`  ${name}: ${size.toLocaleString()} bytes (${pct}% of EIP-170 limit)`);
    }

    // === 5. ADVANCED: Nonce Gap Detection ===
    console.log("\n=== 5. NONCE GAP DETECTION ===");
    // Check for nonce gaps (indicates failed/dropped txs)
    const uniqueSenders = [...new Set(txs.map(tx => tx.from))].slice(0, 10);
    for (const sender of uniqueSenders) {
        const confirmed = await provider.getTransactionCount(sender, "latest");
        const pending = await provider.getTransactionCount(sender, "pending");
        if (pending > confirmed) {
            console.log(`  ${sender.slice(0, 14)}...: confirmed=${confirmed}, pending=${pending} (gap=${pending-confirmed})`);
        }
    }
    console.log(`  Checked ${uniqueSenders.length} senders`);

    console.log("\n✓ ETHERS.JS EXPERT DRILL 1 COMPLETE");
}
main().catch(console.error);
