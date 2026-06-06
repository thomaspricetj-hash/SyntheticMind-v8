# bitdrop_core/ai/metamodel/bitdrop_manager.py

from __future__ import annotations
from typing import Any, List, Dict, Tuple, Optional
import hashlib
import zlib
import struct
import json

from .bitdrop_kernel_adapter import BitDropKernelAdapter


class BitDropManager:
    """
    BitDrop v3 – Binary-native compression manager with integrity checks and tunable compression.

    Everything that crosses a boundary (text, JSON, metadata) is:
        • converted to bytes
        • collapsed by the GPU BitDrop kernel (multi-pass)
        • wrapped in a flat PTS binary block
        • compressed by a high-level compressor (zlib stand-in)

    Blob layout (flat PTS, performance-optimized):

        [ magic 4B ]        = b'BDP3'
        [ payload_len 4B ]  = uint32
        [ tags_len 4B ]     = uint32
        [ crc32 4B ]        = uint32 over payload||tags
        [ payload bytes ]   = collapsed payload
        [ tags bytes ]      = tag stream (1 byte per position)

    Positions are implicit by index; rule IDs are implicit via tag→rule table.
    """

    MAGIC = b"BDP3"

    def __init__(
        self,
        chunk_size: int = 256,
        bloom_size: int = 2048,
        bloom_hashes: int = 3,
        lib_path: Optional[str] = None,
        max_passes: int = 8,
        compression_level: int = 6,
    ) -> None:
        self.chunk_size = chunk_size
        self.bloom_size = bloom_size
        self.bloom_hashes = bloom_hashes
        self.kernel = BitDropKernelAdapter(lib_path=lib_path)
        self.max_passes = max_passes
        # zlib compression level (1–9)
        self.compression_level = max(1, min(9, compression_level))

    # ------------------------------------------------------------
    # CHUNKING / BLOOM / PATTERNS (for routing, not stored in blob)
    # ------------------------------------------------------------
    def chunk_text(self, text: str) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []
        return [
            text[i : i + self.chunk_size]
            for i in range(0, len(text), self.chunk_size)
        ]

    def build_bloom(self, chunks: List[str]) -> set:
        bloom = set()
        for chunk in chunks:
            for i in range(self.bloom_hashes):
                h = hashlib.sha256(f"{i}:{chunk}".encode("utf-8")).hexdigest()
                idx = int(h, 16) % self.bloom_size
                bloom.add(idx)
        return bloom

    def extract_patterns(self, chunks: List[str]) -> Dict[str, Any]:
        joined = " ".join(chunks).lower()
        has_code = any(
            m in joined
            for m in ["def ", "class ", "import ", "console.log", "#include", "public static void"]
        )
        has_math = any(
            m in joined
            for m in ["integral", "derivative", "theorem", "lemma", "∫", "∑", "√"]
        )
        avg_len = sum(len(c) for c in chunks) / len(chunks) if chunks else 0.0

        return {
            "has_code": has_code,
            "has_math": has_math,
            "avg_len": avg_len,
        }

    # ------------------------------------------------------------
    # INTERNAL: multi-pass collapse + flat PTS packing
    # ------------------------------------------------------------
    def _multi_pass_collapse(self, data: bytes) -> Tuple[bytes, bytes]:
        """
        Run the GPU kernel repeatedly until collapse_count == 0
        or max_passes is reached.

        Returns:
            final_payload, accumulated_tags

        Tags are accumulated across passes; positions are implicit by index.
        """
        payload = data
        all_tags = bytearray()

        for _ in range(self.max_passes):
            payload, tags, count = self.kernel.collapse_pass(payload)
            all_tags.extend(tags)
            if count == 0:
                break

        return payload, bytes(all_tags)

    def _compute_crc32(self, payload: bytes, tags: bytes) -> int:
        """
        Compute CRC32 over payload||tags for integrity checking.
        """
        return zlib.crc32(payload + tags) & 0xFFFFFFFF

    def _pack_pts_blob(self, payload: bytes, tags: bytes) -> bytes:
        """
        Build the flat PTS binary block:

            magic | payload_len | tags_len | crc32 | payload | tags
        """
        crc = self._compute_crc32(payload, tags)
        header = struct.pack(
            ">4sIII",
            self.MAGIC,
            len(payload),
            len(tags),
            crc,
        )
        return header + payload + tags

    def _unpack_pts_blob(self, blob: bytes) -> Tuple[bytes, bytes]:
        """
        Parse the flat PTS binary block and verify CRC.
        Returns (payload, tags); returns (b"", b"") on failure.
        """
        header_size = 4 + 4 + 4 + 4  # magic + payload_len + tags_len + crc32
        if len(blob) < header_size:
            return b"", b""

        magic, payload_len, tags_len, crc = struct.unpack(">4sIII", blob[:header_size])
        if magic != self.MAGIC:
            return b"", b""

        start_payload = header_size
        end_payload = start_payload + payload_len
        start_tags = end_payload
        end_tags = start_tags + tags_len

        if end_tags > len(blob):
            return b"", b""

        payload = blob[start_payload:end_payload]
        tags = blob[start_tags:end_tags]

        # Verify CRC
        expected_crc = self._compute_crc32(payload, tags)
        if expected_crc != crc:
            return b"", b""

        return payload, tags

    def is_valid_blob(self, blob: bytes) -> bool:
        """
        Quick integrity check: validates magic, lengths, and CRC.
        """
        if not blob:
            return False
        payload, tags = self._unpack_pts_blob(blob)
        return bool(payload or tags)

    # ------------------------------------------------------------
    # PUBLIC: text collapse / expand (binary-first)
    # ------------------------------------------------------------
    def collapse_text(self, text: str) -> bytes:
        """
        Full forward pipeline for text:

            text -> UTF-8 bytes
                 -> multi-pass GPU collapse (payload + tags)
                 -> PTS binary block
                 -> high-level compression

        Returns:
            opaque binary blob (bytes)
        """
        if not text:
            return b""

        raw = text.encode("utf-8")

        payload, tags = self._multi_pass_collapse(raw)
        pts_blob = self._pack_pts_blob(payload, tags)

        compressed = zlib.compress(pts_blob, level=self.compression_level)
        return compressed

    def expand_text(self, blob: bytes) -> str:
        """
        Reverse pipeline (partial until full kernel expand is wired):

            blob -> decompressor -> PTS block -> payload + tags

        For now:
            we decode payload as UTF-8 best-effort.
            When you expose kernel expand + PTS reconstruction,
            this will call that instead.
        """
        if not blob:
            return ""

        try:
            pts_blob = zlib.decompress(blob)
        except Exception:
            # If it's not compressed, treat as raw PTS blob
            pts_blob = blob

        payload, _tags = self._unpack_pts_blob(pts_blob)
        if not payload:
            return ""

        try:
            return payload.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    # ------------------------------------------------------------
    # PUBLIC: raw bytes collapse / expand
    # ------------------------------------------------------------
    def collapse_bytes(self, data: bytes) -> bytes:
        """
        Same as collapse_text, but starts from raw bytes instead of str.
        """
        if not data:
            return b""

        payload, tags = self._multi_pass_collapse(data)
        pts_blob = self._pack_pts_blob(payload, tags)
        compressed = zlib.compress(pts_blob, level=self.compression_level)
        return compressed

    def expand_bytes(self, blob: bytes) -> bytes:
        """
        Reverse of collapse_bytes, returning raw bytes (payload only).
        """
        if not blob:
            return b""

        try:
            pts_blob = zlib.decompress(blob)
        except Exception:
            pts_blob = blob

        payload, _tags = self._unpack_pts_blob(pts_blob)
        return payload

    # ------------------------------------------------------------
    # PUBLIC: JSON / struct compression (binary-first)
    # ------------------------------------------------------------
    def compress_json(self, obj: Any) -> bytes:
        """
        Serialize a Python object (dict/list/etc.) to compact JSON text,
        then run it through the same BitDrop + compression pipeline.

        Output is a fully binary blob suitable for fast transport/storage.
        """
        txt = json.dumps(obj, separators=(",", ":"))
        return self.collapse_text(txt)

    def decompress_json(self, blob: bytes) -> Any:
        """
        Reverse of compress_json:
            blob -> BitDrop expand -> JSON text -> Python object

        Returns:
            Parsed Python object on success, or None on failure.
        """
        txt = self.expand_text(blob)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None



