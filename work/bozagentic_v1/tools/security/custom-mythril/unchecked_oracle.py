"""Custom Mythril detector: Unchecked Oracle Deviation v5
Based on Ostium hack (July 2026, $18M) pattern.

v5: Hook on function ENTRY (CALL) instead of SSTORE.
This catches functions behind require() that block SSTORE hooks.
Uses POST entry point to analyze the full statespace after execution.
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


class UncheckedOracleDeviation(DetectionModule):
    """Detects oracle price updates that may lack deviation bounds.
    
    Hooks on CALL (function entry) to catch functions that have
    require() guards blocking SSTORE-level hooks.
    """

    name = "Oracle update without deviation check"
    swc_id = "841"
    description = (
        "Detects price oracle updates that may not validate the deviation "
        "from the previous price. Ostium hack pattern ($18M, July 2026)."
    )
    entry_point = EntryPoint.CALLBACK
    pre_hooks = ["CALL", "SSTORE"]
    
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
            
            func_lower = func_name.lower()
            oracle_keywords = [
                "price", "oracle", "update", "push", "set",
                "report", "feed", "rate", "upkeep"
            ]
            
            if not any(kw in func_lower for kw in oracle_keywords):
                return []
            
            # Deduplicate
            contract_name = state.environment.active_account.contract_name
            key = (contract_name, func_name)
            if key in self._reported:
                return []
            self._reported.add(key)
            
            address = state.get_current_instruction()["address"]

            return [
                PotentialIssue(
                    contract=contract_name,
                    function_name=func_name,
                    address=address,
                    swc_id=self.swc_id,
                    bytecode=state.environment.code.bytecode,
                    title="Potential Unchecked Oracle Price Deviation",
                    severity="High",
                    description_head="Oracle price update may lack deviation validation.",
                    description_tail=(
                        f"Function '{func_name}' has oracle/price semantics. "
                        "VERIFY: does it check |newPrice - oldPrice| / oldPrice "
                        "< maxDeviation? Does it validate timestamp <= block.timestamp? "
                        "If not, an attacker who compromises the oracle key can set an "
                        "arbitrary price. Reference: Ostium hack (July 2026, $18M)."
                    ),
                    constraints=[],
                    detector=self,
                )
            ]
        except UnsatError:
            return []


detector = UncheckedOracleDeviation()
