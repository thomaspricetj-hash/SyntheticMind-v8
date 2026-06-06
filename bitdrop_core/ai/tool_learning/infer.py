# syntheticmind/tools/tool_signature_inferer.py

from __future__ import annotations
from typing import Dict, Any, List
import re
import traceback


class ToolSignatureInferer:
    """
    Infers tool signatures from repeated call patterns.

    Supports:
        • keyword arguments
        • positional arguments
        • whitespace tolerance
        • malformed pattern safety
        • structured envelopes
    """

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def infer(self, patterns: List[str]) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "signatures": [...],
                "error": None
            }
        """

        signatures = []

        try:
            for p in patterns:
                sig = self._infer_single(p)
                if sig:
                    signatures.append(sig)

            return {
                "ok": True,
                "signatures": signatures,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "signatures": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # INTERNAL: PARSE A SINGLE PATTERN
    # ------------------------------------------------------------
    def _infer_single(self, pattern: str) -> Dict[str, Any] | None:
        """
        Extracts:
            • name
            • params (keyword + positional)
        """

        # Match: name(arg1=..., arg2=..., ...)
        match = re.match(r"\s*([A-Za-z_]\w*)\s*\((.*)\)\s*", pattern)
        if not match:
            return None

        name = match.group(1)
        raw_params = match.group(2).strip()

        if not raw_params:
            return {"name": name, "params": []}

        params = []
        parts = [p.strip() for p in raw_params.split(",") if p.strip()]

        for part in parts:
            # keyword argument: key=value
            if "=" in part:
                key = part.split("=", 1)[0].strip()
                if key:
                    params.append(key)
            else:
                # positional argument: treat as param name
                # e.g. foo(x, y=1) → params: ["x", "y"]
                cleaned = re.sub(r"[^A-Za-z0-9_]", "", part)
                if cleaned:
                    params.append(cleaned)

        return {
            "name": name,
            "params": params,
        }
