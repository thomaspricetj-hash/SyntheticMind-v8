from __future__ import annotations
import time
import traceback
import re
from typing import Any, Dict, List

from .context.packet import Packet

# Multi‑model chapters
from .chapters.reason_talk import ReasonTalk
from .chapters.reason_small import ReasonSmall
from .chapters.reason_general import ReasonGeneral
from .chapters.reason_large import ReasonLarge
from .chapters.reason_code import ReasonCode
from .chapters.reason_math import ReasonMath
from .chapters.reason_vision import ReasonVision
from .chapters.embedder import Embedder

# Summarization model + helper
from bitdrop_core.ai.models.summarizer_model import SummarizerModelV1
from bitdrop_core.ai.metamodel.helpers.summarization_helper import SummarizationHelperV1

# Thinking engine + helpers (MAX‑3D)
from bitdrop_core.ai.metamodel.thinking_engine import ThinkingEngine
from bitdrop_core.ai.metamodel.helpers.physics_helper import PhysicsHelper3D
from bitdrop_core.ai.metamodel.helpers.math_helper import MathHelper3D
from bitdrop_core.ai.metamodel.helpers.logic_helper import LogicHelper3D
from bitdrop_core.ai.metamodel.helpers.code_helper import CodeHelper
from bitdrop_core.ai.metamodel.helpers.reasoning_helper import ReasoningHelperV2


# ============================================================
# Introspection Helper
# ============================================================
class IntrospectionHelper:
    def analyze(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        keywords = [
            "pipeline", "review your pipeline", "look at your pipeline",
            "self audit", "self-audit", "audit yourself", "introspection",
            "look at your code", "analyze your code",
        ]
        return {"detected": any(k in t for k in keywords)}


# ============================================================
# Self‑Audit Chapter
# ============================================================
class SelfAuditChapter:
    def __init__(self, runtime):
        self.runtime = runtime

    def run(self, packet: Packet):
        try:
            report = self.runtime.audit(mode="full")
            files = report.get("files", [])
            summary = report.get("summary", {})

            candidates = []
            for f in files:
                slow = f.get("slow_patterns", [])
                orch = f.get("orchestrator_hints", [])
                cyclo = f.get("cyclomatic_complexity", 0)
                cog = f.get("cognitive_complexity", 0)
                dead = f.get("dead_code", [])

                if slow or orch or dead or cyclo > 40 or cog > 80:
                    severity = (
                        len(slow) * 3 +
                        len(orch) * 2 +
                        len(dead) +
                        (1 if cyclo > 40 else 0) +
                        (1 if cog > 80 else 0)
                    )
                    candidates.append({
                        "path": f.get("path", ""),
                        "slow_patterns": slow,
                        "orchestrator_hints": orch,
                        "cyclomatic_complexity": cyclo,
                        "cognitive_complexity": cog,
                        "dead_code": dead,
                        "severity": severity,
                    })

            candidates.sort(key=lambda x: x["severity"], reverse=True)

            lines = ["Pipeline review — key places to improve:\n"]

            if candidates:
                for c in candidates[:5]:
                    lines.append(f"- {c['path']}")
                    if c["slow_patterns"]:
                        lines.append("  Slow patterns: " + "; ".join(c["slow_patterns"]))
                    if c["orchestrator_hints"]:
                        lines.append("  Orchestrator hints: " + "; ".join(c["orchestrator_hints"]))
                    if c["dead_code"]:
                        lines.append("  Dead/incomplete code present.")
                    if c["cyclomatic_complexity"] > 40 or c["cognitive_complexity"] > 80:
                        lines.append("  High complexity — refactor.")
                    lines.append("")
            else:
                lines.append("No strong slow patterns or bottlenecks detected.\n")

            lines.append("Global summary:")
            lines.append(f"  Total files: {summary.get('total_files', 0)}")
            lines.append(f"  Files with slow patterns: {summary.get('files_with_slow_patterns', 0)}")
            lines.append(f"  Files with orchestrator hints: {summary.get('files_with_orchestrator_hints', 0)}")
            lines.append(f"  High‑complexity files: {summary.get('high_complexity_files', 0)}")
            lines.append(f"  Dependency cycles: {summary.get('dependency_cycles', 0)}")
            lines.append(f"  Duplicate file groups: {summary.get('duplicate_file_groups', 0)}")

            return {"output": "\n".join(lines)}

        except Exception as e:
            return {"output": f"Self‑audit failed: {e}"}


# ============================================================
# Router v7 — 3D‑MAX, benchmark‑aware, hardened
# ============================================================
class Router:
    META_TAIL_RE = re.compile(
        r'\s*end=false\s*,\s*se=\d+(\.\d+)?\s*next_question_id="QA-[^"]+"\s*$',
        re.IGNORECASE
    )

    MATH_RE = re.compile(r"^[0-9\+\-\*/x\^=\(\)\s\.]+$")

    def __init__(self, runtime=None) -> None:
        self.runtime = runtime
       
        # DEBUG: confirm which router file is actually being loaded
        print(">>> USING ROUTER FILE:", __file__)
        
        self.summary_helper = SummarizationHelperV1()
        self.introspection_helper = IntrospectionHelper()

        self.summary_model = SummarizerModelV1(model=ReasonSmall())

        # MAX‑3D helpers
        self.physics_helper_3d = PhysicsHelper3D()
        self.math_helper_3d = MathHelper3D()
        self.logic_helper_3d = LogicHelper3D()
        self.code_helper = CodeHelper()

        # ⭐ Correct wiring: ReasoningHelperV2 uses runtime.local_reasoner
        self.reasoning_helper_v2 = ReasoningHelperV2(self.runtime.local_reasoner)

        # Attach thinking engine
        if getattr(self.runtime, "thinking_engine", None) is None:
            self.runtime.thinking_engine = ThinkingEngine(
                runtime=self.runtime,
                physics_helper=self.physics_helper_3d,
                math_helper=self.math_helper_3d,
                logic_helper=self.logic_helper_3d,
                code_helper=self.code_helper,
                reasoning_helper=self.reasoning_helper_v2,
            )

        self.chapters: Dict[str, Any] = {
            "talk": ReasonTalk(),
            "small_reasoning": ReasonTalk(),
            "light_reasoning": ReasonSmall(),
            "general_reasoning": ReasonGeneral(),
            "large_reasoning": ReasonLarge(),
            "deep_reasoning": ReasonLarge(),
            "code_reasoning": ReasonCode(),
            "math_reasoning": ReasonMath(),
            "vision_reasoning": ReasonVision(),
            "embed": Embedder(),
            "summary_reasoning": self.summary_model,
            "self_audit": SelfAuditChapter(runtime),
        }

    # --------------------------------------------------------
    def _extract_clean_text(self, result: Any) -> str:
        if isinstance(result, str):
            return self.META_TAIL_RE.sub("", result).strip()

        if isinstance(result, dict) and "output" in result:
            return self._extract_clean_text(result["output"])

        return self.META_TAIL_RE.sub("", str(result)).strip()

    # --------------------------------------------------------
    def _detect_physics_deep(self, text: str) -> bool:
        print(">>> PHYSICS CHECK:", text)
        t = text.lower()
        keywords = [
            "photon rocket", "relativistic rocket", "lorentz", "gamma",
            "c^2", "rest mass energy", "energy–momentum", "energy-momentum",
            "schwarzschild", "kerr", "ergosphere", "event horizon",
            "geodesic", "null geodesic", "timelike", "spacelike",
            "general relativity", "special relativity",
        ]
        flag = any(k in t for k in keywords)
        print(">>> PHYSICS DETECTED:", flag)
        return flag

    # --------------------------------------------------------
    def _run_single(self, packet: Packet) -> Dict[str, Any]:
        start = time.time()

        try:
            text = (
                (getattr(packet, "query", None) or getattr(packet, "text", "") or "")
            ).strip()
            print(">>> ROUTER RECEIVED TEXT:", repr(text))

            intent = (getattr(packet, "intent", None) or "talk").strip()
            helpers = getattr(packet, "helpers", None) or {}

            # Math override
            if text and self.MATH_RE.match(text):
                chapter = self.chapters["math_reasoning"]
                result = chapter.run(packet)
                return {
                    "ok": True,
                    "intent": "math_reasoning",
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": self._extract_clean_text(result),
                }

            summary_info = self.summary_helper.analyze(text) if text else {"detected": False}
            helpers["summary"] = summary_info

            introspection_info = self.introspection_helper.analyze(text)
            helpers["introspection"] = introspection_info

            # Deep physics override
            if self._detect_physics_deep(text) or intent in ("deep_physics", "deep_thinking"):
                te_out = self.runtime.thinking_engine.think(
                    text,
                    intent="deep_physics",
                    metadata={"lang_info": {}, "memory_info": {}},
                    use_cache=False,
                )
                return {
                    "ok": True,
                    "intent": "deep_physics",
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": te_out["final"],
                    "tensor": te_out.get("tensor"),
                    "tensor_shape": te_out.get("tensor_shape"),
                }

            # Summary intent
            if intent in ("summary", "summarize", "summary_reasoning"):
                out = self.summary_model.summarize(
                    text,
                    sentences=summary_info.get("sentences"),
                    words=summary_info.get("words"),
                    percent=summary_info.get("percent"),
                    length_hint=summary_info.get("length_hint"),
                )
                return {
                    "ok": True,
                    "intent": "summary_reasoning",
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": out,
                }

            # Self‑audit
            if intent == "self_audit" or introspection_info.get("detected"):
                chapter = self.chapters["self_audit"]
                result = chapter.run(packet)
                return {
                    "ok": True,
                    "intent": "self_audit",
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": result["output"],
                }

            # Implicit summary
            if summary_info.get("detected"):
                out = self.summary_model.summarize(
                    text,
                    sentences=summary_info.get("sentences"),
                    words=summary_info.get("words"),
                    percent=summary_info.get("percent"),
                    length_hint=summary_info.get("length_hint"),
                )
                return {
                    "ok": True,
                    "intent": "summary_reasoning",
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": out,
                }

            # Normal routing
            route_key = self._select_route(intent, text, packet, helpers)
            if route_key not in self.chapters:
                route_key = "talk"

            chapter = self.chapters[route_key]
            result = chapter.run(packet)

            if isinstance(result, dict) and result.get("escalate"):
                result = self.chapters["deep_reasoning"].run(packet)
                route_key = "deep_reasoning"

            return {
                "ok": True,
                "intent": route_key,
                "latency_ms": int((time.time() - start) * 1000),
                "output": self._extract_clean_text(result)
                if intent in ("conversation", "small_reasoning", "talk")
                else result,
            }

        except Exception:
            return {
                "ok": False,
                "intent": getattr(packet, "intent", None),
                "error": "Router crashed",
                "traceback": traceback.format_exc(),
                "latency_ms": int((time.time() - start) * 1000),
                "output": "Router encountered an internal error.",
            }

    # --------------------------------------------------------
    def run(self, packet: Packet) -> Dict[str, Any]:
        return self._run_single(packet)

    def run_batch(self, packets: List[Packet]) -> List[Dict[str, Any]]:
        return [self._run_single(p) for p in packets]

    def run_3d(self, packets_3d: List[List[List[Packet]]]) -> List[List[List[Dict[str, Any]]]]:
        depth = len(packets_3d)
        if depth == 0:
            return []

        out: List[List[List[Dict[str, Any]]]] = []
        for plane in packets_3d:
            plane_out = []
            for row in plane:
                row_out = [self._run_single(pkt) for pkt in row]
                plane_out.append(row_out)
            out.append(plane_out)
        return out

    # --------------------------------------------------------
    def _select_route(self, intent: str, text: str, packet: Packet, helpers: Dict[str, Any]) -> str:
        bench = getattr(packet, "metadata", {}).get("benchmark")

        if bench:
            if bench in ("gsm8k", "math"):
                return "math_reasoning"
            if bench in ("humaneval", "mbpp", "evalplus"):
                return "code_reasoning"
            if bench in ("mmlu", "arc_challenge", "hellaswag", "bigbench_hard", "gpqa"):
                return "large_reasoning"
            if bench in ("naturalquestions", "triviaqa", "squad", "winogrande"):
                return "general_reasoning"
            if bench in ("truthfulqa", "safetybench", "advbench"):
                return "large_reasoning"
            if bench in ("ruler", "longbench", "needle", "infinitebench"):
                return "large_reasoning"

        if intent in self.chapters:
            return intent
        if intent in ("embed", "embedding", "vectorize"):
            return "embed"
        if getattr(packet, "data", None) is not None:
            return "vision_reasoning"
        if helpers.get("introspection", {}).get("detected"):
            return "self_audit"
        if helpers.get("summary", {}).get("detected"):
            return "summary_reasoning"
        if helpers.get("code", {}).get("detected"):
            return "code_reasoning"
        if helpers.get("math", {}).get("detected"):
            return "math_reasoning"
        if helpers.get("physics", {}).get("detected"):
            return "large_reasoning"
        if helpers.get("logic", {}).get("detected"):
            return "general_reasoning"
        if helpers.get("web", {}).get("detected"):
            return "general_reasoning"
        if helpers.get("world", {}).get("entities"):
            return "general_reasoning"

        L = len(text)
        if L <= 200:
            return "talk"
        if L <= 800:
            return "general_reasoning"
        return "deep_reasoning"


