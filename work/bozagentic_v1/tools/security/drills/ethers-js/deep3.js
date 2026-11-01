/**
 * ETHERS.JS DEEP DRILL 3: Decompiler patterns, State Diff, Real-time
 */
const { ethers } = require("ethers");

async function main() {
    const provider = new ethers.JsonRpcProvider("https://1rpc.io/eth");
    const latest = await provider.getBlockNumber();

    // === 1. BYTECODE PATTERN MATCHING (security) ===
    console.log("=== 1. BYTECODE SECURITY PATTERNS ===");
    const KILN = "0x0A7272e8573aea8359FEC143ac02AED90F822bD0";
    const code = await provider.getCode(KILN);
    const hex = code.slice(2);

    // Pattern: SSTORE without preceding SLOAD (write-only storage = suspicious)
    let sstoreCount = 0, sloadCount = 0, delegatecallCount = 0, selfdestructCount = 0;
    let callCount = 0, staticcallCount = 0, createCount = 0, create2Count = 0;
    const bytes = Buffer.from(hex, 'hex');
    for (let i = 0; i < bytes.length; i++) {
        switch(bytes[i]) {
            case 0x54: sloadCount++; break;
            case 0x55: sstoreCount++; break;
            case 0xf1: callCount++; break;
            case 0xf4: delegatecallCount++; break;
            case 0xfa: staticcallCount++; break;
            case 0xf0: createCount++; break;
            case 0xf5: create2Count++; break;
            case 0xff: selfdestructCount++; break;
        }
    }
    console.log(`  Kiln (${(code.length-2)/2} bytes):`);
    console.log(`    SLOAD: ${sloadCount}, SSTORE: ${sstoreCount}`);
    console.log(`    CALL: ${callCount}, DELEGATECALL: ${delegatecallCount}, STATICCALL: ${staticcallCount}`);
    console.log(`    CREATE: ${createCount}, CREATE2: ${create2Count}`);
    console.log(`    SELFDESTRUCT: ${selfdestructCount} ${selfdestructCount > 0 ? "⚠️" : "✓"}`);

    // Check for known vulnerable patterns
    // Pattern: CALLVALUE + ISZERO + JUMPI (payable check)
    let payableChecks = 0;
    for (let i = 0; i < bytes.length - 3; i++) {
        if (bytes[i] === 0x34 && bytes[i+1] === 0x15) payableChecks++; // CALLVALUE ISZERO
    }
    console.log(`    Payable guards: ${payableChecks}`);

    // === 2. STATE DIFF: Compare two blocks ===
    console.log("\n=== 2. STATE DIFF ANALYSIS ===");
    const USDT = ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7");
    
    // Read multiple slots at two different blocks
    const slotsToCheck = [0, 1, 2, 3, 4, 5];
    const blockA = latest - 10;
    const blockB = latest;
    
    let changes = 0;
    for (const slot of slotsToCheck) {
        const [valA, valB] = await Promise.all([
            provider.getStorage(USDT, slot, blockA),
            provider.getStorage(USDT, slot, blockB),
        ]);
        if (valA !== valB) {
            changes++;
            console.log(`  Slot ${slot}: CHANGED`);
            console.log(`    Before: ${valA.slice(0, 20)}...`);
            console.log(`    After:  ${valB.slice(0, 20)}...`);
        }
    }
    console.log(`  Slots changed (${blockA}->${blockB}): ${changes}/${slotsToCheck.length}`);

    // === 3. FUNCTION SELECTOR BRUTE FORCE ===
    console.log("\n=== 3. SELECTOR BRUTE FORCE ===");
    // Generate selectors for common functions and match against bytecode
    const commonFuncs = [
        "deposit()", "withdraw(uint256)", "withdraw(bytes)", "transfer(address,uint256)",
        "approve(address,uint256)", "balanceOf(address)", "totalSupply()",
        "owner()", "admin()", "paused()", "initialize()", "renounceOwnership()",
        "getAdmin()", "getTreasury()", "getGlobalFee()", "getOperatorFee()",
        "setGlobalFee(uint256)", "setOperatorFee(uint256)", "setTreasury(address)",
        "requestValidatorsExit(bytes)", "addValidators(uint256,uint256,bytes,bytes)",
        "removeValidators(uint256,uint256[])", "addOperator(address,address)",
        "DEPOSIT_SIZE()", "PUBLIC_KEY_LENGTH()", "SIGNATURE_LENGTH()",
        "acceptOwnership()", "transferOwnership(address)", "getPendingAdmin()",
        "deposit()", "withdrawELFee(bytes)", "withdrawCLFee(bytes)",
        "batchWithdraw(bytes)", "setDepositsStopped(bool)",
        "getAvailableValidatorCount()", "getDepositsStopped()",
        "toggleWithdrawnFromPublicKeyRoot(bytes32)",
        "getWithdrawer(bytes)", "getWithdrawerFromPublicKeyRoot(bytes32)",
        "getExitRequestedFromRoot(bytes32)", "getWithdrawnFromPublicKeyRoot(bytes32)",
        "getEnabledFromPublicKeyRoot(bytes32)", "getOperatorFeeRecipient(bytes32)",
        "getELFeeRecipient(bytes)", "getCLFeeRecipient(bytes)",
        "getOperator(uint256)", "getValidator(uint256,uint256)",
        "initialize_1(address,address,address,address,address,address,uint256,uint256,uint256,uint256)",
        "initialize_2(uint256,uint256)", "setOperatorAddresses(uint256,address,address)",
        "deactivateOperator(uint256,address)", "activateOperator(uint256,address)",
        "setOperatorLimit(uint256,uint256,uint256)", "setWithdrawer(bytes,address)",
        "setWithdrawerCustomizationEnabled(bool)",
    ];

    const selectorMap = {};
    for (const func of commonFuncs) {
        const sel = ethers.id(func).slice(0, 10);
        selectorMap[sel] = func;
    }

    // Find which selectors exist in Kiln bytecode
    let found = 0;
    for (const [sel, func] of Object.entries(selectorMap)) {
        if (hex.includes(sel.slice(2))) {
            found++;
        }
    }
    console.log(`  Kiln selectors matched: ${found}/${commonFuncs.length}`);

    // === 4. MULTICALL STATE SNAPSHOT ===
    console.log("\n=== 4. MULTICALL STATE SNAPSHOT ===");
    const MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11";
    const mcAbi = ["function aggregate3(tuple(address target, bool allowFailure, bytes callData)[] calls) view returns (tuple(bool success, bytes returnData)[])"];
    const mc = new ethers.Contract(MULTICALL3, mcAbi, provider);

    const kilnAbi = [
        "function getAdmin() view returns (address)",
        "function getTreasury() view returns (address)",
        "function getGlobalFee() view returns (uint256)",
        "function getOperatorFee() view returns (uint256)",
        "function getAvailableValidatorCount() view returns (uint256)",
        "function getDepositsStopped() view returns (bool)",
        "function getPendingAdmin() view returns (address)",
        "function DEPOSIT_SIZE() view returns (uint256)",
    ];
    const kilnIface = new ethers.Interface(kilnAbi);
    const kilnContract = new ethers.Contract(KILN, kilnAbi, provider);

    // Batch all reads
    const calls = kilnAbi
        .filter(f => f.startsWith("function"))
        .map(f => {
            const name = f.match(/function (\w+)/)[1];
            return {
                target: KILN,
                allowFailure: true,
                callData: kilnIface.encodeFunctionData(name, [])
            };
        });

    const results = await mc.aggregate3.staticCall(calls);
    const names = kilnAbi.filter(f => f.startsWith("function")).map(f => f.match(/function (\w+)/)[1]);
    
    console.log("  Kiln on-chain state:");
    for (let i = 0; i < names.length; i++) {
        if (results[i].success) {
            const decoded = kilnIface.decodeFunctionResult(names[i], results[i].returnData);
            const val = decoded[0];
            if (typeof val === "bigint") {
                console.log(`    ${names[i]}: ${val}`);
            } else {
                console.log(`    ${names[i]}: ${val}`);
            }
        } else {
            console.log(`    ${names[i]}: FAILED`);
        }
    }

    // === 5. REAL-TIME EVENT SUBSCRIPTION ===
    console.log("\n=== 5. EVENT SUBSCRIPTION (3 blocks) ===");
    let blockCount = 0;
    await new Promise((resolve) => {
        provider.on("block", async (blockNum) => {
            blockCount++;
            const block = await provider.getBlock(blockNum);
            console.log(`  Block ${blockNum}: ${block.transactions.length} txs, gas=${block.gasUsed.toLocaleString()}`);
            if (blockCount >= 3) {
                provider.removeAllListeners("block");
                resolve();
            }
        });
        // Timeout after 30s
        setTimeout(() => { provider.removeAllListeners("block"); resolve(); }, 30000);
    });

    console.log("\n✓ ETHERS.JS DEEP DRILL 3 COMPLETE");
}
main().catch(console.error);
