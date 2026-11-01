/**
 * ETHERS.JS MASTER DRILL 1: Advanced Security Tooling
 * - Sandwich detection with profit calculation
 * - Access list analysis (EIP-2930)
 * - Blob tx detection (EIP-4844)
 * - Real-time alerting system
 * - Advanced ABI: tuple/struct decoding
 */
const { ethers } = require("ethers");

async function main() {
    const provider = new ethers.JsonRpcProvider("https://ethereum-rpc.publicnode.com");
    const latest = await provider.getBlockNumber();

    // === 1. SANDWICH DETECTION WITH PROFIT ===
    console.log("=== 1. SANDWICH DETECTION ===");
    const SWAP_TOPIC = ethers.id("Swap(address,uint256,uint256,uint256,uint256,address)");
    const TRANSFER_TOPIC = ethers.id("Transfer(address,address,uint256)");
    
    // Scan last 3 blocks
    for (let offset = 0; offset < 3; offset++) {
        const blockNum = latest - offset;
        const block = await provider.getBlock(blockNum, true);
        const txs = block.prefetchedTransactions || [];
        
        // Get all receipts
        const receipts = await Promise.all(
            txs.slice(0, 30).map(tx => provider.getTransactionReceipt(tx.hash))
        );
        
        // Find swap txs
        const swapTxs = [];
        for (let i = 0; i < receipts.length; i++) {
            const r = receipts[i];
            if (!r) continue;
            const swaps = r.logs.filter(l => l.topics[0] === SWAP_TOPIC);
            if (swaps.length > 0) {
                swapTxs.push({ tx: txs[i], receipt: r, swaps, index: i });
            }
        }
        
        // Group by sender
        const bySender = {};
        for (const st of swapTxs) {
            const sender = st.tx.from;
            if (!bySender[sender]) bySender[sender] = [];
            bySender[sender].push(st);
        }
        
        // Check for sandwiches
        for (const [sender, sts] of Object.entries(bySender)) {
            if (sts.length >= 2) {
                const first = sts[0];
                const last = sts[sts.length - 1];
                
                // Decode swaps
                const swapAbi = ["event Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)"];
                const iface = new ethers.Interface(swapAbi);
                
                const firstSwap = iface.parseLog({ topics: first.swaps[0].topics, data: first.swaps[0].data });
                const lastSwap = iface.parseLog({ topics: last.swaps[0].topics, data: last.swaps[0].data });
                
                if (first.swaps[0].address === last.swaps[0].address) {
                    // Same pair - check direction
                    const buy = firstSwap.args.amount0In > 0n && firstSwap.args.amount1Out > 0n;
                    const sell = lastSwap.args.amount1In > 0n && lastSwap.args.amount0Out > 0n;
                    
                    if (buy && sell) {
                        const victims = swapTxs.filter(st => st.index > first.index && st.index < last.index);
                        const profit = lastSwap.args.amount0Out - firstSwap.args.amount0In;
                        console.log(`  🥪 Block ${blockNum}: ${sender.slice(0,14)}...`);
                        console.log(`     Buy: ${firstSwap.args.amount0In} -> ${firstSwap.args.amount1Out}`);
                        console.log(`     Sell: ${lastSwap.args.amount1In} -> ${lastSwap.args.amount0Out}`);
                        console.log(`     Victims: ${victims.length}, Profit: ${profit}`);
                    }
                }
            }
        }
        
        if (offset === 0) {
            console.log(`  Block ${blockNum}: ${txs.length} txs, ${swapTxs.length} with swaps`);
        }
    }

    // === 2. EIP-4844 BLOB TX DETECTION ===
    console.log("\n=== 2. EIP-4844 BLOB TX DETECTION ===");
    const block = await provider.getBlock(latest, true);
    const txs = block.prefetchedTransactions || [];
    
    let blobTxs = 0, eip1559Txs = 0, legacyTxs = 0, eip2930Txs = 0;
    for (const tx of txs) {
        switch (tx.type) {
            case 0: legacyTxs++; break;
            case 1: eip2930Txs++; break;
            case 2: eip1559Txs++; break;
            case 3: blobTxs++; break;
        }
    }
    console.log(`  Block ${latest}: ${txs.length} txs`);
    console.log(`    Legacy (type 0): ${legacyTxs}`);
    console.log(`    EIP-2930 (type 1): ${eip2930Txs}`);
    console.log(`    EIP-1559 (type 2): ${eip1559Txs}`);
    console.log(`    EIP-4844 blob (type 3): ${blobTxs}`);
    
    // Check blob gas
    if (block.blobGasUsed !== undefined && block.blobGasUsed !== null) {
        console.log(`    Blob gas used: ${block.blobGasUsed}`);
        console.log(`    Excess blob gas: ${block.excessBlobGas}`);
    }

    // === 3. ACCESS LIST ANALYSIS ===
    console.log("\n=== 3. ACCESS LIST ANALYSIS ===");
    // EIP-2930/1559 txs can have access lists
    const txsWithAccessList = txs.filter(tx => tx.accessList && tx.accessList.length > 0);
    console.log(`  Txs with access lists: ${txsWithAccessList.length}/${txs.length}`);
    for (const tx of txsWithAccessList.slice(0, 3)) {
        console.log(`    ${tx.hash.slice(0,14)}... : ${tx.accessList.length} addresses`);
        for (const item of tx.accessList.slice(0, 2)) {
            console.log(`      ${item.address.slice(0,14)}... : ${item.storageKeys.length} slots`);
        }
    }

    // === 4. ADVANCED ABI: TUPLE/STRUCT DECODING ===
    console.log("\n=== 4. TUPLE/STRUCT DECODING ===");
    // Uniswap V3 Pool.slot0() returns a struct
    const UNIV3_POOL = ethers.getAddress("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"); // USDC/ETH
    const poolAbi = [
        "function slot0() view returns (uint160 sqrtPriceX96, int24 tick, uint16 observationIndex, uint16 observationCardinality, uint16 observationCardinalityNext, uint8 feeProtocol, bool unlocked)",
        "function liquidity() view returns (uint128)",
        "function fee() view returns (uint24)",
        "function token0() view returns (address)",
        "function token1() view returns (address)",
    ];
    
    try {
        const pool = new ethers.Contract(UNIV3_POOL, poolAbi, provider);
        const [slot0, liquidity, fee, token0, token1] = await Promise.all([
            pool.slot0(), pool.liquidity(), pool.fee(), pool.token0(), pool.token1(),
        ]);
        
        // Decode sqrtPriceX96 to actual price
        const sqrtPrice = slot0.sqrtPriceX96;
        const price = Number(sqrtPrice) ** 2 / (2 ** 192);
        // For USDC/ETH: price = USDC per ETH (adjusted for decimals)
        const adjustedPrice = price * (10 ** 18) / (10 ** 6);
        
        console.log(`  Uniswap V3 USDC/ETH Pool:`);
        console.log(`    sqrtPriceX96: ${sqrtPrice}`);
        console.log(`    tick: ${slot0.tick}`);
        console.log(`    fee: ${fee} (${Number(fee)/10000}%)`);
        console.log(`    liquidity: ${liquidity}`);
        console.log(`    token0: ${token0.slice(0,14)}...`);
        console.log(`    token1: ${token1.slice(0,14)}...`);
        console.log(`    Price (approx): ${adjustedPrice.toFixed(2)} USDC/ETH`);
        console.log(`    unlocked: ${slot0.unlocked}`);
    } catch (e) {
        console.log(`  Uniswap V3 read failed: ${e.shortMessage || e.message.slice(0, 60)}`);
    }

    // === 5. REAL-TIME ALERTING SYSTEM ===
    console.log("\n=== 5. REAL-TIME ALERTING (3 blocks) ===");
    const USDT = ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7");
    const usdt = new ethers.Contract(USDT, ["event Transfer(address indexed from, address indexed to, uint256 value)"], provider);
    
    let alertCount = 0;
    const WHALE_THRESHOLD = BigInt(1_000_000) * BigInt(10**6); // $1M
    
    await new Promise((resolve) => {
        const filter = usdt.filters.Transfer();
        usdt.on(filter, (from, to, value, event) => {
            if (value > WHALE_THRESHOLD) {
                alertCount++;
                console.log(`  🐋 WHALE: $${(Number(value) / 10**6).toLocaleString()} USDT`);
                console.log(`     ${from.slice(0,14)}... -> ${to.slice(0,14)}...`);
                console.log(`     Block: ${event.log.blockNumber}, TX: ${event.log.transactionHash.slice(0,14)}...`);
            }
        });
        
        // Also monitor new blocks
        let blockCount = 0;
        provider.on("block", (blockNum) => {
            blockCount++;
            if (blockCount >= 3) {
                usdt.removeAllListeners();
                provider.removeAllListeners("block");
                resolve();
            }
        });
        
        setTimeout(() => {
            usdt.removeAllListeners();
            provider.removeAllListeners("block");
            resolve();
        }, 30000);
    });
    
    if (alertCount === 0) {
        console.log(`  No whale transfers in monitored blocks`);
    }
    console.log(`  Total whale alerts: ${alertCount}`);

    // === 6. ADVANCED: Contract Verification Status ===
    console.log("\n=== 6. VERIFICATION STATUS ===");
    // Check if contracts are verified by comparing bytecode patterns
    const contracts = {
        "Kiln": "0x0A7272e8573aea8359FEC143ac02AED90F822bD0",
        "USDT": USDT,
        "Multicall3": "0xcA11bde05977b3631167028862bE2a173976CA11",
    };
    
    for (const [name, addr] of Object.entries(contracts)) {
        const code = await provider.getCode(addr);
        const size = (code.length - 2) / 2;
        // Solidity metadata: last 2 bytes = length of CBOR, then CBOR data
        // CBOR starts with 0xa2 (map with 2 entries)
        const lastBytes = code.slice(-10);
        const hasMetadata = code.includes("a264") || code.includes("a265");
        const solcVersion = hasMetadata ? code.slice(-8, -4) : "unknown";
        
        console.log(`  ${name}: ${size} bytes, metadata=${hasMetadata ? "yes" : "no"}`);
    }

    console.log("\n✓ ETHERS.JS MASTER DRILL 1 COMPLETE");
}
main().catch(console.error);
