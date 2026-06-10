from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
import time
import traceback
import re


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class WExt3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# WORLD EXTRACTOR — MAX EXTRACTION + 3D‑MAX
# ============================================================

class WorldExtractor:
    """
    Production-grade lightweight extractor (3D‑MAX Edition).

    Features:
        • multi-word entity extraction
        • simple relation extraction ("X is Y", "X uses Y", "X depends on Y")
        • structured envelopes
        • latency measurement
        • deterministic output
        • future-proof for LLM-based extraction
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self._last_3d: Optional[WExt3D] = None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def extract(self, text: str) -> Dict[str, Any]:
        start = time.time()

        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("input text is empty or invalid")

            cleaned = text.strip()

            # ENTITY EXTRACTION
            entities = self._extract_entities(cleaned)

            # RELATION EXTRACTION
            relations = self._extract_relations(cleaned)

            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = WExt3D(
                axis_x="extract",
                axis_y=[
                    f"text_len:{len(cleaned)}",
                    f"entities:{len(entities)}",
                    f"relations:{len(relations)}",
                ],
                axis_z={"latency_ms": latency},
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "text": text,
                "entities": entities,
                "relations": relations,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WExt3D(
                axis_x="extract",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "text": text,
                "entities": [],
                "relations": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # ENTITY EXTRACTION
    # ------------------------------------------------------------
    def _extract_entities(self, text: str) -> List[str]:
        """
        Extracts multi-word capitalized entities.
        Example: "New York City", "MetaModelRuntime", "World Graph Engine"
        """

        pattern = r"\b([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*)\b"
        matches = re.findall(pattern, text)

        seen = set()
        entities = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                entities.append(m)

        # 3D‑MAX telemetry
        self._last_3d = WExt3D(
            axis_x="_extract_entities",
            axis_y=[f"entities:{len(entities)}"],
            axis_z={"ok": True},
        )

        return entities

    # ------------------------------------------------------------
    # RELATION EXTRACTION
    # ------------------------------------------------------------
    def _extract_relations(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Extracts simple relations:
            X is Y
            X uses Y
            X depends on Y
        """

        relations: List[Tuple[str, str, str]] = []

        # X is Y
        is_matches = re.findall(
            r"(\b[A-Z][A-Za-z0-9_]*\b)\s+is\s+(\b[A-Z][A-Za-z0-9_]*\b)", text
        )
        for a, b in is_matches:
            relations.append((a, "is", b))

        # X uses Y
        uses_matches = re.findall(
            r"(\b[A-Z][A-Za-z0-9_]*\b)\s+uses\s+(\b[A-Z][A-Za-z0-9_]*\b)", text
        )
        for a, b in uses_matches:
            relations.append((a, "uses", b))

        # X depends on Y
        depends_matches = re.findall(
            r"(\b[A-Z][A-Za-z0-9_]*\b)\s+depends on\s+(\b[A-Z][A-Za-z0-9_]*\b)", text
        )
        for a, b in depends_matches:
            relations.append((a, "depends_on", b))

        # 3D‑MAX telemetry
        self._last_3d = WExt3D(
            axis_x="_extract_relations",
            axis_y=[f"relations:{len(relations)}"],
            axis_z={"ok": True},
        )

        return relations

