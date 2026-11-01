"""Custom Mythril detector: Checkpoint Reset on Deposit
Based on Synthetix StakingRewards pattern + Drill 10.
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


class CheckpointResetOnDeposit(DetectionModule):
    """Detects checkpoint resets that destroy accrued rewards."""

    name = "Checkpoint reset destroys accrued rewards"
    swc_id = "841"
    description = (
        "Detects deposit/stake functions that reset the user's reward "
        "checkpoint, destroying yield accrued on existing shares."
    )
    entry_point = EntryPoint.CALLBACK
    pre_hooks = ["SSTORE"]

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
            if not any(kw in func_lower for kw in ["deposit", "stake", "add", "supply", "enter"]):
                return []
            
            address = state.get_current_instruction()["address"]

            return [
                PotentialIssue(
                    contract=state.environment.active_account.contract_name,
                    function_name=func_name,
                    address=address,
                    swc_id=self.swc_id,
                    bytecode=state.environment.code.bytecode,
                    title="Checkpoint Reset on Deposit",
                    severity="Medium",
                    description_head="Deposit/stake function may reset reward checkpoint.",
                    description_tail=(
                        f"Function '{func_name}' writes to storage during deposit. "
                        "If it resets checkpoint[user] = globalAccumulator, existing shares "
                        "lose all accrued rewards. Fix: weighted average or per-batch tracking."
                    ),
                    constraints=[],
                    detector=self,
                )
            ]
        except UnsatError:
            return []


detector = CheckpointResetOnDeposit()
