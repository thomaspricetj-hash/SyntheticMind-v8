from __future__ import annotations
from typing import Dict, Any, List, Tuple
import time
import traceback
import re


class WorldExtractor:
    """
    Production-grade lightweight extractor.

    Features:
        • multi-word entity extraction
        • simple relation extraction ("X is Y", "X uses Y", "X depends on Y")
        • structured envelopes
        • latency measurement
        • deterministic output
        • future-proof for LLM-based extraction
    """

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def extract(self, text: str) -> Dict[str, Any]:
        start = time.time()

        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("input text is empty or invalid")

            cleaned = text.strip()

            # ----------------------------------------------------
            # ENTITY EXTRACTION (multi-word)
            # ----------------------------------------------------
            entities = self._extract_entities(cleaned)

            # ----------------------------------------------------
            # RELATION EXTRACTION (simple patterns)
            # ----------------------------------------------------
            relations = self._extract_relations(cleaned)

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "text": text,
                "entities": entities,
                "relations": relations,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
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

        # Capture sequences of capitalized words
        pattern = r"\b([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*)\b"
        matches = re.findall(pattern, text)

        # Deduplicate while preserving order
        seen = set()
        entities = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                entities.append(m)

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

        relations = []

        # Pattern: X is Y
        is_matches = re.findall(r"(\b[A-Z][A-Za-z0-9_]*\b)\s+is\s+(\b[A-Z][A-Za-z0-9_]*\b)", text)
        for a, b in is_matches:
            relations.append((a, "is", b))

        # Pattern: X uses Y
        uses_matches = re.findall(r"(\b[A-Z][A-Za-z0-9_]*\b)\s+uses\s+(\b[A-Z][A-Za-z0-9_]*\b)", text)
        for a, b in uses_matches:
            relations.append((a, "uses", b))

        # Pattern: X depends on Y
        depends_matches = re.findall(
            r"(\b[A-Z][A-Za-z0-9_]*\b)\s+depends on\s+(\b[A-Z][A-Za-z0-9_]*\b)", text
        )
        for a, b in depends_matches:
            relations.append((a, "depends_on", b))

        return relations
