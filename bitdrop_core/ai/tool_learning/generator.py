# syntheticmind/tools/tool_generator.py

from __future__ import annotations
from typing import Dict, Any, List
import keyword
import traceback


class ToolGenerator:
    """
    Generates Python tool wrappers from inferred signatures.
    Produces:
        • deterministic, clean Python code
        • validated identifiers
        • structured envelopes
        • docstrings
        • type hints
    """

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------
    def _validate_name(self, name: str):
        if not name.isidentifier() or keyword.iskeyword(name):
            raise ValueError(f"Invalid tool name: {name}")

    def _validate_params(self, params: List[str]):
        for p in params:
            if not p.isidentifier() or keyword.iskeyword(p):
                raise ValueError(f"Invalid parameter name: {p}")

    # ------------------------------------------------------------
    # MAIN GENERATION ENTRYPOINT
    # ------------------------------------------------------------
    def generate(self, signature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "code": str,
                "error": None
            }
        """

        try:
            name = signature["name"]
            params = signature.get("params", [])

            self._validate_name(name)
            self._validate_params(params)

            # Build parameter list
            param_list = ", ".join(params)

            # Build dict literal
            param_dict = ", ".join([f"'{p}': {p}" for p in params])

            # Deterministic, clean code
            code = (
                f"def {name}({param_list}) -> dict:\n"
                f"    \"\"\"\n"
                f"    Auto-generated tool wrapper.\n"
                f"    Signature: {name}({', '.join(params)})\n"
                f"    \"\"\"\n"
                f"    return {{\n"
                f"        'tool': '{name}',\n"
                f"        'params': {{{param_dict}}}\n"
                f"    }}\n"
            )

            return {
                "ok": True,
                "code": code,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "code": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

