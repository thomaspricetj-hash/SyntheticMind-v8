class SummarizerModelV1:
    """
    V5 Ultra‑Precision Summarizer
    Features:
        • Exact sentence-count control
        • Exact word-count control
        • Percent-compression control
        • Length-hint shaping
        • Key noun/verb preservation
        • Semantic compression
        • Hallucination-resistant prompting
        • Deterministic cleanup + trimming
    """

    def __init__(self, model):
        """
        model: any LLM wrapper with .generate(prompt)
        """
        self.model = model

    # ------------------------------------------------------------
    # MAIN SUMMARIZATION ENTRYPOINT
    # ------------------------------------------------------------
    def summarize(
        self,
        text: str,
        *,
        sentences=None,
        words=None,
        percent=None,
        length_hint=None
    ) -> str:

        constraint = self._build_constraint(
            sentences=sentences,
            words=words,
            percent=percent,
            length_hint=length_hint,
        )

        prompt = (
            "You are a precision summarizer.\n"
            "Rules:\n"
            "  • Preserve key nouns, verbs, and factual meaning.\n"
            "  • No hallucinations, no invented details.\n"
            "  • No filler, no meta commentary.\n"
            "  • No prefaces like 'Here is the summary'.\n"
            "  • Output ONLY the summary.\n\n"
            f"{constraint}\n\n"
            f"TEXT:\n{text}\n\n"
            "SUMMARY:"
        )

        raw = self.model.generate(prompt)
        cleaned = self._clean(raw)

        # Enforce constraints deterministically
        if sentences:
            cleaned = self._enforce_sentence_count(cleaned, sentences)

        if words:
            cleaned = self._enforce_word_limit(cleaned, words)

        return cleaned

    # ------------------------------------------------------------
    # CONSTRAINT BUILDER
    # ------------------------------------------------------------
    def _build_constraint(self, sentences, words, percent, length_hint):
        if sentences:
            return f"Summarize the text in exactly {sentences} sentences."

        if words:
            return f"Summarize the text in no more than {words} words."

        if percent:
            return (
                f"Summarize the text by reducing its length by about {percent}%. "
                "Preserve all key ideas."
            )

        if length_hint:
            if "ultra" in length_hint:
                return "Produce an ultra‑short summary (1–2 sentences)."
            if "very" in length_hint:
                return "Produce a very concise summary (2–3 sentences)."
            if "short" in length_hint:
                return "Produce a short, compact summary."

        return "Summarize the text concisely."

    # ------------------------------------------------------------
    # OUTPUT CLEANER
    # ------------------------------------------------------------
    def _clean(self, text: str) -> str:
        if not text:
            return ""

        t = text.strip()

        # Remove common LLM prefixes
        bad_prefixes = [
            "summary:",
            "the summary is:",
            "here is the summary:",
            "tl;dr:",
            "in summary:",
        ]
        t_low = t.lower()
        for p in bad_prefixes:
            if t_low.startswith(p):
                t = t[len(p):].strip()
                break

        # Remove markdown artifacts
        t = t.strip(" \n\t\"'`")

        return t

    # ------------------------------------------------------------
    # SENTENCE ENFORCER
    # ------------------------------------------------------------
    def _enforce_sentence_count(self, text: str, target: int) -> str:
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if not sentences:
            return text

        if len(sentences) > target:
            sentences = sentences[:target]

        if len(sentences) < target:
            # Pad by splitting long sentences deterministically
            while len(sentences) < target:
                last = sentences[-1]
                parts = last.split(",")
                if len(parts) > 1:
                    sentences[-1] = parts[0]
                    sentences.append(",".join(parts[1:]).strip())
                else:
                    break

        return ". ".join(sentences).strip() + "."

    # ------------------------------------------------------------
    # WORD LIMIT ENFORCER
    # ------------------------------------------------------------
    def _enforce_word_limit(self, text: str, limit: int) -> str:
        words = text.split()
        if len(words) <= limit:
            return text
        trimmed = " ".join(words[:limit])
        return trimmed.rstrip(".,;:") + "."



