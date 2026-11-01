const { ethers } = require("ethers");

async function main() {
    console.log("=== ETHERS.JS: WebSocket + Multicall fix ===");
    
    const RPC = "https://ethereum-rpc.publicnode.com";
    const provider = new ethers.JsonRpcProvider(RPC);
    
    // [5] WebSocket — proper cleanup
    console.log("\n[5] WebSocket (fixed cleanup)");
    try {
        const wsProvider = new ethers.WebSocketProvider("wss://ethereum-rpc.publicnode.com");
        
        let blockCount = 0;
        await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                console.log("  WS timeout (30s)");
                resolve();
            }, 30000);
            
            wsProvider.on("block", (blockNumber) => {
                blockCount++;
                console.log(`  Block: ${blockNumber}`);
                if (blockCount >= 2) {
                    clearTimeout(timeout);
                    resolve();
                }
            });
            
            wsProvider.on("error", (e) => {
                console.log(`  WS error: ${e.message.slice(0, 60)}`);
                clearTimeout(timeout);
                resolve();
            });
        });
        
        // Proper cleanup
        wsProvider.removeAllListeners();
        try { wsProvider.destroy(); } catch(e) {}
        console.log(`  Received ${blockCount} blocks`);
    } catch (e) {
        console.log(`  WS failed: ${e.message.slice(0, 60)}`);
    }
    
    // [6] Multicall with allowFailure (separate provider)
    console.log("\n[6] Multicall with allowFailure");
    const MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11";
    const multicallAbi = [
        "function aggregate3(tuple(address target, bool allowFailure, bytes callData)[] calls) view returns (tuple(bool success, bytes returnData)[])"
    ];
    const multicall = new ethers.Contract(MULTICALL3, multicallAbi, provider);
    const erc20Iface = new ethers.Interface(["function balanceOf(address) view returns (uint256)"]);
    
    const vitalik = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045";
    const calls = [
        { target: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", allowFailure: true, 
          callData: erc20Iface.encodeFunctionData("balanceOf", [vitalik]) },
        { target: "0x0000000000000000000000000000000000000001", allowFailure: true,
          callData: erc20Iface.encodeFunctionData("balanceOf", [vitalik]) },
        { target: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", allowFailure: true,
          callData: erc20Iface.encodeFunctionData("balanceOf", [vitalik]) },
    ];
    
    try {
        const results = await multicall.aggregate3(calls);
        const tokens = ["WETH", "INVALID", "USDC"];
        for (let i = 0; i < results.length; i++) {
            if (results[i].success && results[i].returnData !== "0x") {
                const bal = BigInt("0x" + results[i].returnData.slice(2));
                const decimals = i === 2 ? 6 : 18;
                console.log(`  ${tokens[i]}: ${ethers.formatUnits(bal, decimals)}`);
            } else {
                console.log(`  ${tokens[i]}: FAILED (expected)`);
            }
        }
    } catch (e) {
        console.log(`  Multicall error: ${e.message.slice(0, 80)}`);
    }
    
    console.log("\n=== ETHERS.JS ADVANCED: 6/6 COMPLETE ===");
}

main().catch(console.error);
