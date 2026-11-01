/**
 * ETHERS.JS DEEP DRILL 4: Advanced Security Patterns
 * - Signature malleability
 * - EIP-712 domain separation
 * - Contract interaction simulation
 * - Access control verification
 */
const { ethers } = require("ethers");

async function main() {
    const provider = new ethers.JsonRpcProvider("https://1rpc.io/eth");

    // === 1. SIGNATURE MALLEABILITY CHECK ===
    console.log("=== 1. SIGNATURE MALLEABILITY ===");
    const wallet = ethers.Wallet.createRandom();
    const msg = "test message";
    const sig = await wallet.signMessage(msg);
    
    // Parse signature components
    const sigObj = ethers.Signature.from(sig);
    console.log(`  v: ${sigObj.v}`);
    console.log(`  r: ${sigObj.r.slice(0, 20)}...`);
    console.log(`  s: ${sigObj.s.slice(0, 20)}...`);
    
    // Check for malleability: s should be in lower half of curve
    const secp256k1n = BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141");
    const s = BigInt(sigObj.s);
    const isMalleable = s > secp256k1n / 2n;
    console.log(`  s in lower half: ${!isMalleable ? "✓ (non-malleable)" : "⚠️ MALLEABLE"}`);
    
    // Ethers v6 automatically normalizes s to lower half
    console.log(`  Ethers normalizes: ✓ (always low-s)`);

    // === 2. EIP-712 DOMAIN SEPARATION ===
    console.log("\n=== 2. EIP-712 DOMAIN SEPARATION ===");
    // Different domains produce different hashes (prevents cross-protocol replay)
    const types = {
        Permit: [
            { name: "owner", type: "address" },
            { name: "spender", type: "address" },
            { name: "value", type: "uint256" },
            { name: "nonce", type: "uint256" },
            { name: "deadline", type: "uint256" },
        ]
    };
    const value = {
        owner: wallet.address,
        spender: ethers.getAddress("0x7a250d5630b4cf539739df2c5dacb4c659f2488d"),
        value: ethers.parseEther("1000"),
        nonce: 0,
        deadline: Math.floor(Date.now() / 1000) + 3600,
    };

    // Domain 1: Uniswap
    const domain1 = { name: "Uniswap V2", version: "1", chainId: 1, verifyingContract: ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7") };
    const hash1 = ethers.TypedDataEncoder.hash(domain1, types, value);

    // Domain 2: Different contract (same params)
    const domain2 = { name: "SushiSwap", version: "1", chainId: 1, verifyingContract: ethers.getAddress("0x6b3595068778dd592e39a122f4f5a5cf09c90fe2") };
    const hash2 = ethers.TypedDataEncoder.hash(domain2, types, value);

    // Domain 3: Different chain
    const domain3 = { name: "Uniswap V2", version: "1", chainId: 137, verifyingContract: ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7") };
    const hash3 = ethers.TypedDataEncoder.hash(domain3, types, value);

    console.log(`  Domain 1 (Uni, chain 1):  ${hash1.slice(0, 20)}...`);
    console.log(`  Domain 2 (Sushi, chain 1): ${hash2.slice(0, 20)}...`);
    console.log(`  Domain 3 (Uni, chain 137): ${hash3.slice(0, 20)}...`);
    console.log(`  All different: ${hash1 !== hash2 && hash2 !== hash3 && hash1 !== hash3 ? "✓" : "✗"}`);

    // Sign and verify
    const typedSig = await wallet.signTypedData(domain1, types, value);
    const recovered = ethers.verifyTypedData(domain1, types, value, typedSig);
    console.log(`  Sign + verify: ${recovered === wallet.address ? "✓" : "✗"}`);

    // Cross-domain replay should FAIL
    const crossRecovered = ethers.verifyTypedData(domain2, types, value, typedSig);
    console.log(`  Cross-domain replay: ${crossRecovered === wallet.address ? "⚠️ VULNERABLE" : "✓ BLOCKED"}`);

    // === 3. CONTRACT INTERACTION SIMULATION ===
    console.log("\n=== 3. CONTRACT INTERACTION SIMULATION ===");
    const USDT = ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7");
    const usdtAbi = [
        "function balanceOf(address) view returns (uint256)",
        "function allowance(address,address) view returns (uint256)",
        "function totalSupply() view returns (uint256)",
        "function transfer(address,uint256) returns (bool)",
        "function approve(address,uint256) returns (bool)",
    ];
    const usdt = new ethers.Contract(USDT, usdtAbi, provider);

    // Simulate a transfer (read-only, will revert but shows the error)
    try {
        await usdt.transfer.staticCall(ethers.ZeroAddress, 1, { from: wallet.address });
        console.log("  Transfer simulation: SUCCESS (unexpected)");
    } catch (e) {
        console.log(`  Transfer simulation: REVERTED (expected - no balance)`);
        console.log(`  Error: ${e.shortMessage || e.message.slice(0, 60)}`);
    }

    // Estimate gas for a real transfer
    try {
        const vitalik = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045";
        const gasEstimate = await usdt.transfer.estimateGas(vitalik, 1000000, { from: vitalik });
        console.log(`  Gas estimate (USDT transfer): ${gasEstimate.toLocaleString()}`);
    } catch (e) {
        console.log(`  Gas estimate failed: ${e.shortMessage || "insufficient balance"}`);
    }

    // === 4. ACCESS CONTROL VERIFICATION ===
    console.log("\n=== 4. ACCESS CONTROL PATTERNS ===");
    // Check who can call what on USDT
    const owner = await usdt.owner ? await usdt.owner() : "N/A";
    console.log(`  USDT owner: ${owner}`);

    // Check Kiln access control via multicall
    const KILN = "0x0A7272e8573aea8359FEC143ac02AED90F822bD0";
    const kilnAbi = [
        "function getAdmin() view returns (address)",
        "function getTreasury() view returns (address)",
        "function getGlobalFee() view returns (uint256)",
        "function getOperatorFee() view returns (uint256)",
        "function getDepositsStopped() view returns (bool)",
        "function getPendingAdmin() view returns (address)",
    ];
    const kiln = new ethers.Contract(KILN, kilnAbi, provider);

    try {
        const [admin, treasury, gFee, oFee, stopped, pending] = await Promise.all([
            kiln.getAdmin(), kiln.getTreasury(), kiln.getGlobalFee(),
            kiln.getOperatorFee(), kiln.getDepositsStopped(), kiln.getPendingAdmin(),
        ]);
        console.log(`  Kiln admin: ${admin}`);
        console.log(`  Kiln treasury: ${treasury}`);
        console.log(`  Kiln globalFee: ${gFee} bps`);
        console.log(`  Kiln operatorFee: ${oFee} bps`);
        console.log(`  Kiln depositsStopped: ${stopped}`);
        console.log(`  Kiln pendingAdmin: ${pending}`);
        
        // Security check: admin should not be zero
        if (admin === ethers.ZeroAddress) {
            console.log("  ⚠️ ADMIN IS ZERO ADDRESS - This is the implementation, not proxy!");
        }
    } catch (e) {
        console.log(`  Kiln read failed: ${e.shortMessage || e.message.slice(0, 60)}`);
    }

    // === 5. NONCE MANAGEMENT (security) ===
    console.log("\n=== 5. NONCE SECURITY ===");
    const nonce = await provider.getTransactionCount(wallet.address);
    const pendingNonce = await provider.getTransactionCount(wallet.address, "pending");
    console.log(`  Confirmed nonce: ${nonce}`);
    console.log(`  Pending nonce: ${pendingNonce}`);
    console.log(`  Nonce gap: ${pendingNonce - nonce} (should be 0 for new wallet)`);

    // === 6. CHAIN REPLAY PROTECTION ===
    console.log("\n=== 6. CHAIN REPLAY PROTECTION ===");
    const network = await provider.getNetwork();
    console.log(`  Chain ID: ${network.chainId}`);
    console.log(`  EIP-155: tx includes chainId in signing hash`);
    console.log(`  EIP-1559: type 2 tx with maxFeePerGas`);
    
    // Build a tx and verify chainId is embedded
    const tx = {
        to: ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7"),
        value: 0, data: "0x", chainId: network.chainId, nonce: 0,
        gasLimit: 21000, maxFeePerGas: ethers.parseUnits("5", "gwei"),
        maxPriorityFeePerGas: ethers.parseUnits("1", "gwei"),
    };
    const signed = await wallet.signTransaction(tx);
    const parsed = ethers.Transaction.from(signed);
    console.log(`  Signed tx chainId: ${parsed.chainId}`);
    console.log(`  Replay protected: ${parsed.chainId === network.chainId ? "✓" : "✗"}`);

    console.log("\n✓ ETHERS.JS DEEP DRILL 4 COMPLETE");
}
main().catch(console.error);
