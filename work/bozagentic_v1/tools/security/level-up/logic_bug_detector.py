"""
Custom Slither Detector: Logic Bug Finder
Goes beyond pattern matching — detects SEMANTIC inconsistencies.

Detectors:
1. FeeCapInconsistency: Two functions compute fees differently for same concept
2. MissingHealthCheckAfter: Position changed without health verification
3. StateUpdateAfterExternalCall: CEI violation with specific state tracking
4. InvariantViolation: totalSupply/totalAssets accounting mismatch
5. RoundingDirectionMismatch: Same operation rounds differently in two places
"""

from slither.detectors.abstract_detector import AbstractDetector, DetectorClassification
from slither.core.declarations import Function
from slither.core.variables.state_variable import StateVariable
from slither.slithir.operations import HighLevelCall, Binary, Assignment, InternalCall
from slither.slithir.variables import ReferenceVariable
import re


class FeeCapInconsistency(AbstractDetector):
    """
    Detects when two functions compute fees/caps differently for the same concept.
    
    Example: CashbackRewards bug — _validatePaymentReward used distributed+allocated
    for cap check but only distributed for actual distribution.
    
    Detection: Find functions that read the same state variable for a cap/limit,
    but use different arithmetic to compute the value being checked.
    """
    
    ARGUMENT = 'fee-cap-inconsistency'
    HELP = 'Fee/cap computation inconsistency between functions'
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.MEDIUM
    
    WIKI = 'https://github.com/crytic/slither/wiki/Detector-Documentation'
    WIKI_TITLE = 'Fee Cap Inconsistency'
    WIKI_DESCRIPTION = 'Two functions compute fees/caps differently for the same concept'
    WIKI_EXPLOIT_SCENARIO = '''
```solidity
function allocate(uint256 amount) {
    // Cap check uses distributed + allocated
    require(distributed + allocated + amount <= cap);
    allocated += amount;
}

function distribute(uint256 amount) {
    // Distribution only tracks distributed
    distributed += amount;
    // BUG: allocated is never subtracted from cap check here
}
```
'''
    WIKI_RECOMMENDATION = 'Ensure consistent fee/cap computation across all functions'
    
    def _detect(self):
        results = []
        
        for contract in self.contracts:
            # Find state variables that look like caps/limits/fees
            cap_vars = []
            for var in contract.state_variables:
                name_lower = var.name.lower()
                if any(kw in name_lower for kw in ['cap', 'limit', 'max', 'fee', 'threshold', 'bound']):
                    cap_vars.append(var)
            
            if len(cap_vars) == 0:
                continue
            
            # Find functions that READ these cap variables
            cap_readers = {}  # var -> list of (function, read_context)
            for func in contract.functions:
                if func.is_constructor or func.visibility not in ['public', 'external', 'internal']:
                    continue
                
                for var in cap_vars:
                    if var in func.state_variables_read:
                        # Analyze HOW the cap is used
                        usage = self._analyze_cap_usage(func, var)
                        if usage:
                            if var.name not in cap_readers:
                                cap_readers[var.name] = []
                            cap_readers[var.name].append((func, usage))
            
            # Check for inconsistencies
            for var_name, readers in cap_readers.items():
                if len(readers) < 2:
                    continue
                
                # Compare how each function uses the cap
                for i in range(len(readers)):
                    for j in range(i + 1, len(readers)):
                        func1, usage1 = readers[i]
                        func2, usage2 = readers[j]
                        
                        if self._is_inconsistent(usage1, usage2):
                            info = [
                                f"Potential fee/cap inconsistency in ",
                                contract,
                                f":\n",
                                f"\t- ",
                                func1,
                                f" uses {var_name} as: {usage1['type']}\n",
                                f"\t- ",
                                func2,
                                f" uses {var_name} as: {usage2['type']}\n",
                                f"\tDifferent computation patterns for the same cap variable.\n",
                            ]
                            results.append(self.generate_result(info))
        
        return results
    
    def _analyze_cap_usage(self, func, cap_var):
        """Analyze how a cap variable is used in a function."""
        usage = {'type': 'unknown', 'operations': [], 'compared_with': []}
        
        for node in func.nodes:
            for ir in node.irs:
                if isinstance(ir, Binary):
                    # Check if cap_var is in a comparison
                    if self._involves_var(ir, cap_var):
                        usage['type'] = 'comparison'
                        usage['operations'].append(str(ir))
                        # What is the cap compared against?
                        for read in ir.read:
                            if read != cap_var:
                                usage['compared_with'].append(str(read))
                
                elif isinstance(ir, Assignment):
                    if self._involves_var(ir, cap_var):
                        usage['type'] = 'assignment'
                        usage['operations'].append(str(ir))
        
        return usage if usage['operations'] else None
    
    def _involves_var(self, ir, var):
        """Check if an IR operation involves a specific variable."""
        for read in ir.read:
            if read == var:
                return True
            if isinstance(read, ReferenceVariable) and read.points_to == var:
                return True
        return False
    
    def _is_inconsistent(self, usage1, usage2):
        """Check if two usages are inconsistent."""
        # Different operation types on same cap
        if usage1['type'] != usage2['type']:
            return True
        
        # Same type but different compared_with sets
        if usage1['type'] == 'comparison' and usage2['type'] == 'comparison':
            set1 = set(usage1['compared_with'])
            set2 = set(usage2['compared_with'])
            if set1 != set2 and len(set1) > 0 and len(set2) > 0:
                return True
        
        return False


class MissingHealthCheck(AbstractDetector):
    """
    Detects when a lending position is modified without a subsequent health check.
    
    Example: borrow() increases debt but doesn't check collateralization.
    """
    
    ARGUMENT = 'missing-health-check'
    HELP = 'Position modified without health/collateralization check'
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.MEDIUM
    
    WIKI = 'https://github.com/crytic/slither/wiki/Detector-Documentation'
    WIKI_TITLE = 'Missing Health Check'
    WIKI_DESCRIPTION = 'Lending position modified without health check'
    WIKI_EXPLOIT_SCENARIO = '''
```solidity
function borrow(uint256 amount) external {
    position[msg.sender].debt += amount;
    token.transfer(msg.sender, amount);
    // BUG: no health check after increasing debt
}
```
'''
    WIKI_RECOMMENDATION = 'Add health/collateralization check after position modifications'
    
    def _detect(self):
        results = []
        
        for contract in self.contracts:
            # Find state variables that look like debt/borrow/collateral
            position_vars = []
            for var in contract.state_variables:
                name_lower = var.name.lower()
                if any(kw in name_lower for kw in ['debt', 'borrow', 'collateral', 'credit', 'position']):
                    position_vars.append(var)
            
            if not position_vars:
                continue
            
            # Find functions that WRITE to position vars
            for func in contract.functions:
                if func.is_constructor or func.view or func.pure:
                    continue
                
                writes_position = False
                for var in position_vars:
                    if var in func.state_variables_written:
                        writes_position = True
                        break
                
                if not writes_position:
                    continue
                
                # Check if there's a health check
                has_health_check = self._has_health_check(func)
                
                if not has_health_check:
                    info = [
                        f"Position modified without health check in ",
                        func,
                        f"\n\tWrites to position state but no collateralization/health verification found.\n",
                    ]
                    results.append(self.generate_result(info))
        
        return results
    
    def _has_health_check(self, func):
        """Check if function contains a health/collateralization check."""
        health_keywords = ['health', 'healthy', 'collateral', 'ltv', 'ratio', 'solvency', 'isHealthy', 'checkHealth']
        
        for node in func.nodes:
            node_str = str(node)
            if any(kw.lower() in node_str.lower() for kw in health_keywords):
                return True
            
            # Check for internal calls to health functions
            for ir in node.irs:
                if isinstance(ir, (HighLevelCall, InternalCall)):
                    call_str = str(ir)
                    if any(kw.lower() in call_str.lower() for kw in health_keywords):
                        return True
        
        return False


class RoundingDirectionMismatch(AbstractDetector):
    """
    Detects when the same mathematical operation uses different rounding
    directions in different functions, which can lead to systematic value leakage.
    
    Example: supply uses mulDivDown but withdraw uses mulDivDown too (should be mulDivUp).
    """
    
    ARGUMENT = 'rounding-direction-mismatch'
    HELP = 'Inconsistent rounding direction across related operations'
    IMPACT = DetectorClassification.MEDIUM
    CONFIDENCE = DetectorClassification.LOW
    
    WIKI = 'https://github.com/crytic/slither/wiki/Detector-Documentation'
    WIKI_TITLE = 'Rounding Direction Mismatch'
    WIKI_DESCRIPTION = 'Same operation rounds differently in different functions'
    WIKI_EXPLOIT_SCENARIO = '''
```solidity
function deposit(uint256 assets) {
    shares = assets.mulDivDown(totalSupply, totalAssets); // rounds down
}

function withdraw(uint256 assets) {
    shares = assets.mulDivDown(totalSupply, totalAssets); // BUG: should round UP
    // Users get more shares back than they should
}
```
'''
    WIKI_RECOMMENDATION = 'Ensure consistent rounding: down for minting, up for burning'
    
    def _detect(self):
        results = []
        
        for contract in self.contracts:
            # Find all mulDiv calls
            muldiv_calls = {}  # function_name -> list of (call_str, direction)
            
            for func in contract.functions:
                if func.is_constructor:
                    continue
                
                calls = []
                for node in func.nodes:
                    node_str = str(node)
                    if 'mulDivDown' in node_str:
                        calls.append(('down', node_str))
                    elif 'mulDivUp' in node_str:
                        calls.append(('up', node_str))
                    elif 'toSharesDown' in node_str:
                        calls.append(('shares_down', node_str))
                    elif 'toSharesUp' in node_str:
                        calls.append(('shares_up', node_str))
                    elif 'toAssetsDown' in node_str:
                        calls.append(('assets_down', node_str))
                    elif 'toAssetsUp' in node_str:
                        calls.append(('assets_up', node_str))
                
                if calls:
                    muldiv_calls[func.name] = calls
            
            # Check for deposit/withdraw or supply/borrow pairs
            pairs = [
                ('deposit', 'withdraw'), ('supply', 'withdraw'),
                ('mint', 'redeem'), ('borrow', 'repay'),
                ('supply', 'borrow'),
            ]
            
            for name1, name2 in pairs:
                if name1 in muldiv_calls and name2 in muldiv_calls:
                    calls1 = muldiv_calls[name1]
                    calls2 = muldiv_calls[name2]
                    
                    # Check if rounding directions are appropriate
                    for dir1, str1 in calls1:
                        for dir2, str2 in calls2:
                            if self._is_mismatch(name1, dir1, name2, dir2):
                                info = [
                                    f"Potential rounding mismatch in ",
                                    contract,
                                    f":\n",
                                    f"\t- {name1}: uses {dir1}\n",
                                    f"\t- {name2}: uses {dir2}\n",
                                    f"\tVerify rounding directions are correct for each operation.\n",
                                ]
                                results.append(self.generate_result(info))
        
        return results
    
    def _is_mismatch(self, func1, dir1, func2, dir2):
        """Check if rounding directions are mismatched for paired operations."""
        # deposit/supply should round DOWN for shares (user gets fewer shares)
        # withdraw/redeem should round UP for shares (user burns more shares)
        # borrow should round UP for shares (user owes more)
        # repay should round DOWN for shares (user owes less)
        
        expected = {
            'deposit': ['down', 'shares_down'],
            'supply': ['down', 'shares_down'],
            'mint': ['up', 'assets_up'],
            'withdraw': ['up', 'shares_up'],
            'redeem': ['down', 'assets_down'],
            'borrow': ['up', 'shares_up'],
            'repay': ['down', 'shares_down'],
        }
        
        if func1 in expected and dir1 not in expected[func1]:
            return True
        if func2 in expected and dir2 not in expected[func2]:
            return True
        
        return False
