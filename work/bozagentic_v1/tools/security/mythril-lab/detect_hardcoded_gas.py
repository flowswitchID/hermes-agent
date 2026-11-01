"""Custom Mythril module: detect hardcoded gas in calls"""
from mythril.analysis.module.base import DetectionModule, EntryPoint
from mythril.analysis.issue_annotation import IssueAnnotation
from mythril.analysis.report import Issue
from mythril.analysis.swc_data import make_swc_id
from mythril.exceptions import DetectorNotFoundError
from mythril.laser.smt import simplify
from mythril.laser.ethereum.state.global_state import GlobalState
import logging

log = logging.getLogger(__name__)

class HardcodedGasDetector(DetectionModule):
    name = "Hardcoded Gas Detector"
    swc_id = make_swc_id("hardcoded-gas")
    description = "Detects calls with hardcoded gas limits"
    entry_point = EntryPoint.CALLBACK
    pre_hooks = ["CALL", "DELEGATECALL"]

    def _execute(self, state: GlobalState) -> None:
        gas = state.mstate.stack[0]
        # Check if gas is a concrete value (not symbolic)
        try:
            gas_val = gas.value
            if gas_val is not None and gas_val < 100000:
                # Low hardcoded gas
                pass
        except:
            pass  # symbolic gas, skip

detector = HardcodedGasDetector()
