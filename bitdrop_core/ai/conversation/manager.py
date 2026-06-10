from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bitdrop_core.ai.metamodel.context.packet import Packet
from bitdrop_core.ai.self_model.personality_adapter import PersonalityAdapter
from bitdrop_core.ai.self_model.growth_loop import run_growth_cycle


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Conversation3D:
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# CONVERSATION MANAGER (3D‑MAX, DEEP ROUTER AWARE)
# ============================================================

class ConversationManager:
    HARD_WEB_TRIGGERS = [
        "use web search", "search the internet", "search the web",
        "look up online", "online search", "web search",
        "find online", "lookup online",
    ]

    SOFT_WEB_TRIGGERS = [
        "what is", "who is", "latest", "current", "news",
        "update", "recent", "information about", "info about",
    ]

    def __init__(self, runtime: "MetaModelRuntime", base_dir: str):
        self.runtime = runtime
        self.base_dir = base_dir
        self.persona = PersonalityAdapter(base_dir=base_dir)
        self.session_states: Dict[str, Dict[str, Any]] = {}
        self._last_3d: Optional[Conversation3D] = None
        self._last_packet: Optional[Packet] = None
        self._last_router_result: Any = None

        te = getattr(self.runtime, "thinking_engine", None)
        if te is not None and hasattr(te, "warmup"):
            try:
                te.warmup(mode="conversation")
            except Exception:
                pass

    # ---------------------------------------------------------
    # Session state
    # ---------------------------------------------------------
    def _get_session(self, session_id: Optional[str]) -> Dict[str, Any]:
        if not session_id:
            session_id = "default"

        if session_id not in self.session_states:
            self.session_states[session_id] = {
                "last_user_text": "",
                "last_intent": None,
                "mood": "neutral",
                "turns": 0,
                "history": [],
                "persona_header": None,
            }

        return self.session_states[session_id]

    # ---------------------------------------------------------
    # Tone detection
    # ---------------------------------------------------------
    def _detect_tone(self, text: str) -> str:
        t = text.strip().lower()
        if not t:
            return "neutral"

        if any(x in t for x in ["lol", "lmao", "😂", "🤣", "haha"]):
            return "playful"
        if any(x in t for x in ["wtf", "why is", "this sucks", "annoying"]):
            return "frustrated"
        if any(x in t for x in ["i feel", "worried", "scared", "anxious"]):
            return "emotional"
        if any(x in t for x in ["let's build", "architecture", "design", "pipeline"]):
            return "builder"
        if any(x in t for x in ["serious", "honestly", "for real"]):
            return "serious"
        if "?" in t:
            return "curious"

        return "neutral"

    # ---------------------------------------------------------
    # High-level intent detection
    # ---------------------------------------------------------
    def _detect_high_level_intent(self, text: str) -> str:
        t = text.strip().lower()
        if not t:
            return "small_talk"

        if any(x in t for x in ["hi", "hey", "hello", "yo"]):
            return "greeting"
        if "thank" in t:
            return "gratitude"
        if any(x in t for x in ["explain", "how does", "why does", "what is"]):
            return "explain"
        if any(x in t for x in ["help me plan", "strategy", "roadmap"]):
            return "strategy"
        if any(x in t for x in ["simulate", "what happens if"]):
            return "simulate"
        if any(x in t for x in ["argue", "debate", "pros and cons"]):
            return "debate"
        if any(x in t for x in ["remember that", "store this", "save this"]):
            return "memory_write"

        return "small_talk"

    # ---------------------------------------------------------
    # Web-search intent detection
    # ---------------------------------------------------------
    def _detect_web_search_intent(self, text: str) -> Optional[str]:
        q = text.lower()
        if any(t in q for t in self.HARD_WEB_TRIGGERS):
            return "hard"
        if any(q.startswith(t) for t in self.SOFT_WEB_TRIGGERS):
            return "soft"
        return None

    # ---------------------------------------------------------
    # Complexity scoring
    # ---------------------------------------------------------
    def _score_complexity(self, text: str) -> Dict[str, Any]:
        t = text.strip()
        tl = t.lower()

        length = len(t)
        lines = t.count("\n") + 1
        has_math = bool(re.search(r"[0-9][0-9\+\-\*/x\^=\(\)]", t))
        has_code = "```" in t or "def " in t or "class " in t or ("{" in t and "}" in t)

        # FIXED: no unterminated string literal
        has_latex = ("$" in t) or (r"\(" in t) or (r"\[" in t)


        has_physics = any(
            k in tl
            for k in [
                "photon rocket",
                "relativistic rocket",
                "lorentz",
                "gamma",
                "c^2",
                "rest mass energy",
                "energy–momentum",
                "energy-momentum",
                "schwarzschild",
                "kerr",
                "ergosphere",
                "event horizon",
                "geodesic",
                "null geodesic",
                "timelike",
                "spacelike",
                "general relativity",
                "special relativity",
            ]
        )

        score = 0
        score += min(length // 80, 10)
        score += 2 * int(has_math)
        score += 2 * int(has_code)
        score += 2 * int(has_latex)
        score += 3 * int(has_physics)
        score += min(lines // 4, 5)

        gpu_batch_preferred = score >= 6

        return {
            "score": score,
            "length": length,
            "lines": lines,
            "has_math": has_math,
            "has_code": has_code,
            "has_latex": has_latex,
            "has_physics": has_physics,
            "gpu_batch_preferred": gpu_batch_preferred,
        }

    # ---------------------------------------------------------
    # Persona selection
    # ---------------------------------------------------------
    def _select_persona(self, tone: str, high_intent: str) -> str:
        return "hybrid"

    # ---------------------------------------------------------
    # Style wrapper
    # ---------------------------------------------------------
    def _wrap_response(self, core_text: str, persona: str, tone: str) -> str:
        return core_text.strip()

    # ---------------------------------------------------------
    # Routing into subsystems
    # ---------------------------------------------------------
    def _route_to_subsystem(
        self,
        text: str,
        high_intent: str,
        session_id: Optional[str],
        user_id: Optional[str],
        force_web: Optional[str] = None,
        persona_header: Optional[str] = None,
        complexity: Optional[Dict[str, Any]] = None,
    ) -> str:

        if complexity is None:
            complexity = self._score_complexity(text)

        route_axis_y = [
            f"intent:{high_intent}",
            f"web:{bool(force_web)}",
            f"complexity:{complexity['score']}",
        ]

        # Persona injection
        if persona_header and high_intent not in (
            "strategy",
            "simulate",
            "debate",
            "memory_write",
        ):
            text = f"{persona_header}\n\nUser: {text}"
            route_axis_y.append("persona:applied")
        else:
            route_axis_y.append("persona:neutral")

        # Web search
        if force_web:
            out = self.runtime.librarian_orchestrator.answer(
                text,
                metadata={
                    "force_web_search": True,
                    "web_strength": force_web,
                    "complexity": complexity,
                },
            )
            self._last_3d = Conversation3D(
                axis_x="route",
                axis_y=route_axis_y + ["path:web"],
                axis_z={"session_id": session_id, "user_id": user_id},
            )
            return out

        # Strategy
        if high_intent == "strategy":
            result = self.runtime.generate(
                text=text,
                intent="strategy",
                metadata={"action": "plan_for_text", "complexity": complexity},
                user_id=user_id,
                session_id=session_id,
            )
            out = self._extract_text_from_strategy(result)
            self._last_3d = Conversation3D(
                axis_x="route",
                axis_y=route_axis_y + ["path:strategy"],
                axis_z={"session_id": session_id, "user_id": user_id},
            )
            return out

        # Simulation
        if high_intent == "simulate":
            result = self.runtime.generate(
                intent="simulation",
                metadata={
                    "action": "counterfactual",
                    "base": text,
                    "variation": f"best-case outcome of: {text}",
                    "complexity": complexity,
                },
                user_id=user_id,
                session_id=session_id,
            )
            out = self._extract_text_from_simulation(result)
            self._last_3d = Conversation3D(
                axis_x="route",
                axis_y=route_axis_y + ["path:simulation"],
                axis_z={"session_id": session_id, "user_id": user_id},
            )
            return out

        # Debate
        if high_intent == "debate":
            result = self.runtime.generate(
                text=text,
                intent="debate",
                user_id=user_id,
                session_id=session_id,
            )
            out = self._extract_text_from_debate(result)
            self._last_3d = Conversation3D(
                axis_x="route",
                axis_y=route_axis_y + ["path:debate"],
                axis_z={"session_id": session_id, "user_id": user_id},
            )
            return out

        # Memory write
        if high_intent == "memory_write":
            self.runtime.memory.remember(text)
            out = "Got it — I’ll keep that in mind."
            self._last_3d = Conversation3D(
                axis_x="route",
                axis_y=route_axis_y + ["path:memory_write"],
                axis_z={"session_id": session_id, "user_id": user_id},
            )
            return out

        # Normal → Router
        router_intent = "conversation"
        router_metadata = {
            "source": "conversation_manager",
            "high_intent": high_intent,
            "complexity": complexity,
        }

        if complexity["has_physics"]:
            router_intent = "deep_physics"
            router_metadata["force_deep_physics"] = True
            route_axis_y.append("flag:physics")

        if complexity["has_math"]:
            router_metadata["math_heavy"] = True
            route_axis_y.append("flag:math")

        if complexity["has_code"]:
            router_metadata["code_heavy"] = True
            route_axis_y.append("flag:code")

        if complexity["gpu_batch_preferred"]:
            router_metadata["gpu_batch_preferred"] = True
            route_axis_y.append("flag:gpu_batch")

        packet = Packet(
            text=text,
            data=None,
            metadata=router_metadata,
            intent=router_intent,
            model=None,
            compressed=False,
            return_compressed=False,
            user_id=user_id,
            session_id=session_id,
            trace_id=str(uuid.uuid4()),
        )

        packet = packet.copy(query=text)

        self._last_packet = packet
        result = self.runtime.router.run(packet)
        self._last_router_result = result

        out = self._extract_text_generic(result)

        self._last_3d = Conversation3D(
            axis_x="route",
            axis_y=route_axis_y + ["path:router"],
            axis_z={
                "session_id": session_id,
                "user_id": user_id,
                "router_ok": isinstance(result, dict) and result.get("ok", True),
                "complexity": complexity,
            },
        )

        return out

    # ---------------------------------------------------------
    # Extractors
    # ---------------------------------------------------------
    def _extract_text_generic(self, result: Any) -> str:
        if isinstance(result, dict):
            if "reply" in result:
                return str(result["reply"])
            if "output" in result:
                out = result["output"]
                if isinstance(out, dict) and "output" in out:
                    return str(out["output"])
                return str(out)
            for key in ("final", "simulation", "debate"):
                if key in result:
                    return str(result[key])
        return str(result)

    def _extract_text_from_simulation(self, result: Any) -> str:
        if not isinstance(result, dict):
            return str(result)
        sim = result.get("simulation", {})
        analysis = sim.get("analysis", {})
        return analysis.get("summary", str(sim))

    def _extract_text_from_debate(self, result: Any) -> str:
        if not isinstance(result, dict):
            return str(result)
        debate = result.get("debate", {})
        consensus = debate.get("consensus")
        return consensus if consensus else str(debate)

    def _extract_text_from_strategy(self, result: Any) -> str:
        if not isinstance(result, dict):
            return str(result)
        strat = result.get("strategy", {})
        plan = strat.get("plan", {})
        steps = plan.get("steps", [])
        if steps:
            lines = ["Here’s a solid way to approach this:"]
            for i, s in enumerate(steps, 1):
                lines.append(f"{i}. {s}")
            return "\n".join(lines)
        return str(strat)

    # ---------------------------------------------------------
    # Public entrypoint
    # ---------------------------------------------------------
    def converse(
        self,
        text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        start = time.time()
        trace_id = str(uuid.uuid4())

        session = self._get_session(session_id)
        session["last_user_text"] = text
        session["turns"] += 1
        session["history"].append(text)

        tone = self._detect_tone(text)
        high_intent = self._detect_high_level_intent(text)
        web_strength = self._detect_web_search_intent(text)
        complexity = self._score_complexity(text)

        if session["persona_header"] is None:
            session["persona_header"] = self.persona.apply(
                user_text=text,
                metadata={"social_read": {"tone": tone}},
            )

        persona_header = session["persona_header"]
        persona = self._select_persona(tone, high_intent)

        core_reply = self._route_to_subsystem(
            text=text,
            high_intent=high_intent,
            session_id=session_id,
            user_id=user_id,
            force_web=web_strength,
            persona_header=persona_header,
            complexity=complexity,
        )

        final_reply = self._wrap_response(core_reply, persona, tone)
        latency_ms = int((time.time() - start) * 1000)

        run_growth_cycle(
            base_dir=self.base_dir,
            metadata={
                "intent": high_intent,
                "social_read": {"tone": tone},
                "reasoning_context": {"complexity": complexity},
                "model_role": "conversation",
            },
            reply=final_reply,
        )

        self._last_3d = Conversation3D(
            axis_x="converse",
            axis_y=[
                f"tone:{tone}",
                f"intent:{high_intent}",
                f"web:{bool(web_strength)}",
                f"persona:{persona}",
                f"complexity:{complexity['score']}",
            ],
            axis_z={
                "latency_ms": latency_ms,
                "trace_id": trace_id,
                "session_id": session_id or "default",
                "user_id": user_id,
                "input_len": len(text),
                "reply_len": len(final_reply),
                "complexity": complexity,
            },
        )

        return {
            "reply": final_reply,
            "persona": persona,
            "tone": tone,
            "intent": high_intent,
            "web_search": bool(web_strength),
            "trace_id": trace_id,
            "latency_ms": latency_ms,
        }

    # ---------------------------------------------------------
    # Introspection helpers
    # ---------------------------------------------------------
    def last_3d(self) -> Optional[Conversation3D]:
        return self._last_3d

    def last_packet(self) -> Optional[Packet]:
        return self._last_packet

    def last_router_result(self) -> Any:
        return self._last_router_result

