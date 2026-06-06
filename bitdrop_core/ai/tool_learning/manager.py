# ai/tool_learning/manager.py

from __future__ import annotations

from .observer import ToolPatternObserver
from .infer import ToolSignatureInferer
from .generator import ToolGenerator
from .tester import ToolTester


class ToolLearningManager:
    """
    Central coordinator for the tool‑learning pipeline.

    Responsibilities:
      • Observe tool usage patterns
      • Infer candidate tool signatures
      • Generate tool implementations
      • Test generated tools safely
      • Register validated tools into the runtime
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

        # 1. Gather usage patterns
        patterns = self.observer.scan()
        if not patterns:
            return []

        # 2. Infer tool signatures
        signatures = self.inferer.infer(patterns)
        if not signatures:
            return []

        created = []

        for sig in signatures:
            name = sig.get("name")
            if not name:
                continue

            # Skip if already learned
            if name in self.learned_tools:
                continue

            # 3. Generate code
            try:
                code = self.generator.generate(sig)
            except Exception as e:
                self._log(f"[ToolLearning] Code generation failed for {name}: {e}")
                continue

            # 4. Test code
            try:
                ok = self.tester.test(code)
            except Exception as e:
                self._log(f"[ToolLearning] Test crashed for {name}: {e}")
                ok = False

            if not ok:
                self._log(f"[ToolLearning] Tool rejected: {name}")
                continue

            # 5. Register tool into runtime
            try:
                self.runtime.agent.register_dynamic_tool(name, code)
            except Exception as e:
                self._log(f"[ToolLearning] Registration failed for {name}: {e}")
                continue

            # Success
            self.learned_tools[name] = code
            created.append(sig)
            self._log(f"[ToolLearning] Tool learned: {name}")

        return created

    def list(self) -> dict[str, str]:
        """Returns all learned tools."""
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

