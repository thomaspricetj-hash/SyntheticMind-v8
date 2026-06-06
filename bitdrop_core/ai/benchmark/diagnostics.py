# bitdrop_core/ai/benchmark/diagnostics.py

from __future__ import annotations
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List


STAGE_KEYS = [
    "router",
    "model",
    "memory_read",
    "memory_write",
    "compression",
    "web_search",
    "post",
    "other",
]


@dataclass
class StageStats:
    name: str
    total_ms: float = 0.0
    calls: int = 0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.calls if self.calls else 0.0


class DiagnosticsContext:
    """
    Lightweight per-request diagnostics context.

    Usage inside runtime (optional but recommended):

        diag.start("router")
        ... router work ...
        diag.stop("router")

        diag.start("model")
        ... model work ...
        diag.stop("model")

    If the runtime doesn't use it yet, the smart benchmark still works
    with total-only timing.
    """

    def __init__(self, case_id: str, model_id: str):
        self.case_id = case_id
        self.model_id = model_id
        self._active: Dict[str, float] = {}
        self._stages: Dict[str, StageStats] = {
            k: StageStats(name=k) for k in STAGE_KEYS
        }
        self.total_ms: float = 0.0

    # ------------------------------------------------------------
    # Timing API
    # ------------------------------------------------------------
    def start(self, stage: str) -> None:
        now = time.time()
        self._active[stage] = now

    def stop(self, stage: str) -> None:
        now = time.time()
        start = self._active.pop(stage, None)
        if start is None:
            return
        elapsed = (now - start) * 1000.0
        stats = self._stages.get(stage)
        if stats is None:
            stats = StageStats(name=stage)
            self._stages[stage] = stats
        stats.total_ms += elapsed
        stats.calls += 1

    def record_external(self, stage: str, ms: float) -> None:
        stats = self._stages.get(stage)
        if stats is None:
            stats = StageStats(name=stage)
            self._stages[stage] = stats
        stats.total_ms += ms
        stats.calls += 1

    def finalize_total(self, total_ms: float) -> None:
        self.total_ms = total_ms

    # ------------------------------------------------------------
    # Export
    # ------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "model_id": self.model_id,
            "total_ms": self.total_ms,
            "stages": {
                name: {
                    "total_ms": s.total_ms,
                    "calls": s.calls,
                    "avg_ms": s.avg_ms,
                }
                for name, s in self._stages.items()
                if s.calls > 0 or s.total_ms > 0.0
            },
        }


class SlowdownAdvisor:
    """
    Analyzes per-stage timings and suggests concrete fixes.
    """

    def analyze(self, diag: DiagnosticsContext) -> Dict[str, Any]:
        data = diag.to_dict()
        stages = data.get("stages", {})
        total = data.get("total_ms", 0.0)

        if not stages or total <= 0.0:
            return {
                "bottleneck_stage": None,
                "bottleneck_ms": 0.0,
                "bottleneck_ratio": 0.0,
                "advice": [
                    "No per-stage data available. Consider wiring DiagnosticsContext into your runtime stages."
                ],
            }

        # Find dominant stage
        max_stage = None
        max_ms = 0.0
        for name, s in stages.items():
            t = s.get("total_ms", 0.0)
            if t > max_ms:
                max_ms = t
                max_stage = name

        ratio = max_ms / total if total > 0 else 0.0
        advice = self._advice_for_stage(max_stage, max_ms, ratio)

        return {
            "bottleneck_stage": max_stage,
            "bottleneck_ms": max_ms,
            "bottleneck_ratio": ratio,
            "advice": advice,
        }

    # ------------------------------------------------------------
    # Heuristic advice per stage
    # ------------------------------------------------------------
    def _advice_for_stage(self, stage: Optional[str], ms: float, ratio: float) -> List[str]:
        if stage is None:
            return ["No clear bottleneck detected."]

        r_pct = int(ratio * 100)

        if stage == "model":
            return [
                f"Model execution dominates latency (~{r_pct}% of total).",
                "Consider using a smaller or faster model for this intent (e.g., qwen2.5:7b instead of a larger one).",
                "Enable GPU acceleration and KV-cache if not already.",
                "Reduce max tokens / temperature for simple queries.",
            ]

        if stage == "router":
            return [
                f"Routing logic is a noticeable cost (~{r_pct}% of total).",
                "Simplify routing rules or cache routing decisions for repeated patterns.",
                "Avoid heavy analysis (e.g., large regex or embeddings) in the hot path.",
            ]

        if stage == "memory_read":
            return [
                f"Memory reads are a bottleneck (~{r_pct}% of total).",
                "Enable in-memory caching for recent episodes.",
                "Batch memory lookups instead of multiple small reads.",
                "Check disk / NVMe performance and OS caching.",
            ]

        if stage == "memory_write":
            return [
                f"Memory writes are a bottleneck (~{r_pct}% of total).",
                "Defer non-critical writes to a background worker.",
                "Batch writes instead of writing per-token or per-step.",
                "Reduce verbosity of what gets stored (only store distilled summaries).",
            ]

        if stage == "compression":
            return [
                f"Compression kernel is dominating (~{r_pct}% of total).",
                "Switch to 'warm' compression mode for short-lived data.",
                "Reduce number of compression passes for small payloads.",
                "Profile specific collapse rules that may be too expensive.",
            ]

        if stage == "web_search":
            return [
                f"Web search is the main slowdown (~{r_pct}% of total).",
                "Enable result caching for repeated queries.",
                "Reduce number of search calls per request.",
                "Use shorter snippets or fewer sources when possible.",
            ]

        if stage == "post":
            return [
                f"Post-processing is significant (~{r_pct}% of total).",
                "Simplify formatting / cleanup logic.",
                "Avoid heavy regex or large JSON transformations in the hot path.",
            ]

        return [
            f"Stage '{stage}' is the main bottleneck (~{r_pct}% of total).",
            "Profile this stage in more detail and consider caching, batching, or simplifying its logic.",
        ]
