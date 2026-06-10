from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Reasoning3D:
    """
    Lightweight 3D structural view of a reasoning query.
    axis_x: raw query text
    axis_y: line-wise decomposition
    axis_z: attached context (lang + memory + meta)
    """
    raw_query: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


class ReasoningHelperV2:
    """
    ReasoningHelperV2 — MAX-3D structured reasoning helper.

    Goals:
      - Force internal step-by-step reasoning (hidden from user)
      - Require internal self-checking
      - Output a structured 4-section envelope + short final answer
      - Never leak chain-of-thought
      - Deterministic, low-temperature reasoning
      - Robust to malformed model output
      - Provide a 3D structural view of the reasoning context
      - Align with physics/math/logic/code helpers (sections + metadata)
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
        self.name = "ReasoningHelper"

    # --------------------------------------------------------
    # 3D builder
    # --------------------------------------------------------
    def _build_3d(self, query: str, lang_info: Any, memory_info: Any) -> Reasoning3D:
        lines = (query or "").splitlines()
        axis_z = {
            "lang_info": lang_info,
            "memory_info": memory_info,
        }
        return Reasoning3D(
            raw_query=query or "",
            axis_x=query or "",
            axis_y=lines,
            axis_z=axis_z,
        )

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------
    def run(self, query: str, *, lang_info=None, memory_info=None, **_: Any) -> Dict[str, Any]:
        reasoning_3d = self._build_3d(query, lang_info, memory_info)
        prompt = self._build_prompt(query, lang_info=lang_info, memory_info=memory_info)

        try:
            request = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }

            raw = self.llm_engine.generate(request)
            sections = self._extract_sections(raw)
            final_answer = sections.get("Final Answer", "").strip()

            envelope = {
                "ok": True,
                "answer": final_answer,
                "sections": [
                    "Definitions",
                    "Derivation",
                    "Conditions",
                    "Final Answer",
                ],
                "structured": {
                    "Definitions": sections.get("Definitions", ""),
                    "Derivation": sections.get("Derivation", ""),
                    "Conditions": sections.get("Conditions", ""),
                    "Final Answer": final_answer,
                },
                "domain": "general_reasoning",
                "valid": True if final_answer else False,
                "structure_3d": reasoning_3d,
                "raw_model_output": raw,
            }

            return envelope

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "answer": None,
                "sections": [],
                "structured": {},
                "domain": "general_reasoning",
                "valid": False,
                "structure_3d": reasoning_3d,
                "raw_model_output": None,
            }

    # --------------------------------------------------------
    # Prompt builder (aligned with 4-section structure)
    # --------------------------------------------------------
    def _build_prompt(self, query: str, *, lang_info=None, memory_info=None) -> str:
        """
        Builds a deterministic reasoning prompt with:
          - hidden chain-of-thought
          - explicit self-verification
          - 4-section structured output
          - final answer tag
        """

        parts: List[str] = []

        parts.append(
            "You are a structured reasoning engine.\n"
            "You MUST think step-by-step internally, verify your reasoning, "
            "and then output ONLY a structured 4-section answer plus a short final answer.\n"
            "Do NOT reveal your internal chain-of-thought.\n"
        )

        if lang_info:
            parts.append("\nLanguage analysis (context, not to be repeated verbatim):\n")
            parts.append(str(lang_info))

        if memory_info:
            parts.append("\nRelevant memory (context, not to be repeated verbatim):\n")
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
            "\nVISIBLE OUTPUT FORMAT (STRICT):\n"
            "[1] Definitions\n"
            "Write a concise list of key definitions, symbols, and concepts.\n\n"
            "[2] Derivation\n"
            "Write a concise, high-level derivation or reasoning path (no step-by-step chain-of-thought, just the main moves).\n\n"
            "[3] Conditions\n"
            "State assumptions, constraints, and conditions under which the answer holds.\n\n"
            "[4] Final Answer\n"
            "Write a short, direct final answer in 1–3 sentences.\n\n"
            "<final_answer>\n"
            "Repeat ONLY the short final answer here, in 1–3 sentences.\n"
            "</final_answer>\n"
        )

        return "".join(parts)

    # --------------------------------------------------------
    # Section + final answer extractor
    # --------------------------------------------------------
    def _extract_sections(self, raw: str) -> Dict[str, str]:
        """
        Extracts the 4 labeled sections and the <final_answer> block.
        Falls back gracefully if formatting is imperfect.
        """
        if not raw:
            return {
                "Definitions": "",
                "Derivation": "",
                "Conditions": "",
                "Final Answer": "",
            }

        text = raw

        def _extract_block(label: str) -> str:
            marker = f"[{label}]"
            idx = text.find(marker)
            if idx == -1:
                return ""
            # Find next section marker or end
            next_idx = len(text)
            for other in ("[1] Definitions", "[2] Derivation", "[3] Conditions", "[4] Final Answer"):
                if other == marker:
                    continue
                j = text.find(other, idx + len(marker))
                if j != -1 and j < next_idx:
                    next_idx = j
            return text[idx + len(marker):next_idx].strip()

        definitions = _extract_block("1] Definitions")
        derivation = _extract_block("2] Derivation")
        conditions = _extract_block("3] Conditions")
        final_section = _extract_block("4] Final Answer")

        final_answer = self._extract_final_answer(raw)
        if not final_answer:
            final_answer = final_section

        return {
            "Definitions": definitions,
            "Derivation": derivation,
            "Conditions": conditions,
            "Final Answer": final_answer,
        }

    def _extract_final_answer(self, raw: str) -> str:
        """
        Extracts the <final_answer>...</final_answer> block.
        Falls back to empty string if not present.
        """
        if not raw:
            return ""

        lower = raw.lower()
        start = lower.find("<final_answer>")
        end = lower.find("</final_answer>")

        if start != -1 and end != -1 and end > start:
            content = raw[start + len("<final_answer>") : end]
            return content.strip()

        return ""

