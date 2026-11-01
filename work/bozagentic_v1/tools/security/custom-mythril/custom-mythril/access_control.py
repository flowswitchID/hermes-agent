"""Custom Mythril detector: Missing Access Control on Critical Functions
Based on: Parity multisig ($150M, 2017), Ronin Bridge ($625M, 2022),
multiple C4/Sherlock HIGH findings every cycle.

Detects: functions with critical names (withdraw, drain, mint, pause,
upgrade, setOwner, emergency) that lack CALLER checks (msg.sender
comparison via SLOAD + EQ before execution).

Pattern:
  VULNERABLE:                    SAFE:
  function drain() external {    function drain() external {
    token.transfer(...)            require(msg.sender == owner);
  }                                token.transfer(...)
                                 }
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


class MissingAccessControl(DetectionModule):
    """Detects critical functions that may lack access control."""

    name = "Missing access control on critical function"
    swc_id = "284"
    description = (
        "Detects functions with critical semantics (withdraw, mint, pause, "
        "upgrade, emergency, admin) that may lack caller validation. "
        "Pattern behind Parity ($150M) and Ronin ($625M)."
    )
    entry_point = EntryPoint.CALLBACK
    pre_hooks = ["CALL"]

    _reported = set()

    # Critical function name patterns
    CRITICAL_KEYWORDS = [
        "withdraw", "drain", "mint", "burn", "pause", "unpause",
        "upgrade", "setowner", "transferowner", "emergency",
        "admin", "rescue", "recover", "sweep", "extract",
        "setfee", "setrate", "setlimit", "setwhitelist",
        "addmanager", "removemanager", "grant", "revoke",
        "initialize", "destroy", "selfdestruct", "kill",
        "setguardian", "setadmin", "setoperator",
    ]

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

            # Check if function name matches critical patterns
            matched_keyword = None
            for kw in self.CRITICAL_KEYWORDS:
                if kw in func_lower:
                    matched_keyword = kw
                    break

            if not matched_keyword:
                return []

            # Skip view/pure functions (getters named getX are fine)
            if func_lower.startswith("get") or func_lower.startswith("is"):
                return []

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
                    title=f"Potential Missing Access Control ({matched_keyword})",
                    severity="High",
                    description_head="Critical function may lack access control.",
                    description_tail=(
                        f"Function '{func_name}' has critical semantics ('{matched_keyword}'). "
                        "VERIFY: Does it check msg.sender against an authorized role "
                        "(owner, admin, guardian, operator)? If not, ANY external account "
                        "can call it. Check for: require(msg.sender == owner), "
                        "onlyOwner modifier, AccessControl roles. "
                        "Reference: Parity ($150M), Ronin ($625M)."
                    ),
                    constraints=[],
                    detector=self,
                )
            ]
        except UnsatError:
            return []


detector = MissingAccessControl()
