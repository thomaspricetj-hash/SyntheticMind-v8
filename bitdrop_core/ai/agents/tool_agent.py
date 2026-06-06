# ai/agents/tool_agent.py

from __future__ import annotations
from .base import Agent


class ToolAgent(Agent):
    """
    Executes tool commands safely through the runtime's tool orchestrator.
    """

    name = "tool"
    description = "Runs tool commands safely."
    capabilities = {
        "tool_execution": True,
        "safe_sandbox": True,
        "structured_commands": True,
    }

    # ------------------------------------------------------------
    # INTERNAL EXECUTION
    # ------------------------------------------------------------
    def _run(self, command: str, **kwargs):
        """
        Core tool execution logic.
        This method is wrapped by Agent.run() for:
            • tracing
            • timing
            • error handling
            • pre/post hooks

        Expected command format:
            "tool_name {json_args}"
        or:
            {"tool": "name", "args": {...}}
        """

        orchestrator = getattr(self.runtime, "tool_orchestrator", None)
        if orchestrator is None or not hasattr(orchestrator, "execute"):
            return {
                "error": "Tool orchestrator unavailable",
                "command": command,
            }

        # Parse command
        parsed = self._parse_command(command)
        if "error" in parsed:
            return parsed

        tool_name = parsed["tool"]
        args = parsed["args"]

        # Execute tool
        try:
            result = orchestrator.execute(tool_name, args)
        except Exception as e:
            return {
                "error": f"Tool execution failed: {e}",
                "tool": tool_name,
                "args": args,
            }

        return {
            "tool": tool_name,
            "args": args,
            "result": result,
        }

    # ------------------------------------------------------------
    # COMMAND PARSER
    # ------------------------------------------------------------
    def _parse_command(self, command: str):
        """
        Accepts:
            • raw string: "search {\"query\": \"hello\"}"
            • dict: {"tool": "search", "args": {...}}
        """

        # Dict format
        if isinstance(command, dict):
            tool = command.get("tool")
            args = command.get("args", {})
            if not tool:
                return {"error": "Missing 'tool' in command dict"}
            return {"tool": tool, "args": args}

        # String format
        if isinstance(command, str):
            parts = command.strip().split(" ", 1)
            tool = parts[0]
            if len(parts) == 1:
                return {"tool": tool, "args": {}}

            import json
            try:
                args = json.loads(parts[1])
            except Exception:
                return {"error": f"Invalid JSON args in command: {command}"}

            return {"tool": tool, "args": args}

        return {"error": f"Unsupported command type: {type(command)}"}

    # ------------------------------------------------------------
    # OPTIONAL HOOKS
    # ------------------------------------------------------------
    def _pre_run(self, args, kwargs):
        # Could log tool usage intent
        pass

    def _post_run(self, result, success: bool):
        # Log tool usage into episodic memory
        if success and isinstance(result, dict) and "tool" in result:
            self.runtime.memory.remember(
                f"[tool-agent] executed tool '{result['tool']}'"
            )

