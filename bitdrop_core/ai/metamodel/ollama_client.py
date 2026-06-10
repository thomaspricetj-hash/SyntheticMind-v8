# ai/llm/ollama_client.py

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Dict, Any, Optional, Iterable, Generator, List, Tuple


class OllamaClient:
    """
    Robust Ollama HTTP client for local model inference (3D‑MAX, v2).

    Design:
        • Backward‑compatible generate(model, prompt, ...) API
        • Streaming generate_stream() for token streaming
        • Chat API: chat(model, messages)
        • Embeddings API: embed(model, text)
        • Batch + 3D APIs: generate_batch(), generate_3d()
        • Centralized error handling + retry logic
        • JSON‑safe helpers for higher‑level wrappers
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11434,
        timeout: int = 60,
        *,
        max_retries: int = 2,
        retry_backoff: float = 0.35,
    ):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    # ------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------
    def _request(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        timeout: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Core non‑streaming request helper.
        Returns a normalized dict: {ok, model, response, error, raw}
        """
        url = f"{self.base}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout = timeout or self.timeout

        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")

                    if resp.status != 200:
                        last_error = f"HTTP {resp.status}: {raw}"
                        continue

                    try:
                        result = json.loads(raw)
                    except json.JSONDecodeError:
                        last_error = f"Malformed JSON from Ollama: {raw}"
                        continue

                    return {
                        "ok": True,
                        "model": payload.get("model"),
                        "response": result,
                        "error": None,
                        "raw": raw,
                    }

            except urllib.error.HTTPError as e:
                last_error = f"HTTPError {e.code}: {e.reason}"

            except urllib.error.URLError as e:
                if isinstance(e.reason, ConnectionRefusedError):
                    last_error = "Connection refused — is Ollama running?"
                elif isinstance(e.reason, socket.timeout):
                    last_error = "Request timed out"
                else:
                    last_error = f"URLError: {e.reason}"

            except Exception as e:
                last_error = f"Unexpected error: {e}"

            if attempt < self.max_retries:
                time.sleep(self.retry_backoff * (attempt + 1))

        return {
            "ok": False,
            "model": payload.get("model"),
            "response": None,
            "error": last_error or "Unknown error",
            "raw": None,
        }

    def _request_stream(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        timeout: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streaming request helper.
        Yields parsed JSON chunks from Ollama's streaming API.
        """
        url = f"{self.base}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout = timeout or self.timeout

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    yield {
                        "ok": False,
                        "model": payload.get("model"),
                        "response": "",
                        "error": f"HTTP {resp.status}",
                    }
                    return

                for line in resp:
                    try:
                        chunk_raw = line.decode("utf-8").strip()
                        if not chunk_raw:
                            continue
                        chunk = json.loads(chunk_raw)
                    except Exception:
                        continue

                    yield {
                        "ok": True,
                        "model": payload.get("model"),
                        "response": chunk,
                        "error": None,
                    }

        except urllib.error.HTTPError as e:
            yield {
                "ok": False,
                "model": payload.get("model"),
                "response": "",
                "error": f"HTTPError {e.code}: {e.reason}",
            }

        except urllib.error.URLError as e:
            if isinstance(e.reason, ConnectionRefusedError):
                err = "Connection refused — is Ollama running?"
            elif isinstance(e.reason, socket.timeout):
                err = "Request timed out"
            else:
                err = f"URLError: {e.reason}"
            yield {
                "ok": False,
                "model": payload.get("model"),
                "response": "",
                "error": err,
            }

        except Exception as e:
            yield {
                "ok": False,
                "model": payload.get("model"),
                "response": "",
                "error": f"Unexpected error: {e}",
            }

    # ------------------------------------------------------------
    # Text generation (non‑streaming)
    # ------------------------------------------------------------
    def generate(
        self,
        model: str,
        prompt: str,
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Backward‑compatible generate().

        Returns:
            {
                "ok": bool,
                "model": str,
                "response": str,
                "error": Optional[str],
            }
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options

        result = self._request("/api/generate", payload, timeout=timeout)

        if not result["ok"]:
            return {
                "ok": False,
                "model": model,
                "response": "",
                "error": result["error"],
            }

        data = result["response"] or {}
        text = data.get("response", "")
        return {
            "ok": True,
            "model": model,
            "response": text,
            "error": None,
        }

    # ------------------------------------------------------------
    # Text generation (streaming)
    # ------------------------------------------------------------
    def generate_stream(
        self,
        model: str,
        prompt: str,
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Generator[str, None, None]:
        """
        Streaming token generator.

        Yields raw text chunks as they arrive.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        if options:
            payload["options"] = options

        for chunk in self._request_stream("/api/generate", payload, timeout=timeout):
            if not chunk.get("ok"):
                break
            data = chunk.get("response") or {}
            text_piece = data.get("response", "")
            if text_piece:
                yield text_piece

    # ------------------------------------------------------------
    # Chat API
    # ------------------------------------------------------------
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Chat‑style API wrapper.

        messages: [{"role": "user"|"assistant"|"system", "content": "..."}]
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options

        result = self._request("/api/chat", payload, timeout=timeout)

        if not result["ok"]:
            return {
                "ok": False,
                "model": model,
                "response": "",
                "error": result["error"],
            }

        data = result["response"] or {}
        msg = data.get("message") or {}
        content = msg.get("content", "")
        return {
            "ok": True,
            "model": model,
            "response": content,
            "error": None,
        }

    # ------------------------------------------------------------
    # Embeddings API
    # ------------------------------------------------------------
    def embed(
        self,
        model: str,
        text: str,
        timeout: Optional[int] = None,
    ) -> list[float]:
        """
        Embedding wrapper.

        Returns a single embedding vector (list[float]).
        """
        payload: Dict[str, Any] = {
            "model": model,
            "input": text,
        }

        result = self._request("/api/embeddings", payload, timeout=timeout)
        if not result["ok"]:
            return []

        data = result["response"] or {}
        vec = data.get("embedding") or data.get("embeddings") or []
        if isinstance(vec, list) and vec and isinstance(vec[0], list):
            vec = vec[0]
        return [float(x) for x in vec] if isinstance(vec, list) else []

    # ------------------------------------------------------------
    # Batch + 3D generation
    # ------------------------------------------------------------
    def generate_batch(
        self,
        model: str,
        prompts: Iterable[str],
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Simple batch wrapper over generate().
        """
        return [self.generate(model, p, timeout=timeout, options=options) for p in prompts]

    def generate_3d(
        self,
        model: str,
        prompts_3d: List[List[List[str]]],
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        3D tensor‑style generation:
            prompts_3d[d][h][w] -> same shape of result dicts.
        """
        depth = len(prompts_3d)
        if depth == 0:
            return []

        out: List[List[List[Dict[str, Any]]]] = []
        for d in range(depth):
            plane = prompts_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for p in row:
                    row_out.append(self.generate(model, p, timeout=timeout, options=options))
                plane_out.append(row_out)
            out.append(plane_out)
        return out

    # ------------------------------------------------------------
    # JSON‑safe helpers
    # ------------------------------------------------------------
    def generate_json(
        self,
        model: str,
        prompt: str,
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate and parse JSON from the model.

        The model is expected to return valid JSON.
        """
        result = self.generate(model, prompt, timeout=timeout, options=options)
        if not result.get("ok"):
            return {
                "ok": False,
                "model": model,
                "data": None,
                "error": result.get("error"),
            }

        raw = result.get("response") or ""
        try:
            data = json.loads(raw)
        except Exception as e:
            return {
                "ok": False,
                "model": model,
                "data": None,
                "error": f"JSON parse error: {e}",
            }

        return {
            "ok": True,
            "model": model,
            "data": data,
            "error": None,
        }

    def generate_json_batch(
        self,
        model: str,
        prompts: Iterable[str],
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return [self.generate_json(model, p, timeout=timeout, options=options) for p in prompts]

    def generate_json_3d(
        self,
        model: str,
        prompts_3d: List[List[List[str]]],
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(prompts_3d)
        if depth == 0:
            return []

        out: List[List[List[Dict[str, Any]]]] = []
        for d in range(depth):
            plane = prompts_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for p in row:
                    row_out.append(self.generate_json(model, p, timeout=timeout, options=options))
                plane_out.append(row_out)
            out.append(plane_out)
        return out


