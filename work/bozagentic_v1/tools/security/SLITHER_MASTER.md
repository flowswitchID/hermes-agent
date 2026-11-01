# SLITHER MASTER — Complete Reference
# BOZAGENTIC | All detectors, printers, custom plugins

---

## WORKFLOW

```bash
# 1. Basic scan (all detectors)
slither src/ --filter-paths "lib|test|script"

# 2. Exclude noise
slither src/ --exclude-informational --exclude-low

# 3. Specific detectors only
slither src/ --detect reentrancy-eth,arbitrary-send-erc20

# 4. Custom detectors (plugin)
pip install -e /path/to/slither-plugin/
slither src/ --detect inconsistent-state-tracking

# 5. Printers for analysis
slither src/ --print vars-and-auth    # Authorization matrix
slither src/ --print function-summary # Function overview
slither src/ --print data-dependency  # Variable dependencies
slither src/ --print human-summary    # Quick overview
slither src/ --print entry-points     # Attack surface
slither src/ --print echidna          # Echidna guidance
slither src/ --print loc              # Lines of code
slither src/ --print call-graph       # Call graph (dot)
slither src/ --print cfg              # Control flow graph
slither src/ --print slithir          # IR representation
```

---

## 27 PRINTERS

```
# | PRINTER           | USE CASE
══|═══════════════════|══════════════════════════════════════
1 | call-graph        | Map all function calls (attack surface)
2 | cfg               | Control flow per function (find paths)
3 | cheatcode         | Foundry cheatcode usage
4 | ck                | Complexity metrics (CK suite)
5 | constructor-calls | Constructor execution order
6 | contract-summary  | Quick contract overview
7 | data-dependency   | Variable dependency chains
8 | declaration       | Source declarations + references
9 | dominator         | Dominator tree (control flow)
10| echidna           | Echidna-compatible output
11| entry-points      | State-changing entry points ← IMPORTANT
12| evm               | EVM instructions per node
13| function-id       | Function selectors (keccak256)
14| function-summary  | Function details (reads/writes/calls)
15| halstead          | Halstead complexity metrics
16| human-summary     | Human-readable overview ← START HERE
17| inheritance       | Inheritance relations
18| inheritance-graph | Inheritance graph (dot)
19| loc               | Lines of code count
20| martin            | Martin agile metrics
21| modifiers         | Modifier usage per function
22| not-pausable      | Functions without whenNotPaused
23| require           | require/assert per function
24| slithir           | SlithIR representation
25| slithir-ssa       | SlithIR SSA form
26| variable-order    | Storage variable order
27| vars-and-auth     | State vars + authorization ← IMPORTANT
```

---

## CUSTOM DETECTORS (BOZAGENTIC)

```
DETECTOR                      | CATCHES
══════════════════════════════|══════════════════════════════
inconsistent-state-tracking   | CashbackRewards maxRewardBps bypass
erc4626-inflation-attack      | Basin/Beanstalk inflation attack
cross-chain-signature-replay  | Hardcoded chainId in EIP-712
unlimited-admin-drain         | Admin drain without limit
```

### How to install:
```bash
cd /path/to/slither-plugin/
pip install -e .
# Now all 4 detectors available via --detect
```

### How to write new detector:
```python
from slither.detectors.abstract_detector import (
    AbstractDetector, DetectorClassification
)

class MyDetector(AbstractDetector):
    ARGUMENT = "my-detector"
    HELP = "Description"
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.MEDIUM

    def _detect(self):
        results = []
        for contract in self.contracts:
            for function in contract.functions_declared:
                # Analyze function.nodes, function.irs
                # Build info list, append to results
                pass
        return results
```

### Plugin registration:
```python
# __init__.py
from .my_detector import MyDetector
def make_plugin():
    return ([MyDetector], [])  # (detectors, printers)
```

### setup.py:
```python
setup(
    name="slither-plugin",
    entry_points={
        "slither_analyzer.plugin": [
            "my-detector = slither_plugin:make_plugin",
        ],
    },
)
```

---

## KEY DETECTORS FOR AUDIT

```
ALWAYS RUN:
  reentrancy-eth, reentrancy-no-eth
  arbitrary-send-erc20, arbitrary-send-eth
  unprotected-upgrade
  controlled-delegatecall
  suicidal
  unchecked-lowlevel
  unchecked-transfer

SOMETIMES USEFUL:
  timestamp (block.timestamp dependence)
  tx-origin (tx.origin auth)
  incorrect-modifier
  void-cst
  calls-in-loop
  dead-code

USUALLY NOISE:
  informational (pragma, naming, etc.)
  low (optimization, style)
```

---

## LEVEL ASSESSMENT

```
BEFORE: 80% (run + validate FP)
NOW:    88% (custom detectors, printers, plugin system)
EXPERT: 95% (write detectors for ANY pattern, SSA analysis)
GAP:    SSA-level analysis, dominator tree usage
```
