/**
 * ETHERS.JS TRANSCENDENT: Full Automated Security Scanner + Cross-Chain
 */
const { ethers } = require("ethers");

async function scanContract(provider, addr, name) {
    console.log(`\n${"=".repeat(60)}`);
    console.log(`SCANNING: ${name || addr}`);
    console.log(`${"=".repeat(60)}`);
    
    const findings = [];
    let risk = 0;
    
    const code = await provider.getCode(addr);
    if (code === "0x") {
        console.log("  NO CODE (EOA or destroyed)");
        return { risk: 0, findings: ["EOA"] };
    }
    
    const bytes = Buffer.from(code.slice(2), 'hex');
    const size = bytes.length;
    
    // === 1. BYTECODE ===
    console.log(`\n  [BYTECODE]`);
    console.log(`  Size: ${size} bytes (${(size/24576*100).toFixed(1)}% of EIP-170)`);
    
    // Count opcodes properly
    let counts = {};
    let i = 0;
    while (i < bytes.length) {
        const op = bytes[i];
        const names = {0x54:'SLOAD',0x55:'SSTORE',0xf1:'CALL',0xf2:'CALLCODE',0xf4:'DELEGATECALL',
            0xfa:'STATICCALL',0xf0:'CREATE',0xf5:'CREATE2',0xff:'SELFDESTRUCT',0xfd:'REVERT',
            0x56:'JUMP',0x57:'JUMPI',0x5b:'JUMPDEST',0x20:'KECCAK256',0x32:'ORIGIN',0x42:'TIMESTAMP'};
        if (names[op]) counts[names[op]] = (counts[names[op]] || 0) + 1;
        if (op >= 0x60 && op <= 0x7f) i += (op - 0x5f) + 1;
        else i++;
    }
    
    if (counts['SELFDESTRUCT']) { findings.push(`SELFDESTRUCT x${counts['SELFDESTRUCT']}`); risk += 25; }
    if (counts['CALLCODE']) { findings.push(`CALLCODE x${counts['CALLCODE']} (deprecated)`); risk += 20; }
    if (counts['DELEGATECALL']) { findings.push(`DELEGATECALL x${counts['DELEGATECALL']}`); risk += 10; }
    if (counts['CREATE2']) { findings.push(`CREATE2 x${counts['CREATE2']}`); risk += 5; }
    if (counts['ORIGIN']) { findings.push(`tx.origin x${counts['ORIGIN']} (phishing risk)`); risk += 15; }
    
    console.log(`  SLOAD=${counts['SLOAD']||0} SSTORE=${counts['SSTORE']||0} CALL=${counts['CALL']||0} DC=${counts['DELEGATECALL']||0} SD=${counts['SELFDESTRUCT']||0}`);
    
    // === 2. SELECTORS ===
    const selectors = new Set();
    i = 0;
    while (i < bytes.length - 5) {
        if (bytes[i] === 0x63) { // PUSH4
            const sel = '0x' + bytes.slice(i+1, i+5).toString('hex');
            for (let j = i+5; j < Math.min(i+10, bytes.length); j++) {
                if (bytes[j] === 0x14) { selectors.add(sel); break; } // EQ
                if (bytes[j] === 0x63 && j > i+1) break;
            }
            i += 5;
        } else if (bytes[i] >= 0x60 && bytes[i] <= 0x7f) {
            i += (bytes[i] - 0x5f) + 1;
        } else i++;
    }
    console.log(`  Selectors: ${selectors.size}`);
    
    // Match known functions
    const KNOWN = {};
    const funcs = ['transfer(address,uint256)','transferFrom(address,address,uint256)','approve(address,uint256)',
        'balanceOf(address)','totalSupply()','owner()','admin()','deposit()','withdraw(uint256)',
        'mint(address,uint256)','burn(uint256)','pause()','unpause()','paused()',
        'upgradeTo(address)','initialize()','kill()','destroy()','selfdestruct(address)',
        'setOwner(address)','setAdmin(address)','getAdmin()'];
    for (const f of funcs) KNOWN[ethers.id(f).slice(0,10)] = f;
    
    let matched = 0;
    const dangerous = [];
    for (const sel of selectors) {
        if (KNOWN[sel]) {
            matched++;
            if (['kill()','destroy()','selfdestruct(address)','setOwner(address)'].includes(KNOWN[sel])) {
                dangerous.push(KNOWN[sel]);
            }
        }
    }
    if (dangerous.length) { findings.push(`Dangerous: ${dangerous.join(', ')}`); risk += 20; }
    console.log(`  Matched: ${matched}/${selectors.size}`);
    
    // === 3. PROXY ===
    console.log(`\n  [PROXY]`);
    const hex = code.slice(2);
    if (hex.includes('363d3d373d3d3d363d73')) {
        const idx = hex.indexOf('363d3d373d3d3d363d73') + 20;
        const impl = ethers.getAddress('0x' + hex.slice(idx, idx+40));
        console.log(`  ERC-1167 -> ${impl}`);
        findings.push(`ERC-1167 clone`);
        risk += 5;
    } else {
        const EIP1967 = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
        const implRaw = await provider.getStorage(addr, EIP1967);
        if (BigInt(implRaw) > 0n) {
            const impl = ethers.getAddress('0x' + implRaw.slice(26));
            console.log(`  EIP-1967 -> ${impl}`);
            findings.push(`EIP-1967 proxy`);
            risk += 10;
            
            const ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103";
            const adminRaw = await provider.getStorage(addr, ADMIN);
            if (BigInt(adminRaw) > 0n) {
                console.log(`  Admin: ${ethers.getAddress('0x' + adminRaw.slice(26))}`);
                findings.push(`Upgradeable`);
                risk += 10;
            }
        } else {
            console.log(`  Not a proxy`);
        }
    }
    
    // === 4. BALANCE ===
    const balance = await provider.getBalance(addr);
    console.log(`\n  [BALANCE] ${ethers.formatEther(balance)} ETH`);
    if (balance > ethers.parseEther("10")) { findings.push(`Holds ${ethers.formatEther(balance)} ETH`); risk += 15; }
    
    // === 5. METADATA ===
    const hasMetadata = hex.includes('a264') || hex.includes('a265');
    console.log(`  [VERIFY] Metadata: ${hasMetadata ? 'yes' : 'NO (unverified!)'}`);
    if (!hasMetadata) { findings.push('Unverified'); risk += 15; }
    
    // === 6. ACCESS CONTROL ===
    console.log(`\n  [ACCESS CONTROL]`);
    const attacker = "0x000000000000000000000000000000000000dEaD";
    const adminSigs = [['owner()','0x8da5cb5b'],['getAdmin()','0x6e9960c3'],['paused()','0x5c975abb']];
    for (const [fname, sel] of adminSigs) {
        if (selectors.has(sel)) {
            try {
                const result = await provider.call({ to: addr, data: sel });
                if (result.length >= 66) {
                    const val = ethers.getAddress('0x' + result.slice(26));
                    console.log(`  ${fname}: ${val}`);
                    if (val === ethers.ZeroAddress) { findings.push(`${fname} = zero!`); risk += 20; }
                }
            } catch {}
        }
    }
    
    // === SUMMARY ===
    risk = Math.min(risk, 100);
    const level = risk < 30 ? "LOW" : risk < 60 ? "MEDIUM" : risk < 80 ? "HIGH" : "CRITICAL";
    console.log(`\n  [RISK] ${risk}/100 (${level}), ${findings.length} findings`);
    for (const f of findings) console.log(`    - ${f}`);
    
    return { risk, level, findings: findings.length, selectors: selectors.size };
}

async function main() {
    const provider = new ethers.JsonRpcProvider("https://ethereum-rpc.publicnode.com");
    const latest = await provider.getBlockNumber();
    console.log(`Block: ${latest}`);
    
    // === SCAN CONTRACTS ===
    const targets = {
        "Kiln Staking": "0x0A7272e8573aea8359FEC143ac02AED90F822bD0",
        "Kiln CL Dispatcher": "0x462Dd07A79e5DDfBe0C171449C5c01788d5d03C3",
        "USDT": ethers.getAddress("0xdac17f958d2ee523a2206206994597c13d831ec7"),
        "Wormhole": "0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
        "Multicall3": "0xcA11bde05977b3631167028862bE2a173976CA11",
    };
    
    const results = {};
    for (const [name, addr] of Object.entries(targets)) {
        try { results[name] = await scanContract(provider, addr, name); }
        catch (e) { console.log(`  ERROR: ${e.shortMessage || e.message.slice(0,60)}`); }
    }
    
    // === CROSS-CHAIN COMPARISON ===
    console.log(`\n${"=".repeat(60)}`);
    console.log("CROSS-CHAIN COMPARISON");
    console.log(`${"=".repeat(60)}`);
    
    const baseProvider = new ethers.JsonRpcProvider("https://mainnet.base.org");
    const chains = { "Ethereum": provider, "Base": baseProvider };
    const erc20 = ["function symbol() view returns (string)", "function totalSupply() view returns (uint256)", "function decimals() view returns (uint8)"];
    
    const tokens = {
        "USDC": { Ethereum: ethers.getAddress("0xa0b86991c627ce246199b89ff4b35b54c5c85687"), Base: ethers.getAddress("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913") },
        "WETH": { Ethereum: ethers.getAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"), Base: "0x4200000000000000000000000000000000000006" },
    };
    
    for (const [token, addrs] of Object.entries(tokens)) {
        for (const [chain, addr] of Object.entries(addrs)) {
            try {
                const prov = chains[chain];
                const c = new ethers.Contract(addr, erc20, prov);
                const [sym, supply, dec] = await Promise.all([c.symbol(), c.totalSupply(), c.decimals()]);
                const codeSize = ((await prov.getCode(addr)).length - 2) / 2;
                console.log(`  ${token} on ${chain}: ${ethers.formatUnits(supply, dec)} ${sym}, ${codeSize}B`);
            } catch (e) { console.log(`  ${token} on ${chain}: failed`); }
        }
    }
    
    // === COMPARATIVE TABLE ===
    console.log(`\n${"=".repeat(60)}`);
    console.log("COMPARATIVE ANALYSIS");
    console.log(`${"=".repeat(60)}`);
    console.log(`\n  ${"Contract".padEnd(25)} ${"Risk".padStart(5)} ${"Level".padEnd(10)} ${"Findings".padStart(8)}`);
    console.log(`  ${"-".repeat(55)}`);
    for (const [name, r] of Object.entries(results).sort((a,b) => b[1].risk - a[1].risk)) {
        console.log(`  ${name.padEnd(25)} ${String(r.risk).padStart(5)} ${r.level.padEnd(10)} ${String(r.findings).padStart(8)}`);
    }
    
    console.log("\n✓ ETHERS.JS TRANSCENDENT COMPLETE");
}
main().catch(console.error);
