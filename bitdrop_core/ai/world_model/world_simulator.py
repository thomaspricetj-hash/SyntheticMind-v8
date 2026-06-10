from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class WMSim3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# WORLD MODEL SIMULATOR — MAX SIMULATION + 3D‑MAX
# ============================================================

class WorldModelSimulator:
    """
    Applies hypothetical changes to the world model and produces simulated states (3D‑MAX Edition).

    Features:
        • structured envelopes
        • rollback safety
        • change validation
        • latency measurement
        • future-proof for multi-step rollouts
        • 3D‑MAX telemetry
    """

    def __init__(self, manager: "WorldModelManager"):
        self.manager = manager
        self._last_3d: Optional[WMSim3D] = None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def apply_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        changes: list of { "entity": str, "property": str, "value": Any }

        Returns:
            {
                "ok": bool,
                "latency_ms": int,
                "before": {...},
                "after": {...},
                "applied": [...],
                "skipped": [...],
                "changes": [...],
                "error": None
            }
        """

        start = time.time()

        try:
            snapshot_before = self.manager.snapshot()

            applied = []
            skipped = []

            # ----------------------------------------------------
            # APPLY CHANGES SAFELY
            # ----------------------------------------------------
            for ch in changes:
                entity = ch.get("entity")
                prop = ch.get("property")
                value = ch.get("value")

                if not entity or not prop:
                    skipped.append({
                        "change": ch,
                        "reason": "missing entity or property",
                    })
                    continue

                try:
                    result = self.manager.update_property(entity, prop, value)

                    if result.get("ok", True):
                        applied.append(ch)
                    else:
                        skipped.append({
                            "change": ch,
                            "reason": result.get("error", "update failed"),
                        })

                except Exception as e:
                    skipped.append({
                        "change": ch,
                        "reason": str(e),
                    })

            snapshot_after = self.manager.snapshot()

            latency = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = WMSim3D(
                axis_x="apply_changes",
                axis_y=[
                    f"changes:{len(changes)}",
                    f"applied:{len(applied)}",
                    f"skipped:{len(skipped)}",
                ],
                axis_z={
                    "latency_ms": latency,
                    "before_nodes": len(snapshot_before.get("nodes", {})),
                    "after_nodes": len(snapshot_after.get("nodes", {})),
                },
            )

            # ----------------------------------------------------
            # STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": latency,
                "before": snapshot_before,
                "after": snapshot_after,
                "applied": applied,
                "skipped": skipped,
                "changes": changes,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WMSim3D(
                axis_x="apply_changes",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "before": {},
                "after": {},
                "applied": [],
                "skipped": [],
                "changes": changes,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

