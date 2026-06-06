from __future__ import annotations
from typing import List, Dict, Any, Optional

from .librarian_helper import LibrarianHelper
from .book_metadata import find_by_role


class Librarian:
    """
    Librarian orchestrator:
        • pulls from multiple specialist reasoning models
        • aggregates their technical notes
        • summarizes into a compact context packet
        • (final answer is composed later by the small model)
    """

    def __init__(self, helper: LibrarianHelper | None = None):
        # Helper handles:
        #   - ollama.generate()
        #   - summarization
        #   - embeddings (if needed)
        self.helper = helper or LibrarianHelper()

        # Default roles to query for context building
        self.default_roles = [
            "general_reasoning",
            "deep_reasoning",
            "math",
            "code",
        ]

    # ------------------------------------------------------------
    # INTERNAL: resolve model name for a given role
    # ------------------------------------------------------------
    def _model_for_role(self, role: str) -> Optional[str]:
        page = find_by_role(role)
        if not page:
            return None
        return page.get("name")

    # ------------------------------------------------------------
    # PUBLIC: build a compressed context summary
    # ------------------------------------------------------------
    def build_context(
        self,
        query: str,
        max_words: int = 220,
        roles: Optional[List[str]] = None,
    ) -> str:
        """
        Pull focused notes from multiple specialist models, then summarize.
        This is NOT the final answer — the small model uses this as context.

        Steps:
            1. Normalize query
            2. Select roles
            3. Query each model for technical notes
            4. Aggregate notes
            5. Summarize into a compact context packet
        """
        query = (query or "").strip()
        if not query:
            return ""

        roles = roles or self.default_roles
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
                f"Do NOT explain like a teacher.\n"
                f"Do NOT format as a full essay.\n\n"
                f"Return concise bullet points or short paragraphs of raw reasoning."
            )

            result = self.helper.ollama.generate(model_name, prompt)

            if result.get("ok"):
                resp = (result.get("response") or "").strip()
                if resp:
                    notes.append(f"[{role}] {resp}")

        if not notes:
            return ""

        # --------------------------------------------------------
        # Combine raw notes
        # --------------------------------------------------------
        raw_context = "\n\n".join(notes)

        # --------------------------------------------------------
        # Summarize into a compact context packet
        # --------------------------------------------------------
        summary = self.helper.summarize_text(raw_context, max_words=max_words)

        # If summarizer fails, fall back to raw context
        return summary or raw_context

    # ------------------------------------------------------------
    # PUBLIC: full reasoning pipeline (optional)
    # ------------------------------------------------------------
    def answer_with_context(
        self,
        query: str,
        max_words: int = 220,
        roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Optional helper: returns BOTH the context and the raw notes.
        Useful for debugging or for feeding into your Orchestrator.
        """
        query = (query or "").strip()
        if not query:
            return {"context": "", "raw_notes": []}

        roles = roles or self.default_roles
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

        return {
            "context": summary or raw_context,
            "raw_notes": notes,
        }




