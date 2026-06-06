# syntheticmind/context/compression_manager.py

from __future__ import annotations
from typing import Any, Dict, Optional
from dataclasses import dataclass
import traceback

from ...bitdrop.compressor import BitDropCompressor
from .packet import Packet


@dataclass
class CompressionResult:
    data: bytes
    size: int
    ratio: float
    codec: str
    fingerprint: str


class CompressionManager:
    """
    Connects Packet objects to the BitDrop GPU compression engine.
    Handles:
        • packet decompression
        • packet recompression
        • binary payloads
        • metadata
        • corruption detection
        • safe fallbacks
        • structured envelopes
    """

    def __init__(self):
        self.engine = BitDropCompressor.instance()

    # ------------------------------------------------------------
    # PACKET DECOMPRESSION
    # ------------------------------------------------------------
    def decompress_packet(self, packet: Packet) -> Packet:
        """
        Decompresses packet.data if present.
        Validates expected_size.
        Returns a new Packet with decompressed bytes.
        """

        # Nothing to decompress
        if packet.data is None:
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

        # Convert dict → bytes
        raw_bytes = str(result).encode("utf-8")
        raw_size = len(raw_bytes)

        try:
            blob, meta = self.engine.compress(raw_bytes)
            # meta contains: ratio, fingerprint, codec, etc.
        except Exception as e:
            raise RuntimeError(f"BitDrop compression failed: {e}")

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
            return packet.copy(
                compressed=False,
                metadata={
                    **packet.metadata,
                    "decompression_error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

