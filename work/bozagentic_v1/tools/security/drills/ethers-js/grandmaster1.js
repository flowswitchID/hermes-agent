/**
 * ETHERS.JS GRANDMASTER DRILL: Advanced Security Tooling
 * - EIP-7702 detection
 * - Advanced log decoding
 * - Contract factory pattern analysis
 * - State diff via eth_call replay
 * - Advanced wallet ops (HD derivation, multisig)
 */
const { ethers } = require("ethers");

async function main() {
    const provider = new ethers.JsonRpcProvider("https://ethereum-rpc.publicnode.com");
    const latest = await provider.getBlockNumber();

    // === 1. EIP-7702 DETECTION (Account Abstraction) ===
    console.log("=== 1. EIP-7702 DETECTION ===");
    // EIP-7702: EOA can delegate to a contract via authorization
    // Detection: code starts with 0xef0100 (delegation designator)
    const block = await provider.getBlock(latest, true);
    const txs = block.prefetchedTransactions || [];
    
    let eip7702Count = 0;
    for (const tx of txs.slice(0, 50)) {
        if (tx.type === 4) { // EIP-7702 tx type
            eip7702Count++;
            console.log(`  EIP-7702 tx: ${tx.hash.slice(0,14)}...`);
            if (tx.authorizationList) {
                console.log(`    Authorizations: ${tx.authorizationList.length}`);
            }
        }
    }
    console.log(`  EIP-7702 txs in block: ${eip7702Count}/${txs.length}`);
    
    // Check if any EOA has delegation code
    const uniqueSenders = [...new Set(txs.map(tx => tx.from))].slice(0, 10);
    for (const sender of uniqueSenders) {
        const code = await provider.getCode(sender);
        if (code !== "0x" && code.startsWith("0xef0100")) {
            console.log(`  🆕 EIP-7702 delegated EOA: ${sender}`);
            console.log(`    Delegation: ${code}`);
        }
    }

    // === 2. ADVANCED LOG DECODING ===
    console.log("\n=== 2. ADVANCED LOG DECODING ===");
    // Decode ALL events in a complex tx
    const complexTx = txs.find(tx => tx.data.length > 100);
    if (complexTx) {
        const receipt = await provider.getTransactionReceipt(complexTx.hash);
        console.log(`  TX: ${complexTx.hash.slice(0,14)}...`);
        console.log(`  Logs: ${receipt.logs.length}`);
        
        // Common event signatures
        const eventSigs = {
            [ethers.id("Transfer(address,address,uint256)")]: "Transfer",
            [ethers.id("Approval(address,address,uint256)")]: "Approval",
            [ethers.id("Deposit(address,uint256)")]: "Deposit",
            [ethers.id("Withdrawal(address,uint256)")]: "Withdrawal",
            [ethers.id("Sync(uint112,uint112)")]: "Sync",
            [ethers.id("Swap(address,uint256,uint256,uint256,uint256,address)")]: "Swap",
            [ethers.id("Mint(address,uint256)")]: "Mint",
            [ethers.id("Burn(address,uint256)")]: "Burn",
        };
        
        for (const log of receipt.logs.slice(0, 10)) {
            const topic0 = log.topics[0];
            const name = eventSigs[topic0] || "Unknown";
            const addr = log.address.slice(0, 12);
            console.log(`    [${name}] ${addr}... (${log.topics.length} topics, ${(log.data.length-2)/2} bytes)`);
            
            // Decode Transfer/Approval
            if (name === "Transfer" || name === "Approval") {
                const from = ethers.getAddress("0x" + log.topics[1].slice(26));
                const to = ethers.getAddress("0x" + log.topics[2].slice(26));
                const value = BigInt(log.data);
                console.log(`      ${from.slice(0,10)}... -> ${to.slice(0,10)}... : ${value}`);
            }
        }
    }

    // === 3. FACTORY PATTERN ANALYSIS ===
    console.log("\n=== 3. FACTORY PATTERN ANALYSIS ===");
    // Detect factory contracts: contracts that CREATE/CREATE2 other contracts
    const FACTORIES = {
        "Uniswap V2 Factory": ethers.getAddress("0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"),
        "Uniswap V3 Factory": ethers.getAddress("0x1f98431c8ad98523631ae4a59f267346ea31f984"),
        "Create2Deployer": "0x4e59b44847b379578588920cA78FbF26c0B4956C",
    };
    
    for (const [name, addr] of Object.entries(FACTORIES)) {
        const code = await provider.getCode(addr);
        const size = (code.length - 2) / 2;
        
        // Count CREATE/CREATE2 opcodes
        const bytes = Buffer.from(code.slice(2), 'hex');
        let creates = 0, create2s = 0;
        for (let i = 0; i < bytes.length; i++) {
            if (bytes[i] === 0xf0) creates++;
            if (bytes[i] === 0xf5) create2s++;
        }
        
        console.log(`  ${name}: ${size} bytes, CREATE=${creates}, CREATE2=${create2s}`);
    }

    // === 4. STATE DIFF VIA REPLAY ===
    console.log("\n=== 4. STATE DIFF VIA REPLAY ===");
    // Replay a tx at its block to see what it changed
    const USDT = ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7");
    
    // Find a USDT transfer tx
    const usdtTx = txs.find(tx => tx.to === USDT && tx.data.startsWith("0xa9059cbb"));
    if (usdtTx) {
        const receipt = await provider.getTransactionReceipt(usdtTx.hash);
        console.log(`  USDT transfer: ${usdtTx.hash.slice(0,14)}...`);
        console.log(`  Block: ${receipt.blockNumber}`);
        
        // Decode transfer
        const to = ethers.getAddress("0x" + usdtTx.data.slice(34, 74));
        const amount = BigInt("0x" + usdtTx.data.slice(74));
        console.log(`  To: ${to.slice(0,14)}...`);
        console.log(`  Amount: ${ethers.formatUnits(amount, 6)} USDT`);
        
        // Read balances before and after
        const from = usdtTx.from;
        const balSlotFrom = ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(["address","uint256"], [from, 2]));
        const balSlotTo = ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(["address","uint256"], [to, 2]));
        
        const [beforeFrom, afterFrom, beforeTo, afterTo] = await Promise.all([
            provider.getStorage(USDT, balSlotFrom, receipt.blockNumber - 1),
            provider.getStorage(USDT, balSlotFrom, receipt.blockNumber),
            provider.getStorage(USDT, balSlotTo, receipt.blockNumber - 1),
            provider.getStorage(USDT, balSlotTo, receipt.blockNumber),
        ]);
        
        console.log(`  From balance: ${BigInt(beforeFrom)/BigInt(10**6)} -> ${BigInt(afterFrom)/BigInt(10**6)}`);
        console.log(`  To balance:   ${BigInt(beforeTo)/BigInt(10**6)} -> ${BigInt(afterTo)/BigInt(10**6)}`);
        console.log(`  Delta from:   ${(BigInt(afterFrom) - BigInt(beforeFrom))/BigInt(10**6)}`);
        console.log(`  Delta to:     ${(BigInt(afterTo) - BigInt(beforeTo))/BigInt(10**6)}`);
    } else {
        console.log("  No USDT transfer in this block");
    }

    // === 5. HD WALLET DERIVATION ===
    console.log("\n=== 5. HD WALLET DERIVATION ===");
    const mnemonic = "test test test test test test test test test test test junk";
    const hdNode = ethers.HDNodeWallet.fromPhrase(mnemonic);
    
    console.log(`  Mnemonic: "${mnemonic.slice(0, 20)}..."`);
    console.log(`  Root: ${hdNode.address}`);
    
    // Derive first 5 accounts
    for (let i = 0; i < 5; i++) {
        const child = hdNode.derivePath(`m/44'/60'/0'/0/${i}`);
        console.log(`  m/44'/60'/0'/0/${i}: ${child.address}`);
    }
    
    // Verify derivation matches known Hardhat accounts
    const expected = [
        "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    ];
    for (let i = 0; i < 3; i++) {
        const child = hdNode.derivePath(`m/44'/60'/0'/0/${i}`);
        const match = child.address === expected[i];
        console.log(`  Account ${i} matches Hardhat: ${match ? "✓" : "✗"}`);
    }

    // === 6. ADVANCED: Multisig Pattern Detection ===
    console.log("\n=== 6. MULTISIG DETECTION ===");
    // Gnosis Safe pattern: proxy with specific implementation
    const GNOSIS_SAFE_IMPL = "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"; // Safe v1.3.0
    const GNOSIS_SAFE_IMPL_141 = "0x41675C099F32341bf84BFc5382aF534df5C7461a"; // Safe v1.4.1
    
    // Check some known multisig addresses
    const multisigs = {
        "Ethereum Foundation": "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe",
        "Vitalik": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    };
    
    for (const [name, addr] of Object.entries(multisigs)) {
        const code = await provider.getCode(addr);
        const isContract = code !== "0x";
        
        if (isContract) {
            // Check if it's a Gnosis Safe proxy
            const EIP1967_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
            const implRaw = await provider.getStorage(addr, EIP1967_IMPL);
            const impl = BigInt(implRaw);
            
            // Gnosis Safe uses a different proxy pattern (slot 0 = implementation)
            const slot0 = await provider.getStorage(addr, 0);
            const slot0Addr = ethers.getAddress("0x" + slot0.slice(26));
            
            const isSafe = slot0Addr === GNOSIS_SAFE_IMPL || slot0Addr === GNOSIS_SAFE_IMPL_141;
            console.log(`  ${name}: contract (${(code.length-2)/2} bytes), Safe=${isSafe ? "✓" : "no"}`);
            if (isSafe) {
                console.log(`    Implementation: ${slot0Addr}`);
            }
        } else {
            console.log(`  ${name}: EOA`);
        }
    }

    // === 7. ADVANCED: Gas Golfing Analysis ===
    console.log("\n=== 7. GAS GOLFING ===");
    // Analyze gas efficiency of recent txs
    const gasData = [];
    for (const tx of txs.slice(0, 30)) {
        const receipt = await provider.getTransactionReceipt(tx.hash);
        if (receipt) {
            gasData.push({
                hash: tx.hash.slice(0, 10),
                gasUsed: Number(receipt.gasUsed),
                gasLimit: Number(tx.gasLimit),
                efficiency: Number(receipt.gasUsed) / Number(tx.gasLimit) * 100,
                logs: receipt.logs.length,
                status: receipt.status,
            });
        }
    }
    
    const avgEff = gasData.reduce((s, g) => s + g.efficiency, 0) / gasData.length;
    const failed = gasData.filter(g => g.status === 0);
    console.log(`  Avg gas efficiency: ${avgEff.toFixed(1)}%`);
    console.log(`  Failed txs: ${failed.length}/${gasData.length}`);
    console.log(`  Most efficient: ${gasData.sort((a,b) => b.efficiency - a.efficiency)[0]?.hash}... (${gasData[0]?.efficiency.toFixed(1)}%)`);
    console.log(`  Least efficient: ${gasData[gasData.length-1]?.hash}... (${gasData[gasData.length-1]?.efficiency.toFixed(1)}%)`);

    console.log("\n✓ ETHERS.JS GRANDMASTER DRILL COMPLETE");
}
main().catch(console.error);
