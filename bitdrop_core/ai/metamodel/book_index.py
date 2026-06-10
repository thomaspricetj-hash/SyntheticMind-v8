# bitdrop_core/ai/metamodel/book_index.py

"""
Book-style index of all models in the system.
Each entry is a "page" in the book with chapter, role, and description.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import zlib


MODEL_BOOK: List[Dict[str, Any]] = [
    {
        "name": "phi3:mini",
        "role": "narrator",
        "chapter": "talk",
        "intent": "talk",
        "summary": "Fast conversational model used as the primary voice.",
        "description": "Handles small talk, narration, light reasoning, and stitching other models' outputs together.",
    },
    {
        "name": "qwen2.5:1.5b",
        "role": "light_reasoning",
        "chapter": "light_reasoning",
        "intent": "light_reasoning",
        "summary": "Lightweight reasoning model.",
        "description": "Used for slightly more complex tasks than phi3, but still fast and efficient.",
    },
    {
        "name": "llama3.1:8b",
        "role": "general_reasoning",
        "chapter": "general_reasoning",
        "intent": "general_reasoning",
        "summary": "General-purpose reasoning model.",
        "description": "Handles medium-length, multi-step reasoning and explanation tasks.",
    },
    {
        "name": "qwen2.5:7b",
        "role": "deep_reasoning",
        "chapter": "deep_reasoning",
        "intent": "deep_reasoning",
        "summary": "Deep reasoning and escalation model.",
        "description": "Used when tasks are long, complex, or escalated from smaller models.",
    },
    {
        "name": "deepseek-coder:6.7b",
        "role": "code",
        "chapter": "code_reasoning",
        "intent": "code_reasoning",
        "summary": "Code-focused model.",
        "description": "Handles code generation, debugging, refactoring, and technical programming explanations.",
    },
    {
        "name": "deepseek-r1:7b",
        "role": "math",
        "chapter": "math_reasoning",
        "intent": "math_reasoning",
        "summary": "Math and logic model.",
        "description": "Used for equations, proofs, structured reasoning, and step-by-step problem solving.",
    },
    {
        "name": "qwen3-vl:8b",
        "role": "vision",
        "chapter": "vision_reasoning",
        "intent": "vision_reasoning",
        "summary": "Vision-language model.",
        "description": "Handles image understanding, OCR-like tasks, and visual question answering.",
    },
    {
        "name": "bge-large:latest",
        "role": "embedding",
        "chapter": "embed",
        "intent": "embed",
        "summary": "Embedding model.",
        "description": "Used for semantic search, memory indexing, and vector-based retrieval.",
    },
]


# ------------------------------------------------------------
# MICRO HELPERS
# ------------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()

    @staticmethod
    def clean(text: str) -> str:
        return " ".join((text or "").split())


class MicroFastHash:
    __slots__ = ()

    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


# ------------------------------------------------------------
# MODEL BOOK INDEX (1D, cached)
# ------------------------------------------------------------
class ModelBookIndex:
    """
    Fast, cached lookup over MODEL_BOOK for routing by intent/role/chapter.
    """

    def __init__(self) -> None:
        self._by_name: Dict[str, Dict[str, Any]] = {}
        self._cache_route: Dict[int, Dict[str, Any]] = {}
        self._build_index()

    def _build_index(self) -> None:
        for entry in MODEL_BOOK:
            name = entry.get("name")
            if name:
                self._by_name[name] = entry

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return self._by_name.get(name)

    def route(
        self,
        intent: Optional[str] = None,
        role: Optional[str] = None,
        chapter: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Simple routing:
            • exact intent match preferred
            • then role
            • then chapter
            • fallback: first entry
        """
        key_parts = [
            MicroStringStripper.clean(intent or ""),
            MicroStringStripper.clean(role or ""),
            MicroStringStripper.clean(chapter or ""),
        ]
        key = "|".join(key_parts)
        h = MicroFastHash.h(key)
        cached = self._cache_route.get(h)
        if cached is not None:
            return cached

        intent_l = key_parts[0].lower()
        role_l = key_parts[1].lower()
        chapter_l = key_parts[2].lower()

        best: Optional[Dict[str, Any]] = None

        # 1) exact intent
        if intent_l:
            for e in MODEL_BOOK:
                if e.get("intent", "").lower() == intent_l:
                    best = e
                    break

        # 2) role
        if best is None and role_l:
            for e in MODEL_BOOK:
                if e.get("role", "").lower() == role_l:
                    best = e
                    break

        # 3) chapter
        if best is None and chapter_l:
            for e in MODEL_BOOK:
                if e.get("chapter", "").lower() == chapter_l:
                    best = e
                    break

        # 4) fallback
        if best is None and MODEL_BOOK:
            best = MODEL_BOOK[0]

        self._cache_route[h] = best
        return best


# ------------------------------------------------------------
# MODEL BOOK INDEX 3D (3D-max wrapper)
# ------------------------------------------------------------
class ModelBookIndex3D:
    """
    3D router over MODEL_BOOK:
        • Reuses ModelBookIndex core logic
        • Accepts 3D grids of routing hints
        • Returns 3D grids of model entries or names
    """

    def __init__(self) -> None:
        self.index = ModelBookIndex()

    def route_3d(
        self,
        intents_3d: List[List[List[Optional[str]]]],
        roles_3d: Optional[List[List[List[Optional[str]]]]] = None,
        chapters_3d: Optional[List[List[List[Optional[str]]]]] = None,
    ) -> List[List[List[Optional[Dict[str, Any]]]]]:
        depth = len(intents_3d)
        out: List[List[List[Optional[Dict[str, Any]]]]] = []

        for d in range(depth):
            plane_i = intents_3d[d]
            plane_r = roles_3d[d] if roles_3d is not None else None
            plane_c = chapters_3d[d] if chapters_3d is not None else None

            plane_out: List[List[Optional[Dict[str, Any]]]] = []
            for r_idx, row_i in enumerate(plane_i):
                row_r = plane_r[r_idx] if plane_r is not None else None
                row_c = plane_c[r_idx] if plane_c is not None else None

                row_out: List[Optional[Dict[str, Any]]] = []
                for c_idx, intent in enumerate(row_i):
                    role = row_r[c_idx] if row_r is not None else None
                    chapter = row_c[c_idx] if row_c is not None else None
                    row_out.append(self.index.route(intent=intent, role=role, chapter=chapter))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def route_names_3d(
        self,
        intents_3d: List[List[List[Optional[str]]]],
        roles_3d: Optional[List[List[List[Optional[str]]]]] = None,
        chapters_3d: Optional[List[List[List[Optional[str]]]]] = None,
    ) -> List[List[List[Optional[str]]]]:
        envelopes_3d = self.route_3d(intents_3d, roles_3d, chapters_3d)
        depth = len(envelopes_3d)
        out: List[List[List[Optional[str]]]] = []

        for d in range(depth):
            plane = envelopes_3d[d]
            plane_out: List[List[Optional[str]]] = []
            for row in plane:
                row_out: List[Optional[str]] = []
                for e in row:
                    row_out.append(e.get("name") if e is not None else None)
                plane_out.append(row_out)
            out.append(plane_out)

        return out
