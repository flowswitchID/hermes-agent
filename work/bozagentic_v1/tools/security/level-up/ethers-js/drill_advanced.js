const { ethers } = require("ethers");

async function main() {
    console.log("=".repeat(60));
    console.log("ETHERS.JS ADVANCED DRILL");
    console.log("=".repeat(60));
    
    const RPC = "https://ethereum-rpc.publicnode.com";
    const provider = new ethers.JsonRpcProvider(RPC);
    
    // === 1. ABI Encode/Decode Manual ===
    console.log("\n[1] ABI Encode/Decode Manual");
    const iface = new ethers.Interface([
        "function transfer(address to, uint256 amount) returns (bool)",
        "function balanceOf(address) view returns (uint256)",
        "event Transfer(address indexed from, address indexed to, uint256 value)"
    ]);
    
    // Encode function call
    const encoded = iface.encodeFunctionData("transfer", [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        ethers.parseEther("1.5")
    ]);
    console.log(`  transfer() calldata: ${encoded.slice(0, 40)}...`);
    console.log(`  Selector: ${encoded.slice(0, 10)}`);
    
    // Decode function call
    const decoded = iface.decodeFunctionData("transfer", encoded);
    console.log(`  Decoded: to=${decoded[0].slice(0,12)}..., amount=${ethers.formatEther(decoded[1])}`);
    
    // Encode/decode event
    const eventTopic = iface.getEvent("Transfer").topicHash;
    console.log(`  Transfer topic: ${eventTopic}`);
    
    // === 2. Contract Deployment (dry run — no private key) ===
    console.log("\n[2] Contract Deployment Pattern");
    const SimpleStorage = new ethers.ContractFactory(
        ["function set(uint256 x)", "function get() view returns (uint256)"],
        "0x608060405234801561001057600080fd5b50610150806100206000396000f3fe", // minimal bytecode
        null // no signer (dry run)
    );
    console.log(`  Factory created: ${SimpleStorage.interface.fragments.length} functions`);
    console.log(`  Deploy tx would cost: ~${ethers.formatEther(21000n * 30000000000n)} ETH (estimate)`);
    
    // === 3. Transaction Signing Pattern ===
    console.log("\n[3] Transaction Signing (offline)");
    // Create a random wallet for demo (NOT a real key)
    const wallet = ethers.Wallet.createRandom();
    console.log(`  Random wallet: ${wallet.address}`);
    
    const tx = {
        to: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        value: ethers.parseEther("0.001"),
        nonce: 0,
        gasLimit: 21000,
        maxFeePerGas: ethers.parseUnits("30", "gwei"),
        maxPriorityFeePerGas: ethers.parseUnits("1", "gwei"),
        chainId: 1
    };
    
    const signedTx = await wallet.signTransaction(tx);
    console.log(`  Signed tx: ${signedTx.slice(0, 40)}...`);
    console.log(`  Tx hash: ${ethers.keccak256(signedTx)}`);
    
    // Parse it back
    const parsed = ethers.Transaction.from(signedTx);
    console.log(`  Parsed: to=${parsed.to?.slice(0,12)}..., value=${ethers.formatEther(parsed.value)}`);
    
    // === 4. Error Handling Patterns ===
    console.log("\n[4] Error Handling Patterns");
    try {
        // This will fail — calling a non-contract
        const bad = new ethers.Contract("0x0000000000000000000000000000000000000001", 
            ["function foo()"], provider);
        await bad.foo();
    } catch (e) {
        if (e.code === "CALL_EXCEPTION") {
            console.log(`  CALL_EXCEPTION: ${e.message.slice(0, 80)}`);
        } else if (e.code === "NETWORK_ERROR") {
            console.log(`  NETWORK_ERROR: ${e.message.slice(0, 80)}`);
        } else {
            console.log(`  Error (${e.code}): ${e.message.slice(0, 80)}`);
        }
    }
    
    // === 5. WebSocket Pattern (subscription) ===
    console.log("\n[5] WebSocket Subscription Pattern");
    try {
        const wsProvider = new ethers.WebSocketProvider("wss://ethereum-rpc.publicnode.com");
        
        // Subscribe to new blocks
        let blockCount = 0;
        const blockPromise = new Promise((resolve) => {
            wsProvider.on("block", (blockNumber) => {
                blockCount++;
                console.log(`  New block: ${blockNumber}`);
                if (blockCount >= 2) {
                    wsProvider.removeAllListeners();
                    resolve();
                }
            });
        });
        
        // Wait for 2 blocks with timeout
        await Promise.race([
            blockPromise,
            new Promise(resolve => setTimeout(resolve, 30000))
        ]);
        
        if (blockCount === 0) {
            console.log("  WebSocket: no blocks received (30s timeout)");
        }
        wsProvider.destroy();
    } catch (e) {
        console.log(`  WebSocket error: ${e.message.slice(0, 80)}`);
    }
    
    // === 6. Multicall with Error Handling ===
    console.log("\n[6] Multicall with allowFailure");
    const MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11";
    const multicallAbi = [
        "function aggregate3(tuple(address target, bool allowFailure, bytes callData)[] calls) view returns (tuple(bool success, bytes returnData)[])"
    ];
    const multicall = new ethers.Contract(MULTICALL3, multicallAbi, provider);
    
    const erc20Iface = new ethers.Interface(["function balanceOf(address) view returns (uint256)"]);
    
    // Mix of valid and invalid calls
    const calls = [
        { target: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", allowFailure: true, 
          callData: erc20Iface.encodeFunctionData("balanceOf", ["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"]) },
        { target: "0x0000000000000000000000000000000000000001", allowFailure: true, // will fail
          callData: erc20Iface.encodeFunctionData("balanceOf", ["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"]) },
        { target: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", allowFailure: true,
          callData: erc20Iface.encodeFunctionData("balanceOf", ["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"]) },
    ];
    
    try {
        const results = await multicall.aggregate3(calls);
        for (let i = 0; i < results.length; i++) {
            if (results[i].success) {
                const bal = BigInt("0x" + results[i].returnData.slice(2));
                console.log(`  Call ${i}: SUCCESS, balance=${ethers.formatEther(bal)}`);
            } else {
                console.log(`  Call ${i}: FAILED (allowFailure=true, no revert)`);
            }
        }
    } catch (e) {
        console.log(`  Multicall error: ${e.message.slice(0, 80)}`);
    }
    
    console.log("\n" + "=".repeat(60));
    console.log("ETHERS.JS ADVANCED DRILL COMPLETE — 6/6");
    console.log("=".repeat(60));
}

main().catch(console.error);
