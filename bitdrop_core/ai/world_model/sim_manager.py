# syntheticmind/worldmodel/world_model_simulation_manager.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback

from .simulator import WorldModelSimulator
from .propagator import WorldModelPropagator
from .dynamics import WorldModelDynamics


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class WMSim3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# WORLD MODEL SIMULATION MANAGER — MAX SIMULATION + 3D‑MAX
# ============================================================

class WorldModelSimulationManager:
    """
    High-level interface for world-model-based simulation (3D‑MAX Edition).

    Features:
        • structured envelopes
        • safe execution
        • latency measurement
        • unified simulation + dynamics output
        • future-proof for multi-step rollouts
        • 3D‑MAX telemetry
    """

    def __init__(self, manager: "WorldModelManager"):
        self.manager = manager
        self.simulator = WorldModelSimulator(manager)
        self.propagator = WorldModelPropagator(manager)
        self.dynamics = WorldModelDynamics()
        self._last_3d: Optional[WMSim3D] = None

    # ------------------------------------------------------------
    # SIMULATE CHANGES
    # ------------------------------------------------------------
    def simulate_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies a list of changes to the world model and evaluates
        the resulting state with WorldModelDynamics.
        """

        start = time.time()

        try:
            sim_state = self.simulator.apply_changes(changes)
            if not sim_state.get("ok", True):
                raise ValueError(sim_state.get("error", "simulation failed"))

            after_state = sim_state.get("after", {})
            dyn = self.dynamics.evaluate(after_state)

            latency = int((time.time() - start) * 1000)

            self._last_3d = WMSim3D(
                axis_x="simulate_changes",
                axis_y=[f"changes:{len(changes)}"],
                axis_z={
                    "latency_ms": latency,
                    "sim_ok": sim_state.get("ok", False),
                    "dyn_ok": dyn.get("ok", False),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "changes": changes,
                "simulation": sim_state,
                "dynamics": dyn,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WMSim3D(
                axis_x="simulate_changes",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "changes": changes,
                "simulation": {},
                "dynamics": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # SIMULATE PROPAGATION
    # ------------------------------------------------------------
    def simulate_propagation(self, root_entity: str) -> Dict[str, Any]:
        """
        Runs multi-hop propagation from a root entity and evaluates
        the current world-model state with WorldModelDynamics.
        """

        start = time.time()

        try:
            prop = self.propagator.propagate(root_entity)
            if not prop.get("ok", True):
                raise ValueError(prop.get("error", "propagation failed"))

            snapshot = self.manager.snapshot()
            dyn = self.dynamics.evaluate(snapshot)

            latency = int((time.time() - start) * 1000)

            self._last_3d = WMSim3D(
                axis_x="simulate_propagation",
                axis_y=[f"root:{root_entity}"],
                axis_z={
                    "latency_ms": latency,
                    "prop_ok": prop.get("ok", False),
                    "dyn_ok": dyn.get("ok", False),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "root": root_entity,
                "propagation": prop,
                "dynamics": dyn,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WMSim3D(
                axis_x="simulate_propagation",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "root": root_entity,
                "propagation": {},
                "dynamics": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

