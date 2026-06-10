# ai/tool_learning/manager.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from .observer import ToolPatternObserver
from .infer import ToolSignatureInferer
from .generator import ToolGenerator
from .tester import ToolTester


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class ToolLearn3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TOOL LEARNING MANAGER — MAX LEARNING + 3D‑MAX
# ============================================================

class ToolLearningManager:
    """
    Central coordinator for the tool‑learning pipeline (3D‑MAX Edition).

    Responsibilities:
      • Observe tool usage patterns
      • Infer candidate tool signatures
      • Generate tool implementations
      • Test generated tools safely
      • Register validated tools into the runtime
      • Provide 3D‑MAX telemetry for every phase
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

        # Subsystems
        self.observer = ToolPatternObserver(runtime)
        self.inferer = ToolSignatureInferer()
        self.generator = ToolGenerator()
        self.tester = ToolTester()

        # Persisted learned tools: {tool_name: code_str}
        self.learned_tools: dict[str, str] = {}

        # 3D‑MAX telemetry
        self._last_3d: Optional[ToolLearn3D] = None

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def learn(self) -> list[dict]:
        """
        Executes the full learning cycle:
          1. Observe patterns
          2. Infer signatures
          3. Generate code
          4. Test code
          5. Register tool

        Returns a list of successfully created tool signatures.
        """

        # ------------------------------------------------------------
        # 1. Observe usage patterns
        # ------------------------------------------------------------
        patterns = self.observer.scan()

        self._last_3d = ToolLearn3D(
            axis_x="learn.observe",
            axis_y=[f"patterns:{len(patterns)}"],
            axis_z={"ok": True},
        )

        if not patterns:
            return []

        # ------------------------------------------------------------
        # 2. Infer tool signatures
        # ------------------------------------------------------------
        sig_env = self.inferer.infer(patterns)
        if not sig_env.get("ok"):
            self._last_3d = ToolLearn3D(
                axis_x="learn.infer",
                axis_y=["infer_failed"],
                axis_z={"error": sig_env.get("error")},
            )
            return []

        signatures = sig_env.get("signatures", [])
        if not signatures:
            return []

        self._last_3d = ToolLearn3D(
            axis_x="learn.infer",
            axis_y=[f"signatures:{len(signatures)}"],
            axis_z={"ok": True},
        )

        created = []

        # ------------------------------------------------------------
        # 3–5. Generate → Test → Register
        # ------------------------------------------------------------
        for sig in signatures:
            name = sig.get("name")
            if not name:
                continue

            # Skip if already learned
            if name in self.learned_tools:
                continue

            # -------------------------
            # 3. Generate code
            # -------------------------
            try:
                code_env = self.generator.generate(sig)
                if not code_env.get("ok"):
                    raise ValueError(code_env.get("error"))
                code = code_env["code"]
            except Exception as e:
                self._log(f"[ToolLearning] Code generation failed for {name}: {e}")
                self._last_3d = ToolLearn3D(
                    axis_x="learn.generate",
                    axis_y=[f"name:{name}"],
                    axis_z={"error": str(e)},
                )
                continue

            # -------------------------
            # 4. Test code
            # -------------------------
            try:
                ok = self.tester.test(code)
            except Exception as e:
                ok = False
                self._log(f"[ToolLearning] Test crashed for {name}: {e}")

            if not ok:
                self._log(f"[ToolLearning] Tool rejected: {name}")
                self._last_3d = ToolLearn3D(
                    axis_x="learn.test",
                    axis_y=[f"name:{name}"],
                    axis_z={"ok": False},
                )
                continue

            # -------------------------
            # 5. Register tool
            # -------------------------
            try:
                self.runtime.agent.register_dynamic_tool(name, code)
            except Exception as e:
                self._log(f"[ToolLearning] Registration failed for {name}: {e}")
                self._last_3d = ToolLearn3D(
                    axis_x="learn.register",
                    axis_y=[f"name:{name}"],
                    axis_z={"error": str(e)},
                )
                continue

            # Success
            self.learned_tools[name] = code
            created.append(sig)

            self._last_3d = ToolLearn3D(
                axis_x="learn.success",
                axis_y=[f"name:{name}"],
                axis_z={"ok": True},
            )

            self._log(f"[ToolLearning] Tool learned: {name}")

        return created

    def list(self) -> dict[str, str]:
        """Returns all learned tools."""
        self._last_3d = ToolLearn3D(
            axis_x="list",
            axis_y=[f"count:{len(self.learned_tools)}"],
            axis_z={"ok": True},
        )
        return dict(self.learned_tools)

    # ------------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        """Runtime‑safe logging hook."""
        try:
            self.runtime.log(msg)
        except Exception:
            print(msg)


