# syntheticmind/tools/tool_signature_inferer.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import re
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class ToolSig3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TOOL SIGNATURE INFERER — MAX SIGNAL + 3D‑MAX
# ============================================================

class ToolSignatureInferer:
    """
    Infers tool signatures from repeated call patterns (3D‑MAX Edition).

    Supports:
        • keyword arguments
        • positional arguments
        • whitespace tolerance
        • malformed pattern safety
        • structured envelopes
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self._last_3d: Optional[ToolSig3D] = None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def infer(self, patterns: List[str]) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "signatures": [...],
                "error": None
            }
        """

        signatures = []
        start_count = len(patterns)

        try:
            for p in patterns:
                sig = self._infer_single(p)
                if sig:
                    signatures.append(sig)

            self._last_3d = ToolSig3D(
                axis_x="infer",
                axis_y=[f"patterns:{start_count}"],
                axis_z={
                    "ok": True,
                    "signatures": len(signatures),
                },
            )

            return {
                "ok": True,
                "signatures": signatures,
                "error": None,
            }

        except Exception as e:
            self._last_3d = ToolSig3D(
                axis_x="infer",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )

            return {
                "ok": False,
                "signatures": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # INTERNAL: PARSE A SINGLE PATTERN
    # ------------------------------------------------------------
    def _infer_single(self, pattern: str) -> Dict[str, Any] | None:
        """
        Extracts:
            • name
            • params (keyword + positional)
        """

        try:
            match = re.match(r"\s*([A-Za-z_]\w*)\s*\((.*)\)\s*", pattern)
            if not match:
                self._last_3d = ToolSig3D(
                    axis_x="_infer_single",
                    axis_y=["no_match"],
                    axis_z={"pattern": pattern},
                )
                return None

            name = match.group(1)
            raw_params = match.group(2).strip()

            if not raw_params:
                params = []
            else:
                params = []
                parts = [p.strip() for p in raw_params.split(",") if p.strip()]

                for part in parts:
                    if "=" in part:
                        key = part.split("=", 1)[0].strip()
                        if key:
                            params.append(key)
                    else:
                        cleaned = re.sub(r"[^A-Za-z0-9_]", "", part)
                        if cleaned:
                            params.append(cleaned)

            self._last_3d = ToolSig3D(
                axis_x="_infer_single",
                axis_y=[f"name:{name}", f"params:{len(params)}"],
                axis_z={"ok": True},
            )

            return {
                "name": name,
                "params": params,
            }

        except Exception as e:
            self._last_3d = ToolSig3D(
                axis_x="_infer_single",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )
            return None

