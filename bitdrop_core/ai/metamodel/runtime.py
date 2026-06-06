from typing import Dict, Any, Optional
import uuid
import time
import os

from .context.packet import Packet
from .router import Router
from ..conversation.manager import ConversationManager

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
from .librarian_orchestrator import LibrarianOrchestrator


# ⭐ Correct imports for your folder layout
from .helpers.web_search_helper import WebSearchHelper
from ...web.search_engine import WebSearchEngine

# ⭐ Self‑audit engine (V4)
from .self_audit_engine import SelfAuditEngineV4


class LibrarianOrchestrator:
    """
    Minimal orchestrator used by ConversationManager.
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.web_helper = WebSearchHelper(runtime.web_search_engine)

    def answer(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        runtime = self.runtime
        metadata = metadata or {}
        start = time.time()

        # MEMORY WRITE
        if text:
            runtime.memory.remember(text)

        # MEMORY READ
        recalled = runtime.memory.recall(text, top_k=3)
        recalled_text = "\n".join(recalled)

        # ⭐ Optional web search
        web_block = ""
        web_info = self.web_helper.process(
            query=text,
            lang_info={},
            memory_info={},
            top_k=5,
        )
        if web_info.get("detected") and web_info.get("results"):
            web_block = "\n\nWeb search results:\n" + self._format_web_results(web_info["results"])

        # Build augmented context
        context_parts = []
        if recalled_text.strip():
            context_parts.append("Relevant past context:\n" + recalled_text)
        if web_block.strip():
            context_parts.append(web_block)
        context_parts.append("User message:\n" + text)
        augmented_text = "\n\n".join(context_parts)

        # Build Packet
        packet = Packet(
            text=augmented_text,
            query=text,   # REQUIRED FOR SELF‑AUDIT + INTROSPECTION
            data=None,
            metadata=metadata,
            intent="small_reasoning",
            compressed=False,
            return_compressed=False,
            user_id=None,
            session_id=None,
            trace_id=str(uuid.uuid4())
        )


        # ROUTER (no diagnostics)
        result = runtime.router.run(packet)

        # Extract reply
        reply = result.get("output", "")
        if not isinstance(reply, str):
            reply = str(reply)

        # Meta stats
        latency_ms = int((time.time() - start) * 1000)
        runtime.meta.record_call("conversation_core", latency_ms, {
            "user_id": None,
            "session_id": None,
        })

        return reply

    def _format_web_results(self, results):
        lines = []
        for i, r in enumerate(results, 1):
            title = (r.get("title") or "").strip()
            snippet = (r.get("snippet") or "").strip()
            url = (r.get("url") or "").strip()
            block = f"{i}. {title}"
            if snippet:
                block += f"\n{snippet}"
            if url:
                block += f"\n{url}"
            lines.append(block)
        return "\n\n".join(lines)


class MetaModelRuntime:
    """
    BitDrop MetaModel Runtime — unified cognitive architecture.
    """

    def __init__(self):
        # Root dir for self‑audit (project root: two levels up from this file)
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        # ⭐ FIX APPLIED HERE — pass runtime into Router
        self.router = Router(self)

        self.conversation = ConversationManager(self)
        self.memory = MemoryManager()
        self.agent = Agent()
        self.planner = Planner()
        self.vision = VisionProcessor()
        self.refiner = Refiner()
        self.taskgraph_planner = TaskGraphPlanner()
        self.taskgraph_executor = TaskGraphExecutor(self)
        self.skills = SkillRunner(self)

        # Agents
        self.agents = {
            "planner": PlannerAgent(self),
            "executor": ExecutorAgent(self),
            "critic": CriticAgent(self),
            "memory": MemoryAgent(self),
            "vision": VisionAgent(self),
            "tool": ToolAgent(self),
        }

        # Subsystems
        self.goals = GoalManager(self)
        self.background = BackgroundLearner(self)
        self.healer = MemoryHealer(self)
        self.world = WorldModelManager(self)
        self.meta = MetaOptimizer(self)
        self.tool_learning = ToolLearningManager(self)
        self.simulation = SimulationManager(self)
        self.debate = DebateManager(self)
        self.strategy = StrategyManager(self)

        # ⭐ Correct web search wiring
        self.web_search_engine = WebSearchEngine()
        self.web_helper = WebSearchHelper(self.web_search_engine)

        # Orchestrator used by ConversationManager
        self.librarian_orchestrator = LibrarianOrchestrator(self)

        # ⭐ Self‑audit engine (V4) — full codebase introspection
        self.self_audit = SelfAuditEngineV4(root_path=self.root_dir)

    # -------------------------------------------------------------
    # PUBLIC SELF‑AUDIT API
    # -------------------------------------------------------------
    def audit(self, *, mode: str = "full") -> Dict[str, Any]:
        """
        Run self‑audit over the codebase.

        mode:
            "full"  -> full report
            "light" -> summary only (no per‑file details)
        """
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

    # -------------------------------------------------------------
    # MAIN EXECUTION ENTRYPOINT
    # -------------------------------------------------------------
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

        # =========================================================
        # SELF‑AUDIT MODE (developer‑facing)
        # =========================================================
        if intent == "self_audit":
            mode = metadata.get("mode", "full")
            report = self.audit(mode=mode)
            return {
                "type": "self_audit",
                "mode": mode,
                "report": report,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000),
            }

        # =========================================================
        # GOAL MODE
        # =========================================================
        if intent == "goal":
            if not metadata or "action" not in metadata:
                return {"error": "goal intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "create":
                goal = self.goals.create(text, metadata.get("metadata"))
                return {
                    "type": "goal",
                    "action": "create",
                    "goal_id": goal.id,
                    "text": goal.text,
                    "status": goal.status,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "resume":
                goal_id = metadata.get("goal_id")
                result = self.goals.resume(goal_id)
                return {
                    "type": "goal",
                    "action": "resume",
                    "goal_id": goal_id,
                    "result": result,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "list":
                goals = [
                    {"id": g.id, "text": g.text, "status": g.status, "progress": g.progress}
                    for g in self.goals.list()
                ]
                return {
                    "type": "goal",
                    "action": "list",
                    "goals": goals,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown goal action: {action}"}

        # (rest of file unchanged)


        # =========================================================
        # STRATEGIC PLANNER MODE
        # =========================================================
        if intent == "strategy":
            if not metadata or "action" not in metadata:
                return {"error": "strategy intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "plan_for_text":
                goal_text = text
                strat = self.strategy.plan_for_goal(goal_text)
                self.memory.remember(f"[strategy-text] {strat}")
                return {
                    "type": "strategy",
                    "action": "plan_for_text",
                    "strategy": strat,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "plan_for_goal":
                goal_id = metadata.get("goal_id", "")
                strat = self.strategy.plan_for_existing_goal(goal_id)
                self.memory.remember(f"[strategy-goal] {strat}")
                return {
                    "type": "strategy",
                    "action": "plan_for_goal",
                    "strategy": strat,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown strategy action: {action}"}

        # =========================================================
        # AGENT MODE
        # =========================================================
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

            return {
                "type": "agent",
                "agent": agent_name,
                "result": result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # BACKGROUND LEARNING MODE
        # =========================================================
        if intent == "background":
            insights = self.background.run()
            self.memory.remember(f"[background-learning] {insights}")
            return {
                "type": "background",
                "insights": insights,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # MEMORY HEALING MODE
        # =========================================================
        if intent == "heal_memory":
            issues = self.healer.run()
            self.memory.remember(f"[memory-heal] {issues}")
            return {
                "type": "memory_heal",
                "issues": issues,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # WORLD MODEL MODE
        # =========================================================
        if intent == "world_model":
            if not metadata or "action" not in metadata:
                return {"error": "world_model intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "ingest":
                extracted = self.world.ingest(text)
                self.memory.remember(f"[world-ingest] {text} -> {extracted}")
                return {
                    "type": "world_model",
                    "action": "ingest",
                    "extracted": extracted,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "query":
                label = metadata.get("label", "")
                relations = self.world.query(label)
                return {
                    "type": "world_model",
                    "action": "query",
                    "label": label,
                    "relations": relations,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "snapshot":
                snap = self.world.snapshot()
                return {
                    "type": "world_model",
                    "action": "snapshot",
                    "graph": snap,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "simulate_changes":
                changes = metadata.get("changes", [])
                sim = self.world.sim.simulate_changes(changes)
                self.memory.remember(f"[world-sim-changes] {sim}")
                return {
                    "type": "world_model",
                    "action": "simulate_changes",
                    "result": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "simulate_propagation":
                root = metadata.get("root", "")
                sim = self.world.sim.simulate_propagation(root)
                self.memory.remember(f"[world-sim-propagation] {sim}")
                return {
                    "type": "world_model",
                    "action": "simulate_propagation",
                    "result": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown world_model action: {action}"}

from typing import Dict, Any, Optional
import uuid
import time
import os

from .context.packet import Packet
from .router import Router
from ..conversation.manager import ConversationManager

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

# ⭐ Correct imports for your folder layout
from .helpers.web_search_helper import WebSearchHelper
from ...web.search_engine import WebSearchEngine

# ⭐ Self‑audit engine (V4)
from .self_audit_engine import SelfAuditEngineV4


class LibrarianOrchestrator:
    """
    Minimal orchestrator used by ConversationManager.
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.web_helper = WebSearchHelper(runtime.web_search_engine)

    def answer(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        runtime = self.runtime
        metadata = metadata or {}
        start = time.time()

        # MEMORY WRITE
        if text:
            runtime.memory.remember(text)

        # MEMORY READ
        recalled = runtime.memory.recall(text, top_k=3)
        recalled_text = "\n".join(recalled)

        # ⭐ Optional web search
        web_block = ""
        web_info = self.web_helper.process(
            query=text,
            lang_info={},
            memory_info={},
            top_k=5,
        )
        if web_info.get("detected") and web_info.get("results"):
            web_block = "\n\nWeb search results:\n" + self._format_web_results(web_info["results"])

        # Build augmented context
        context_parts = []
        if recalled_text.strip():
            context_parts.append("Relevant past context:\n" + recalled_text)
        if web_block.strip():
            context_parts.append(web_block)
        context_parts.append("User message:\n" + text)
        augmented_text = "\n\n".join(context_parts)

        # Build Packet
        packet = Packet(
            text=augmented_text,
            query=text,
            data=None,
            metadata=metadata,
            intent="small_reasoning",
            compressed=False,
            return_compressed=False,
            user_id=None,
            session_id=None,
            trace_id=str(uuid.uuid4())
        )

        # ROUTER (no diagnostics)
        result = runtime.router.run(packet)

        # Extract reply
        reply = result.get("output", "")
        if not isinstance(reply, str):
            reply = str(reply)

        # Meta stats
        latency_ms = int((time.time() - start) * 1000)
        runtime.meta.record_call("conversation_core", latency_ms, {
            "user_id": None,
            "session_id": None,
        })

        return reply

    def _format_web_results(self, results):
        lines = []
        for i, r in enumerate(results, 1):
            title = (r.get("title") or "").strip()
            snippet = (r.get("snippet") or "").strip()
            url = (r.get("url") or "").strip()
            block = f"{i}. {title}"
            if snippet:
                block += f"\n{snippet}"
            if url:
                block += f"\n{url}"
            lines.append(block)
        return "\n\n".join(lines)


class MetaModelRuntime:
    """
    BitDrop MetaModel Runtime — unified cognitive architecture.
    """

    def __init__(self):
        # Root dir for self‑audit (project root: two levels up from this file)
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        # ⭐ Router wired with runtime
        self.router = Router(self)

        self.conversation = ConversationManager(self)
        self.memory = MemoryManager()
        self.agent = Agent()
        self.planner = Planner()
        self.vision = VisionProcessor()
        self.refiner = Refiner()
        self.taskgraph_planner = TaskGraphPlanner()
        self.taskgraph_executor = TaskGraphExecutor(self)
        self.skills = SkillRunner(self)

        # Agents
        self.agents = {
            "planner": PlannerAgent(self),
            "executor": ExecutorAgent(self),
            "critic": CriticAgent(self),
            "memory": MemoryAgent(self),
            "vision": VisionAgent(self),
            "tool": ToolAgent(self),
        }

        # Subsystems
        self.goals = GoalManager(self)
        self.background = BackgroundLearner(self)
        self.healer = MemoryHealer(self)
        self.world = WorldModelManager(self)
        self.meta = MetaOptimizer(self)
        self.tool_learning = ToolLearningManager(self)
        self.simulation = SimulationManager(self)
        self.debate = DebateManager(self)
        self.strategy = StrategyManager(self)

        # ⭐ Correct web search wiring
        self.web_search_engine = WebSearchEngine()
        self.web_helper = WebSearchHelper(self.web_search_engine)

        # Orchestrator used by ConversationManager
        self.librarian_orchestrator = LibrarianOrchestrator(self)

        # ⭐ Self‑audit engine (V4) — full codebase introspection
        self.self_audit = SelfAuditEngineV4(root_path=self.root_dir)

    # -------------------------------------------------------------
    # PUBLIC SELF‑AUDIT API
    # -------------------------------------------------------------
    def audit(self, *, mode: str = "full") -> Dict[str, Any]:
        """
        Run self‑audit over the codebase.

        mode:
            "full"  -> full report
            "light" -> summary only (no per‑file details)
        """
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

    # -------------------------------------------------------------
    # MAIN EXECUTION ENTRYPOINT
    # -------------------------------------------------------------
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

        # =========================================================
        # SELF‑AUDIT MODE (developer‑facing)
        # =========================================================
        if intent == "self_audit":
            mode = metadata.get("mode", "full")
            report = self.audit(mode=mode)
            return {
                "type": "self_audit",
                "mode": mode,
                "report": report,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000),
            }

        # =========================================================
        # GOAL MODE
        # =========================================================
        if intent == "goal":
            if not metadata or "action" not in metadata:
                return {"error": "goal intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "create":
                goal = self.goals.create(text, metadata.get("metadata"))
                return {
                    "type": "goal",
                    "action": "create",
                    "goal_id": goal.id,
                    "text": goal.text,
                    "status": goal.status,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "resume":
                goal_id = metadata.get("goal_id")
                result = self.goals.resume(goal_id)
                return {
                    "type": "goal",
                    "action": "resume",
                    "goal_id": goal_id,
                    "result": result,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "list":
                goals = [
                    {"id": g.id, "text": g.text, "status": g.status, "progress": g.progress}
                    for g in self.goals.list()
                ]
                return {
                    "type": "goal",
                    "action": "list",
                    "goals": goals,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown goal action: {action}"}

        # =========================================================
        # STRATEGIC PLANNER MODE
        # =========================================================
        if intent == "strategy":
            if not metadata or "action" not in metadata:
                return {"error": "strategy intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "plan_for_text":
                goal_text = text
                strat = self.strategy.plan_for_goal(goal_text)
                self.memory.remember(f"[strategy-text] {strat}")
                return {
                    "type": "strategy",
                    "action": "plan_for_text",
                    "strategy": strat,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "plan_for_goal":
                goal_id = metadata.get("goal_id", "")
                strat = self.strategy.plan_for_existing_goal(goal_id)
                self.memory.remember(f"[strategy-goal] {strat}")
                return {
                    "type": "strategy",
                    "action": "plan_for_goal",
                    "strategy": strat,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown strategy action: {action}"}

        # =========================================================
        # AGENT MODE
        # =========================================================
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

            return {
                "type": "agent",
                "agent": agent_name,
                "result": result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # BACKGROUND LEARNING MODE
        # =========================================================
        if intent == "background":
            insights = self.background.run()
            self.memory.remember(f"[background-learning] {insights}")
            return {
                "type": "background",
                "insights": insights,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # MEMORY HEALING MODE
        # =========================================================
        if intent == "heal_memory":
            issues = self.healer.run()
            self.memory.remember(f"[memory-heal] {issues}")
            return {
                "type": "memory_heal",
                "issues": issues,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # WORLD MODEL MODE
        # =========================================================
        if intent == "world_model":
            if not metadata or "action" not in metadata:
                return {"error": "world_model intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "ingest":
                extracted = self.world.ingest(text)
                self.memory.remember(f"[world-ingest] {text} -> {extracted}")
                return {
                    "type": "world_model",
                    "action": "ingest",
                    "extracted": extracted,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "query":
                label = metadata.get("label", "")
                relations = self.world.query(label)
                return {
                    "type": "world_model",
                    "action": "query",
                    "label": label,
                    "relations": relations,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "snapshot":
                snap = self.world.snapshot()
                return {
                    "type": "world_model",
                    "action": "snapshot",
                    "graph": snap,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "simulate_changes":
                changes = metadata.get("changes", [])
                sim = self.world.sim.simulate_changes(changes)
                self.memory.remember(f"[world-sim-changes] {sim}")
                return {
                    "type": "world_model",
                    "action": "simulate_changes",
                    "result": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "simulate_propagation":
                root = metadata.get("root", "")
                sim = self.world.sim.simulate_propagation(root)
                self.memory.remember(f"[world-sim-propagation] {sim}")
                return {
                    "type": "world_model",
                    "action": "simulate_propagation",
                    "result": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown world_model action: {action}"}

        # =========================================================
        # SKILL EVOLUTION MODE
        # =========================================================
        if intent == "skill_evolve":
            if not metadata or "action" not in metadata:
                return {"error": "skill_evolve intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "mutate":
                skill_name = metadata.get("skill")
                info = self.skills.evolve(skill_name)
                self.memory.remember(f"[skill-mutate] {info}")
                return {
                    "type": "skill_evolve",
                    "action": "mutate",
                    "info": info,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "metrics":
                snap = self.skills.metrics_snapshot()
                return {
                    "type": "skill_evolve",
                    "action": "metrics",
                    "metrics": snap,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "variants":
                snap = self.skills.evolution_snapshot()
                return {
                    "type": "skill_evolve",
                    "action": "variants",
                    "variants": snap,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown skill_evolve action: {action}"}

        # =========================================================
        # TOOL LEARNING MODE
        # =========================================================
        if intent == "tool_learning":
            if not metadata or "action" not in metadata:
                return {"error": "tool_learning intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "learn":
                created = self.tool_learning.learn()
                self.memory.remember(f"[tool-learn] {created}")
                return {
                    "type": "tool_learning",
                    "action": "learn",
                    "created": created,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "list":
                tools = self.tool_learning.list()
                return {
                    "type": "tool_learning",
                    "action": "list",
                    "tools": tools,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown tool_learning action: {action}"}

        # =========================================================
        # META OPTIMIZER MODE
        # =========================================================
        if intent == "meta":
            suggestions = self.meta.suggest()
            return {
                "type": "meta",
                "suggestions": suggestions,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # SIMULATION MODE
        # =========================================================
        if intent == "simulation":
            if not metadata or "action" not in metadata:
                return {"error": "simulation intent requires metadata.action", "trace_id": str(uuid.uuid4())}

            action = metadata["action"]

            if action == "plan":
                steps = metadata.get("steps", [])
                sim = self.simulation.simulate_plan(steps)
                self.memory.remember(f"[simulation-plan] {sim}")
                return {
                    "type": "simulation",
                    "action": "plan",
                    "simulation": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            if action == "counterfactual":
                base = metadata.get("base", "")
                variation = metadata.get("variation", "")
                sim = self.simulation.simulate_counterfactual(base, variation)
                self.memory.remember(f"[simulation-counterfactual] {sim}")
                return {
                    "type": "simulation",
                    "action": "counterfactual",
                    "simulation": sim,
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": int((time.time() - start) * 1000)
                }

            return {"error": f"unknown simulation action: {action}"}

        # =========================================================
        # DEBATE MODE
        # =========================================================
        if intent == "debate":
            question = text
            debate_result = self.debate.run_debate(question)
            self.memory.remember(f"[debate] {debate_result}")
            return {
                "type": "debate",
                "question": question,
                "debate": debate_result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # TOOL MODE
        # =========================================================
        if intent == "tool":
            command = self.planner.plan(text)
            tool_result = self.agent.run(command)
            self.memory.remember(f"TOOL COMMAND: {command}")
            self.memory.remember(f"TOOL RESULT: {tool_result}")
            return {
                "type": "tool",
                "command": command,
                "result": tool_result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # VISION MODE
        # =========================================================
        if intent == "vision":
            if data is None:
                return {"error": "vision intent requires image bytes", "trace_id": str(uuid.uuid4())}

            if metadata and "question" in metadata:
                output = self.vision.ask(metadata["question"], data)
            else:
                output = self.vision.describe(data)

            self.memory.remember(f"[vision] {output}")

            return {
                "type": "vision",
                "output": output,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # TASKGRAPH MODE
        # =========================================================
        if intent == "taskgraph":
            graph = self.taskgraph_planner.plan(text)
            tg_result = self.taskgraph_executor.run(graph)
            self.memory.remember(f"[taskgraph-goal] {text}")
            self.memory.remember(f"[taskgraph-final] {tg_result.get('final', '')}")
            return {
                "type": "taskgraph",
                "goal": tg_result["goal"],
                "final": tg_result["final"],
                "nodes": tg_result["nodes"],
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # SKILL MODE
        # =========================================================
        if intent == "skill":
            if not metadata or "skill" not in metadata:
                return {"error": "skill intent requires metadata.skill", "trace_id": str(uuid.uuid4())}

            skill_name = metadata["skill"]
            params = metadata.get("params", {})
            result = self.skills.run(skill_name, params)

            self.memory.remember(f"[skill] {skill_name}({params}) -> {result}")

            return {
                "type": "skill",
                "skill": skill_name,
                "result": result,
                "trace_id": str(uuid.uuid4()),
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # CONVERSATION MODE (FIXED — NO RECURSION)
        # =========================================================
        if intent == "conversation":
            packet = Packet(
                text=text,
                query=text,
                data=data,
                metadata=metadata,
                intent="conversation",
                compressed=compressed,
                return_compressed=return_compressed,
                user_id=user_id,
                session_id=session_id,
                trace_id=str(uuid.uuid4())
            )

            # Route directly through Router (NO ConversationManager recursion)
            result = self.router.run(packet)

            reply = result.get("output", "")
            if not isinstance(reply, str):
                reply = str(reply)

            self.memory.remember(f"[conversation:user] {text}")
            self.memory.remember(f"[conversation:ai] {reply}")

            return {
                "type": "conversation",
                "reply": reply,
                "trace_id": packet.trace_id,
                "latency_ms": int((time.time() - start) * 1000)
            }


        # =========================================================
        # MEMORY WRITE
        # =========================================================
        if text:
            self.memory.remember(text)

        # =========================================================
        # MEMORY RECALL (strict M2: recall returns list[str])
        # =========================================================
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

        # =========================================================
        # Build Packet
        # =========================================================
        packet = Packet(
            text=augmented_text,
            query=text,
            data=data,
            metadata=metadata or {},
            intent=intent,
            compressed=compressed,
            return_compressed=return_compressed,
            user_id=user_id,
            session_id=session_id,
            trace_id=str(uuid.uuid4())
        )

        # =========================================================
        # Route through the system
        # =========================================================
        result = self.router.run(packet)

        # =========================================================
        # SELF-REFINE MODE
        # =========================================================
        if intent == "self_refine":
            original_output = result.get("output", "")
            refined = self.refiner.refine(text, original_output, passes=2)

            self.memory.remember(f"[refined] {refined}")

            return {
                "type": "self_refine",
                "original": original_output,
                "refined": refined,
                "trace_id": packet.trace_id,
                "latency_ms": int((time.time() - start) * 1000)
            }

        # =========================================================
        # Attach system metadata
        # =========================================================
        latency_ms = int((time.time() - start) * 1000)
        result["trace_id"] = packet.trace_id
        result["latency_ms"] = latency_ms

        # =========================================================
        # META OPTIMIZER RECORDING
        # =========================================================
        self.meta.record_call(intent, latency_ms, {
            "user_id": user_id,
            "session_id": session_id,
        })

        return result
