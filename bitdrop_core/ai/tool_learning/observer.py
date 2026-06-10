# syntheticmind/tools/tool_pattern_observer.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback
import re


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class ToolPattern3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TOOL PATTERN OBSERVER — MAX SIGNAL + 3D‑MAX
# ============================================================

class ToolPatternObserver:
    """
    Observes memory for repeated structured patterns that look like tool calls (3D‑MAX Edition).

    Detects:
        • function-like patterns: foo(x=1, y=2)
        • keyword-only patterns
        • positional patterns
        • mixed patterns
        • repeated patterns (frequency scoring)

    Returns structured envelopes for ToolLearningManager.
    """

    # ------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------
    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

        # Regex for function-like patterns
        self.pattern_re = re.compile(
            r"\b([A-Za-z_]\w*)\s*\(([^)]*)\)"
        )

        self._last_3d: Optional[ToolPattern3D] = None

    # ------------------------------------------------------------
    # MAIN SCAN ENTRYPOINT
    # ------------------------------------------------------------
    def scan(self, last_n: int = 100) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "patterns": [...],
                "frequency": {pattern: count},
                "error": None
            }
        """

        start = time.time()
        patterns: List[str] = []
        freq: Dict[str, int] = {}

        try:
            items = self.runtime.memory.last_n(last_n)

            for _, payload in items:
                if not isinstance(payload, str):
                    continue

                # Extract all function-like patterns
                matches = self.pattern_re.findall(payload)
                for name, args in matches:
                    raw = f"{name}({args})"
                    patterns.append(raw)
                    freq[raw] = freq.get(raw, 0) + 1

            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = ToolPattern3D(
                axis_x="scan",
                axis_y=[f"items:{len(items)}", f"patterns:{len(patterns)}"],
                axis_z={
                    "latency_ms": latency,
                    "unique_patterns": len(freq),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "patterns": patterns,
                "frequency": freq,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = ToolPattern3D(
                axis_x="scan",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "patterns": [],
                "frequency": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

