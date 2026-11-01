const { ethers } = require("ethers");

async function main() {
    const provider = new ethers.JsonRpcProvider("https://ethereum-rpc.publicnode.com");
    const latest = await provider.getBlockNumber();

    // === 1. HD WALLET (FIXED) ===
    console.log("=== 1. HD WALLET DERIVATION ===");
    const mnemonic = "test test test test test test test test test test test junk";
    // FIX: use HDNodeWallet.fromPhrase with path
    for (let i = 0; i < 5; i++) {
        const wallet = ethers.HDNodeWallet.fromPhrase(mnemonic, undefined, `m/44'/60'/0'/0/${i}`);
        console.log(`  m/44'/60'/0'/0/${i}: ${wallet.address}`);
    }
    // Verify Hardhat accounts
    const expected = ["0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266","0x70997970C51812dc3A010C7d01b50e0d17dc79C8","0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"];
    for (let i = 0; i < 3; i++) {
        const w = ethers.HDNodeWallet.fromPhrase(mnemonic, undefined, `m/44'/60'/0'/0/${i}`);
        console.log(`  Account ${i} = Hardhat: ${w.address === expected[i] ? "✓" : "✗"}`);
    }

    // === 2. EIP-7702 DEEP DIVE ===
    console.log("\n=== 2. EIP-7702 DEEP DIVE ===");
    const block = await provider.getBlock(latest, true);
    const txs = block.prefetchedTransactions || [];
    const eip7702 = txs.filter(tx => tx.type === 4);
    console.log(`  EIP-7702 txs: ${eip7702.length}/${txs.length}`);
    for (const tx of eip7702.slice(0, 3)) {
        console.log(`  TX: ${tx.hash.slice(0,14)}...`);
        console.log(`    From: ${tx.from}`);
        if (tx.authorizationList) {
            for (const auth of tx.authorizationList) {
                console.log(`    Auth: chainId=${auth.chainId}, address=${auth.address}, nonce=${auth.nonce}`);
            }
        }
    }
    
    // Check for delegated EOAs (code starts with 0xef0100)
    const senders = [...new Set(txs.map(tx => tx.from))].slice(0, 15);
    let delegated = 0;
    for (const s of senders) {
        const code = await provider.getCode(s);
        if (code !== "0x" && code.startsWith("0xef0100")) {
            delegated++;
            const delegationTarget = ethers.getAddress("0x" + code.slice(6));
            console.log(`  🆕 Delegated EOA: ${s.slice(0,14)}... -> ${delegationTarget.slice(0,14)}...`);
        }
    }
    console.log(`  Delegated EOAs: ${delegated}/${senders.length}`);

    // === 3. ADVANCED: Uniswap V3 Price Oracle ===
    console.log("\n=== 3. UNISWAP V3 PRICE ORACLE ===");
    const UNIV3_USDC_ETH = ethers.getAddress("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640");
    const poolAbi = [
        "function slot0() view returns (uint160 sqrtPriceX96, int24 tick, uint16 observationIndex, uint16 observationCardinality, uint16 observationCardinalityNext, uint8 feeProtocol, bool unlocked)",
        "function observe(uint32[] secondsAgos) view returns (int56[] tickCumulatives, uint160[] secondsPerLiquidityCumulativeX128s)",
        "function fee() view returns (uint24)",
        "function liquidity() view returns (uint128)",
    ];
    const pool = new ethers.Contract(UNIV3_USDC_ETH, poolAbi, provider);
    
    const [slot0, fee, liquidity] = await Promise.all([
        pool.slot0(), pool.fee(), pool.liquidity(),
    ]);
    
    // Calculate price from tick
    const tick = Number(slot0.tick);
    const price = Math.pow(1.0001, tick);
    // USDC/ETH pool: token0=USDC(6dec), token1=ETH(18dec)
    // price = token1/token0 = ETH/USDC
    const ethPrice = 1 / price * Math.pow(10, 12); // adjust for decimal diff
    
    console.log(`  Tick: ${tick}`);
    console.log(`  Fee: ${Number(fee)/10000}%`);
    console.log(`  Liquidity: ${liquidity}`);
    console.log(`  ETH price: ~$${ethPrice.toFixed(2)}`);
    
    // TWAP: observe last 30 minutes
    try {
        const [tickCumulatives] = await pool.observe([1800, 0]);
        const tickDiff = Number(tickCumulatives[1] - tickCumulatives[0]);
        const avgTick = tickDiff / 1800;
        const twapPrice = 1 / Math.pow(1.0001, avgTick) * Math.pow(10, 12);
        console.log(`  30min TWAP tick: ${avgTick.toFixed(2)}`);
        console.log(`  30min TWAP ETH: ~$${twapPrice.toFixed(2)}`);
    } catch (e) {
        console.log(`  TWAP: ${e.shortMessage || "failed"}`);
    }

    // === 4. ADVANCED: Calldata Compression Analysis ===
    console.log("\n=== 4. CALLDATA ANALYSIS ===");
    const calldataSizes = txs.map(tx => (tx.data.length - 2) / 2);
    const sorted = [...calldataSizes].sort((a, b) => a - b);
    const totalCalldata = calldataSizes.reduce((a, b) => a + b, 0);
    
    console.log(`  Txs: ${txs.length}`);
    console.log(`  Total calldata: ${totalCalldata.toLocaleString()} bytes`);
    console.log(`  Min: ${sorted[0]}, Median: ${sorted[Math.floor(sorted.length/2)]}, Max: ${sorted[sorted.length-1]}`);
    console.log(`  Avg: ${(totalCalldata / txs.length).toFixed(0)} bytes/tx`);
    
    // Blob txs carry data cheaper
    const blobTxs = txs.filter(tx => tx.type === 3);
    console.log(`  Blob txs (EIP-4844): ${blobTxs.length}`);
    if (blobTxs.length > 0) {
        for (const btx of blobTxs.slice(0, 2)) {
            console.log(`    ${btx.hash.slice(0,14)}... blobs=${btx.blobVersionedHashes?.length || 0}`);
        }
    }

    // === 5. ADVANCED: Contract Verification via Metadata ===
    console.log("\n=== 5. METADATA VERIFICATION ===");
    const contracts = {
        "Kiln": "0x0A7272e8573aea8359FEC143ac02AED90F822bD0",
        "USDT": ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7"),
        "Multicall3": "0xcA11bde05977b3631167028862bE2a173976CA11",
    };
    
    for (const [name, addr] of Object.entries(contracts)) {
        const code = await provider.getCode(addr);
        const hex = code.slice(2);
        
        // Solidity metadata: CBOR encoded at end
        // Last 2 bytes = length of CBOR data
        const cborLen = parseInt(hex.slice(-4), 16);
        const cborStart = hex.length - 4 - cborLen * 2;
        const cbor = hex.slice(cborStart, -4);
        
        // Check for solc version in CBOR
        const hasSolc = cbor.includes("736f6c63"); // "solc" in hex
        const hasIpfs = cbor.includes("69706673"); // "ipfs" in hex
        
        console.log(`  ${name}: ${(code.length-2)/2} bytes, CBOR=${cborLen}B, solc=${hasSolc?"yes":"no"}, ipfs=${hasIpfs?"yes":"no"}`);
    }

    // === 6. ADVANCED: Nonce Analysis for MEV Bots ===
    console.log("\n=== 6. BOT NONCE ANALYSIS ===");
    const senderNonces = {};
    for (const tx of txs) {
        if (!senderNonces[tx.from]) senderNonces[tx.from] = [];
        senderNonces[tx.from].push(tx.nonce);
    }
    
    // Bots have very high nonces and multiple txs per block
    const bots = Object.entries(senderNonces)
        .filter(([, nonces]) => nonces.length >= 2)
        .map(([addr, nonces]) => ({ addr, count: nonces.length, maxNonce: Math.max(...nonces) }))
        .sort((a, b) => b.maxNonce - a.maxNonce);
    
    console.log(`  Multi-tx senders: ${bots.length}`);
    for (const bot of bots.slice(0, 5)) {
        console.log(`    ${bot.addr.slice(0,14)}... : ${bot.count} txs, maxNonce=${bot.maxNonce.toLocaleString()}`);
    }

    // === 7. ADVANCED: State Root Verification ===
    console.log("\n=== 7. STATE ROOT ===");
    const blockData = await provider.getBlock(latest);
    console.log(`  Block: ${blockData.number}`);
    console.log(`  State root: ${blockData.stateRoot?.slice(0,20)}...`);
    console.log(`  Tx root: ${blockData.transactionsRoot?.slice(0,20)}...`);
    console.log(`  Receipt root: ${blockData.receiptsRoot?.slice(0,20)}...`);
    console.log(`  Parent hash: ${blockData.parentHash?.slice(0,20)}...`);

    console.log("\n✓ GRANDMASTER DRILL 2 COMPLETE");
}
main().catch(console.error);
