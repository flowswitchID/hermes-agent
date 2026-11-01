#!/usr/bin/env python3
"""
Mythril Custom Module Runner v2
Workaround for Mythril v0.24.8 bug: --custom-modules-directory is accepted
but never actually used to load modules.

v2 features:
  - --bin-runtime: analyze deployed bytecode (skip constructor)
  - --contract-name: target specific contract in multi-contract files
  - --function: target specific function by name or selector
  - --from-foundry: auto-extract bytecode from Foundry build output
  - Custom module registration via ModuleLoader.register_module()

Usage:
  # Analyze Solidity source
  python3 run_custom_mythril.py contract.sol

  # Analyze specific contract in multi-contract file
  python3 run_custom_mythril.py flat.sol --contract-name MyContract

  # Analyze deployed bytecode (skip constructor)
  python3 run_custom_mythril.py contract.bin --bin-runtime

  # Auto-extract from Foundry build output
  python3 run_custom_mythril.py /path/to/foundry-project \
    --from-foundry StabilityPool

  # Target specific function
  python3 run_custom_mythril.py contract.bin --bin-runtime \
    --function provideToSP

  # Select specific custom modules
  python3 run_custom_mythril.py contract.sol --modules unchecked_oracle
"""
import sys
import os
import json
import argparse
import importlib.util
import logging

logging.basicConfig(level=logging.WARNING)


# ============================================================
# MODULE LOADING
# ============================================================
def load_custom_module(filepath):
    """Load a custom detection module from a .py file."""
    spec = importlib.util.spec_from_file_location("custom_module", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, 'detector'):
        return module.detector
    return None


def register_custom_modules(modules_dir, selected=None):
    """Register custom modules with Mythril's ModuleLoader."""
    from mythril.analysis.module.loader import ModuleLoader

    loader = ModuleLoader()
    registered = []

    for filename in sorted(os.listdir(modules_dir)):
        if not filename.endswith('.py') or filename.startswith('_'):
            continue
        if filename in ('defi_detectors.py', 'run_custom_mythril.py'):
            continue

        name = filename.replace('.py', '')
        if selected and name not in selected:
            continue

        filepath = os.path.join(modules_dir, filename)
        try:
            detector = load_custom_module(filepath)
            if detector:
                loader.register_module(detector)
                registered.append(f"  ✅ {name}: {detector.name}")
            else:
                registered.append(f"  ❌ {name}: no detector found")
        except Exception as e:
            registered.append(f"  ❌ {name}: {e}")

    return registered


# ============================================================
# BYTECODE EXTRACTION
# ============================================================
def extract_from_foundry(project_dir, contract_name):
    """Extract deployed bytecode + ABI from Foundry build output."""
    # Search for contract JSON in out/
    out_dir = os.path.join(project_dir, "out")
    if not os.path.isdir(out_dir):
        print(f"  ❌ No out/ directory in {project_dir}")
        return None, None, None

    for sol_file in os.listdir(out_dir):
        json_path = os.path.join(out_dir, sol_file, f"{contract_name}.json")
        if os.path.isfile(json_path):
            with open(json_path) as f:
                data = json.load(f)

            deployed = data.get("deployedBytecode", {}).get("object", "")
            abi = data.get("abi", [])

            if deployed:
                print(f"  Found: {json_path}")
                print(f"  Deployed bytecode: {len(deployed)} chars")
                print(f"  ABI functions: {len([a for a in abi if a.get('type')=='function'])}")
                return deployed, abi, contract_name

    print(f"  ❌ {contract_name}.json not found in {out_dir}/")
    return None, None, None


def get_function_map(abi):
    """Build selector -> signature map from ABI."""
    from web3 import Web3
    funcs = {}
    for item in abi:
        if item.get("type") == "function":
            name = item["name"]
            inputs = ",".join([i["type"] for i in item.get("inputs", [])])
            sig = f"{name}({inputs})"
            sel = "0x" + Web3.keccak(text=sig)[:4].hex()
            funcs[sel] = sig
    return funcs


# ============================================================
# ANALYSIS
# ============================================================
def run_analysis(
    contract_path,
    modules_dir,
    selected=None,
    timeout=60,
    contract_name=None,
    bin_runtime=False,
    from_foundry=None,
    target_function=None,
    max_depth=30,
    tx_count=2,
):
    """Run Mythril with custom modules registered."""

    print("=" * 60)
    print("  CUSTOM MYTHRIL ANALYSIS v2")
    print("=" * 60)

    # Register custom modules
    print("\n[1/4] Loading custom modules...")
    registered = register_custom_modules(modules_dir, selected)
    for r in registered:
        print(r)

    from mythril.analysis.module.loader import ModuleLoader
    from mythril.analysis.module.base import EntryPoint

    all_modules = ModuleLoader().get_detection_modules(EntryPoint.CALLBACK)
    custom_count = len([r for r in registered if "✅" in r])
    print(f"\n  Total CALLBACK modules: {len(all_modules)}")
    print(f"  Custom: {custom_count} | Built-in: {len(all_modules) - custom_count}")

    # Load contract
    print(f"\n[2/4] Loading contract...")

    abi = None
    func_map = {}

    if from_foundry:
        # Extract from Foundry build output
        bytecode, abi, cname = extract_from_foundry(contract_path, from_foundry)
        if not bytecode:
            return None

        from mythril.ethereum.evmcontract import EVMContract
        contract = EVMContract(bytecode, name=cname)
        bin_runtime = True
        contract_name = cname

        if abi:
            func_map = get_function_map(abi)
            print(f"\n  Functions ({len(func_map)}):")
            for sel, sig in sorted(func_map.items(), key=lambda x: x[1]):
                print(f"    {sel} = {sig}")

    elif bin_runtime:
        # Load raw bytecode
        with open(contract_path) as f:
            bytecode = f.read().strip()

        from mythril.ethereum.evmcontract import EVMContract
        contract = EVMContract(bytecode, name=contract_name or "Unknown")
        print(f"  Bytecode: {len(bytecode)} chars")

    else:
        # Load Solidity source
        from mythril.solidity.soliditycontract import SolidityContract

        try:
            contract = SolidityContract(contract_path, name=contract_name)
        except Exception as e:
            print(f"  ❌ Failed to compile: {e}")
            return None

    print(f"  Contract: {contract.name}")
    print(f"  Mode: {'bin-runtime (skip constructor)' if bin_runtime else 'source (with constructor)'}")

    # Target function
    if target_function and func_map:
        target_sel = None
        for sel, sig in func_map.items():
            if target_function.lower() in sig.lower():
                target_sel = sel
                print(f"\n  Target function: {sig} ({sel})")
                break
        if not target_sel:
            print(f"\n  ⚠️ Function '{target_function}' not found in ABI")

    # Run analysis
    print(f"\n[3/4] Running symbolic execution...")
    print(f"  Timeout: {timeout}s | Max depth: {max_depth} | TXs: {tx_count}")

    from mythril.analysis.symbolic import SymExecWrapper
    from mythril.analysis.security import retrieve_callback_issues
    from mythril.support.support_args import args

    args.pruning_factor = 1

    try:
        sym = SymExecWrapper(
            contract,
            "0x0000000000000000000000000000000000000000",
            "dfs",
            execution_timeout=timeout,
            create_timeout=0 if bin_runtime else timeout // 2,
            max_depth=max_depth,
            transaction_count=tx_count,
            run_analysis_modules=True,
        )

        print(f"\n[4/4] Collecting results...")

        callback_issues = retrieve_callback_issues()
        all_issues = callback_issues

        # Report
        print(f"\n{'=' * 60}")
        print(f"  RESULTS: {len(all_issues)} issues found")
        print(f"{'=' * 60}")

        for i, issue in enumerate(all_issues):
            severity = getattr(issue, "severity", "?")
            title = getattr(issue, "title", getattr(issue, "head", "?"))
            func = getattr(issue, "function", "?")
            contract_n = getattr(issue, "contract", "?")
            desc = getattr(issue, "description", "")

            # Decode function selector if we have ABI
            func_display = func
            if func_map and func.startswith("_function_"):
                sel = "0x" + func.replace("_function_", "")
                if sel in func_map:
                    func_display = func_map[sel]

            print(f"\n  [{i+1}] {severity}: {title}")
            print(f"      Contract: {contract_n}")
            print(f"      Function: {func_display}")
            if desc:
                print(f"      Detail: {desc[:250]}")

        if not all_issues:
            print("\n  No issues found.")

        return all_issues

    except Exception as e:
        print(f"\n  ❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mythril with custom DeFi detectors v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solidity source
  python3 run_custom_mythril.py contract.sol

  # Specific contract in multi-contract file
  python3 run_custom_mythril.py flat.sol --contract-name MyContract

  # Deployed bytecode (skip constructor)
  python3 run_custom_mythril.py contract.bin --bin-runtime

  # From Foundry build output (recommended for real projects)
  python3 run_custom_mythril.py /path/to/foundry-project --from-foundry StabilityPool

  # Target specific function
  python3 run_custom_mythril.py /path/to/project --from-foundry Vault --function deposit
        """,
    )
    parser.add_argument("contract", help="Solidity file, bytecode file, or Foundry project dir")
    parser.add_argument("--contract-name", default=None, help="Contract name (multi-contract files)")
    parser.add_argument("--bin-runtime", action="store_true", help="Analyze deployed bytecode (skip constructor)")
    parser.add_argument("--from-foundry", default=None, help="Extract bytecode from Foundry out/ for this contract")
    parser.add_argument("--function", default=None, help="Target specific function by name")
    parser.add_argument("--modules", default=None, help="Comma-separated custom module names")
    parser.add_argument("--timeout", type=int, default=90, help="Execution timeout (seconds)")
    parser.add_argument("--max-depth", type=int, default=30, help="Max symbolic execution depth")
    parser.add_argument("--tx-count", type=int, default=2, help="Number of transactions")
    parser.add_argument(
        "--modules-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Custom modules directory",
    )

    args = parser.parse_args()
    selected = args.modules.split(",") if args.modules else None

    run_analysis(
        args.contract,
        args.modules_dir,
        selected,
        args.timeout,
        args.contract_name,
        args.bin_runtime,
        args.from_foundry,
        args.function,
        args.max_depth,
        args.tx_count,
    )
