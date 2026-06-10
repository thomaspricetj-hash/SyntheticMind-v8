# bitdrop_core/ai/metamodel/runtime.py

from __future__ import annotations

import inspect
import importlib
import pkgutil
import uuid
import time
import os
import re
from typing import Dict, Any, Optional, List

from bitdrop_core.ai.runtime.response_quality import ResponseQualityController

from .context.packet import Packet
from .router import Router
from . import helpers as helper_pkg

from ..conversation.manager import ConversationManager
from ..self_model.personality_adapter import PersonalityAdapter

from ..memory.memory_manager import MemoryManager
from ..tools.agent import Agent
from ..tools.planner import Planner
from ..vision.vision_processor import VisionProcessor
from ..self_refine.refiner import Refiner
from ..taskgraph.planner import TaskGraphPlanner
from ..taskgraph.executor import TaskGraphExecutor
from ..skills.runner import SkillRunner

from ..agents.planner_agent import PlannerAgent
from ..agents.executor_agent import ExecutorAgent
from ..agents.critic_agent import CriticAgent
from ..agents.memory_agent import MemoryAgent
from ..agents.vision_agent import VisionAgent
from ..agents.tool_agent import ToolAgent

from ..goals.manager import GoalManager
from ..background.learner import BackgroundLearner
from ..memory_heal.healer import MemoryHealer
from ..world_model.manager import WorldModelManager
from ..meta.optimizer import MetaOptimizer
from ..tool_learning.manager import ToolLearningManager
from ..simulation.manager import SimulationManager
from ..debate.manager import DebateManager
from ..strategy.manager import StrategyManager

from ..reasoning.local_reasoning_model import LocalReasoningModel

from .helpers.web_search_helper import WebSearchHelper
from ...web.search_engine import WebSearchEngine

from .self_audit_engine import SelfAuditEngineV4

from ..telemetry.perf_profiler_v8 import PerfProfilerV8

from bitdrop_core.ai.storage.ai_store import AIStore

from .helpers.helper_mesh import HelperMesh, HelperConfig
from .feature_builder import FeatureBuilder
from .neural_predictor import NeuralPredictor

from bitdrop_core.ai.metamodel.librarian_orchestrator import LibrarianOrchestrator

from bitdrop_core.ai.bitdrop.compressor import BitDropCompressor
from bitdrop_core.ai.compression.bitdrop_collapse_codec import BitDropCollapseEngine

from bitdrop_core.ai.backend.hybrid_backend import (
    HybridBackend,
    create_default_hybrid_backend,
)

from .thinking_engine import ThinkingEngine


class ExecutionEngine:
    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

    def run(
        self,
        task: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        task_type = task.get("type", "natural_language")

        if task_type == "tool":
            command = task.get("command")
            if not command:
                command = self.runtime.planner.plan(task.get("text", ""))
            result = self.runtime.agent.run(command)
            self.runtime.memory.remember(f"[action:tool-command] {command}")
            self.runtime.memory.remember(f"[action:tool-result] {result}")
            return {
                "mode": "tool",
                "command": command,
                "result": result,
            }

        if task_type == "taskgraph":
            goal_text = task.get("goal", "")
            graph = self.runtime.taskgraph_planner.plan(goal_text)
            tg_result = self.runtime.taskgraph_executor.run(graph)
            self.runtime.memory.remember(f"[action:taskgraph-goal] {goal_text}")
            self.runtime.memory.remember(f"[action:taskgraph-final] {tg_result.get('final', '')}")
            return {
                "mode": "taskgraph",
                "goal": tg_result.get("goal"),
                "final": tg_result.get("final"),
                "nodes": tg_result.get("nodes"),
            }

        if task_type == "skill":
            skill_name = task.get("skill")
            params = task.get("params", {})
            result = self.runtime.skills.run(skill_name, params)
            self.runtime.memory.remember(f"[action:skill] {skill_name}({params}) -> {result}")
            return {
                "mode": "skill",
                "skill": skill_name,
                "result": result,
            }

        nl_text = task.get("text", "")
        command = self.runtime.planner.plan(nl_text)
        result = self.runtime.agent.run(command)
        self.runtime.memory.remember(f"[action:nl] {nl_text}")
        self.runtime.memory.remember(f"[action:nl-command] {command}")
        self.runtime.memory.remember(f"[action:nl-result] {result}")
        return {
            "mode": "natural_language",
            "command": command,
            "result": result,
        }

    def run_batch(
        self,
        tasks: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [self.run(t, user_id=user_id, session_id=session_id) for t in tasks]

    def run_3d(
        self,
        tasks_3d: List[List[List[Dict[str, Any]]]],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[List[List[Dict[str, Any]]]]:
        if not tasks_3d:
            return []
        out: List[List[List[Dict[str, Any]]]] = []
        for plane in tasks_3d:
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for task in row:
                    row_out.append(self.run(task, user_id=user_id, session_id=session_id))
                plane_out.append(row_out)
            out.append(plane_out)
        return out


class MetaModelRuntime:
    """
    SyntheticMind v8 MetaModel Runtime

    Backbones:
        - BitDropCompressor: byte-level compression backbone
        - BitDropCollapseEngine: prompt-level collapse backbone
        - HybridBackend (Ollama-only via metadata override): remote LLM

    3D‑MAX extensions:
        - generate_batch(): batched request handling
        - generate_3d(): tensor-style 3D request handling
        - think_batch(): batched thinking
        - think_3d(): tensor-style 3D thinking
    """

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        self.store = AIStore(
            root_path="C:/Users/thomas price/Desktop/SyntheticMind-v8/bitdrop_core/ai/storage"
        )

        self.profiler = PerfProfilerV8()

        self.memory = MemoryManager()
        self.compressor = BitDropCompressor.instance()
        self.quality = ResponseQualityController()

        # Create the local LLM engine FIRST
        self.local_reasoner = LocalReasoningModel(
            memory=self.memory,
            name="local_reasoner",
            config={
                "cache_size": 4096,
                "act_rows": 4,
                "act_cols": 16,
                "deterministic": True,
                "simulate_logits": True,
            },
        )

        # ------------------------------------------------------------
        # MAX-3D Helper Wiring (Notepad-safe indentation)
        # ------------------------------------------------------------
        from bitdrop_core.ai.metamodel.helpers.physics_helper import PhysicsHelper3D
        from bitdrop_core.ai.metamodel.helpers.math_helper import MathHelper3D
        from bitdrop_core.ai.metamodel.helpers.logic_helper import LogicHelper3D
        from bitdrop_core.ai.metamodel.helpers.code_helper import CodeHelper
        from bitdrop_core.ai.metamodel.helpers.reasoning_helper import ReasoningHelperV2

        # Attach MAX-3D helpers directly to runtime so ThinkingEngine can find them
        self.physics_helper = PhysicsHelper3D()
        self.math_helper = MathHelper3D()
        self.logic_helper = LogicHelper3D()
        self.code_helper = CodeHelper()
        self.reasoning_helper = ReasoningHelperV2(self.local_reasoner)

        # Router MUST come AFTER local_reasoner exists
        self.router = Router(self)


        self.thinking_engine = ThinkingEngine(self)


        self.base_dir = os.getcwd()
        self.conversation = ConversationManager(self, base_dir=self.base_dir)

        self.personality = PersonalityAdapter(base_dir=self.base_dir)

        self.agent = Agent()
        self.planner = Planner()
        self.vision = VisionProcessor()
        self.refiner = Refiner()
        self.taskgraph_planner = TaskGraphPlanner()
        self.taskgraph_executor = TaskGraphExecutor(self)
        self.skills = SkillRunner(self)

        self.agents = {
            "planner": PlannerAgent(self),
            "executor": ExecutorAgent(self),
            "critic": CriticAgent(self),
            "memory": MemoryAgent(self),
            "vision": VisionAgent(self),
            "tool": ToolAgent(self),
        }

        self.goals = GoalManager(self)
        self.background = BackgroundLearner(self)
        self.healer = MemoryHealer(self)
        self.world = WorldModelManager(self)
        self.meta = MetaOptimizer(self)
        self.tool_learning = ToolLearningManager(self)
        self.simulation = SimulationManager(self)
        self.debate = DebateManager(self)
        self.strategy = StrategyManager(self)

        self.taskgraph = self.taskgraph_planner
        self.world_model = self.world

        self.web_search_engine = WebSearchEngine()
        self.web_helper = WebSearchHelper(self.web_search_engine)

        self.self_audit = SelfAuditEngineV4(root_path=self.root_dir)

        self.helpers = self._load_all_helpers()
        self.helper_mesh = HelperMesh(
            helpers=self.helpers,
            configs={name: HelperConfig(priority=10) for name in self.helpers.keys()},
        )
        self.feature_builder = FeatureBuilder()
        self.predictor = NeuralPredictor(helper_manager=self.helper_mesh)

        self.collapse_engine = BitDropCollapseEngine()

        self.hybrid_backend: HybridBackend = create_default_hybrid_backend(
            collapser=self.collapse_engine,
            expand_response=True,
        )

        self.librarian_orchestrator = LibrarianOrchestrator(
            compression_engine=self.compressor,
            llm_engine=self.local_reasoner,
            model_book=None,
            memory=self.memory,
            world_model=self.world,
            web_search_engine=self.web_search_engine,
        )

        self.execution = ExecutionEngine(self)

    # ------------------------------------------------------------------
    # Helper loading / audit
    # ------------------------------------------------------------------
    def _load_all_helpers(self) -> Dict[str, Any]:
        helper_instances: Dict[str, Any] = {}

        for module_info in pkgutil.iter_modules(helper_pkg.__path__):
            module_name = module_info.name
            if module_name == "helper_mesh":
                continue

            module = importlib.import_module(f"{helper_pkg.__name__}.{module_name}")

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.endswith("Helper"):
                    try:
                        helper_instances[name] = obj()
                    except Exception:
                        continue

        return helper_instances

    def audit(self, *, mode: str = "full") -> Dict[str, Any]:
        report = self.self_audit.audit()
        if mode == "light":
            return {
                "ok": report.get("ok", True),
                "summary": report.get("summary", {}),
                "dependency_cycles": report.get("dependency_cycles", []),
                "duplicate_files": report.get("duplicate_files", []),
                "self_reflection": report.get("self_reflection", []),
                "latency_ms": report.get("latency_ms", 0),
            }
        return report

    # ------------------------------------------------------------------
    # High-level reasoning helper
    # ------------------------------------------------------------------
    def reason(self, text: str) -> str:
        try:
            if text:
                self.memory.remember(f"[reason:user] {text}")

            recalled = self.memory.recall(text, top_k=5)
            recalled_text = "\n".join(recalled).strip()

            if recalled_text:
                context_block = (
                    "Relevant past context:\n" +
                    recalled_text +
                    "\n\nUser message:\n" +
                    text
                )
            else:
                context_block = text

            persona = self.personality.apply(context_block)
            full_prompt = f"{persona}\n\nUser: {context_block}"
            out = self.local_reasoner.generate(full_prompt)

            if isinstance(out, dict):
                reply = out.get("text", "")
            else:
                reply = str(out)

            if reply:
                self.memory.remember(f"[reason:ai] {reply}")

            return reply
        except Exception as e:
            return f"[ReasoningError] {e}"

    # ------------------------------------------------------------------
    # Core generate()
    # ------------------------------------------------------------------
    def generate(
        self,
        text: str = "",
        data: Optional[bytes] = None,
        intent: str = "small_reasoning",
        compressed: bool = False,
        return_compressed: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        start = time.time()
        metadata = metadata or {}

        if compressed and data is not None:
            try:
                decompressed = self.compressor.decompress(data)
                text = decompressed.decode("utf-8")
            except Exception:
                pass

        # ACTION / EXECUTION MODE
        if intent in ("action", "execute"):
            task = metadata.get("task")
            if task is None:
                task = {
                    "type": "natural_language",
                    "text": text,
                }

            result = self.execution.run(task, user_id=user_id, session_id=session_id)

            out = {
                "type": "action",
                "task": task,
                "result": result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000),
            }

            if return_compressed:
                payload = str(out.get("result", ""))
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True

            return out

        # SELF-AUDIT MODE
        if intent == "self_audit":
            mode = metadata.get("mode", "full")
            report = self.audit(mode=mode)
            out = {
                "type": "self_audit",
                "mode": mode,
                "report": report,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000),
            }

            if return_compressed:
                payload = str(report)
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True

            return out

        # GOAL MODE
        if intent == "goal":
            if not metadata or "action" not in metadata:
                return {"error": "goal intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "create":
                goal = self.goals.create(text, metadata.get("metadata"))
                out = {
                    "type": "goal",
                    "action": "create",
                    "goal_id": goal.id,
                    "text": goal.text,
                    "status": goal.status,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = goal.text
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "resume":
                goal_id = metadata.get("goal_id")
                result = self.goals.resume(goal_id)
                out = {
                    "type": "goal",
                    "action": "resume",
                    "goal_id": goal_id,
                    "result": result,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(result)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "list":
                goals = [
                    {"id": g.id, "text": g.text, "status": g.status, "progress": g.progress}
                    for g in self.goals.list()
                ]
                out = {
                    "type": "goal",
                    "action": "list",
                    "goals": goals,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(goals)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            return {"error": f"unknown goal action: {action}"}

        # STRATEGY MODE
        if intent == "strategy":
            if not metadata or "action" not in metadata:
                return {"error": "strategy intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "plan_for_text":
                goal_text = text
                strat = self.strategy.plan_for_goal(goal_text)
                self.memory.remember(f"[strategy-text] {strat}")
                out = {
                    "type": "strategy",
                    "action": "plan_for_text",
                    "strategy": strat,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(strat)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "plan_for_goal":
                goal_id = metadata.get("goal_id", "")
                strat = self.strategy.plan_for_existing_goal(goal_id)
                self.memory.remember(f"[strategy-goal] {strat}")
                out = {
                    "type": "strategy",
                    "action": "plan_for_goal",
                    "strategy": strat,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(strat)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            return {"error": f"unknown strategy action: {action}"}

        # AGENT MODE
        if intent == "agent":
            if not metadata or "agent" not in metadata:
                return {"error": "agent intent requires metadata.agent", "trace_id": str(uuid.uuid4())}

            agent_name = metadata["agent"]
            agent = self.agents.get(agent_name)

            if not agent:
                return {"error": f"unknown agent: {agent_name}", "trace_id": str(uuid.uuid4())}

            params = metadata.get("params", {})
            result = agent.run(**params)

            self.memory.remember(f"[agent:{agent_name}] {params} -> {result}")

            out = {
                "type": "agent",
                "agent": agent_name,
                "result": result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }
            if return_compressed:
                payload = str(result)
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True
            return out

        # BACKGROUND MODE
        if intent == "background":
            insights = self.background.run()
            self.memory.remember(f"[background-learning] {insights}")
            out = {
                "type": "background",
                "insights": insights,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }
            if return_compressed:
                payload = str(insights)
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True
            return out

        # MEMORY HEAL MODE
        if intent == "heal_memory":
            issues = self.healer.run()
            self.memory.remember(f"[memory-heal] {issues}")
            out = {
                "type": "memory_heal",
                "issues": issues,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }
            if return_compressed:
                payload = str(issues)
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True
            return out

        # WORLD MODEL MODE
        if intent == "world_model":
            if not metadata or "action" not in metadata:
                return {"error": "world_model intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "ingest":
                extracted = self.world.ingest(text)
                self.memory.remember(f"[world-ingest] {text} -> {extracted}")
                out = {
                    "type": "world_model",
                    "action": "ingest",
                    "extracted": extracted,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(extracted)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "query":
                label = metadata.get("label", "")
                relations = self.world.query(label)
                out = {
                    "type": "world_model",
                    "action": "query",
                    "label": label,
                    "relations": relations,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(relations)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "snapshot":
                snap = self.world.snapshot()
                out = {
                    "type": "world_model",
                    "action": "snapshot",
                    "graph": snap,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(snap)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "simulate_changes":
                changes = metadata.get("changes", [])
                sim = self.world.sim.simulate_changes(changes)
                self.memory.remember(f"[world-sim-changes] {sim}")
                out = {
                    "type": "world_model",
                    "action": "simulate_changes",
                    "result": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(sim)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "simulate_propagation":
                root = metadata.get("root", "")
                sim = self.world.sim.simulate_propagation(root)
                self.memory.remember(f"[world-sim-propagation] {sim}")
                out = {
                    "type": "world_model",
                    "action": "simulate_propagation",
                    "result": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(sim)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            return {"error": f"unknown world_model action: {action}"}

        # SKILL EVOLVE MODE
        if intent == "skill_evolve":
            if not metadata or "action" not in metadata:
                return {"error": "skill_evolve intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "mutate":
                skill_name = metadata.get("skill")
                info = self.skills.evolve(skill_name)
                self.memory.remember(f"[skill-mutate] {info}")
                out = {
                    "type": "skill_evolve",
                    "action": "mutate",
                    "info": info,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(info)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            if action == "metrics":
                snap = self.skills.metrics_snapshot()
                out = {
                    "type": "skill_evolve",
                    "action": "metrics",
                    "metrics": snap,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }
                if return_compressed:
                    payload = str(snap)
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True
                return out

            return {"error": f"unknown skill_evolve action: {action}"}

        # TASKGRAPH MODE
        if intent == "taskgraph":
            graph = self.taskgraph_planner.plan(text)
            tg_result = self.taskgraph_executor.run(graph)
            self.memory.remember(f"[taskgraph-goal] {text}")
            self.memory.remember(f"[taskgraph-final] {tg_result.get('final', '')}")
            out = {
                "type": "taskgraph",
                "goal": tg_result["goal"],
                "final": tg_result["final"],
                "nodes": tg_result["nodes"],
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }
            if return_compressed:
                payload = str(tg_result)
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True
            return out

        # SKILL MODE
        if intent == "skill":
            if not metadata or "skill" not in metadata:
                return {"error": "skill intent requires metadata.skill", "trace_id": str(uuid.uuid4())}

            skill_name = metadata["skill"]
            params = metadata.get("params", {})
            result = self.skills.run(skill_name, params)

            self.memory.remember(f"[skill] {skill_name}({params}) -> {result}")

            out = {
                "type": "skill",
                "skill": skill_name,
                "result": result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }
            if return_compressed:
                payload = str(result)
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True
            return out

        # THINKING MODES (deep / physics / math)
        if intent in ("deep_thinking", "physics_reasoning", "math_reasoning"):
            think_result = self.thinking.think(
                prompt=text,
                intent=intent,
                metadata=metadata,
                use_cache=True,
            )

            out = {
                "type": "thinking",
                "intent": intent,
                "final": think_result.get("final", ""),
                "subproblems": think_result.get("subproblems", []),
                "tensor_shape": think_result.get("tensor_shape"),
                "cache_hit": think_result.get("cache_hit", False),
                "trace_id": str(uuid.uuid4()),
                "latency_ms": think_result.get("latency_ms", int((time.time() - start) * 1000)),
            }

            if return_compressed:
                payload = out.get("final", "")
                if isinstance(payload, str) and payload:
                    blob = self.compressor.compress(payload.encode("utf-8"))
                    out["data"] = blob
                    out["compressed"] = True

            return out

        # CONVERSATION MODE (Ollama-only via HybridBackend, memory-augmented)
        if intent == "conversation":
            if text:
                self.memory.remember(f"[conversation:user] {text}")

            recalled = self.memory.recall(text, top_k=5)
            recalled_text = "\n".join(recalled).strip()

            if recalled_text:
                augmented_text = (
                    "Relevant past context:\n" +
                    recalled_text +
                    "\n\nUser message:\n" +
                    text
                )
            else:
                augmented_text = text

            meta_for_backend = dict(metadata)
            meta_for_backend["backend"] = "ollama"

            backend_result = self.hybrid_backend.generate(
                prompt=augmented_text,
                intent="conversation",
                system_prompt=None,
                max_tokens=512,
                temperature=0.7,
                metadata=meta_for_backend,
            )

            reply = backend_result.text or ""

            if reply:
                self.memory.remember(f"[conversation:ai] {reply}")

            out = {
                "type": "conversation",
                "reply": reply,
                "backend": backend_result.backend,
                "model": backend_result.model,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": backend_result.latency_ms,
            }

            if return_compressed:
                blob = self.compressor.compress(reply.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True

            return out

        # FAST LOCAL REASONING MODE (memory-augmented)
        if intent in ("small_reasoning", "local_reasoning", "reasoning"):
            if text:
                self.memory.remember(f"[local_reasoning:user] {text}")

            recalled = self.memory.recall(text, top_k=5)
            recalled_text = "\n".join(recalled).strip()

            if recalled_text:
                augmented_text = (
                    "Relevant past context:\n" +
                    recalled_text +
                    "\n\nUser message:\n" +
                    text
                )
            else:
                augmented_text = text

            with self.profiler.section(f"local_reasoner.intent.{intent}"):
                result = self.local_reasoner.generate(
                    prompt=augmented_text,
                    meta={
                        "intent": intent,
                        "user_id": user_id,
                        "session_id": session_id,
                    },
                )

            reply = result.get("text", "")
            if not isinstance(reply, str):
                reply = str(reply)

            if reply:
                self.memory.remember(f"[local_reasoning:ai] {reply}")

            latency_ms = int((time.time() - start) * 1000)
            self.meta.record_call(intent, latency_ms, {
                "user_id": user_id,
                "session_id": session_id,
            })

            out = {
                "type": "local_reasoning",
                "reply": reply,
                "activation_key": result.get("meta", {}).get("activation_key"),
                "model": result.get("meta", {}).get("model"),
                "trace_id": str(uuid.uuid4()),
                "latency_ms": latency_ms,
            }

            if return_compressed:
                blob = self.compressor.compress(reply.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True

            return out

        # MEMORY WRITE
        if text:
            self.memory.remember(text)

        # MEMORY RECALL
        recalled = self.memory.recall(text, top_k=3)
        recalled_text = "\n".join(recalled)

        if recalled_text.strip():
            augmented_text = (
                "Relevant past context:\n" +
                recalled_text +
                "\n\nUser message:\n" +
                text
            )
        else:
            augmented_text = text

        helpers = {
            "math": {
                "detected": bool(
                    re.match(r"^[0-9\+\-\*/x\^=\(\)\s\.]+$", text.strip())
                )
            },
            "code": {
                "detected": (
                    "def " in text or
                    "class " in text or
                    "{" in text
                )
            },
            "logic": {
                "detected": any(
                    w in text.lower()
                    for w in ["if", "then", "therefore"]
                )
            },
            "physics": {
                "detected": any(
                    w in text.lower()
                    for w in ["force", "mass", "velocity"]
                )
            },
            "web": {
                "detected": "http" in text
            },
            "world": {
                "entities": []
            },
        }

        packet = Packet(
            text=augmented_text,
            query=text,
            data=data,
            metadata=metadata or {},
            intent=intent,
            helpers=helpers,
            compressed=compressed,
            return_compressed=return_compressed,
            user_id=user_id,
            session_id=session_id,
            trace_id=str(uuid.uuid4())
        )

        with self.profiler.section(f"router.intent.{intent}"):
            result = self.router.run(packet)

        if intent == "self_refine":
            original_output = result.get("output", "")
            refined = self.refiner.refine(text, original_output, passes=2)

            self.memory.remember(f"[refined] {refined}")

            out = {
                "type": "self_refine",
                "original": original_output,
                "refined": refined,
                "trace_id": packet.trace_id,
                "latency_ms": int((time.time() - start) * 1000)
            }

            if return_compressed:
                payload = str(refined)
                blob = self.compressor.compress(payload.encode("utf-8"))
                out["data"] = blob
                out["compressed"] = True

            return out

        latency_ms = int((time.time() - start) * 1000)
        result["trace_id"] = packet.trace_id
        result["latency_ms"] = latency_ms

        self.meta.record_call(intent, latency_ms, {
            "user_id": user_id,
            "session_id": session_id,
        })

        if return_compressed:
            primary = None
            for key in ("reply", "output", "text"):
                if key in result and isinstance(result[key], str):
                    primary = result[key]
                    break
            if primary is not None:
                blob = self.compressor.compress(primary.encode("utf-8"))
                result["data"] = blob
                result["compressed"] = True

        return result

    # ------------------------------------------------------------
    # 2D / 3D GENERATION APIS
    # ------------------------------------------------------------
    def generate_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for req in requests:
            out.append(self.generate(
                text=req.get("text", ""),
                data=req.get("data"),
                intent=req.get("intent", "small_reasoning"),
                compressed=req.get("compressed", False),
                return_compressed=req.get("return_compressed", False),
                metadata=req.get("metadata"),
                user_id=req.get("user_id"),
                session_id=req.get("session_id"),
            ))
        return out

    def generate_3d(
        self,
        requests_3d: List[List[List[Dict[str, Any]]]],
    ) -> List[List[List[Dict[str, Any]]]]:
        if not requests_3d:
            return []

        out: List[List[List[Dict[str, Any]]]] = []
        for plane in requests_3d:
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for req in row:
                    row_out.append(self.generate(
                        text=req.get("text", ""),
                        data=req.get("data"),
                        intent=req.get("intent", "small_reasoning"),
                        compressed=req.get("compressed", False),
                        return_compressed=req.get("return_compressed", False),
                        metadata=req.get("metadata"),
                        user_id=req.get("user_id"),
                        session_id=req.get("session_id"),
                    ))
                plane_out.append(row_out)
            out.append(plane_out)
        return out

    # ------------------------------------------------------------
    # 2D / 3D THINKING APIS
    # ------------------------------------------------------------
    def think_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.thinking.think_batch(requests, use_cache=True)

    def think_3d(
        self,
        requests_3d: List[List[List[Dict[str, Any]]]],
    ) -> List[List[List[Dict[str, Any]]]]:
        return self.thinking.think_3d(requests_3d, use_cache=True)

