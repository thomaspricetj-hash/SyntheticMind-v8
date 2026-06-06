import time
import traceback
from typing import Any, Dict

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



# ============================================================
# NEW: Introspection Helper
# ============================================================
class IntrospectionHelper:
    def analyze(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        keywords = [
            "speed", "faster", "optimize", "slow", "latency",
            "performance", "bottleneck", "improve", "audit",
            "look at your code", "analyze your code",
            "how to make you faster", "why are you slow",
            "self audit", "self-audit", "introspection"
        ]
        return {"detected": any(k in t for k in keywords)}


# ============================================================
# NEW: Self‑Audit Chapter
# ============================================================
class SelfAuditChapter:
    def __init__(self, runtime):
        self.runtime = runtime

    def run(self, packet: Packet):
        try:
            report = self.runtime.audit(mode="full")
            return {"output": report}
        except Exception as e:
            return {"output": f"Self‑audit failed: {e}"}


class Router:
    """
    Router v6 — summarization‑aware, helper‑aware, introspection‑aware,
    multi‑model routing with explicit summary/embed/self‑audit support.
    """

    def __init__(self, runtime=None) -> None:
        self.runtime = runtime

        # Helpers
        self.summary_helper = SummarizationHelperV1()
        self.introspection_helper = IntrospectionHelper()

        # Summarization model
        self.summary_model = SummarizerModelV1(
            model=ReasonSmall()
        )

        # Chapters
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

    def run(self, packet: Packet) -> Dict[str, Any]:
        start = time.time()

        try:
            text = (
                (getattr(packet, "query", None) or getattr(packet, "text", "") or "")
            ).strip()
            intent = (getattr(packet, "intent", None) or "talk").strip()
            helpers = getattr(packet, "helpers", None) or {}

            summary_info = self.summary_helper.analyze(text) if text else {"detected": False}
            helpers["summary"] = summary_info

            introspection_info = self.introspection_helper.analyze(text)
            helpers["introspection"] = introspection_info

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

            if intent == "self_audit":
                chapter = self.chapters["self_audit"]
                result = chapter.run(packet)
                return {
                    "ok": True,
                    "intent": "self_audit",
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": result["output"],
                }

            if introspection_info.get("detected"):
                chapter = self.chapters["self_audit"]
                result = chapter.run(packet)
                return {
                    "ok": True,
                    "intent": "self_audit",
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": result["output"],
                }

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

            route_key = self._select_route(intent, text, packet, helpers)
            if route_key not in self.chapters:
                route_key = "talk"

            chapter = self.chapters[route_key]
            result = chapter.run(packet)

            if isinstance(result, dict) and result.get("escalate"):
                result = self.chapters["deep_reasoning"].run(packet)
                route_key = "deep_reasoning"

            latency_ms = int((time.time() - start) * 1000)

            if intent in ("conversation", "small_reasoning", "talk"):
                return {
                    "ok": True,
                    "intent": route_key,
                    "latency_ms": latency_ms,
                    "output": self._extract_clean_text(result),
                }

            return {
                "ok": True,
                "intent": route_key,
                "latency_ms": latency_ms,
                "output": result,
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

    def _extract_clean_text(self, result: Any) -> str:
        if isinstance(result, str):
            return result.strip()
        if isinstance(result, dict) and "output" in result:
            return self._extract_clean_text(result["output"])
        return str(result).strip()

    def _select_route(
        self,
        intent: str,
        text: str,
        packet: Packet,
        helpers: Dict[str, Any],
    ) -> str:

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














