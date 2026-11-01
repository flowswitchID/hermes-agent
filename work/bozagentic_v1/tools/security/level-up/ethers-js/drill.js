const { ethers } = require("ethers");

async function main() {
    console.log("=".repeat(60));
    console.log("ETHERS.JS DRILL: MULTICALL + EVENTS + PROVIDER");
    console.log("=".repeat(60));
    
    const RPC = "https://ethereum-rpc.publicnode.com";
    const provider = new ethers.JsonRpcProvider(RPC);
    
    // === DRILL 1: Provider management + health check ===
    console.log("\n[1] Provider Management");
    try {
        const network = await provider.getNetwork();
        console.log(`  Network: ${network.name} (chainId: ${network.chainId})`);
        const blockNumber = await provider.getBlockNumber();
        console.log(`  Block: ${blockNumber}`);
        const gasPrice = await provider.getFeeData();
        console.log(`  Gas: maxFee=${ethers.formatUnits(gasPrice.maxFeePerGas, "gwei")} gwei`);
    } catch (e) {
        console.log(`  Provider error: ${e.message}`);
        return;
    }
    
    // === DRILL 2: Multicall3 — batch reads ===
    console.log("\n[2] Multicall3 — Batch Reads");
    const MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11";
    const multicallAbi = [
        "function aggregate3(tuple(address target, bool allowFailure, bytes callData)[] calls) view returns (tuple(bool success, bytes returnData)[])"
    ];
    const multicall = new ethers.Contract(MULTICALL3, multicallAbi, provider);
    
    // Batch: read WETH balance of 3 addresses + total supply
    const WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2";
    const erc20Abi = [
        "function balanceOf(address) view returns (uint256)",
        "function totalSupply() view returns (uint256)",
        "function symbol() view returns (string)"
    ];
    const iface = new ethers.Interface(erc20Abi);
    
    const calls = [
        { target: WETH, allowFailure: false, callData: iface.encodeFunctionData("balanceOf", ["0x00000000219ab540356cBB839Cbe05303d7705Fa"]) },
        { target: WETH, allowFailure: false, callData: iface.encodeFunctionData("balanceOf", ["0xdAC17F958D2ee523a2206206994597C13D831ec7"]) },
        { target: WETH, allowFailure: false, callData: iface.encodeFunctionData("totalSupply") },
        { target: WETH, allowFailure: false, callData: iface.encodeFunctionData("symbol") },
    ];
    
    try {
        const results = await multicall.aggregate3(calls);
        console.log(`  Batch ${calls.length} calls in 1 RPC request:`);
        console.log(`    WETH bal (deposit contract): ${ethers.formatEther(results[0].returnData ? BigInt("0x" + results[0].returnData.slice(2)) : 0n)}`);
        console.log(`    WETH totalSupply: ${ethers.formatEther(BigInt("0x" + results[2].returnData.slice(2)))}`);
        console.log(`    Symbol: ${iface.decodeFunctionResult("symbol", results[3].returnData)[0]}`);
    } catch (e) {
        console.log(`  Multicall error: ${e.message}`);
    }
    
    // === DRILL 3: Event decoding ===
    console.log("\n[3] Event Decoding — WETH Deposit events");
    const wethContract = new ethers.Contract(WETH, [
        "event Deposit(address indexed dst, uint256 wad)",
        "event Withdrawal(address indexed src, uint256 wad)",
        "event Transfer(address indexed from, address indexed to, uint256 value)"
    ], provider);
    
    try {
        const currentBlock = await provider.getBlockNumber();
        // Get last 10 blocks of Transfer events
        const filter = wethContract.filters.Transfer();
        const events = await wethContract.queryFilter(filter, currentBlock - 5, currentBlock);
        console.log(`  Found ${events.length} Transfer events in last 5 blocks`);
        for (const evt of events.slice(0, 5)) {
            const decoded = {
                from: evt.args[0],
                to: evt.args[1],
                value: ethers.formatEther(evt.args[2]),
                block: evt.blockNumber,
                txHash: evt.transactionHash.slice(0, 16) + "..."
            };
            console.log(`    ${decoded.value} WETH: ${decoded.from.slice(0,10)}→${decoded.to.slice(0,10)} @${decoded.block}`);
        }
    } catch (e) {
        console.log(`  Event query error: ${e.message}`);
    }
    
    // === DRILL 4: Contract interaction patterns ===
    console.log("\n[4] Contract Read Patterns");
    const USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48";
    const usdc = new ethers.Contract(USDC, erc20Abi, provider);
    
    try {
        const [symbol, totalSupply, bal] = await Promise.all([
            usdc.symbol(),
            usdc.totalSupply(),
            usdc.balanceOf("0x00000000219ab540356cBB839Cbe05303d7705Fa")
        ]);
        console.log(`  ${symbol}: supply=${ethers.formatUnits(totalSupply, 6)}, deposit_bal=${ethers.formatUnits(bal, 6)}`);
    } catch (e) {
        console.log(`  USDC error: ${e.message}`);
    }
    
    // === DRILL 5: ENS resolution ===
    console.log("\n[5] ENS Resolution");
    try {
        const addr = await provider.resolveName("vitalik.eth");
        console.log(`  vitalik.eth → ${addr}`);
        const name = await provider.lookupAddress(addr);
        console.log(`  Reverse: ${name}`);
    } catch (e) {
        console.log(`  ENS error: ${e.message}`);
    }
    
    // === DRILL 6: Transaction analysis ===
    console.log("\n[6] Transaction Analysis");
    try {
        const latestBlock = await provider.getBlock("latest", true);
        if (latestBlock && latestBlock.prefetchedTransactions) {
            const txs = latestBlock.prefetchedTransactions;
            console.log(`  Block ${latestBlock.number}: ${txs.length} txs`);
            const sorted = txs.sort((a, b) => Number(b.gasPrice - a.gasPrice));
            for (const tx of sorted.slice(0, 3)) {
                console.log(`    ${tx.hash.slice(0,16)}... gas=${ethers.formatUnits(tx.gasPrice, "gwei")}gwei to=${tx.to?.slice(0,10)}`);
            }
        } else {
            console.log(`  Block ${latestBlock?.number}: prefetched txs not available`);
        }
    } catch (e) {
        console.log(`  Block error: ${e.message}`);
    }
    
    console.log("\n" + "=".repeat(60));
    console.log("ETHERS.JS DRILL COMPLETE");
    console.log("=".repeat(60));
}

main().catch(console.error);
