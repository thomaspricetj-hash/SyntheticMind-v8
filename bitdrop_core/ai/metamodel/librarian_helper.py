from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable

from .book_metadata import get_all_pages, find_by_role, find_by_intent
from .ollama_client import OllamaClient

# Shared client instance (keeps connections warm)
_OLLAMA_CLIENT = OllamaClient()


class LibrarianHelper:
    """
    LibrarianHelper V2:
        • embeddings (single, batch, chunked)
        • summarization (single, batch, chunked)
        • JSON-safe model calls
        • intent-to-model routing
        • safe chat wrapper
        • fail-soft everywhere
        • fully backward compatible
    """

    def __init__(
        self,
        embed_model: str = "bge-large:latest",
        summary_model: str = "phi3:mini",
        chunk_size: int = 2000,
    ) -> None:
        self.embed_model = embed_model
        self.summary_model = summary_model
        self.chunk_size = chunk_size
        self.ollama = _OLLAMA_CLIENT

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    # ------------------------------------------------------------
    # EMBEDDINGS
    # ------------------------------------------------------------
    def embed_text(self, text: str, max_chars: int = 4000) -> List[float]:
        text = (text or "").strip()
        if not text:
            return []

        if max_chars > 0 and len(text) > max_chars:
            text = text[:max_chars]

        try:
            return self.ollama.embed(self.embed_model, text)
        except Exception:
            return []

    def embed_batch(self, texts: List[str], max_chars: int = 4000) -> List[List[float]]:
        return [self.embed_text(t, max_chars=max_chars) for t in texts]

    def embed_chunked(self, text: str) -> List[List[float]]:
        chunks = self._chunk_text(text, self.chunk_size)
        return self.embed_batch(chunks)

    # ------------------------------------------------------------
    # SUMMARIZATION
    # ------------------------------------------------------------
    def summarize_text(self, text: str, max_words: int = 120) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        prompt = (
            f"Summarize the following content in under {max_words} words.\n"
            f"Keep key technical details. Do NOT add new information.\n\n"
            f"{text}"
        )

        try:
            result = self.ollama.generate(self.summary_model, prompt)
        except Exception:
            return ""

        if not result.get("ok"):
            return ""

        return (result.get("response") or "").strip()

    def summarize_many(self, texts: List[str], max_words: int = 120) -> List[str]:
        return [self.summarize_text(t, max_words=max_words) for t in texts]

    def summarize_chunked(self, text: str, max_words: int = 120) -> str:
        chunks = self._chunk_text(text, self.chunk_size)
        partials = self.summarize_many(chunks, max_words=max_words)
        combined = " ".join(partials).strip()
        return self.summarize_text(combined, max_words=max_words)

    # ------------------------------------------------------------
    # BOOK METADATA ACCESS
    # ------------------------------------------------------------
    def list_book_pages(self) -> str:
        from .book_metadata import describe_book
        return describe_book()

    def get_narrator_page(self) -> Optional[Dict[str, Any]]:
        return find_by_role("narrator")

    def get_page_for_intent(self, intent: str) -> Optional[Dict[str, Any]]:
        return find_by_intent(intent)

    def get_model_for_intent(self, intent: str) -> Optional[str]:
        page = self.get_page_for_intent(intent)
        if not page:
            return None
        return page.get("model_name") or page.get("model") or None

    # ------------------------------------------------------------
    # MODEL EXECUTION HELPERS
    # ------------------------------------------------------------
    def generate_with_model(
        self,
        model_name: str,
        prompt: str,
        *,
        strip: bool = True,
    ) -> str:
        try:
            result = self.ollama.generate(model_name, prompt)
        except Exception:
            return ""

        if not result.get("ok"):
            return ""

        resp = result.get("response") or ""
        return resp.strip() if strip else resp

    def generate_json_with_model(
        self,
        model_name: str,
        prompt: str,
        *,
        validator: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> Optional[Dict[str, Any]]:
        import json

        json_prompt = (
            "You MUST respond with valid JSON only. No explanation. No commentary.\n\n"
            f"{prompt}"
        )

        raw = self.generate_with_model(model_name, json_prompt, strip=True)
        if not raw:
            return None

        try:
            data = json.loads(raw)
        except Exception:
            return None

        if validator:
            try:
                if not validator(data):
                    return None
            except Exception:
                return None

        return data

    def batch_generate(self, model_name: str, prompts: List[str]) -> List[str]:
        return [self.generate_with_model(model_name, p) for p in prompts]

    # ------------------------------------------------------------
    # CHAT WRAPPER
    # ------------------------------------------------------------
    def chat(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        *,
        strip: bool = True,
    ) -> str:
        """
        Safe chat wrapper for models that support chat-style messages.
        """
        try:
            result = self.ollama.chat(model_name, messages)
        except Exception:
            return ""

        if not result.get("ok"):
            return ""

        resp = result.get("response") or ""
        return resp.strip() if strip else resp

    # ------------------------------------------------------------
    # PAGE LOOKUP HELPERS
    # ------------------------------------------------------------
    def get_all_pages(self) -> List[Dict[str, Any]]:
        return get_all_pages()

    def get_page_by_role(self, role: str) -> Optional[Dict[str, Any]]:
        return find_by_role(role)


