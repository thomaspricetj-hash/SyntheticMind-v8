from __future__ import annotations
from typing import Any, Dict


class ReasoningHelperV2:
    """
    ReasoningHelperV2 — high‑reliability structured reasoning helper.

    Goals:
      - Force internal step-by-step reasoning (hidden from user)
      - Require internal self-checking
      - Output ONLY a short, clean final answer
      - Never leak chain-of-thought
      - Deterministic, low-temperature reasoning
      - Robust to malformed model output
    """

    def __init__(
        self,
        llm_engine,
        *,
        model_name: str = "syntheticmind-reasoner-v2",
        max_tokens: int = 512,
        temperature: float = 0.2,
    ):
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------
    def run(self, query: str, *, lang_info=None, memory_info=None, **_: Any) -> Dict[str, Any]:
        prompt = self._build_prompt(query, lang_info=lang_info, memory_info=memory_info)

        try:
            request = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }

            raw = self.llm_engine.generate(request)
            final = self._extract_final_answer(raw)

            return {"ok": True, "answer": final}

        except Exception as exc:
            return {"ok": False, "error": str(exc), "answer": None}

    # --------------------------------------------------------
    # Prompt builder
    # --------------------------------------------------------
    def _build_prompt(self, query: str, *, lang_info=None, memory_info=None) -> str:
        """
        Builds a deterministic reasoning prompt with:
          - hidden chain-of-thought
          - explicit self-verification
          - final answer tag
        """

        parts = []

        parts.append(
            "You are a structured reasoning engine.\n"
            "You MUST think step-by-step internally, verify your reasoning, "
            "and then output ONLY the final answer.\n"
            "Do NOT reveal your reasoning.\n"
        )

        if lang_info:
            parts.append("\nLanguage analysis:\n")
            parts.append(str(lang_info))

        if memory_info:
            parts.append("\nRelevant memory:\n")
            parts.append(str(memory_info))

        parts.append("\nUser question:\n")
        parts.append(query)

        parts.append(
            "\n\nINTERNAL REASONING (hidden from user):\n"
            "- Break the problem into steps.\n"
            "- Solve each step.\n"
            "- Check for contradictions.\n"
            "- Confirm the final answer is correct.\n"
            "- DO NOT output this section.\n"
        )

        parts.append(
            "\nFINAL ANSWER FORMAT:\n"
            "<final_answer>\n"
            "Your short, clean answer here.\n"
            "</final_answer>\n"
        )

        return "".join(parts)

    # --------------------------------------------------------
    # Final answer extractor
    # --------------------------------------------------------
    def _extract_final_answer(self, raw: str) -> str:
        """
        Extracts the <final_answer>...</final_answer> block.
        Falls back to a trimmed version of the raw output.
        """

        if not raw:
            return ""

        lower = raw.lower()

        start = lower.find("<final_answer>")
        end = lower.find("</final_answer>")

        if start != -1 and end != -1 and end > start:
            content = raw[start + len("<final_answer>") : end]
            return content.strip()

        # Fallback: return trimmed raw output
        return raw.strip()
