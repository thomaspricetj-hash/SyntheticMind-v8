# syntheticmind/tools/tool_generator.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import keyword
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class ToolGen3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TOOL GENERATOR — MAX CODEGEN + 3D‑MAX
# ============================================================

class ToolGenerator:
    """
    Generates Python tool wrappers from inferred signatures (3D‑MAX Edition).
    Produces:
        • deterministic, clean Python code
        • validated identifiers
        • structured envelopes
        • docstrings
        • type hints
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self._last_3d: Optional[ToolGen3D] = None

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

            # Validation
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

            # 3D‑MAX telemetry
            self._last_3d = ToolGen3D(
                axis_x="generate",
                axis_y=[f"name:{name}", f"params:{len(params)}"],
                axis_z={
                    "ok": True,
                    "code_len": len(code),
                },
            )

            return {
                "ok": True,
                "code": code,
                "error": None,
            }

        except Exception as e:
            self._last_3d = ToolGen3D(
                axis_x="generate",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )

            return {
                "ok": False,
                "code": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


