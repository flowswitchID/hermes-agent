import os
import sys
import subprocess
import shutil

def run_check(title, cmd, check_fn=None):
    print(f"[*] Checking {title}...")
    try:
        if isinstance(cmd, list):
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            out = res.stdout + res.stderr
            code = res.returncode
        else:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            out = res.stdout + res.stderr
            code = res.returncode
        
        if code == 0 and (check_fn is None or check_fn(out)):
            print(f"  [PASS] {title} is ready.")
            return True
        else:
            print(f"  [WARN] {title} not ready or error: {out.strip()[:100]}")
            return False
    except Exception as e:
        print(f"  [FAIL] {title} failed: {e}")
        return False

def main():
    print("=================================================================")
    print("          BOZAGENTIC ENVIRONMENT VERIFICATION (SMOKE TEST)       ")
    print("=================================================================")
    
    # 1. Python version
    py_ver = sys.version_info
    print(f"[*] Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    
    # 2. Key Python dependencies
    deps = ['z3', 'web3', 'eth_account', 'httpx', 'requests', 'pydantic', 'rich']
    all_deps_ok = True
    for d in deps:
        try:
            __import__(d)
            print(f"  [PASS] Python module '{d}' loaded.")
        except ImportError:
            print(f"  [MISSING] Python module '{d}' not installed (run: pip install {d})")
            all_deps_ok = False
            
    # 3. Node & PM2
    run_check("Node.js", "node -v")
    run_check("PM2 Process Manager", "pm2 -v")
    
    # 4. Foundry Web3 Toolkit
    run_check("Foundry (Forge)", "forge --version")
    run_check("Foundry (Cast)", "cast --version")
    
    # 5. Z3 Solver Engine
    try:
        import z3
        x = z3.Int('x')
        s = z3.Solver()
        s.add(x > 10, x < 20)
        if s.check() == z3.sat:
            print("  [PASS] Z3 SMT Solver logic verified.")
    except Exception as e:
        print(f"  [FAIL] Z3 Solver error: {e}")
        
    print("=================================================================")
    print("Verification complete. Ready to run BOZAGENTIC.")

if __name__ == "__main__":
    main()
