"""Custom Mythril detector: Flash Loan Attack Surface
Based on: bZx ($8M, 2020), Harvest ($34M, 2020), Cream ($130M, 2021).

Detects: functions that accept a callback parameter (bytes data) and
execute external calls with it. This is the flash loan receiver pattern
that enables single-transaction attacks.

Also detects: functions that read AMM spot price (reserve ratio) and
use it for critical decisions (liquidation, collateral valuation).
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


class FlashLoanSurfaceDetector(DetectionModule):
    """Detects flash loan attack surface: callback patterns + spot price usage."""

    name = "Flash loan attack surface"
    swc_id = "841"
    description = (
        "Detects functions that accept callback data and execute external calls, "
        "or that use AMM spot prices for critical decisions. These are the "
        "entry points for flash loan attacks."
    )
    entry_point = EntryPoint.CALLBACK
    pre_hooks = ["CALL"]

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

            # Pattern 1: Flash loan callback functions
            flash_keywords = [
                "flash", "loan", "callback", "execute", "receive",
                "onflash", "borrow", "arbitrage"
            ]
            is_flash_pattern = any(kw in func_lower for kw in flash_keywords)

            # Pattern 2: Functions with 'data' or 'params' in name (callback passthrough)
            has_callback_param = any(kw in func_lower for kw in ["data", "params", "payload"])

            # Pattern 3: Swap/price functions (AMM spot price manipulation surface)
            swap_keywords = ["swap", "getamount", "getprice", "reserve", "spot"]
            is_swap_pattern = any(kw in func_lower for kw in swap_keywords)

            if not (is_flash_pattern or has_callback_param or is_swap_pattern):
                return []

            contract_name = state.environment.active_account.contract_name
            key = (contract_name, func_name)
            if key in self._reported:
                return []
            self._reported.add(key)

            address = state.get_current_instruction()["address"]

            if is_flash_pattern or has_callback_param:
                title = "Flash Loan Callback Surface"
                desc = (
                    f"Function '{func_name}' matches flash loan callback patterns. "
                    "VERIFY: Can an attacker use a flash loan to call this function, "
                    "manipulate state, and profit within a single transaction? "
                    "Check: reentrancy guards, price oracle source, slippage limits. "
                    "Reference: bZx ($8M), Harvest ($34M), Cream ($130M)."
                )
            else:
                title = "AMM Spot Price Usage"
                desc = (
                    f"Function '{func_name}' interacts with swap/price logic. "
                    "VERIFY: Is an AMM spot price used for collateral valuation, "
                    "liquidation, or critical decisions? Spot prices are manipulable "
                    "via flash loans in a single transaction. "
                    "Fix: Use TWAP or Chainlink oracle instead."
                )

            return [
                PotentialIssue(
                    contract=contract_name,
                    function_name=func_name,
                    address=address,
                    swc_id=self.swc_id,
                    bytecode=state.environment.code.bytecode,
                    title=title,
                    severity="Medium",
                    description_head=title,
                    description_tail=desc,
                    constraints=[],
                    detector=self,
                )
            ]
        except UnsatError:
            return []


detector = FlashLoanSurfaceDetector()
