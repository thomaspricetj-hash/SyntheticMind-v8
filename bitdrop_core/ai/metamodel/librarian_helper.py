from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
import zlib

from .book_metadata import get_all_pages, find_by_role, find_by_intent
from .ollama_client import OllamaClient

# Shared client instance (keeps connections warm)
_OLLAMA_CLIENT = OllamaClient()


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
# LibrarianHelper V2 (max-improved)
# ------------------------------------------------------------
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

        # Caches
        self._embed_cache: Dict[int, List[float]] = {}
        self._summary_cache: Dict[int, str] = {}
        self._model_intent_cache: Dict[int, Optional[Dict[str, Any]]] = {}
        self._model_name_cache: Dict[int, Optional[str]] = {}

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        text = MicroStringStripper.clean(text or "")
        if not text:
            return []
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    # ------------------------------------------------------------
    # EMBEDDINGS
    # ------------------------------------------------------------
    def embed_text(self, text: str, max_chars: int = 4000) -> List[float]:
        text = MicroStringStripper.clean(text or "")
        if not text:
            return []

        if max_chars > 0 and len(text) > max_chars:
            text = text[:max_chars]

        h = MicroFastHash.h(f"{self.embed_model}|{text}")
        cached = self._embed_cache.get(h)
        if cached is not None:
            return cached

        try:
            vec = self.ollama.embed(self.embed_model, text)
        except Exception:
            vec = []

        self._embed_cache[h] = vec
        return vec

    def embed_batch(self, texts: List[str], max_chars: int = 4000) -> List[List[float]]:
        return [self.embed_text(t, max_chars=max_chars) for t in texts]

    def embed_chunked(self, text: str) -> List[List[float]]:
        chunks = self._chunk_text(text, self.chunk_size)
        return self.embed_batch(chunks)

    # ------------------------------------------------------------
    # SUMMARIZATION
    # ------------------------------------------------------------
    def summarize_text(self, text: str, max_words: int = 120) -> str:
        text = MicroStringStripper.clean(text or "")
        if not text:
            return ""

        key = f"{self.summary_model}|{max_words}|{text}"
        h = MicroFastHash.h(key)
        cached = self._summary_cache.get(h)
        if cached is not None:
            return cached

        prompt = (
            f"Summarize the following content in under {max_words} words.\n"
            f"Keep key technical details. Do NOT add new information.\n\n"
            f"{text}"
        )

        try:
            result = self.ollama.generate(self.summary_model, prompt)
        except Exception:
            self._summary_cache[h] = ""
            return ""

        if not result.get("ok"):
            self._summary_cache[h] = ""
            return ""

        resp = (result.get("response") or "").strip()
        self._summary_cache[h] = resp
        return resp

    def summarize_many(self, texts: List[str], max_words: int = 120) -> List[str]:
        return [self.summarize_text(t, max_words=max_words) for t in texts]

    def summarize_chunked(self, text: str, max_words: int = 120) -> str:
        chunks = self._chunk_text(text, self.chunk_size)
        if not chunks:
            return ""
        partials = self.summarize_many(chunks, max_words=max_words)
        combined = " ".join(p for p in partials if p).strip()
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
        intent_clean = MicroStringStripper.clean(intent or "").lower()
        if not intent_clean:
            return None
        h = MicroFastHash.h(f"intent|{intent_clean}")
        cached = self._model_intent_cache.get(h)
        if cached is not None:
            return cached
        page = find_by_intent(intent_clean)
        self._model_intent_cache[h] = page
        return page

    def get_model_for_intent(self, intent: str) -> Optional[str]:
        intent_clean = MicroStringStripper.clean(intent or "").lower()
        if not intent_clean:
            return None
        h = MicroFastHash.h(f"model_for_intent|{intent_clean}")
        cached = self._model_name_cache.get(h)
        if cached is not None:
            return cached

        page = self.get_page_for_intent(intent_clean)
        if not page:
            self._model_name_cache[h] = None
            return None

        # Prefer explicit model fields, then fall back to "name"
        model_name = (
            page.get("model_name")
            or page.get("model")
            or page.get("name")
            or None
        )
        self._model_name_cache[h] = model_name
        return model_name

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
        prompt = MicroStringStripper.clean(prompt or "")
        if not prompt or not model_name:
            return ""

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

        prompt = MicroStringStripper.clean(prompt or "")
        if not prompt or not model_name:
            return None

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
        if not model_name or not messages:
            return ""

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


# ------------------------------------------------------------
# LibrarianHelper3D (3D-max wrapper)
# ------------------------------------------------------------
class LibrarianHelper3D:
    """
    3D-max helper wrapper:
        • Reuses LibrarianHelper core logic
        • Operates on 3D grids [D][H][W]
        • Batch-style embeddings, summaries, generations, and chats
    """

    def __init__(self, base_helper: Optional[LibrarianHelper] = None) -> None:
        self.helper = base_helper or LibrarianHelper()

    # 3D embeddings
    def embed_text_3d(
        self,
        texts_3d: List[List[List[str]]],
        max_chars: int = 4000,
    ) -> List[List[List[List[float]]]]:
        depth = len(texts_3d)
        out: List[List[List[List[float]]]] = []

        for d in range(depth):
            plane = texts_3d[d]
            plane_out: List[List[List[float]]] = []
            for row in plane:
                row_out: List[List[float]] = []
                for t in row:
                    row_out.append(self.helper.embed_text(t, max_chars=max_chars))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D summarization
    def summarize_text_3d(
        self,
        texts_3d: List[List[List[str]]],
        max_words: int = 120,
    ) -> List[List[List[str]]]:
        depth = len(texts_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = texts_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for t in row:
                    row_out.append(self.helper.summarize_text(t, max_words=max_words))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D generate
    def generate_with_model_3d(
        self,
        model_name: str,
        prompts_3d: List[List[List[str]]],
        *,
        strip: bool = True,
    ) -> List[List[List[str]]]:
        depth = len(prompts_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = prompts_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for p in row:
                    row_out.append(
                        self.helper.generate_with_model(
                            model_name=model_name,
                            prompt=p,
                            strip=strip,
                        )
                    )
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D chat
    def chat_3d(
        self,
        model_name: str,
        messages_3d: List[List[List[List[Dict[str, str]]]]],
        *,
        strip: bool = True,
    ) -> List[List[List[str]]]:
        depth = len(messages_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = messages_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for msgs in row:
                    row_out.append(
                        self.helper.chat(
                            model_name=model_name,
                            messages=msgs,
                            strip=strip,
                        )
                    )
                plane_out.append(row_out)
            out.append(plane_out)

        return out
