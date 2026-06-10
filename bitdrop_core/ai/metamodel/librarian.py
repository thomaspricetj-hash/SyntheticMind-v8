# bitdrop_core/ai/metamodel/librarian.py

from __future__ import annotations
from typing import List, Dict, Any, Optional
import zlib

from .librarian_helper import LibrarianHelper
from .book_metadata import find_by_role


# ------------------------------------------------------------
# MICRO HELPERS (shared)
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
# Librarian (1D, max‑improved)
# ------------------------------------------------------------
class Librarian:
    """
    Librarian orchestrator:
        • pulls from multiple specialist reasoning models
        • aggregates their technical notes
        • summarizes into a compact context packet
        • (final answer is composed later by the small model)
    """

    def __init__(self, helper: LibrarianHelper | None = None):
        self.helper = helper or LibrarianHelper()

        self.default_roles = [
            "general_reasoning",
            "deep_reasoning",
            "math",
            "code",
        ]

        # Cache for context summaries
        self._context_cache: Dict[int, str] = {}
        self._notes_cache: Dict[int, List[str]] = {}

    # ------------------------------------------------------------
    # INTERNAL: resolve model name for a given role
    # ------------------------------------------------------------
    def _model_for_role(self, role: str) -> Optional[str]:
        page = find_by_role(role)
        if not page:
            return None
        return page.get("name")

    # ------------------------------------------------------------
    # PUBLIC: build a compressed context summary (cached)
    # ------------------------------------------------------------
    def build_context(
        self,
        query: str,
        max_words: int = 220,
        roles: Optional[List[str]] = None,
    ) -> str:
        query = MicroStringStripper.clean(query or "")
        if not query:
            return ""

        roles = roles or self.default_roles

        # Cache key
        key = f"{query}|{','.join(roles)}|{max_words}"
        h = MicroFastHash.h(key)
        cached = self._context_cache.get(h)
        if cached is not None:
            return cached

        notes: List[str] = []

        # --------------------------------------------------------
        # Query each specialist model for technical notes
        # --------------------------------------------------------
        for role in roles:
            model_name = self._model_for_role(role)
            if not model_name:
                continue

            prompt = (
                f"You are the {role.replace('_', ' ')} expert.\n\n"
                f"User question:\n{query}\n\n"
                f"Provide ONLY technical notes, insights, equations, edge cases, "
                f"and reasoning fragments relevant to answering this question.\n"
                f"Do NOT provide a final answer.\n"
                f"Return concise bullet points or short paragraphs of raw reasoning."
            )

            result = self.helper.ollama.generate(model_name, prompt)
            if result.get("ok"):
                resp = (result.get("response") or "").strip()
                if resp:
                    notes.append(f"[{role}] {resp}")

        if not notes:
            self._context_cache[h] = ""
            return ""

        raw_context = "\n\n".join(notes)
        summary = self.helper.summarize_text(raw_context, max_words=max_words)
        final = summary or raw_context

        self._context_cache[h] = final
        self._notes_cache[h] = notes
        return final

    # ------------------------------------------------------------
    # PUBLIC: full reasoning pipeline (cached)
    # ------------------------------------------------------------
    def answer_with_context(
        self,
        query: str,
        max_words: int = 220,
        roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        query = MicroStringStripper.clean(query or "")
        if not query:
            return {"context": "", "raw_notes": []}

        roles = roles or self.default_roles

        key = f"ANSWER|{query}|{','.join(roles)}|{max_words}"
        h = MicroFastHash.h(key)
        if h in self._context_cache and h in self._notes_cache:
            return {
                "context": self._context_cache[h],
                "raw_notes": self._notes_cache[h],
            }

        notes: List[str] = []

        for role in roles:
            model_name = self._model_for_role(role)
            if not model_name:
                continue

            prompt = (
                f"You are the {role.replace('_', ' ')} expert.\n\n"
                f"User question:\n{query}\n\n"
                f"Provide ONLY technical notes, insights, equations, edge cases, "
                f"and reasoning fragments. No final answer."
            )

            result = self.helper.ollama.generate(model_name, prompt)
            if result.get("ok"):
                resp = (result.get("response") or "").strip()
                if resp:
                    notes.append(f"[{role}] {resp}")

        raw_context = "\n\n".join(notes)
        summary = self.helper.summarize_text(raw_context, max_words=max_words)
        final = summary or raw_context

        self._context_cache[h] = final
        self._notes_cache[h] = notes

        return {
            "context": final,
            "raw_notes": notes,
        }


# ------------------------------------------------------------
# Librarian3D (3D‑max wrapper)
# ------------------------------------------------------------
class Librarian3D:
    """
    3D‑max Librarian:
        • Accepts 3D grids [D][H][W] of queries
        • Returns 3D grids of context summaries
        • Uses full caching from Librarian
    """

    def __init__(self, helper: LibrarianHelper | None = None):
        self.librarian = Librarian(helper)

    def build_context_3d(
        self,
        queries_3d: List[List[List[str]]],
        max_words: int = 220,
        roles: Optional[List[str]] = None,
    ) -> List[List[List[str]]]:
        depth = len(queries_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for q in row:
                    row_out.append(
                        self.librarian.build_context(
                            query=q,
                            max_words=max_words,
                            roles=roles,
                        )
                    )
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def answer_with_context_3d(
        self,
        queries_3d: List[List[List[str]]],
        max_words: int = 220,
        roles: Optional[List[str]] = None,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    row_out.append(
                        self.librarian.answer_with_context(
                            query=q,
                            max_words=max_words,
                            roles=roles,
                        )
                    )
                plane_out.append(row_out)
            out.append(plane_out)

        return out
