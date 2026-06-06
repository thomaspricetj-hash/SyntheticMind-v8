# syntheticmind/vision/vision_processor.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from .vision_client import VisionClient


class VisionProcessor:
    """
    High-level vision interface:
        - describe images
        - OCR
        - answer questions
        - multimodal reasoning

    Produces structured envelopes compatible with:
        • VisionAgent
        • MetaModelRuntime
        • StrategyManager
        • TaskGraph nodes
    """

    def __init__(self, model: str = "qwen2.5-vl"):
        self.client = VisionClient(model=model)

    # ------------------------------------------------------------
    # INTERNAL: SAFE CALL WRAPPER
    # ------------------------------------------------------------
    def _safe_call(self, prompt: str, image_bytes: bytes) -> Dict[str, Any]:
        start = time.time()

        try:
            result = self.client.analyze(prompt, image_bytes)

            # VisionClient already returns a structured envelope
            return {
                "ok": result.get("ok", False),
                "latency_ms": int((time.time() - start) * 1000),
                "prompt": prompt,
                "response": result.get("response"),
                "model": result.get("model"),
                "error": result.get("error"),
                "traceback": result.get("traceback"),
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "prompt": prompt,
                "response": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # DESCRIBE IMAGE
    # ------------------------------------------------------------
    def describe(self, image_bytes: bytes) -> Dict[str, Any]:
        prompt = "Describe this image in detail."
        return self._safe_call(prompt, image_bytes)

    # ------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------
    def ocr(self, image_bytes: bytes) -> Dict[str, Any]:
        prompt = "Extract all text from this image."
        return self._safe_call(prompt, image_bytes)

    # ------------------------------------------------------------
    # QUESTION ANSWERING
    # ------------------------------------------------------------
    def ask(self, question: str, image_bytes: bytes) -> Dict[str, Any]:
        prompt = f"Answer the following question about the image:\n{question}"
        return self._safe_call(prompt, image_bytes)
