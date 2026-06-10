# bitdrop_core/ai/backend/hybrid_backend.py

from __future__ import annotations

import time
import json
import requests
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Protocol

from bitdrop_core.ai.compression.bitdrop_collapse_codec import BitDropCollapseEngine


# ============================================================
# Collapser protocol
# ============================================================
class Collapser(Protocol):
    def collapse(
        self,
        text: str,
        *,
        rules: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Any:
        ...

    def expand(self, text: str) -> Any:
        ...


# ============================================================
# Result container
# ============================================================
@dataclass
class BackendResult:
    text: str
    backend: str
    model: str
    latency_ms: int
    raw: Dict[str, Any]


# ============================================================
# Base backend interface
# ============================================================
class BaseBackend:
    name: str

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackendResult:
        raise NotImplementedError


# ============================================================
# Ollama backend
# ============================================================
class OllamaBackend(BaseBackend):
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
    ) -> None:
        self.name = "ollama"
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackendResult:

        url = f"{self.base_url}/api/generate"
        full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        start = time.time()
        resp = requests.post(url, json=payload, timeout=self.timeout)
        latency_ms = int((time.time() - start) * 1000)

        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "") or ""

        return BackendResult(
            text=text,
            backend=self.name,
            model=self.model,
            latency_ms=latency_ms,
            raw=data,
        )


# ============================================================
# OpenAI‑compatible backend (vLLM / LM Studio)
# ============================================================
class OpenAICompatibleBackend(BaseBackend):
    def __init__(
        self,
        name: str,
        model: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 120,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackendResult:

        url = f"{self.base_url}/v1/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start = time.time()
        resp = requests.post(url, headers=self._headers(), data=json.dumps(payload), timeout=self.timeout)
        latency_ms = int((time.time() - start) * 1000)

        resp.raise_for_status()
        data = resp.json()

        text = ""
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            text = ""

        return BackendResult(
            text=text,
            backend=self.name,
            model=self.model,
            latency_ms=latency_ms,
            raw=data,
        )


# bitdrop_core/ai/backend/hybrid_backend.py



import time
import json
import requests
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Protocol, Tuple

from bitdrop_core.ai.compression.bitdrop_collapse_codec import BitDropCollapseEngine


# ============================================================
# Collapser protocol
# ============================================================
class Collapser(Protocol):
    def collapse(
        self,
        text: str,
        *,
        rules: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Any:
        ...

    def expand(self, text: str) -> Any:
        ...


# ============================================================
# Result container
# ============================================================
@dataclass
class BackendResult:
    text: str
    backend: str
    model: str
    latency_ms: int
    raw: Dict[str, Any]


# ============================================================
# 3D STRUCTURE
# ============================================================
@dataclass
class Backend3D:
    """
    3D structural view of a backend generation operation.

    axis_x: high-level op ("generate", "collapse", "expand")
    axis_y: structural decomposition (backend, model, intent)
    axis_z: metadata (latency, lengths, collapse/expand flags)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# Base backend interface
# ============================================================
class BaseBackend:
    name: str

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackendResult:
        raise NotImplementedError


# ============================================================
# Ollama backend
# ============================================================
class OllamaBackend(BaseBackend):
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
    ) -> None:
        self.name = "ollama"
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackendResult:

        url = f"{self.base_url}/api/generate"
        full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        start = time.time()
        resp = requests.post(url, json=payload, timeout=self.timeout)
        latency_ms = int((time.time() - start) * 1000)

        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "") or ""

        return BackendResult(
            text=text,
            backend=self.name,
            model=self.model,
            latency_ms=latency_ms,
            raw=data,
        )


# ============================================================
# OpenAI‑compatible backend (vLLM / LM Studio)
# ============================================================
class OpenAICompatibleBackend(BaseBackend):
    def __init__(
        self,
        name: str,
        model: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 120,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackendResult:

        url = f"{self.base_url}/v1/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start = time.time()
        resp = requests.post(
            url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        latency_ms = int((time.time() - start) * 1000)

        resp.raise_for_status()
        data = resp.json()

        text = ""
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            text = ""

        return BackendResult(
            text=text,
            backend=self.name,
            model=self.model,
            latency_ms=latency_ms,
            raw=data,
        )


# ============================================================
# Backend selector
# ============================================================
class BackendSelector:
    def __init__(self, backends: Dict[str, BaseBackend]) -> None:
        self.backends = backends

    def select(
        self,
        *,
        intent: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BaseBackend:

        metadata = metadata or {}
        task = metadata.get("task") or intent or "conversation"
        L = len(text)

        if "backend" in metadata and metadata["backend"] in self.backends:
            return self.backends[metadata["backend"]]

        if L > 800 or task in ("deep_reasoning", "large_reasoning", "long_context"):
            if "vllm" in self.backends:
                return self.backends["vllm"]

        return self.backends["ollama"]


# ============================================================
# Hybrid backend facade (3D‑MAX)
# ============================================================
class HybridBackend:
    """
    Fully tolerant collapse engine wrapper.
    Ensures collapse/expand ALWAYS return text, never bytes.
    Now 3D‑MAX introspectable.
    """

    def __init__(
        self,
        backends: Dict[str, BaseBackend],
        collapser: Optional[Collapser] = None,
        expand_response: bool = False,
    ) -> None:

        if not backends:
            raise ValueError("HybridBackend requires at least one backend.")

        self.backends = backends
        self.selector = BackendSelector(backends)
        self.collapser = collapser
        self.expand_response = expand_response
        self._last_3d: Optional[Backend3D] = None

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _force_text(self, value: Any) -> str:
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="replace")
            except Exception:
                return value.hex()
        return str(value)

    def _engine_collapse(self, text: str, *, rules: Dict[str, Any], tags: Dict[str, Any]) -> str:
        engine = self.collapser
        if engine is None:
            return text

        if hasattr(engine, "collapse"):
            return self._force_text(engine.collapse(text, rules=rules, tags=tags))

        if hasattr(engine, "encode"):
            return self._force_text(engine.encode(text, rules=rules, tags=tags))

        if hasattr(engine, "compress"):
            return self._force_text(engine.compress(text, rules=rules, tags=tags))

        return text

    def _engine_expand(self, text: str) -> str:
        engine = self.collapser
        if engine is None:
            return text

        if hasattr(engine, "expand"):
            return self._force_text(engine.expand(text))

        if hasattr(engine, "decode"):
            return self._force_text(engine.decode(text))

        if hasattr(engine, "decompress"):
            return self._force_text(engine.decompress(text))

        return text

    def _collapse_prompt(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]],
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:

        metadata = metadata or {}
        if not self.collapser:
            return prompt, None, metadata

        rules = metadata.get("collapse_rules") or {}
        tags = metadata.get("collapse_tags") or {}

        tags.setdefault("mode", "chunked_grouped_patterns")
        tags.setdefault("skimming", True)
        tags.setdefault("patterns", True)
        tags.setdefault("grouping", True)
        tags.setdefault("chunk_size", metadata.get("collapse_chunk_size", 2048))

        collapsed_raw = self._engine_collapse(prompt, rules=rules, tags=tags)
        collapsed = self._force_text(collapsed_raw)

        metadata["collapse_rules"] = rules
        metadata["collapse_tags"] = tags

        # 3D snapshot for collapse
        self._last_3d = Backend3D(
            axis_x="collapse",
            axis_y=["collapse", tags.get("mode", "unknown")],
            axis_z={
                "prompt_len": len(prompt),
                "collapsed_len": len(collapsed),
                "has_collapser": self.collapser is not None,
                "tags": dict(tags),
            },
        )

        return collapsed, collapsed, metadata

    def _expand_text(self, text: str) -> str:
        if not self.collapser or not self.expand_response:
            return text
        try:
            expanded = self._engine_expand(text)
            # 3D snapshot for expand
            self._last_3d = Backend3D(
                axis_x="expand",
                axis_y=["expand"],
                axis_z={
                    "input_len": len(text),
                    "expanded_len": len(expanded),
                    "has_collapser": self.collapser is not None,
                    "expand_enabled": self.expand_response,
                },
            )
            return expanded
        except Exception:
            return text

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        *,
        intent: str = "conversation",
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackendResult:

        backend = self.selector.select(intent=intent, text=prompt, metadata=metadata)

        collapsed_prompt, collapsed_raw, metadata = self._collapse_prompt(prompt, metadata)
        collapsed_prompt = self._force_text(collapsed_prompt)

        start = time.time()
        result = backend.generate(
            collapsed_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            metadata=metadata,
        )
        latency_ms = int((time.time() - start) * 1000)

        result.raw.setdefault("bitdrop", {})
        result.raw["bitdrop"]["collapsed_prompt"] = collapsed_raw

        result.text = self._expand_text(result.text)
        result.latency_ms = latency_ms

        # 3D snapshot for generate
        self._last_3d = Backend3D(
            axis_x="generate",
            axis_y=[backend.name, backend.model if hasattr(backend, "model") else "", intent],
            axis_z={
                "latency_ms": latency_ms,
                "prompt_len": len(prompt),
                "collapsed_len": len(collapsed_prompt),
                "response_len": len(result.text),
                "expand_enabled": self.expand_response,
                "has_collapser": self.collapser is not None,
            },
        )

        return result


# ============================================================
# Convenience factory
# ============================================================
def create_default_hybrid_backend(
    collapser: Optional[Collapser] = None,
    expand_response: bool = False,
) -> HybridBackend:

    backends: Dict[str, BaseBackend] = {}

    backends["ollama"] = OllamaBackend(
        model="llama3.1:8b",
        base_url="http://localhost:11434",
    )

    backends["vllm"] = OpenAICompatibleBackend(
        name="vllm",
        model="meta-llama-3-8b-instruct",
        base_url="http://localhost:8000",
        api_key=None,
    )

    if collapser is None:
        collapser = BitDropCollapseEngine()

    return HybridBackend(
        backends=backends,
        collapser=collapser,
        expand_response=expand_response,
    )
