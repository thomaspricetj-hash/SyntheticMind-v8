# syntheticmind/vision/vision_processor.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import traceback

from .vision_client import VisionClient


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class VisionProc3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# VISION PROCESSOR — MAX MULTIMODAL + 3D‑MAX
# ============================================================

class VisionProcessor:
    """
    High-level vision interface (3D‑MAX Edition):
        - describe images
        - OCR
        - answer questions
        - multimodal reasoning

    Produces structured envelopes compatible with:
        • VisionAgent
        • MetaModelRuntime
        • StrategyManager
        • TaskGraph nodes
        • 3D‑MAX telemetry
    """

    def __init__(self, model: str = "qwen2.5-vl"):
        self.client = VisionClient(model=model)
        self._last_3d: Optional[VisionProc3D] = None

    # ------------------------------------------------------------
    # INTERNAL: SAFE CALL WRAPPER
    # ------------------------------------------------------------
    def _safe_call(self, prompt: str, image_bytes: bytes, mode: str) -> Dict[str, Any]:
        start = time.time()

        try:
            result = self.client.analyze(prompt, image_bytes)

            latency = int((time.time() - start) * 1000)

            self._last_3d = VisionProc3D(
                axis_x="_safe_call",
                axis_y=[mode, f"prompt_len:{len(prompt)}"],
                axis_z={
                    "latency_ms": latency,
                    "client_ok": result.get("ok", False),
                },
            )

            return {
                "ok": result.get("ok", False),
                "latency_ms": latency,
                "prompt": prompt,
                "response": result.get("response"),
                "model": result.get("model"),
                "error": result.get("error"),
                "traceback": result.get("traceback"),
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = VisionProc3D(
                axis_x="_safe_call",
                axis_y=[mode, "exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
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
        return self._safe_call(prompt, image_bytes, mode="describe")

    # ------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------
    def ocr(self, image_bytes: bytes) -> Dict[str, Any]:
        prompt = "Extract all text from this image."
        return self._safe_call(prompt, image_bytes, mode="ocr")

    # ------------------------------------------------------------
    # QUESTION ANSWERING
    # ------------------------------------------------------------
    def ask(self, question: str, image_bytes: bytes) -> Dict[str, Any]:
        prompt = f"Answer the following question about the image:\n{question}"
        return self._safe_call(prompt, image_bytes, mode="ask")
