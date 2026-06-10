from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import traceback
import time

from ...bitdrop.compressor import BitDropCompressor
from .packet import Packet


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class CM3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# COMPRESSION RESULT
# ============================================================

@dataclass
class CompressionResult:
    data: bytes
    size: int
    ratio: float
    codec: str
    fingerprint: str


# ============================================================
# COMPRESSION MANAGER — MAX BITDROP + 3D‑MAX
# ============================================================

class CompressionManager:
    """
    Connects Packet objects to the BitDrop GPU compression engine (3D‑MAX Edition).
    Handles:
        • packet decompression
        • packet recompression
        • binary payloads
        • metadata
        • corruption detection
        • safe fallbacks
        • structured envelopes
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self.engine = BitDropCompressor.instance()
        self._last_3d: Optional[CM3D] = None

    # ------------------------------------------------------------
    # PACKET DECOMPRESSION
    # ------------------------------------------------------------
    def decompress_packet(self, packet: Packet) -> Packet:
        """
        Decompresses packet.data if present.
        Validates expected_size.
        Returns a new Packet with decompressed bytes.
        """

        start = time.time()

        # Nothing to decompress
        if packet.data is None:
            latency = int((time.time() - start) * 1000)
            self._last_3d = CM3D(
                axis_x="decompress_packet",
                axis_y=["no_data"],
                axis_z={"latency_ms": latency},
            )
            return packet.copy(compressed=False)

        expected = packet.metadata.get("expected_size")
        if expected is None:
            raise ValueError("Compressed packet missing expected_size metadata")

        try:
            raw = self.engine.decompress(packet.data, expected)
        except Exception as e:
            raise RuntimeError(f"BitDrop decompression failed: {e}")

        # Corruption check
        if len(raw) != expected:
            raise RuntimeError(
                f"Decompression size mismatch: expected {expected}, got {len(raw)}"
            )

        latency = int((time.time() - start) * 1000)

        # 3D‑MAX telemetry
        self._last_3d = CM3D(
            axis_x="decompress_packet",
            axis_y=[f"expected:{expected}", f"actual:{len(raw)}"],
            axis_z={"latency_ms": latency, "ok": True},
        )

        return packet.copy(
            data=raw,
            compressed=False,
            metadata={**packet.metadata, "codec": "bitdrop", "validated": True},
        )

    # ------------------------------------------------------------
    # PACKET OUTPUT COMPRESSION
    # ------------------------------------------------------------
    def compress_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compresses the result dict into a binary payload.
        Adds metadata:
            • expected_size
            • codec
            • ratio
            • fingerprint
        """

        start = time.time()

        raw_bytes = str(result).encode("utf-8")
        raw_size = len(raw_bytes)

        try:
            blob, meta = self.engine.compress(raw_bytes)
        except Exception as e:
            raise RuntimeError(f"BitDrop compression failed: {e}")

        latency = int((time.time() - start) * 1000)

        # 3D‑MAX telemetry
        self._last_3d = CM3D(
            axis_x="compress_output",
            axis_y=[f"raw_size:{raw_size}", f"ratio:{meta.get('ratio')}"],
            axis_z={
                "latency_ms": latency,
                "codec": meta.get("codec", "bitdrop"),
                "fingerprint": meta.get("fingerprint"),
            },
        )

        return {
            "compressed": True,
            "payload": blob,
            "expected_size": raw_size,
            "codec": meta.get("codec", "bitdrop"),
            "ratio": meta.get("ratio"),
            "fingerprint": meta.get("fingerprint"),
        }

    # ------------------------------------------------------------
    # SAFE WRAPPER (optional)
    # ------------------------------------------------------------
    def safe_compress(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safe compression wrapper that never throws.
        Returns structured error envelopes.
        """

        try:
            return self.compress_output(result)
        except Exception as e:
            self._last_3d = CM3D(
                axis_x="safe_compress",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )
            return {
                "compressed": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "fallback": result,
            }

    def safe_decompress(self, packet: Packet) -> Packet:
        """
        Safe decompression wrapper that never throws.
        Returns packet with error metadata instead of raising.
        """

        try:
            return self.decompress_packet(packet)
        except Exception as e:
            self._last_3d = CM3D(
                axis_x="safe_decompress",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )
            return packet.copy(
                compressed=False,
                metadata={
                    **packet.metadata,
                    "decompression_error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

