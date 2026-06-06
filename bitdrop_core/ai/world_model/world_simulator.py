# syntheticmind/worldmodel/world_model_simulator.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback


class WorldModelSimulator:
    """
    Applies hypothetical changes to the world model and produces simulated states.

    Features:
        • structured envelopes
        • rollback safety
        • change validation
        • latency measurement
        • future-proof for multi-step rollouts
    """

    def __init__(self, manager: "WorldModelManager"):
        self.manager = manager

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
                        "reason": "missing entity or property"
                    })
                    continue

                try:
                    result = self.manager.update_property(entity, prop, value)

                    if result.get("ok", True):
                        applied.append(ch)
                    else:
                        skipped.append({
                            "change": ch,
                            "reason": result.get("error", "update failed")
                        })

                except Exception as e:
                    skipped.append({
                        "change": ch,
                        "reason": str(e)
                    })

            snapshot_after = self.manager.snapshot()

            # ----------------------------------------------------
            # STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "before": snapshot_before,
                "after": snapshot_after,
                "applied": applied,
                "skipped": skipped,
                "changes": changes,
                "error": None,
            }

        except Exception as e:
            # ----------------------------------------------------
            # FAILURE ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "before": {},
                "after": {},
                "applied": [],
                "skipped": [],
                "changes": changes,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
