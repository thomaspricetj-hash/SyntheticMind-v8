from __future__ import annotations
from typing import Dict, Any
import re


class ConversationHelperV4:
    """
    ConversationHelperV4 — high‑level conversational intelligence layer.

    Responsibilities:
      • Detect conversational intent (chat, ask, command, meta)
      • Detect emotional tone (positive, neutral, negative, confused)
      • Detect social cues (lol, hmm, idk, ellipses, etc.)
      • Track topic continuity
      • Shape the LLM's tone and style
      • Provide a structured "conversation profile" for the orchestrator

    This helper does NOT generate text. It enriches the query with
    conversational metadata so the composer can respond naturally.
    """

    # Regex patterns for tone detection
    POSITIVE_RE = re.compile(
        r"\b(thanks|thank you|awesome|great|cool|nice|lol|haha|love it|perfect)\b",
        re.IGNORECASE
    )

    NEGATIVE_RE = re.compile(
        r"\b(sad|upset|angry|annoyed|frustrated|tired|idk|i don't know|hate this|ugh)\b",
        re.IGNORECASE
    )

    # FIXED: escaped literal question marks
    CONFUSED_RE = re.compile(
        r"\b(huh|what|wait|confused|\?\?\?)\b",
        re.IGNORECASE
    )

    # Intent triggers
    META_TRIGGERS = [
        "what do you think",
        "your opinion",
        "how do you feel",
        "be honest",
        "tell me honestly",
    ]

    CHAT_TRIGGERS = [
        "hi", "hello", "hey", "sup", "what's up", "how's it going",
        "yo", "good morning", "good evening"
    ]

    COMMAND_TRIGGERS = [
        "do this", "fix this", "make this", "write", "generate",
        "create", "build", "produce", "give me"
    ]

    def analyze(self, text: str, *, last_topic: str | None = None) -> Dict[str, Any]:
        t = text.lower()

        # --- 1. Intent classification ---
        intent = "ask"  # default

        if any(x in t for x in self.CHAT_TRIGGERS):
            intent = "chat"
        elif any(x in t for x in self.COMMAND_TRIGGERS):
            intent = "command"
        elif any(x in t for x in self.META_TRIGGERS):
            intent = "meta"
        elif t.endswith("?"):
            intent = "ask"

        # --- 2. Tone detection ---
        tone = "neutral"
        if self.POSITIVE_RE.search(t):
            tone = "positive"
        elif self.NEGATIVE_RE.search(t):
            tone = "negative"
        elif self.CONFUSED_RE.search(t):
            tone = "confused"

        # --- 3. Topic continuity ---
        topic_shift = False
        if last_topic and last_topic not in t:
            topic_shift = True

        # --- 4. Social cues ---
        cues = []
        if "lol" in t or "haha" in t:
            cues.append("humor")
        if "hmm" in t:
            cues.append("thinking")
        if "..." in t:
            cues.append("hesitation")
        if "idk" in t or "i don't know" in t:
            cues.append("uncertainty")

        # --- 5. Build conversation profile ---
        return {
            "intent": intent,
            "tone": tone,
            "topic_shift": topic_shift,
            "social_cues": cues,
            "last_topic": last_topic,
        }

    # ------------------------------------------------------------
    # Tone shaping for the LLM
    # ------------------------------------------------------------
    def shape_prompt(self, query: str, profile: Dict[str, Any]) -> str:
        """
        Injects conversational metadata into the prompt so the LLM
        can respond with the right tone and style.
        """

        tone = profile["tone"]
        intent = profile["intent"]
        cues = profile["social_cues"]

        style = []

        # Tone shaping
        if tone == "positive":
            style.append("Respond with warm, upbeat energy.")
        elif tone == "negative":
            style.append("Respond with calm empathy and reassurance.")
        elif tone == "confused":
            style.append("Respond with clarity and patience.")
        else:
            style.append("Respond with natural, human-like clarity.")

        # Intent shaping
        if intent == "chat":
            style.append("Keep the tone conversational and friendly.")
        elif intent == "command":
            style.append("Be direct, efficient, and solution-focused.")
        elif intent == "meta":
            style.append("Be reflective, thoughtful, and transparent.")

        # Social cues
        if "humor" in cues:
            style.append("Light humor is appropriate.")
        if "hesitation" in cues:
            style.append("Be gentle and encouraging.")
        if "uncertainty" in cues:
            style.append("Offer clarity and guidance without pressure.")

        # Build final shaped prompt
        style_block = "\n".join(style)

        return (
            f"{query}\n\n"
            f"---\n"
            f"Conversation style instructions:\n"
            f"{style_block}\n"
            f"---\n"
        )

