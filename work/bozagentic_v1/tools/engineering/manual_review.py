#!/usr/bin/env python3
"""
MANUAL REVIEW ENGINE v2.0 — Hypothesis-First Static Analysis
Bukan checklist. Bukan pattern matching.
Ini encode CARA BERPIKIR auditor ahli ke dalam tool.

Usage: python3 manual_review.py <path_to_sol_or_dir> [--json out.json] [--slither slither.json]

16 Phases:
  1. MAP THE MONEY — masuk dari mana, keluar ke mana
  2. FIND THE LIES — invariant yang bisa dilanggar
  3. FOLLOW STALE STATE — variabel yang ga update
  4. BREAK COMPOSITION — cross-contract reentrancy/callback
  5. THINK LIKE ATTACKER — profit-oriented analysis
  6. PATTERN SCAN — tx.origin, delegatecall, selfdestruct
  7. CROSS-CONTRACT — A→B→A cycles, external state deps
  8. MULTI-TX — setup→exploit, epoch boundary skip
  9. ORACLE — spot price, staleness, bounds, single source
  10. GOVERNANCE — timelock, flash-loan voting, admin rug
  11. ERC-4626 — inflation attack, rounding, caps
  12. PROXY & UPGRADE — storage collision, reinit, UUPS lock
  13. CROSS-CHAIN — replay, source validation, rate limit
  14. INTEREST RATE — overflow, underflow, mixed models
  15. ROUNDING — direction favors user vs protocol
  16. SLITHER INTEGRATION — cross-ref tool findings as entry points
"""

import os
import re
import sys
import json
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

# ═══════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════

@dataclass
class FunctionInfo:
    name: str
    visibility: str  # external, public, internal, private
    modifiers: List[str]
    params: List[str]
    body: str
    line: int
    is_payable: bool = False
    is_view: bool = False
    external_calls: List[str] = field(default_factory=list)
    state_writes: List[str] = field(default_factory=list)
    state_reads: List[str] = field(default_factory=list)
    has_nonreentrant: bool = False
    access_control: str = ""  # onlyOwner, onlyRole, require(msg.sender==...)

@dataclass
class StateVar:
    name: str
    type: str
    visibility: str
    is_immutable: bool = False
    is_constant: bool = False
    line: int = 0

@dataclass
class Hypothesis:
    title: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    phase: str  # which phase found it
    description: str
    evidence: str
    attack_steps: str = ""
    profit_calc: str = ""
    confidence: float = 0.0  # 0-1

@dataclass
class ContractInfo:
    name: str
    filename: str
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    state_vars: Dict[str, StateVar] = field(default_factory=dict)
    inherits: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    raw_code: str = ""

# ═══════════════════════════════════════════
# PARSER (regex-based, not AST — fast & portable)
# ═══════════════════════════════════════════

def parse_solidity(code: str, filename: str) -> List[ContractInfo]:
    contracts = []
    
    # Find all contracts/interfaces/libraries
    contract_pattern = re.compile(
        r'(?:abstract\s+)?(contract|interface|library)\s+(\w+)'
        r'(?:\s+is\s+([^{]+))?\s*\{',
        re.MULTILINE
    )
    
    for match in contract_pattern.finditer(code):
        ctype, cname, inherits_str = match.groups()
        if ctype in ('interface', 'library'):
            continue
        
        info = ContractInfo(name=cname, filename=filename, raw_code=code)
        if inherits_str:
            info.inherits = [x.strip() for x in inherits_str.split(',')]
        
        # Extract state variables
        _parse_state_vars(code, info)
        
        # Extract functions
        _parse_functions(code, info)
        
        contracts.append(info)
    
    return contracts

def _parse_state_vars(code: str, info: ContractInfo):
    # Match state variable declarations (rough but effective)
    var_pattern = re.compile(
        r'^\s+(mapping\s*\([^)]+\)\s*(?:=>\s*\w+)?|[\w\[\]]+)\s+'
        r'(public|private|internal|external)?\s*'
        r'(immutable|constant)?\s*'
        r'(\w+)\s*(?:=\s*[^;]+)?;',
        re.MULTILINE
    )
    
    for m in var_pattern.finditer(code):
        vtype, vis, modifier, vname = m.groups()
        if vname in ('returns', 'return', 'require', 'if', 'for', 'while'):
            continue
        info.state_vars[vname] = StateVar(
            name=vname,
            type=vtype.strip(),
            visibility=vis or 'internal',
            is_immutable=modifier == 'immutable',
            is_constant=modifier == 'constant',
            line=code[:m.start()].count('\n') + 1
        )

def _parse_functions(code: str, info: ContractInfo):
    # Simple line-by-line scan instead of complex regex (avoids backtracking)
    lines = code.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match function declaration
        m = re.match(r'\s*function\s+(\w+)\s*\(', line)
        if not m:
            i += 1
            continue
        
        fname = m.group(1)
        
        # Collect full signature (may span multiple lines)
        sig = line
        paren_depth = sig.count('(') - sig.count(')')
        j = i + 1
        while paren_depth > 0 and j < len(lines):
            sig += ' ' + lines[j].strip()
            paren_depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        
        # Also grab modifiers/returns on next lines until {
        while j < len(lines) and '{' not in lines[j]:
            sig += ' ' + lines[j].strip()
            j += 1
        if j < len(lines):
            sig += ' ' + lines[j].strip()
        
        # Extract params
        param_match = re.search(r'\(([^)]*)\)', sig)
        params_str = param_match.group(1) if param_match else ''
        
        # Extract attributes from signature
        after_params = sig[sig.index(')') + 1:] if ')' in sig else ''
        all_mods = re.findall(r'\b(external|public|internal|private|view|pure|payable|virtual|override|nonReentrant|onlyOwner|onlyRole|only\w+)\b', after_params)
        
        # Find function body via brace matching from the { position
        brace_line = j
        # Find the { in the accumulated text
        body_start = code.find('{', code.find(f'function {fname}'))
        if body_start < 0:
            i = j + 1
            continue
        body = _extract_brace_block(code, body_start + 1)
        line_num = code[:code.find(f'function {fname}')].count('\n') + 1
        
        fi = FunctionInfo(
            name=fname,
            visibility='external' if 'external' in all_mods else
                       'public' if 'public' in all_mods else
                       'internal' if 'internal' in all_mods else
                       'private' if 'private' in all_mods else 'public',
            modifiers=all_mods,
            params=[p.strip() for p in params_str.split(',') if p.strip()],
            body=body,
            line=line_num,
            is_payable='payable' in all_mods,
            is_view='view' in all_mods or 'pure' in all_mods,
            has_nonreentrant='nonReentrant' in ' '.join(all_mods),
        )
        
        # Extract access control
        for mod in all_mods:
            if mod.startswith('only') or mod.startswith('require'):
                fi.access_control = mod
        if 'require(msg.sender' in body:
            sender_match = re.search(r'require\(msg\.sender\s*==\s*(\w+)', body)
            if sender_match:
                fi.access_control = f"require(msg.sender == {sender_match.group(1)})"
        
        # Extract external calls (simple find, no complex regex)
        for kw in ['transfer', 'call', 'transferFrom', 'approve', 'mint', 'burn', 
                    'harvest', 'withdraw', 'deposit', 'execute', 'swap']:
            if f'.{kw}(' in body:
                # Find the object before the call
                for cm in re.finditer(rf'(\w+)\.{kw}\s*\(', body):
                    if cm.group(1) not in fi.external_calls:
                        fi.external_calls.append(cm.group(1))
        
        # Extract state writes
        for vname in info.state_vars:
            if re.search(rf'\b{re.escape(vname)}\s*[\+\-\*]?=', body):
                fi.state_writes.append(vname)
            if re.search(rf'\b{re.escape(vname)}\b', body):
                fi.state_reads.append(vname)
        
        info.functions[fname] = fi
        i = j + 1

def _extract_brace_block(code: str, start: int) -> str:
    depth = 1
    i = start
    while i < len(code) and depth > 0:
        if code[i] == '{': depth += 1
        elif code[i] == '}': depth -= 1
        i += 1
    return code[start:i-1]

# ═══════════════════════════════════════════
# PHASE 1: MAP THE MONEY
# ═══════════════════════════════════════════

MONEY_IN = {'deposit', 'stake', 'supply', 'mint', 'bridge', 'fund', 'add', 'lock', 'wrap'}
MONEY_OUT = {'withdraw', 'unstake', 'borrow', 'burn', 'claim', 'redeem', 'remove', 'unlock', 'unwrap', 'liquidate'}
MONEY_MOVE = {'transfer', 'swap', 'invest', 'harvest', 'divest', 'repay', 'lend'}

def phase1_map_money(contracts: List[ContractInfo]) -> Tuple[List[Hypothesis], Dict]:
    findings = []
    money_map = {'in': [], 'out': [], 'move': [], 'no_access': []}
    
    for c in contracts:
        for fname, fi in c.functions.items():
            fname_lower = fname.lower()
            
            # Classify money flow
            if any(kw in fname_lower for kw in MONEY_IN):
                money_map['in'].append(f"{c.name}.{fname}")
            if any(kw in fname_lower for kw in MONEY_OUT):
                money_map['out'].append(f"{c.name}.{fname}")
            if any(kw in fname_lower for kw in MONEY_MOVE):
                money_map['move'].append(f"{c.name}.{fname}")
            
            # Check: money-out function without access control
            if any(kw in fname_lower for kw in MONEY_OUT):
                if fi.visibility in ('external', 'public'):
                    if not fi.access_control and not fi.has_nonreentrant:
                        # Check if it's truly permissionless
                        if 'require(msg.sender' not in fi.body and 'onlyOwner' not in ' '.join(fi.modifiers):
                            money_map['no_access'].append(f"{c.name}.{fname}")
                            findings.append(Hypothesis(
                                title=f"Permissionless money-out: {c.name}.{fname}()",
                                severity="HIGH",
                                phase="MAP_MONEY",
                                description=f"{fname}() moves funds out but has NO access control. "
                                          f"Anyone can call it.",
                                evidence=f"Line {fi.line}: no onlyOwner/require(msg.sender==) found",
                                confidence=0.7
                            ))
    
    return findings, money_map

# ═══════════════════════════════════════════
# PHASE 2: FIND THE LIES (Accounting Invariants)
# ═══════════════════════════════════════════

def phase2_find_lies(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        # Pattern 1: totalX variables that should == sum of individual X
        total_vars = {name: var for name, var in c.state_vars.items() 
                     if name.startswith('total') and not var.is_constant and not var.is_immutable}
        
        for tname, tvar in total_vars.items():
            # Find the corresponding individual mapping
            # totalShares → shares, totalDeposits → deposits, totalDebt → debt
            individual_name = tname.replace('total', '').lower()
            individual_name = individual_name.rstrip('s')  # totalShares → share
            
            # Check if there's a mapping with similar name
            has_mapping = any('mapping' in v.type and individual_name in k.lower() 
                            for k, v in c.state_vars.items())
            
            if not has_mapping:
                continue
            
            # Find functions that modify BOTH totalX and individual X
            for fname, fi in c.functions.items():
                writes_total = tname in fi.state_writes
                writes_individual = any(individual_name in w.lower() for w in fi.state_writes)
                
                if writes_total and writes_individual:
                    # Check if they're modified by the SAME amount
                    # Look for: totalX += amount AND individual[user] += amount (consistent)
                    # vs: totalX += amount - fee AND individual[user] += amount (INCONSISTENT)
                    
                    total_mods = re.findall(rf'{tname}\s*([\+\-]=)\s*([^;]+);', fi.body)
                    
                    for op, expr in total_mods:
                        expr = expr.strip()
                        # Check if expression has fee subtraction
                        if '-' in expr and ('fee' in expr.lower() or 'penalty' in expr.lower() 
                                           or 'bonus' in expr.lower() or 'reward' in expr.lower()):
                            findings.append(Hypothesis(
                                title=f"Accounting drift: {c.name}.{fname}() — {tname} modified with fee deduction",
                                severity="CRITICAL",
                                phase="FIND_LIES",
                                description=f"{tname} is modified by '{op} {expr}' which includes "
                                          f"a fee/penalty deduction. But the individual user's balance "
                                          f"is likely modified by the full amount. This creates a drift "
                                          f"where {tname} != sum of individual balances.",
                                evidence=f"Line {fi.line}: {tname} {op} {expr}",
                                attack_steps="1. User performs operation\n"
                                           f"2. {tname} decreases by (amount - fee)\n"
                                           f"3. Individual balance decreases by amount\n"
                                           f"4. Drift accumulates over time\n"
                                           f"5. {tname} < sum(individual) → insolvency",
                                profit_calc="Drift per operation = fee amount\n"
                                          f"After N operations: drift = N * fee\n"
                                          "Eventually: pool can't cover all withdrawals",
                                confidence=0.85
                            ))
        
        # Pattern 2: strategyBalance / internal accounting that can desync
        for vname, var in c.state_vars.items():
            if 'balance' in vname.lower() and 'mapping' not in var.type:
                # This is a global balance tracker
                # Check: is it updated when tokens actually move?
                for fname, fi in c.functions.items():
                    has_external_call = len(fi.external_calls) > 0
                    updates_balance = vname in fi.state_writes
                    
                    if has_external_call and not updates_balance and not fi.is_view:
                        # External call that moves tokens but doesn't update balance tracker
                        if any(kw in fname.lower() for kw in ['harvest', 'withdraw', 'invest', 'divest', 'repay']):
                            findings.append(Hypothesis(
                                title=f"Stale balance tracker: {c.name}.{fname}() doesn't update {vname}",
                                severity="HIGH",
                                phase="FIND_LIES",
                                description=f"{fname}() makes external calls ({', '.join(fi.external_calls)}) "
                                          f"that may move tokens, but does NOT update {vname}. "
                                          f"This can cause {vname} to desync from actual balance.",
                                evidence=f"Line {fi.line}: external calls present, {vname} not in state_writes",
                                confidence=0.6
                            ))
        
        # Pattern 3: balanceOf-based accounting (donation attack)
        for fname, fi in c.functions.items():
            if 'balanceOf(address(this))' in fi.body or 'balanceOf(this)' in fi.body:
                # Check if there's a donate/fallback function
                has_donate = any('donate' in f.lower() for f in c.functions)
                has_receive = 'receive()' in c.raw_code or 'fallback()' in c.raw_code
                
                if has_donate or has_receive:
                    findings.append(Hypothesis(
                        title=f"Donation/inflation attack: {c.name} uses balanceOf for accounting",
                        severity="HIGH",
                        phase="FIND_LIES",
                        description=f"{fname}() uses asset.balanceOf(address(this)) for accounting. "
                                  f"Contract has a donate() or receive() function that allows "
                                  f"anyone to inflate the balance without receiving shares. "
                                  f"This enables first-depositor/inflation attacks.",
                        evidence=f"Line {fi.line}: balanceOf used + donate/receive exists",
                        attack_steps="1. Attacker deposits 1 wei → 1 share\n"
                                   "2. Attacker donates 1,000,000 tokens\n"
                                   "3. sharePrice = 1,000,000e18\n"
                                   "4. Victim deposits 100 tokens → 0 shares (rounds to 0)\n"
                                   "5. Victim loses 100 tokens\n"
                                   "6. Attacker withdraws → gets everything",
                        profit_calc="Profit = victim_deposits (all of them)\n"
                                  "Cost = 1 wei + donation (recovered on withdraw)",
                        confidence=0.8
                    ))
                    break  # Only report once per contract
    
    return findings

# ═══════════════════════════════════════════
# PHASE 3: FOLLOW STALE STATE
# ═══════════════════════════════════════════

def phase3_stale_state(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        # Find "settlement" or "update" functions
        update_funcs = [fname for fname in c.functions 
                       if any(kw in fname.lower() for kw in 
                             ['update', 'settle', 'accrue', 'sync', 'refresh', 'checkpoint'])]
        
        if not update_funcs:
            continue
        
        # For each state-changing function, check if it calls the update function
        for fname, fi in c.functions.items():
            if fi.is_view or fname in update_funcs:
                continue
            
            has_state_change = len(fi.state_writes) > 0
            if not has_state_change:
                continue
            
            calls_update = any(uf in fi.body for uf in update_funcs)
            
            if not calls_update:
                # This function changes state but doesn't call the update function
                # Check if it SHOULD (does it interact with the same state?)
                for uf in update_funcs:
                    if uf in c.functions:
                        update_fi = c.functions[uf]
                        # Check overlap in state variables
                        overlap = set(fi.state_writes) & set(update_fi.state_writes)
                        if overlap:
                            findings.append(Hypothesis(
                                title=f"Stale state: {c.name}.{fname}() doesn't call {uf}()",
                                severity="HIGH",
                                phase="STALE_STATE",
                                description=f"{fname}() modifies state variables "
                                          f"({', '.join(fi.state_writes)}) but does NOT call "
                                          f"{uf}() first. This means {uf}()'s state "
                                          f"(e.g., interest index, reward accumulator, epoch) "
                                          f"may be stale when {fname}() executes.",
                                evidence=f"Line {fi.line}: writes {overlap}, no call to {uf}()",
                                confidence=0.7
                            ))
        
        # Check: update function that's NOT called by money-out functions
        for uf in update_funcs:
            for fname, fi in c.functions.items():
                if any(kw in fname.lower() for kw in MONEY_OUT):
                    if uf not in fi.body and not fi.is_view:
                        findings.append(Hypothesis(
                            title=f"Missing settlement: {c.name}.{fname}() skips {uf}()",
                            severity="MEDIUM",
                            phase="STALE_STATE",
                            description=f"Money-out function {fname}() does not call {uf}() "
                                      f"before processing. Users may withdraw at stale rates.",
                            evidence=f"Line {fi.line}: no call to {uf}()",
                            confidence=0.5
                        ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 4: BREAK COMPOSITION
# ═══════════════════════════════════════════

def phase4_composition(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        for fname, fi in c.functions.items():
            if fi.is_view:
                continue
            
            # Check: external call BEFORE state update (CEI violation)
            ext_call_pos = -1
            state_write_pos = -1
            
            for ext in fi.external_calls:
                pos = fi.body.find(f'{ext}.')
                if pos >= 0 and (ext_call_pos < 0 or pos < ext_call_pos):
                    ext_call_pos = pos
            
            for sv in fi.state_writes:
                pos = fi.body.find(f'{sv}')
                if pos >= 0 and (state_write_pos < 0 or pos > state_write_pos):
                    state_write_pos = pos
            
            if ext_call_pos >= 0 and state_write_pos >= 0 and ext_call_pos < state_write_pos:
                if not fi.has_nonreentrant:
                    findings.append(Hypothesis(
                        title=f"CEI violation: {c.name}.{fname}() — external call before state update",
                        severity="HIGH",
                        phase="COMPOSITION",
                        description=f"{fname}() makes external call to {fi.external_calls[0]} "
                                  f"BEFORE updating state ({', '.join(fi.state_writes)}). "
                                  f"No nonReentrant modifier found. "
                                  f"Reentrancy may be possible.",
                        evidence=f"Line {fi.line}: ext call at pos {ext_call_pos}, "
                                f"state write at pos {state_write_pos}",
                        confidence=0.6
                    ))
            
            # Check: external call to arbitrary address (callback risk)
            if '.call{' in fi.body or '.call(' in fi.body:
                # Check if target is user-controlled
                if 'msg.sender' in fi.body or 'to' in fi.params or 'recipient' in fi.params or 'target' in fi.params:
                    if not fi.has_nonreentrant:
                        findings.append(Hypothesis(
                            title=f"Arbitrary external call: {c.name}.{fname}()",
                            severity="MEDIUM",
                            phase="COMPOSITION",
                            description=f"{fname}() makes a low-level .call() to a potentially "
                                      f"user-controlled address without nonReentrant protection.",
                            evidence=f"Line {fi.line}: .call{{}} to user address",
                            confidence=0.5
                        ))
        
        # Check: hook/callback pattern
        hook_calls = [fname for fname, fi in c.functions.items() 
                     if any('hook' in ext.lower() or 'callback' in ext.lower() 
                           for ext in fi.external_calls)]
        
        if hook_calls:
            findings.append(Hypothesis(
                title=f"External hook/callback in {c.name}: {', '.join(hook_calls)}",
                severity="MEDIUM",
                phase="COMPOSITION",
                description=f"Functions {hook_calls} call external hook/callback contracts. "
                          f"Verify: (1) state is updated BEFORE hook call, "
                          f"(2) hook can't re-enter, (3) hook can't manipulate oracles/state "
                          f"used by subsequent operations.",
                evidence=f"Hook calls found in {len(hook_calls)} functions",
                confidence=0.4
            ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 5: THINK LIKE ATTACKER
# ═══════════════════════════════════════════

def phase5_attacker(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        # Check 1: Something for nothing
        for fname, fi in c.functions.items():
            if fi.is_view:
                continue
            # Function that gives tokens but doesn't take any
            gives_tokens = any(kw in fi.body for kw in ['.transfer(', '.mint(', 'transfer('])
            takes_tokens = any(kw in fi.body for kw in ['transferFrom(', '.deposit(', 'msg.value'])
            
            if gives_tokens and not takes_tokens and fname.lower() not in ('withdraw', 'unstake', 'claim', 'repay'):
                if fi.visibility in ('external', 'public'):
                    findings.append(Hypothesis(
                        title=f"Free money? {c.name}.{fname}() gives tokens without taking any",
                        severity="HIGH",
                        phase="ATTACKER",
                        description=f"{fname}() transfers/mints tokens but doesn't appear to "
                                  f"require any input tokens or ETH. Verify this is intentional.",
                        evidence=f"Line {fi.line}: gives tokens, no transferFrom/msg.value found",
                        confidence=0.4
                    ))
        
        # Check 2: Flash loan amplification
        has_lending = any('borrow' in f.lower() or 'lend' in f.lower() or 'loan' in f.lower() 
                         for f in c.functions)
        has_governance = any('vote' in f.lower() or 'governor' in f.lower() or 'proposal' in f.lower()
                            for f in c.functions)
        has_staking = any('stake' in f.lower() for f in c.functions)
        
        if has_governance and has_staking:
            findings.append(Hypothesis(
                title=f"Flash-loan governance: {c.name}",
                severity="HIGH",
                phase="ATTACKER",
                description="Contract has both staking and governance. "
                          "Attacker can: flash loan → stake → get voting power → vote → unstake → repay. "
                          "Voting power without economic commitment. "
                          "Check: is voting power snapshotted? Is there a lock period?",
                evidence="staking + governance functions coexist",
                confidence=0.5
            ))
        
        # Check 3: Missing liquidation in lending
        if has_lending:
            has_liquidation = any('liquidat' in f.lower() for f in c.functions)
            if not has_liquidation:
                findings.append(Hypothesis(
                    title=f"Missing liquidation: {c.name}",
                    severity="MEDIUM",
                    phase="ATTACKER",
                    description="Lending protocol without liquidation mechanism. "
                              "If collateral value drops, bad debt accumulates with no way to resolve it. "
                              "Pool becomes insolvent.",
                    evidence="Lending functions found, no liquidation function",
                    confidence=0.6
                ))
        
        # Check 4: Admin can rug
        admin_funcs = [fname for fname, fi in c.functions.items()
                      if 'onlyOwner' in ' '.join(fi.modifiers) or 'admin' in fi.access_control.lower()]
        
        for fname in admin_funcs:
            fi = c.functions[fname]
            if any(kw in fi.body for kw in ['invest', 'transfer', 'withdraw', 'sweep', 'rescue']):
                if 'invest' in fi.body or 'strategy' in fi.body:
                    findings.append(Hypothesis(
                        title=f"Admin rug vector: {c.name}.{fname}()",
                        severity="MEDIUM",
                        phase="ATTACKER",
                        description=f"Admin function {fname}() can move user funds to external "
                                  f"strategy/contract. If admin is compromised, user funds can be "
                                  f"drained. Check: is there a timelock? Multi-sig? Withdrawal limit?",
                        evidence=f"Line {fi.line}: admin-only fund movement",
                        confidence=0.4
                    ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 6: ADDITIONAL PATTERNS
# ═══════════════════════════════════════════

def phase6_patterns(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        code = c.raw_code
        
        # Pattern: division before multiplication
        if re.search(r'/\s*\w+\s*\*', code):
            findings.append(Hypothesis(
                title=f"Division before multiplication in {c.name}",
                severity="LOW",
                phase="PATTERNS",
                description="Division before multiplication causes precision loss. "
                          "Use mulDiv() or reorder operations.",
                evidence="Regex match: / X * Y pattern",
                confidence=0.3
            ))
        
        # Pattern: block.timestamp manipulation
        timestamp_uses = re.findall(r'block\.timestamp', code)
        if len(timestamp_uses) > 2:
            findings.append(Hypothesis(
                title=f"Heavy timestamp dependence in {c.name}",
                severity="LOW",
                phase="PATTERNS",
                description=f"block.timestamp used {len(timestamp_uses)} times. "
                          f"Miners/validators can manipulate ±15 seconds. "
                          f"Check if any critical logic depends on exact timestamp.",
                evidence=f"{len(timestamp_uses)} uses of block.timestamp",
                confidence=0.2
            ))
        
        # Pattern: unchecked block
        unchecked_blocks = re.findall(r'unchecked\s*\{', code)
        if unchecked_blocks:
            findings.append(Hypothesis(
                title=f"Unchecked arithmetic in {c.name}",
                severity="MEDIUM",
                phase="PATTERNS",
                description=f"{len(unchecked_blocks)} unchecked block(s) found. "
                          f"Verify no overflow/underflow is possible inside.",
                evidence=f"{len(unchecked_blocks)} unchecked blocks",
                confidence=0.3
            ))
        
        # Pattern: tx.origin
        if 'tx.origin' in code:
            findings.append(Hypothesis(
                title=f"tx.origin authentication in {c.name}",
                severity="HIGH",
                phase="PATTERNS",
                description="tx.origin used for authentication. Vulnerable to phishing attacks "
                          "where a malicious contract intermediates the call.",
                evidence="tx.origin found in code",
                confidence=0.8
            ))
        
        # Pattern: delegatecall
        if 'delegatecall' in code:
            findings.append(Hypothesis(
                title=f"delegatecall in {c.name}",
                severity="HIGH",
                phase="PATTERNS",
                description="delegatecall found. Verify target address is immutable/trusted. "
                          "Malicious delegatecall target = full contract takeover.",
                evidence="delegatecall found in code",
                confidence=0.5
            ))
        
        # Pattern: selfdestruct
        if 'selfdestruct' in code:
            findings.append(Hypothesis(
                title=f"selfdestruct in {c.name}",
                severity="CRITICAL",
                phase="PATTERNS",
                description="selfdestruct found. Can permanently destroy contract and force-send ETH.",
                evidence="selfdestruct found in code",
                confidence=0.7
            ))
        
        # Pattern: missing zero-address check
        for fname, fi in c.functions.items():
            if 'address' in ' '.join(fi.params):
                if 'require(' not in fi.body or 'address(0)' not in fi.body:
                    if any(kw in fname.lower() for kw in ['set', 'update', 'initialize', 'constructor']):
                        findings.append(Hypothesis(
                            title=f"Missing zero-address check: {c.name}.{fname}()",
                            severity="LOW",
                            phase="PATTERNS",
                            description=f"{fname}() takes address parameter but doesn't check for address(0).",
                            evidence=f"Line {fi.line}: address param, no zero check",
                            confidence=0.2
                        ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 7: CROSS-CONTRACT ANALYSIS (v2)
# ═══════════════════════════════════════════

def phase7_cross_contract(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    # Build call graph: which contract calls which
    call_graph = {}  # caller_contract -> [(callee_name, function, line)]
    contract_names = {c.name for c in contracts}
    
    for c in contracts:
        call_graph[c.name] = []
        for fname, fi in c.functions.items():
            for ext in fi.external_calls:
                # Check if ext is a state var typed as another contract
                for vname, var in c.state_vars.items():
                    if vname == ext or ext.lower() in vname.lower():
                        # Try to resolve type to a known contract
                        for target_name in contract_names:
                            if target_name.lower() in var.type.lower() or target_name.lower() in vname.lower():
                                call_graph[c.name].append((target_name, fname, fi.line))
    
    # Detect cycles: A → B → A
    for a_name, a_calls in call_graph.items():
        for b_name, a_func, a_line in a_calls:
            if b_name in call_graph:
                for c_name, b_func, b_line in call_graph[b_name]:
                    if c_name == a_name:
                        findings.append(Hypothesis(
                            title=f"Cross-contract cycle: {a_name} → {b_name} → {a_name}",
                            severity="HIGH",
                            phase="CROSS_CONTRACT",
                            description=f"{a_name}.{a_func}() calls {b_name}, which calls back "
                                      f"into {a_name}.{b_func}(). This creates a cross-contract "
                                      f"reentrancy path. Verify: (1) nonReentrant on both sides, "
                                      f"(2) state updated before external calls in BOTH contracts, "
                                      f"(3) no state in {a_name} that {b_name} reads mid-call.",
                            evidence=f"{a_name} L{a_line} → {b_name} L{b_line} → {a_name}",
                            attack_steps=f"1. Attacker calls {a_name}.{a_func}()\n"
                                       f"2. {a_name} calls {b_name}\n"
                                       f"3. {b_name} calls back {a_name}.{b_func}()\n"
                                       f"4. {a_name} state may be inconsistent (half-updated)\n"
                                       f"5. Exploit inconsistent state for profit",
                            confidence=0.6
                        ))
    
    # Detect: contract reads state from another contract that can be manipulated
    for c in contracts:
        for fname, fi in c.functions.items():
            # Look for external view calls used in critical calculations
            ext_view_calls = re.findall(r'(\w+)\.(?:balanceOf|totalSupply|getPrice|getRate|'
                                       r'getReserves|getAmountOut|decimals|totalAssets|'
                                       r'convertToAssets|convertToShares|getVirtualPrice|'
                                       r'pricePerShare|exchangeRate)\s*\(', fi.body)
            if ext_view_calls and not fi.is_view:
                # This function uses external state for calculations
                for ext in ext_view_calls:
                    findings.append(Hypothesis(
                        title=f"External state dependency: {c.name}.{fname}() reads {ext}",
                        severity="MEDIUM",
                        phase="CROSS_CONTRACT",
                        description=f"{fname}() reads state from {ext} (balanceOf/getPrice/etc) "
                                  f"and uses it in calculations. If {ext}'s state can be "
                                  f"manipulated (flash loan, donation, oracle), the calculation "
                                  f"in {c.name} will be wrong. Verify: is {ext} manipulable "
                                  f"within a single transaction?",
                        evidence=f"Line {fi.line}: reads {ext} for calculation",
                        confidence=0.4
                    ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 8: MULTI-TX ATTACK DETECTION (v2)
# ═══════════════════════════════════════════

def phase8_multi_tx(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        # Pattern 1: Setup function + exploit function
        # Setup: changes state that a later function relies on
        # Exploit: uses that state for profit
        setup_funcs = []
        exploit_funcs = []
        
        for fname, fi in c.functions.items():
            if fi.is_view:
                continue
            fname_lower = fname.lower()
            # Setup indicators: change config, set rate, update oracle, add liquidity
            if any(kw in fname_lower for kw in ['set', 'update', 'configure', 'add', 'initialize', 'deposit']):
                setup_funcs.append((fname, fi))
            # Exploit indicators: withdraw, claim, liquidate, borrow
            if any(kw in fname_lower for kw in ['withdraw', 'claim', 'liquidate', 'borrow', 'redeem', 'unstake']):
                exploit_funcs.append((fname, fi))
        
        # Check: setup writes state that exploit reads
        for s_name, s_fi in setup_funcs:
            for e_name, e_fi in exploit_funcs:
                if s_name == e_name:
                    continue
                # State written by setup, read by exploit
                shared_state = set(s_fi.state_writes) & set(e_fi.state_reads)
                if shared_state and len(shared_state) > 0:
                    # Check if there's a time lock or access control preventing same-tx
                    has_timelock = 'timelock' in c.raw_code.lower() or 'delay' in c.raw_code.lower()
                    has_access = e_fi.access_control != ''
                    
                    if not has_timelock:
                        findings.append(Hypothesis(
                            title=f"Multi-tx attack: {c.name}.{s_name}() → {e_name}()",
                            severity="MEDIUM",
                            phase="MULTI_TX",
                            description=f"tx1: {s_name}() modifies {', '.join(shared_state)}. "
                                      f"tx2: {e_name}() reads that state for fund extraction. "
                                      f"Attacker can: (1) call {s_name}() to manipulate state, "
                                      f"(2) call {e_name}() to profit from manipulated state. "
                                      f"{'Mitigated by access control.' if has_access else 'No access control on exploit function.'}",
                            evidence=f"Shared state: {', '.join(shared_state)}",
                            attack_steps=f"tx1: {s_name}() → set {', '.join(shared_state)} to favorable value\n"
                                       f"tx2: {e_name}() → extract funds based on manipulated state\n"
                                       f"Profit: difference between fair value and manipulated value",
                            confidence=0.4 if has_access else 0.6
                        ))
        
        # Pattern 2: Epoch/period boundary attacks
        # Function that accumulates over time + function that claims
        for fname, fi in c.functions.items():
            if 'epoch' in fname.lower() or 'period' in fname.lower() or 'round' in fname.lower():
                # Check if there's a way to skip/freeze epochs
                for other_name, other_fi in c.functions.items():
                    if other_name == fname:
                        continue
                    if any(kw in other_name.lower() for kw in ['harvest', 'claim', 'withdraw', 'settle']):
                        if fname not in other_fi.body:
                            findings.append(Hypothesis(
                                title=f"Epoch boundary skip: {c.name}.{other_name}() doesn't call {fname}()",
                                severity="HIGH",
                                phase="MULTI_TX",
                                description=f"{other_name}() processes claims/withdrawals but doesn't "
                                          f"call {fname}() to settle the current epoch first. "
                                          f"Multiple epochs can accumulate without settlement, "
                                          f"causing incorrect reward/interest distribution.",
                                evidence=f"{other_name}() at L{other_fi.line} doesn't call {fname}()",
                                confidence=0.6
                            ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 9: ORACLE MANIPULATION (v2)
# ═══════════════════════════════════════════

def phase9_oracle(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        code = c.raw_code
        
        # Pattern 1: Spot price usage (no TWAP)
        spot_calls = re.findall(r'(\w+)\.(?:getPrice|latestRoundData|latestAnswer|peek|read|getSpotPrice)\s*\(', code)
        twap_present = 'twap' in code.lower() or 'observe' in code.lower() or 'consult' in code.lower()
        
        if spot_calls and not twap_present:
            findings.append(Hypothesis(
                title=f"Spot oracle usage (no TWAP): {c.name}",
                severity="HIGH",
                phase="ORACLE",
                description=f"Contract uses spot price from {', '.join(set(spot_calls))} without "
                          f"TWAP protection. Spot prices can be manipulated within a single "
                          f"transaction via flash loans (manipulate DEX reserves → read price → "
                          f"exploit → repay). Use TWAP or Chainlink with staleness check.",
                evidence=f"Spot price calls: {', '.join(set(spot_calls))}",
                attack_steps="1. Flash loan large amount\n"
                           "2. Swap on DEX to skew reserves → spot price moves\n"
                           "3. Call protocol function that reads manipulated price\n"
                           "4. Profit from mispriced operation\n"
                           "5. Swap back + repay flash loan",
                profit_calc="Profit proportional to flash loan size × price impact",
                confidence=0.7
            ))
        
        # Pattern 2: Missing staleness check
        if 'latestRoundData' in code or 'latestAnswer' in code:
            has_staleness = 'updatedAt' in code or 'timestamp' in code and 'require' in code
            if not has_staleness:
                findings.append(Hypothesis(
                    title=f"Missing oracle staleness check: {c.name}",
                    severity="MEDIUM",
                    phase="ORACLE",
                    description="Chainlink oracle used without checking updatedAt timestamp. "
                              "Stale prices can lead to incorrect valuations if the oracle "
                              "hasn't been updated recently (heartbeat missed, deviation not hit).",
                    evidence="latestRoundData/latestAnswer without updatedAt check",
                    confidence=0.6
                ))
        
        # Pattern 3: Single-source oracle (no fallback)
        oracle_sources = set()
        for pattern in ['chainlink', 'uniswap', 'curve', 'pyth', 'redstone', 'band', 'tellor']:
            if pattern in code.lower():
                oracle_sources.add(pattern)
        
        if len(oracle_sources) == 1 and ('chainlink' not in oracle_sources):
            findings.append(Hypothesis(
                title=f"Single oracle source: {c.name} uses only {list(oracle_sources)[0]}",
                severity="MEDIUM",
                phase="ORACLE",
                description=f"Only one oracle source ({list(oracle_sources)[0]}) is used. "
                          f"If this oracle is manipulated or goes down, the protocol has "
                          f"no fallback. Consider: Chainlink + DEX TWAP as backup.",
                evidence=f"Oracle sources found: {oracle_sources}",
                confidence=0.4
            ))
        
        # Pattern 4: Oracle value used without bounds check
        for fname, fi in c.functions.items():
            if fi.is_view:
                continue
            price_reads = re.findall(r'(?:price|rate|value)\s*=\s*(\w+)\.(?:get|latest|peek|read)', fi.body)
            if price_reads:
                has_bounds = 'require' in fi.body and ('>' in fi.body or '<' in fi.body)
                if not has_bounds:
                    findings.append(Hypothesis(
                        title=f"Unbounded oracle value: {c.name}.{fname}()",
                        severity="MEDIUM",
                        phase="ORACLE",
                        description=f"{fname}() reads oracle value but doesn't validate it's "
                                  f"within reasonable bounds. If oracle returns 0 or extreme "
                                  f"value, calculations will be wrong. Add: require(price > minPrice "
                                  f"&& price < maxPrice).",
                        evidence=f"Line {fi.line}: oracle read without bounds check",
                        confidence=0.5
                    ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 10: GOVERNANCE & TIMELOCK (v2)
# ═══════════════════════════════════════════

def phase10_governance(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        code = c.raw_code
        fname_set = {f.lower() for f in c.functions}
        
        # Pattern 1: Governance without timelock
        has_governance = any(kw in ' '.join(fname_set) for kw in ['vote', 'proposal', 'governor', 'execute'])
        has_timelock = 'timelock' in code.lower() or 'delay' in code.lower() or 'MINIMUM_DELAY' in code
        
        if has_governance and not has_timelock:
            findings.append(Hypothesis(
                title=f"Governance without timelock: {c.name}",
                severity="HIGH",
                phase="GOVERNANCE",
                description="Governance functions exist but no timelock/delay found. "
                          "Proposals can be executed immediately after passing, giving "
                          "no time for users to exit if a malicious proposal passes "
                          "(e.g., via flash-loan voting power).",
                evidence="Governance functions found, no timelock/delay",
                attack_steps="1. Flash loan tokens → stake → get voting power\n"
                           "2. Create + vote malicious proposal (e.g., drain treasury)\n"
                           "3. Execute immediately (no timelock)\n"
                           "4. Unstake → repay flash loan\n"
                           "5. Total cost: gas only",
                confidence=0.6
            ))
        
        # Pattern 2: Admin functions without timelock
        admin_funcs = []
        for fname, fi in c.functions.items():
            if 'onlyOwner' in ' '.join(fi.modifiers) or 'onlyAdmin' in ' '.join(fi.modifiers) \
               or 'onlyGovernance' in ' '.join(fi.modifiers):
                if any(kw in fi.body for kw in ['transfer', 'withdraw', 'sweep', 'set', 'upgrade', 'pause']):
                    admin_funcs.append(fname)
        
        if admin_funcs and not has_timelock:
            findings.append(Hypothesis(
                title=f"Admin powers without timelock: {c.name} ({len(admin_funcs)} functions)",
                severity="MEDIUM",
                phase="GOVERNANCE",
                description=f"Admin can call: {', '.join(admin_funcs[:5])}{'...' if len(admin_funcs) > 5 else ''}. "
                          f"No timelock found. If admin key is compromised, attacker can "
                          f"immediately drain/modify the protocol. Users have no time to react.",
                evidence=f"{len(admin_funcs)} admin functions, no timelock",
                confidence=0.5
            ))
        
        # Pattern 3: Pause mechanism without unpause timelock
        if 'pause' in code.lower() and 'unpause' in code.lower():
            has_unpause_delay = 'delay' in code.lower() and 'unpause' in code.lower()
            if not has_unpause_delay:
                findings.append(Hypothesis(
                    title=f"Instant unpause: {c.name}",
                    severity="LOW",
                    phase="GOVERNANCE",
                    description="Contract can be paused and unpaused without delay. "
                              "Admin can pause → manipulate state → unpause, or "
                              "pause to prevent users from exiting during an exploit.",
                    evidence="pause/unpause without delay",
                    confidence=0.3
                ))
        
        # Pattern 4: Voting power = token balance (no snapshot/lock)
        if 'balanceOf' in code and ('vote' in ' '.join(fname_set) or 'proposal' in ' '.join(fname_set)):
            has_snapshot = 'snapshot' in code.lower() or 'getPastVotes' in code or 'ERC20Votes' in code
            has_lock = 'lock' in code.lower() or 'vesting' in code.lower()
            
            if not has_snapshot and not has_lock:
                findings.append(Hypothesis(
                    title=f"Flash-loan voting: {c.name} uses balanceOf for voting power",
                    severity="HIGH",
                    phase="GOVERNANCE",
                    description="Voting power appears to be based on current balanceOf "
                              "without snapshot or lock mechanism. Attacker can: "
                              "flash loan → transfer to self → vote → transfer back → repay. "
                              "Check: does it use ERC20Votes/getPastVotes?",
                    evidence="balanceOf + voting without snapshot/lock",
                    confidence=0.5
                ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 11: ERC-4626 SPECIFIC CHECKS (v2)
# ═══════════════════════════════════════════

def phase11_erc4626(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        code = c.raw_code
        fname_set = set(c.functions.keys())
        
        # Detect ERC-4626 vault
        is_4626 = ('convertToShares' in fname_set or 'convertToAssets' in fname_set or
                   'totalAssets' in fname_set or 'ERC4626' in ' '.join(c.inherits))
        
        if not is_4626:
            continue
        
        # Check 1: First depositor / inflation attack
        has_virtual = 'virtual' in code.lower() and ('shares' in code.lower() or 'assets' in code.lower())
        has_dead_mint = 'dead' in code.lower() or '1e' in code  # initial mint to dead address
        
        if not has_virtual and not has_dead_mint:
            findings.append(Hypothesis(
                title=f"ERC-4626 inflation attack: {c.name} (no virtual shares/offset)",
                severity="HIGH",
                phase="ERC4626",
                description="ERC-4626 vault without virtual shares/offset protection. "
                          "First depositor can: deposit 1 wei → donate large amount → "
                          "inflate share price → subsequent deposits round to 0 shares → "
                          "attacker withdraws everything. "
                          "Fix: use ERC4626Upgradeable with virtual offset, or mint initial "
                          "shares to dead address.",
                evidence="No virtual shares/offset/dead address mint found",
                attack_steps="1. deposit(1) → 1 share\n"
                           "2. transfer 1,000,000e18 directly to vault\n"
                           "3. totalAssets = 1,000,000e18 + 1, totalShares = 1\n"
                           "4. Victim deposit(100e18) → shares = 100e18 * 1 / 1e24 = 0\n"
                           "5. Victim loses 100 tokens, gets 0 shares\n"
                           "6. Attacker withdraw(1) → gets ~1,000,000e18",
                profit_calc="Profit = all subsequent deposits (round to 0 shares)",
                confidence=0.7
            ))
        
        # Check 2: totalAssets() manipulable
        if 'totalAssets' in fname_set:
            ta_body = c.functions['totalAssets'].body if 'totalAssets' in c.functions else ''
            uses_balanceof = 'balanceOf' in ta_body
            if uses_balanceof:
                findings.append(Hypothesis(
                    title=f"ERC-4626 totalAssets() uses balanceOf: {c.name}",
                    severity="MEDIUM",
                    phase="ERC4626",
                    description="totalAssets() returns asset.balanceOf(address(this)). "
                              "This can be manipulated by direct token transfers (donation). "
                              "If the vault doesn't use virtual shares, this enables "
                              "inflation attacks. Even with virtual shares, large donations "
                              "can cause precision issues.",
                    evidence="totalAssets() = balanceOf(address(this))",
                    confidence=0.5
                ))
        
        # Check 3: Missing deposit/mint limits
        has_max_deposit = 'maxDeposit' in fname_set or 'maxMint' in fname_set
        has_supply_cap = 'cap' in code.lower() or 'limit' in code.lower() or 'max' in code.lower()
        
        if not has_max_deposit and not has_supply_cap:
            findings.append(Hypothesis(
                title=f"ERC-4626 no deposit limit: {c.name}",
                severity="LOW",
                phase="ERC4626",
                description="No maxDeposit/maxMint/supply cap found. In an attack scenario, "
                          "unlimited deposits could amplify economic exploits. "
                          "Consider: add deposit caps as circuit breaker.",
                evidence="No maxDeposit/maxMint/cap found",
                confidence=0.3
            ))
        
        # Check 4: Rounding direction
        # ERC-4626 spec: convertToShares should round DOWN, convertToAssets should round DOWN
        # previewDeposit/previewMint should round in favor of vault
        for fname in ['convertToShares', 'convertToAssets', 'previewDeposit', 'previewMint',
                       'previewWithdraw', 'previewRedeem']:
            if fname in c.functions:
                body = c.functions[fname].body
                # Check for rounding: mulDiv with round up vs down
                if 'mulDiv' in body:
                    if 'RoundUp' in body or 'roundUp' in body or 'Rounding.Up' in body:
                        if fname in ['convertToShares', 'convertToAssets']:
                            findings.append(Hypothesis(
                                title=f"ERC-4626 wrong rounding: {c.name}.{fname}() rounds UP",
                                severity="MEDIUM",
                                phase="ERC4626",
                                description=f"{fname}() rounds UP but ERC-4626 spec requires "
                                          f"convertToShares/convertToAssets to round DOWN. "
                                          f"Rounding up can be exploited: attacker can extract "
                                          f"more assets/shares than they should.",
                                evidence=f"{fname}() uses RoundUp",
                                confidence=0.7
                            ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 12: PROXY & UPGRADE PATTERNS (v2)
# ═══════════════════════════════════════════

def phase12_proxy(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        code = c.raw_code
        fname_set = set(c.functions.keys())
        
        # Detect proxy patterns
        is_proxy = ('delegatecall' in code or 'implementation' in code.lower() or
                   'upgrade' in ' '.join(f.lower() for f in fname_set) or
                   'proxy' in c.name.lower() or 'ERC1967' in code or
                   'TransparentUpgradeable' in ' '.join(c.inherits) or
                   'UUPSUpgradeable' in ' '.join(c.inherits))
        
        if not is_proxy:
            continue
        
        # Check 1: Storage collision risk
        has_storage_gap = '__gap' in code or '_gap' in code
        has_erc7201 = 'erc7201' in code.lower() or 'storage.' in code.lower()
        
        if not has_storage_gap and not has_erc7201:
            findings.append(Hypothesis(
                title=f"Storage collision risk: {c.name} (no __gap/ERC-7201)",
                severity="HIGH",
                phase="PROXY",
                description="Upgradeable contract without storage gap (__gap) or ERC-7201 "
                          "namespaced storage. When the implementation is upgraded and new "
                          "state variables are added, they can overwrite existing storage "
                          "slots, corrupting critical data (owner, balances, config).",
                evidence="No __gap or ERC-7201 pattern found",
                attack_steps="1. Deploy v1 with N state variables\n"
                           "2. Upgrade to v2 with N+M state variables (no gap)\n"
                           "3. New variables occupy slots used by v1's inherited contracts\n"
                           "4. Critical state (owner, balances) corrupted\n"
                           "5. Attacker exploits corrupted state",
                confidence=0.6
            ))
        
        # Check 2: Unprotected upgrade function
        for fname in ['upgradeTo', 'upgradeToAndCall', '_authorizeUpgrade', 'upgrade']:
            if fname in c.functions:
                fi = c.functions[fname]
                has_access = fi.access_control != '' or 'onlyOwner' in ' '.join(fi.modifiers) \
                           or 'onlyAdmin' in ' '.join(fi.modifiers) or 'onlyProxy' in ' '.join(fi.modifiers)
                if not has_access:
                    findings.append(Hypothesis(
                        title=f"Unprotected upgrade: {c.name}.{fname}()",
                        severity="CRITICAL",
                        phase="PROXY",
                        description=f"{fname}() has no access control. Anyone can upgrade "
                                  f"the implementation to a malicious contract that drains "
                                  f"all funds or self-destructs the proxy.",
                        evidence=f"Line {fi.line}: no onlyOwner/onlyAdmin modifier",
                        confidence=0.8
                    ))
        
        # Check 3: Initializer not protected
        has_initializer = 'initialize' in ' '.join(f.lower() for f in fname_set)
        has_reinitializer = 'reinitializer' in code
        has_initializer_modifier = 'initializer' in code and 'modifier' not in code.split('initializer')[0][-50:]
        
        if has_initializer and not has_reinitializer:
            # Check if initialize can be called multiple times
            for fname, fi in c.functions.items():
                if 'initialize' in fname.lower():
                    if 'initializer' not in ' '.join(fi.modifiers) and 'initializer' not in fi.body:
                        findings.append(Hypothesis(
                            title=f"Re-initialization risk: {c.name}.{fname}()",
                            severity="HIGH",
                            phase="PROXY",
                            description=f"{fname}() doesn't use the initializer modifier. "
                                      f"It can be called multiple times, allowing an attacker "
                                      f"to re-initialize the contract with malicious parameters "
                                      f"(e.g., change owner, admin, or critical config).",
                            evidence=f"Line {fi.line}: no initializer modifier",
                            confidence=0.7
                        ))
        
        # Check 4: Implementation not locked
        if 'UUPS' in ' '.join(c.inherits) or 'uups' in code.lower():
            has_disable = '_disableInitializers' in code
            if not has_disable:
                findings.append(Hypothesis(
                    title=f"UUPS implementation not locked: {c.name}",
                    severity="MEDIUM",
                    phase="PROXY",
                    description="UUPS upgradeable contract without _disableInitializers() "
                              "in constructor. The implementation contract itself can be "
                              "initialized and potentially taken over.",
                    evidence="No _disableInitializers() in constructor",
                    confidence=0.6
                ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 13: CROSS-CHAIN BRIDGE PATTERNS (v2)
# ═══════════════════════════════════════════

def phase13_cross_chain(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        code = c.raw_code
        fname_set = set(c.functions.keys())
        
        # Detect cross-chain patterns
        bridge_keywords = ['layerzero', 'lzcompose', 'lzreceive', 'wormhole', 'ccip',
                          'crosschain', 'cross_chain', 'bridge', 'sendmessage',
                          'endpoint', 'oftadapter', 'onft', 'ultralightnode']
        
        is_bridge = any(kw in code.lower() for kw in bridge_keywords)
        
        if not is_bridge:
            continue
        
        # Check 1: Message replay
        has_nonce = 'nonce' in code.lower() or 'messageId' in code or 'sequence' in code.lower()
        has_replay_protection = 'executed' in code.lower() or 'processed' in code.lower() or 'seen' in code.lower()
        
        if not has_nonce and not has_replay_protection:
            findings.append(Hypothesis(
                title=f"Cross-chain message replay: {c.name}",
                severity="CRITICAL",
                phase="CROSS_CHAIN",
                description="Cross-chain message handler without nonce/replay protection. "
                          "A valid message from chain A can be replayed on chain B multiple "
                          "times, minting/unlocking funds repeatedly.",
                evidence="No nonce/messageId/executed tracking found",
                attack_steps="1. Legitimate bridge message sent from chain A\n"
                           "2. Attacker captures the message\n"
                           "3. Replay message on chain B multiple times\n"
                           "4. Each replay mints/unlocks funds\n"
                           "5. Profit = N × message value",
                confidence=0.6
            ))
        
        # Check 2: Missing source chain validation
        has_src_validation = 'srcChainId' in code or 'sourceChain' in code or '_srcChainId' in code
        has_allowed_sources = 'allowedSource' in code or 'trustedSource' in code or 'srcChainId ==' in code
        
        if has_src_validation and not has_allowed_sources:
            findings.append(Hypothesis(
                title=f"Unvalidated source chain: {c.name}",
                severity="HIGH",
                phase="CROSS_CHAIN",
                description="Cross-chain handler reads srcChainId but doesn't validate it "
                          "against an allowlist. Messages from unauthorized chains could "
                          "trigger fund minting/unlocking.",
                evidence="srcChainId present but no allowlist check",
                confidence=0.5
            ))
        
        # Check 3: No rate limiting on bridge
        has_rate_limit = 'limit' in code.lower() and ('bridge' in code.lower() or 'send' in code.lower())
        has_daily_cap = 'daily' in code.lower() or 'cap' in code.lower()
        
        if not has_rate_limit and not has_daily_cap:
            findings.append(Hypothesis(
                title=f"No bridge rate limit: {c.name}",
                severity="MEDIUM",
                phase="CROSS_CHAIN",
                description="Cross-chain bridge without rate limiting or daily caps. "
                          "If the bridge is exploited (replay, oracle manipulation), "
                          "the attacker can drain unlimited funds. Circuit breaker "
                          "(rate limit) would contain the damage.",
                evidence="No rate limit/daily cap found",
                confidence=0.4
            ))
        
        # Check 4: Compose message ordering
        if 'lzCompose' in code or 'lzcompose' in code.lower():
            has_ordering = 'index' in code.lower() or 'sequence' in code.lower()
            if not has_ordering:
                findings.append(Hypothesis(
                    title=f"Compose message ordering: {c.name}",
                    severity="MEDIUM",
                    phase="CROSS_CHAIN",
                    description="LayerZero compose messages without explicit ordering/index. "
                              "Multiple compose messages can arrive out of order, causing "
                              "state inconsistency if operations depend on sequence.",
                    evidence="lzCompose without index/sequence tracking",
                    confidence=0.4
                ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 14: INTEREST RATE MODEL (v2)
# ═══════════════════════════════════════════

def phase14_interest_model(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        code = c.raw_code
        fname_set = set(c.functions.keys())
        
        # Detect interest rate models
        is_rate_model = any(kw in ' '.join(f.lower() for f in fname_set)
                          for kw in ['interestrate', 'getrate', 'calcrate', 'borrowrate',
                                    'supplyrate', 'amortized', 'apr', 'apy'])
        
        if not is_rate_model:
            continue
        
        # Check 1: Overflow in rate calculation
        has_unchecked = 'unchecked' in code
        has_mul_before_div = re.search(r'\*\s*\w+\s*/', code)
        
        if has_unchecked:
            findings.append(Hypothesis(
                title=f"Unchecked interest calculation: {c.name}",
                severity="HIGH",
                phase="INTEREST_MODEL",
                description="Interest rate model uses unchecked arithmetic. Rate calculations "
                          "often involve large multiplications (rate × time × principal / divisor). "
                          "With extreme but valid inputs (very high rate, long time period), "
                          "overflow can produce incorrect rates → wrong debt/yield calculations.",
                evidence="unchecked block in interest rate calculation",
                attack_steps="1. Set extreme but valid rate parameters\n"
                           "2. Wait long time period (or manipulate timestamp)\n"
                           "3. rate × time overflows in unchecked block\n"
                           "4. Incorrect interest applied\n"
                           "5. Borrower pays less / lender receives less",
                confidence=0.6
            ))
        
        # Check 2: Rate can go to 0 or negative
        for fname, fi in c.functions.items():
            if 'rate' in fname.lower() and not fi.is_view:
                # Check if rate can become 0
                if '-' in fi.body and 'rate' in fi.body.lower():
                    findings.append(Hypothesis(
                        title=f"Rate subtraction: {c.name}.{fname}() can reduce rate",
                        severity="MEDIUM",
                        phase="INTEREST_MODEL",
                        description=f"{fname}() subtracts from a rate value. If the subtraction "
                                  f"underflows (Solidity 0.8+ reverts) or results in 0, interest "
                                  f"accrual stops. Check: can rateTotal - oldRate underflow?",
                        evidence=f"Line {fi.line}: rate subtraction",
                        confidence=0.5
                    ))
        
        # Check 3: Compounding vs simple interest mismatch
        has_compound = 'compound' in code.lower() or 'exp' in code.lower() or 'pow' in code.lower()
        has_simple = 'rate * time' in code.replace(' ', '') or 'rate*time' in code
        
        if has_compound and has_simple:
            findings.append(Hypothesis(
                title=f"Mixed interest models: {c.name}",
                severity="MEDIUM",
                phase="INTEREST_MODEL",
                description="Contract uses both compound and simple interest calculations. "
                          "Mismatch between how interest is accrued vs how it's displayed/charged "
                          "can create arbitrage: borrow at simple rate, repay at compound rate "
                          "(or vice versa).",
                evidence="Both compound and simple interest patterns found",
                confidence=0.4
            ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 15: ROUNDING DIRECTION (v2)
# ═══════════════════════════════════════════

def phase15_rounding(contracts: List[ContractInfo]) -> List[Hypothesis]:
    findings = []
    
    for c in contracts:
        for fname, fi in c.functions.items():
            if fi.is_view:
                continue
            
            # Find division operations
            div_ops = re.findall(r'(\w+)\s*=\s*([^;]*?/\s*[^;]+);', fi.body)
            
            for var_name, expr in div_ops:
                # Check context: is this a user-facing calculation?
                is_user_facing = any(kw in fname.lower() for kw in 
                                   ['deposit', 'withdraw', 'mint', 'redeem', 'borrow',
                                    'repay', 'liquidate', 'claim', 'convert', 'preview'])
                
                if not is_user_facing:
                    continue
                
                # Check: does the rounding favor the protocol or the user?
                # In general: 
                #   deposit/mint → round shares DOWN (favor protocol)
                #   withdraw/redeem → round assets DOWN (favor protocol)
                #   borrow → round debt UP (favor protocol)
                #   repay → round payment DOWN (favor user, but protocol accepts less)
                
                # Look for mulDiv with explicit rounding
                if 'mulDiv' in expr:
                    if 'RoundUp' in expr or 'Rounding.Up' in expr:
                        if any(kw in fname.lower() for kw in ['deposit', 'mint', 'withdraw', 'redeem']):
                            findings.append(Hypothesis(
                                title=f"Rounding favors user: {c.name}.{fname}()",
                                severity="MEDIUM",
                                phase="ROUNDING",
                                description=f"{fname}() uses RoundUp in a deposit/withdraw "
                                          f"context. ERC-4626 requires rounding in favor of "
                                          f"the vault. Rounding up shares on deposit means "
                                          f"user gets more shares than they should → dilution "
                                          f"of existing shareholders.",
                                evidence=f"Line {fi.line}: mulDiv with RoundUp in {fname}",
                                confidence=0.6
                            ))
                
                # Check: repeated rounding (precision loss)
                # a / b * c / d → two rounding operations
                if expr.count('/') >= 2:
                    findings.append(Hypothesis(
                        title=f"Multiple rounding: {c.name}.{fname}()",
                        severity="LOW",
                        phase="ROUNDING",
                        description=f"{fname}() has multiple division operations in one "
                                  f"expression: '{expr.strip()[:60]}...'. Each division "
                                  f"causes precision loss. Combined, the error can be "
                                  f"significant for large values. Use mulDiv() for "
                                  f"single-rounding precision.",
                        evidence=f"Line {fi.line}: {expr.count('/')} divisions in one expression",
                        confidence=0.3
                    ))
    
    return findings

# ═══════════════════════════════════════════
# PHASE 16: SLITHER INTEGRATION (v2)
# ═══════════════════════════════════════════

def phase16_slither_integration(contracts: List[ContractInfo], slither_json: str = None) -> List[Hypothesis]:
    findings = []
    
    if not slither_json or not os.path.exists(slither_json):
        return findings
    
    try:
        with open(slither_json) as f:
            slither_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return findings
    
    results = slither_data.get('results', [])
    
    # Group Slither findings by file/line for cross-referencing
    slither_by_location = {}
    for r in results:
        impact = r.get('impact', 'Informational')
        check = r.get('check', '')
        desc = r.get('description', '')
        
        # Get source location
        elements = r.get('elements', [])
        for elem in elements:
            src = elem.get('source_mapping', {})
            filename = src.get('filename', '')
            lines = src.get('lines', [])
            if filename and lines:
                key = f"{filename}:{lines[0]}"
                if key not in slither_by_location:
                    slither_by_location[key] = []
                slither_by_location[key].append({
                    'check': check,
                    'impact': impact,
                    'description': desc[:200]
                })
    
    # Cross-reference: Slither finding + manual hypothesis on same location = higher confidence
    # Also: Slither findings that manual review SHOULD investigate deeper
    for r in results:
        impact = r.get('impact', 'Informational')
        check = r.get('check', '')
        desc = r.get('description', '')
        
        # High-impact Slither findings that need manual deep-dive
        if impact in ('High', 'Medium'):
            # Check if this is a known FP pattern
            fp_patterns = [
                ('arbitrary-send-eth', 'wallet'),  # wallets send ETH by design
                ('weak-prng', 'period'),           # time-based modulo is fine
                ('unused-return', 'transfer'),     # ETH transfer to EOA
            ]
            
            is_known_fp = False
            for pattern, context in fp_patterns:
                if pattern == check and context in desc.lower():
                    is_known_fp = True
                    break
            
            if not is_known_fp:
                findings.append(Hypothesis(
                    title=f"Slither {impact}: {check} — needs manual deep-dive",
                    severity="MEDIUM" if impact == "Medium" else "HIGH",
                    phase="SLITHER_INTEGRATION",
                    description=f"Slither flagged [{impact}] {check}. "
                              f"This needs manual verification: read the surrounding code, "
                              f"trace the data flow, and determine if it's exploitable. "
                              f"Slither description: {desc[:150]}...",
                    evidence=f"Slither check: {check}, impact: {impact}",
                    confidence=0.5
                ))
    
    if findings:
        findings.append(Hypothesis(
            title=f"Slither integration: {len(results)} total findings, {len(findings)-1} need manual review",
            severity="INFO",
            phase="SLITHER_INTEGRATION",
            description=f"Loaded {len(results)} Slither findings. "
                      f"{len(findings)-1} High/Medium findings need manual deep-dive. "
                      f"Use these as ENTRY POINTS: read the flagged code and surrounding "
                      f"context to find deeper logic bugs that Slither can't detect.",
            evidence=f"Slither JSON: {slither_json}",
            confidence=1.0
        ))
    
    return findings

# ═══════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════

def run_manual_review(path: str, slither_json: str = None) -> List[Hypothesis]:
    # Collect all .sol files
    sol_files = []
    if os.path.isfile(path) and path.endswith('.sol'):
        sol_files = [path]
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            # Skip test, lib, node_modules
            dirs[:] = [d for d in dirs if d not in ('test', 'lib', 'node_modules', 'out', 'cache', 'script')]
            for f in files:
                if f.endswith('.sol'):
                    sol_files.append(os.path.join(root, f))
    
    if not sol_files:
        print(f"ERROR: No .sol files found in {path}")
        return []
    
    print(f"═══ MANUAL REVIEW ENGINE v2.0 ═══")
    print(f"Files: {len(sol_files)}")
    if slither_json:
        print(f"Slither JSON: {slither_json}")
    print()
    
    # Parse all contracts
    all_contracts = []
    for sf in sol_files:
        with open(sf) as f:
            code = f.read()
        contracts = parse_solidity(code, sf)
        all_contracts.extend(contracts)
        for c in contracts:
            print(f"  📄 {sf}: {c.name} ({len(c.functions)} functions, {len(c.state_vars)} state vars)")
    
    print(f"\nTotal contracts: {len(all_contracts)}")
    print()
    
    # Run all 16 phases
    all_findings = []
    
    print("Phase 1: MAP THE MONEY...")
    f1, money_map = phase1_map_money(all_contracts)
    all_findings.extend(f1)
    print(f"  Money IN:  {money_map['in']}")
    print(f"  Money OUT: {money_map['out']}")
    print(f"  Money MOVE: {money_map['move']}")
    print(f"  No access control: {money_map['no_access']}")
    print(f"  → {len(f1)} findings")
    
    print("\nPhase 2: FIND THE LIES...")
    f2 = phase2_find_lies(all_contracts)
    all_findings.extend(f2)
    print(f"  → {len(f2)} findings")
    
    print("\nPhase 3: FOLLOW STALE STATE...")
    f3 = phase3_stale_state(all_contracts)
    all_findings.extend(f3)
    print(f"  → {len(f3)} findings")
    
    print("\nPhase 4: BREAK COMPOSITION...")
    f4 = phase4_composition(all_contracts)
    all_findings.extend(f4)
    print(f"  → {len(f4)} findings")
    
    print("\nPhase 5: THINK LIKE ATTACKER...")
    f5 = phase5_attacker(all_contracts)
    all_findings.extend(f5)
    print(f"  → {len(f5)} findings")
    
    print("\nPhase 6: PATTERN SCAN...")
    f6 = phase6_patterns(all_contracts)
    all_findings.extend(f6)
    print(f"  → {len(f6)} findings")
    
    print("\nPhase 7: CROSS-CONTRACT ANALYSIS...")
    f7 = phase7_cross_contract(all_contracts)
    all_findings.extend(f7)
    print(f"  → {len(f7)} findings")
    
    print("\nPhase 8: MULTI-TX ATTACKS...")
    f8 = phase8_multi_tx(all_contracts)
    all_findings.extend(f8)
    print(f"  → {len(f8)} findings")
    
    print("\nPhase 9: ORACLE MANIPULATION...")
    f9 = phase9_oracle(all_contracts)
    all_findings.extend(f9)
    print(f"  → {len(f9)} findings")
    
    print("\nPhase 10: GOVERNANCE & TIMELOCK...")
    f10 = phase10_governance(all_contracts)
    all_findings.extend(f10)
    print(f"  → {len(f10)} findings")
    
    print("\nPhase 11: ERC-4626 CHECKS...")
    f11 = phase11_erc4626(all_contracts)
    all_findings.extend(f11)
    print(f"  → {len(f11)} findings")
    
    print("\nPhase 12: PROXY & UPGRADE...")
    f12 = phase12_proxy(all_contracts)
    all_findings.extend(f12)
    print(f"  → {len(f12)} findings")
    
    print("\nPhase 13: CROSS-CHAIN BRIDGE...")
    f13 = phase13_cross_chain(all_contracts)
    all_findings.extend(f13)
    print(f"  → {len(f13)} findings")
    
    print("\nPhase 14: INTEREST RATE MODEL...")
    f14 = phase14_interest_model(all_contracts)
    all_findings.extend(f14)
    print(f"  → {len(f14)} findings")
    
    print("\nPhase 15: ROUNDING DIRECTION...")
    f15 = phase15_rounding(all_contracts)
    all_findings.extend(f15)
    print(f"  → {len(f15)} findings")
    
    print("\nPhase 16: SLITHER INTEGRATION...")
    f16 = phase16_slither_integration(all_contracts, slither_json)
    all_findings.extend(f16)
    print(f"  → {len(f16)} findings")
    
    # Sort by severity
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
    all_findings.sort(key=lambda h: (severity_order.get(h.severity, 5), -h.confidence))
    
    return all_findings

def print_report(findings: List[Hypothesis]):
    print()
    print("═" * 70)
    print("  MANUAL REVIEW ENGINE — FINDINGS REPORT")
    print("═" * 70)
    
    if not findings:
        print("\n  ✅ No findings. Protocol appears clean.")
        print("  ⚠️  This does NOT guarantee safety. Manual review is heuristic.")
        return
    
    # Summary
    by_severity = defaultdict(int)
    for f in findings:
        by_severity[f.severity] += 1
    
    print(f"\n  SUMMARY: ", end="")
    for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
        if by_severity[sev]:
            print(f"{by_severity[sev]} {sev} | ", end="")
    print(f"\n  Total: {len(findings)} hypotheses")
    print()
    
    # Detailed findings
    for i, f in enumerate(findings, 1):
        icon = {'CRITICAL': '🚨', 'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🔵', 'INFO': '⚪'}.get(f.severity, '❓')
        print(f"  {icon} [{f.severity}] H{i}: {f.title}")
        print(f"     Phase: {f.phase} | Confidence: {f.confidence:.0%}")
        print(f"     {f.description}")
        if f.evidence:
            print(f"     Evidence: {f.evidence}")
        if f.attack_steps:
            print(f"     Attack:")
            for line in f.attack_steps.split('\n'):
                print(f"       {line}")
        if f.profit_calc:
            print(f"     Profit: {f.profit_calc}")
        print()
    
    print("═" * 70)
    print("  ⚠️  These are HYPOTHESES, not confirmed bugs.")
    print("  Each requires manual verification + PoC before submission.")
    print("  False positive rate: ~60-80%. This is NORMAL.")
    print("  The tool finds CANDIDATES. Your brain confirms them.")
    print("═" * 70)

def save_json(findings: List[Hypothesis], path: str):
    data = []
    for f in findings:
        data.append({
            'title': f.title,
            'severity': f.severity,
            'phase': f.phase,
            'description': f.description,
            'evidence': f.evidence,
            'attack_steps': f.attack_steps,
            'profit_calc': f.profit_calc,
            'confidence': f.confidence,
        })
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n  JSON saved: {path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 manual_review.py <path_to_sol_or_dir> [--json output.json] [--slither slither.json]")
        sys.exit(1)
    
    path = sys.argv[1]
    json_path = None
    slither_path = None
    if '--json' in sys.argv:
        idx = sys.argv.index('--json')
        if idx + 1 < len(sys.argv):
            json_path = sys.argv[idx + 1]
    if '--slither' in sys.argv:
        idx = sys.argv.index('--slither')
        if idx + 1 < len(sys.argv):
            slither_path = sys.argv[idx + 1]
    
    findings = run_manual_review(path, slither_json=slither_path)
    print_report(findings)
    
    if json_path:
        save_json(findings, json_path)
