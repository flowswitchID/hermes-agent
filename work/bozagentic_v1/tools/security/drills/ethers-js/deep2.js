const { ethers } = require("ethers");

async function main() {
    const provider = new ethers.JsonRpcProvider("https://1rpc.io/eth");
    const latest = await provider.getBlockNumber();

    // === 1. ADVANCED ABI ===
    console.log("=== 1. ADVANCED ABI ENCODING ===");
    const complexAbi = [
        "function swapExactTokensForTokens(uint256,uint256,address[],address,uint256) returns (uint256[])",
        "error InsufficientBalance(uint256 available, uint256 required)",
    ];
    const iface = new ethers.Interface(complexAbi);
    const path = [
        ethers.getAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"),
        ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7"),
    ];
    const calldata = iface.encodeFunctionData("swapExactTokensForTokens", [
        ethers.parseEther("1"), 0, path, ethers.ZeroAddress, Math.floor(Date.now()/1000) + 3600,
    ]);
    const decoded = iface.parseTransaction({ data: calldata });
    console.log(`  Encoded: ${calldata.slice(0, 10)}... (${calldata.length/2 - 1} bytes)`);
    console.log(`  Decoded: ${decoded.name}, amountIn=${ethers.formatEther(decoded.args[0])}, path=${decoded.args[2].length} tokens`);

    const errorData = iface.encodeErrorResult("InsufficientBalance", [100, 200]);
    const decodedError = iface.parseError(errorData);
    console.log(`  Error: ${decodedError.name}(${decodedError.args[0]}, ${decodedError.args[1]})`);

    // === 2. CROSS-CHAIN ===
    console.log("\n=== 2. CROSS-CHAIN ===");
    const chains = {
        "Ethereum": new ethers.JsonRpcProvider("https://1rpc.io/eth"),
        "Base": new ethers.JsonRpcProvider("https://mainnet.base.org"),
    };
    const erc20Abi = ["function symbol() view returns (string)", "function totalSupply() view returns (uint256)", "function decimals() view returns (uint8)"];
    const addrs = { "Ethereum": "0xa0b86991c627ce246199b89ff4b35b54c5c85687", "Base": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913" };
    for (const [chain, prov] of Object.entries(chains)) {
        try {
            const token = new ethers.Contract(ethers.getAddress(addrs[chain]), erc20Abi, prov);
            const [sym, supply, dec] = await Promise.all([token.symbol(), token.totalSupply(), token.decimals()]);
            console.log(`  ${chain}: ${sym} supply=${ethers.formatUnits(supply, dec)} block=${await prov.getBlockNumber()}`);
        } catch(e) { console.log(`  ${chain}: failed`); }
    }

    // === 3. WALLET + SIGNING ===
    console.log("\n=== 3. WALLET OPERATIONS ===");
    const wallet = ethers.Wallet.createRandom();
    const message = "Hello Alpenglow!";
    const sig = await wallet.signMessage(message);
    const recovered = ethers.verifyMessage(message, sig);
    console.log(`  Address: ${wallet.address}`);
    console.log(`  EIP-191 verify: ${recovered === wallet.address ? "PASS" : "FAIL"}`);

    const domain = { name: "Test", version: "1", chainId: 1, verifyingContract: ethers.ZeroAddress };
    const types = { Person: [{ name: "name", type: "string" }, { name: "wallet", type: "address" }] };
    const value = { name: "Spectrum", wallet: wallet.address };
    const typedSig = await wallet.signTypedData(domain, types, value);
    const typedRecovered = ethers.verifyTypedData(domain, types, value, typedSig);
    console.log(`  EIP-712 verify: ${typedRecovered === wallet.address ? "PASS" : "FAIL"}`);

    // === 4. RAW TX ===
    console.log("\n=== 4. RAW TX CONSTRUCTION ===");
    const tx = {
        to: ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7"),
        value: 0, data: "0xa9059cbb" + "0".repeat(64), chainId: 1, nonce: 0,
        gasLimit: 60000, maxFeePerGas: ethers.parseUnits("5", "gwei"),
        maxPriorityFeePerGas: ethers.parseUnits("1", "gwei"),
    };
    const signedTx = await wallet.signTransaction(tx);
    const parsed = ethers.Transaction.from(signedTx);
    console.log(`  Signed: ${signedTx.slice(0, 30)}... (${signedTx.length/2 - 1} bytes)`);
    console.log(`  From: ${parsed.from}, Type: ${parsed.type} (EIP-1559), Chain: ${parsed.chainId}`);

    // === 5. DEPLOYMENT PREDICTION ===
    console.log("\n=== 5. DEPLOYMENT PREDICTION ===");
    console.log(`  CREATE (nonce 0): ${ethers.getCreateAddress({ from: wallet.address, nonce: 0 })}`);
    console.log(`  CREATE (nonce 1): ${ethers.getCreateAddress({ from: wallet.address, nonce: 1 })}`);
    const salt = ethers.ZeroHash;
    const initCodeHash = ethers.keccak256("0x6080604052348015600f57600080fd5b50603f80601d6000396000f3fe");
    console.log(`  CREATE2: ${ethers.getCreate2Address(wallet.address, salt, initCodeHash)}`);

    // === 6. LOG BLOOM ===
    console.log("\n=== 6. LOG BLOOM ===");
    const block = await provider.getBlock(latest - 1);
    console.log(`  Bloom: ${block.logsBloom.slice(0, 30)}... (${(block.logsBloom.length-2)/2} bytes)`);

    console.log("\n✓ ETHERS.JS DEEP DRILL 2 COMPLETE");
}
main().catch(console.error);
