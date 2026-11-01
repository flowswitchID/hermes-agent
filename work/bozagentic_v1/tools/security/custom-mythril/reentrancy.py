"""Custom Mythril detector: Reentrancy via External Call Before State Update
Based on: The DAO ($60M, 2016), Uniswap/LendfMe ($25M, 2020), multiple C4 findings.

Detects: external CALL followed by SSTORE in the same function.
If state is updated AFTER the external call, attacker can re-enter
before the state reflects the first call.

Pattern:
  VULNERABLE:                    SAFE (CEI):
  call(target, data)             state[user] -= amount
  state[user] -= amount          call(target, data)
"""
import logging
from typing import List

from mythril.analysis.potential_issues import (
    get_potential_issues_annotation,
    PotentialIssue,
)
from mythril.analysis.module.base import DetectionModule, EntryPoint
from mythril.exceptions import UnsatError
from mythril.laser.ethereum.state.global_state import GlobalState

log = logging.getLogger(__name__)


class ReentrancyDetector(DetectionModule):
    """Detects state changes after external calls (reentrancy risk)."""

    name = "State change after external call (reentrancy)"
    swc_id = "107"
    description = (
        "Detects SSTORE operations that occur after a CALL/DELEGATECALL "
        "in the same function. This is the classic reentrancy pattern "
        "behind The DAO hack ($60M, 2016)."
    )
    entry_point = EntryPoint.CALLBACK
    pre_hooks = ["SSTORE"]

    _reported = set()

    def _execute(self, state: GlobalState) -> None:
        potential_issues = self._analyze_state(state)
        annotation = get_potential_issues_annotation(state)
        annotation.potential_issues.extend(potential_issues)

    def _analyze_state(self, state: GlobalState) -> List[PotentialIssue]:
        try:
            func_name = state.environment.active_function_name
            if not func_name:
                return []

            contract_name = state.environment.active_account.contract_name
            key = (contract_name, func_name)
            if key in self._reported:
                return []

            instructions = state.environment.code.instruction_list
            current_addr = state.get_current_instruction()["address"]

            # Find current SSTORE index
            sstore_idx = None
            for i, instr in enumerate(instructions):
                if instr["address"] == current_addr and instr["opcode"] == "SSTORE":
                    sstore_idx = i
                    break

            if sstore_idx is None:
                return []

            # Walk backwards: is there a CALL/DELEGATECALL/STATICCALL before this SSTORE?
            has_external_call_before = False
            call_opcode = None
            for i in range(sstore_idx - 1, -1, -1):
                op = instructions[i]["opcode"]
                if op in ("CALL", "DELEGATECALL", "CALLCODE"):
                    has_external_call_before = True
                    call_opcode = op
                    break
                # Stop at function boundary (JUMPDEST after JUMP)
                if op == "JUMPDEST" and i > 0 and instructions[i-1]["opcode"] == "JUMP":
                    break

            if not has_external_call_before:
                return []

            self._reported.add(key)
            address = current_addr

            return [
                PotentialIssue(
                    contract=contract_name,
                    function_name=func_name,
                    address=address,
                    swc_id=self.swc_id,
                    bytecode=state.environment.code.bytecode,
                    title="Reentrancy: State Change After External Call",
                    severity="High",
                    description_head="State is modified after an external call.",
                    description_tail=(
                        f"Function '{func_name}' performs SSTORE after {call_opcode}. "
                        "An attacker can re-enter via the external call's fallback/receive "
                        "before state is updated. Fix: follow Checks-Effects-Interactions "
                        "(CEI) pattern — update state BEFORE external calls. "
                        "Reference: The DAO ($60M, 2016), Uniswap/LendfMe ($25M, 2020)."
                    ),
                    constraints=[],
                    detector=self,
                )
            ]
        except UnsatError:
            return []


detector = ReentrancyDetector()
