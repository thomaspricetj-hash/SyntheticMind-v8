from __future__ import annotations
from typing import Dict, Any, Optional
import uuid
import time
import re

from bitdrop_core.ai.metamodel.context.packet import Packet


class ConversationManager:
    """
    Hybrid adaptive conversational layer on top of MetaModelRuntime.

    Capabilities:
        • Tone + intent detection
        • Hybrid persona blending
        • Multi-turn context tracking
        • Memory-aware responses
        • Routing into cognitive subsystems
        • Web-search intent detection
        • Error-safe execution
        • Natural, human-like replies
    """

    HARD_WEB_TRIGGERS = [
        "use web search",
        "search the internet",
        "search the web",
        "look up online",
        "online search",
        "web search",
        "find online",
        "lookup online",
    ]

    SOFT_WEB_TRIGGERS = [
        "what is",
        "who is",
        "latest",
        "current",
        "news",
        "update",
        "recent",
        "information about",
        "info about",
    ]

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.session_states: Dict[str, Dict[str, Any]] = {}

    # ---------------------------------------------------------
    # Session state helpers
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
            }

        return self.session_states[session_id]

    # ---------------------------------------------------------
    # Tone detection
    # ---------------------------------------------------------
    def _detect_tone(self, text: str) -> str:
        t = text.strip().lower()

        if not t:
            return "neutral"

        playful = ["lol", "lmao", "😂", ",🤣", "haha", "funny"]
        frustrated = ["wtf", "why is", "this sucks", "annoying", "frustrated"]
        emotional = ["i feel", "i'm feeling", "worried", "scared", "anxious"]
        builder = ["let's build", "architecture", "design", "pipeline", "optimize"]
        serious = ["serious", "no joke", "honestly", "for real"]

        if any(x in t for x in playful):
            return "playful"
        if any(x in t for x in frustrated):
            return "frustrated"
        if any(x in t for x in emotional):
            return "emotional"
        if any(x in t for x in builder):
            return "builder"
        if any(x in t for x in serious):
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

        greeting = ["hi", "hey", "hello", "yo", "what's up", "sup"]
        explain = ["explain", "how does", "why does", "what is", "teach me"]
        strategy = ["help me plan", "strategy", "roadmap", "multi-step"]
        simulate = ["simulate", "what happens if", "if i do", "if we do"]
        debate = ["argue", "debate", "pros and cons", "which is better"]
        memory_write = ["remember that", "don't forget", "store this", "save this"]

        if any(x in t for x in greeting):
            return "greeting"
        if "thank" in t:
            return "gratitude"
        if any(x in t for x in explain):
            return "explain"
        if any(x in t for x in strategy):
            return "strategy"
        if any(x in t for x in simulate):
            return "simulate"
        if any(x in t for x in debate):
            return "debate"
        if any(x in t for x in memory_write):
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
    # Routing into cognitive subsystems
    # ---------------------------------------------------------
    def _route_to_subsystem(
        self,
        text: str,
        high_intent: str,
        session_id: Optional[str],
        user_id: Optional[str],
        force_web: Optional[str] = None,
    ) -> str:

        # -----------------------------------------------------
        # Web search → orchestrator (RESTORED)
        # -----------------------------------------------------
        if force_web:
            return self.runtime.librarian_orchestrator.answer(
                text,
                metadata={"force_web_search": True, "web_strength": force_web},
            )

        # Strategy
        if high_intent == "strategy":
            result = self.runtime.generate(
                text=text,
                intent="strategy",
                metadata={"action": "plan_for_text"},
                user_id=user_id,
                session_id=session_id,
            )
            return self._extract_text_from_strategy(result)

        # Simulation
        if high_intent == "simulate":
            result = self.runtime.generate(
                intent="simulation",
                metadata={
                    "action": "counterfactual",
                    "base": text,
                    "variation": f"best-case outcome of: {text}",
                },
                user_id=user_id,
                session_id=session_id,
            )
            return self._extract_text_from_simulation(result)

        # Debate
        if high_intent == "debate":
            result = self.runtime.generate(
                text=text,
                intent="debate",
                user_id=user_id,
                session_id=session_id,
            )
            return self._extract_text_from_debate(result)

        # Memory write
        if high_intent == "memory_write":
            self.runtime.memory.remember(text)
            return "Got it — I’ll keep that in mind."

        # Normal conversation → direct Router call
        packet = Packet(
            text=text,
            data=None,
            metadata={},
            intent="conversation",
            model=None,
            compressed=False,
            return_compressed=False,
            user_id=user_id,
            session_id=session_id,
            trace_id=str(uuid.uuid4()),
        )
        packet = packet.copy(query=text)

        result = self.runtime.router.run(packet)
        return self._extract_text_generic(result)

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
        session_id: Optional[str] = None
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

        persona = self._select_persona(tone, high_intent)

        core_reply = self._route_to_subsystem(
            text=text,
            high_intent=high_intent,
            session_id=session_id,
            user_id=user_id,
            force_web=web_strength,
        )

        final_reply = self._wrap_response(core_reply, persona, tone)
        latency_ms = int((time.time() - start) * 1000)

        return {
            "reply": final_reply,
            "persona": persona,
            "tone": tone,
            "intent": high_intent,
            "web_search": bool(web_strength),
            "trace_id": trace_id,
            "latency_ms": latency_ms,
        }



