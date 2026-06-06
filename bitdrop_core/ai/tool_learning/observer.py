# syntheticmind/tools/tool_pattern_observer.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback
import re


class ToolPatternObserver:
    """
    Observes memory for repeated structured patterns that look like tool calls.

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

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "patterns": patterns,
                "frequency": freq,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "patterns": [],
                "frequency": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
