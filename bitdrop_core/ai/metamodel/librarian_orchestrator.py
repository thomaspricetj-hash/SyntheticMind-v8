from __future__ import annotations
from typing import Any, Dict, Optional
import time

# Core helpers
from .helpers.language_helper import LanguageHelper
from .helpers.memory_helper import MemoryHelper
from .helpers.math_helper import MathHelper
from .helpers.code_helper import CodeHelper
from .helpers.logic_helper import LogicHelper
from .helpers.compression_helper import CompressionHelper
from .helpers.world_model_helper import WorldModelHelper
from .helpers.web_search_helper import WebSearchHelper

# Safety + Hallucination
from .helpers.safety_helper import SafetyHelper
from .helpers.hallucination_helper import HallucinationHelper

# Conversation + Reasoning + Summarization + Robustness
from .helpers.conversation_helper import ConversationHelperV4
from .helpers.reasoning_helper import ReasoningHelperV2
from .helpers.summarization_helper import SummarizationHelperV1


from .helpers.robustness_helper import RobustnessHelperV4

# Physics + Math engines
from ..physics.physics_engine import PhysicsEngine
from ..physics.physics_agent import PhysicsAgent
from ..math.math_engine import MathEngine
from ..math.math_agent import MathAgent

# Mesh + Organizer
from .helpers.helper_mesh import HelperMesh
from .helpers.organizer_helper import OrganizerHelperV6

# Specialized helpers
from .helpers.specialized_helpers import (
    MemoryWriterHelperV1,
    ChainOfThoughtHelperV1,
    VerificationHelperV1,
    TaskPlannerHelperV1,
    DomainExpertRouterHelperV1,
)


# ------------------------------------------------------------
# Adapter wrappers for physics + math agents
# ------------------------------------------------------------
class PhysicsToolHelper:
    def __init__(self, agent: PhysicsAgent):
        self.agent = agent

    def run(self, query: str, **kwargs):
        try:
            return {"ok": True, "answer": self.agent.solve(query)}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "answer": None}


class MathToolHelper:
    def __init__(self, agent: MathAgent):
        self.agent = agent

    def run(self, query: str, **kwargs):
        try:
            return {"ok": True, "answer": self.agent.solve(query)}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "answer": None}


# ------------------------------------------------------------
# Composer model wrapper
# ------------------------------------------------------------
class ComposerModelV2:
    def __init__(self, llm_engine, *, model_name: str, max_tokens: int, temperature: float):
        self.engine = llm_engine
        self.name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def __call__(self, *, prompt: str, context_packet: bytes, session_id=None, stream=False):
        request = {
            "model": self.name,
            "prompt": prompt,
            "context_packet": context_packet,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "session_id": session_id,
            "stream": stream,
        }

        if stream:
            collected = []
            for token in self.engine.generate_stream(request):
                collected.append(token)
            return "".join(collected)

        return self.engine.generate(request)


# ------------------------------------------------------------
# Main orchestrator
# ------------------------------------------------------------
class LibrarianOrchestrator:
    def __init__(
        self,
        *,
        compression_engine,
        llm_engine,
        model_book,
        memory,
        world_model=None,
        web_search_engine=None,
    ):

        # Core components
        self.compression = compression_engine
        self.model_book = model_book
        self.memory = memory
        self.world_model = world_model
        self.web_search_engine = web_search_engine
        self.llm_engine = llm_engine

        # Safety + hallucination
        self.safety = SafetyHelper()
        self.hallucination = HallucinationHelper()

        # Conversation + reasoning + summarization + robustness
        self.conversation = ConversationHelperV4()
        self.reasoning = ReasoningHelperV2(llm_engine=self.llm_engine)
        self.summarization = SummarizationHelperV4()
        self.robustness = RobustnessHelperV4()

        # Composer
        self.composer = ComposerModelV2(
            llm_engine=llm_engine,
            model_name="syntheticmind-composer-v2",
            max_tokens=512,
            temperature=0.7,
        )

        # Organizer
        self.organizer = OrganizerHelperV6()

        # Core helpers
        self.language = LanguageHelper()
        self.memory_helper = MemoryHelper(memory=self.memory)

        # Physics + math
        self.physics_helper = PhysicsToolHelper(PhysicsAgent(PhysicsEngine()))
        self.math_helper = MathToolHelper(MathAgent(MathEngine()))

        # Parallel helpers
        self.code = CodeHelper()
        self.logic = LogicHelper()
        self.compression_helper = CompressionHelper()
        self.world = WorldModelHelper(world_model=self.world_model)
        self.web = WebSearchHelper(engine=self.web_search_engine) if self.web_search_engine else None

        # Specialized helpers
        self.domain = DomainExpertRouterHelperV1(llm_engine=self.llm_engine)
        self.cot = ChainOfThoughtHelperV1(llm_engine=self.llm_engine)
        self.planner = TaskPlannerHelperV1(llm_engine=self.llm_engine)
        self.verify = VerificationHelperV1(llm_engine=self.llm_engine)
        self.memory_writer = MemoryWriterHelperV1(memory=self.memory)

        # Helper registry
        base = {
            "math": self.math_helper,
            "physics": self.physics_helper,
            "code": self.code,
            "logic": self.logic,
            "compression": self.compression_helper,
            "world": self.world,
            "domain": self.domain,
            "cot": self.cot,
            "planner": self.planner,
            "reasoning": self.reasoning,
        }

        if self.web:
            base["web"] = self.web

        self.base_helpers = base

        # Default configs
        self.base_configs = {
            "compression": HelperConfig(priority=1, timeout_ms=1500),
            "math": HelperConfig(priority=2, timeout_ms=2000),
            "physics": HelperConfig(priority=3, timeout_ms=2500),
            "code": HelperConfig(priority=4, timeout_ms=2000),
            "logic": HelperConfig(priority=5, timeout_ms=2000),
            "domain": HelperConfig(priority=6, timeout_ms=3000),
            "cot": HelperConfig(priority=7, timeout_ms=3000),
            "planner": HelperConfig(priority=8, timeout_ms=3000),
            "reasoning": HelperConfig(priority=9, timeout_ms=3000),
            "world": HelperConfig(priority=10, timeout_ms=4000),
        }

        if self.web:
            self.base_configs["web"] = HelperConfig(priority=20, timeout_ms=5000)

        # Initial mesh
        self.mesh = HelperMesh(dict(self.base_helpers), configs=dict(self.base_configs))

    # ------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------
    def answer(self, query: str, metadata: Optional[Dict[str, Any]] = None) -> str:

        metadata = metadata or {}
        mode = (metadata.get("mode") or "intelligence").lower()

        # Safety first
        if self.safety.is_unsafe(query):
            return self.safety.refuse(query)

        # Hallucination (raw)
        if self.hallucination.is_fictional(query):
            return self.hallucination.refuse(query)

        # Language clarification
        lang_info = self.language.process(query)
        clarified = lang_info.get("clarified_query", query)

        # Hallucination (clarified)
        if self.hallucination.is_fictional(clarified):
            return self.hallucination.refuse(clarified)

        # Conversation profile + style shaping
        conv_profile = self.conversation.analyze(clarified)
        shaped_query = self.conversation.shape_prompt(clarified, conv_profile)

        # Summarization intent (may adjust instructions)
        sum_info = self.summarization.analyze(clarified)
        if sum_info.get("detected"):
            extra = []

            if sum_info.get("sentences") is not None:
                extra.append(f"Summarize in {sum_info['sentences']} sentences.")
            if sum_info.get("words") is not None:
                extra.append(f"Summarize in {sum_info['words']} words.")
            if sum_info.get("percent") is not None:
                extra.append(f"Roughly reduce length by {sum_info['percent']} percent.")
            if sum_info.get("length_hint"):
                extra.append(f"Target length hint: {sum_info['length_hint']}.")

            if extra:
                shaped_query += "\n\nSummarization constraints:\n" + "\n".join(extra)

        # Memory recall
        memory_info = self.memory_helper.recall(clarified)

        # Helper planning
        plan = self._plan_helpers(shaped_query)
        active = self._select_helpers_for_mode(mode)

        # Apply plan
        selected = {name: helper for name, helper in active.items() if plan.get(name, True)}

        # Build configs
        configs = {name: cfg for name, cfg in self.base_configs.items() if name in selected}

        # Rebuild mesh
        self.mesh = HelperMesh(selected, configs=configs)

        # Organize helpers
        self.mesh.helpers = self.organizer.organize(self.mesh.helpers)

        # Run helpers
        results = self.mesh.run(
            shaped_query,
            lang_info=lang_info,
            memory_info=memory_info,
            timing_callback=self.organizer.record_timing,
        )

        # Physics enrichment
        if "physics" in results and results["physics"].get("ok"):
            shaped_query += (
                "\n\nPhysics engine computed this result:\n"
                f"{results['physics']['answer']}\n\n"
                "Use this as ground truth and explain."
            )

        # Math enrichment
        if "math" in results and results["math"].get("ok"):
            shaped_query += (
                "\n\nMath engine computed this result:\n"
                f"{results['math']['answer']}\n\n"
                "Use this as ground truth and show the steps."
            )

        # Model notes
        notes = self._query_models(
            shaped_query,
            helper_results=results,
            lang_info=lang_info,
            memory_info=memory_info,
        )

        # Build context
        context = {
            "query": shaped_query,
            "lang": lang_info,
            "memory": memory_info,
            "helpers": results,
            "models": notes,
            "metadata": metadata,
            "conversation": conv_profile,
            "summarization": sum_info,
        }

        # Compress
        packet = self.compression.compress(context)

        # Compose final answer
        answer = self.composer(
            prompt=shaped_query,
            context_packet=packet,
            session_id=metadata.get("session_id"),
            stream=False,
        )

        # Verification
        if mode in ("intelligence", "safety"):
            verdict = self.verify.run(query=shaped_query, answer=answer)
            try:
                consistent = bool(verdict.get("consistent", True))
                confidence = float(verdict.get("confidence", 0.5))
            except Exception:
                consistent = True
                confidence = 0.5

            if not consistent and confidence >= 0.6:
                answer = verdict.get("corrected_answer") or answer

        # Robustness evaluation (post‑verification)
        robustness_profile = self.robustness.analyze(shaped_query, answer)
        # You can optionally react to low logic_score here if you want re‑reasoning.

        # Memory write
        try:
            self.memory_writer.run(
                query=shaped_query,
                answer=answer,
                metadata={**metadata, "robustness": robustness_profile},
            )
        except Exception:
            pass

        return answer