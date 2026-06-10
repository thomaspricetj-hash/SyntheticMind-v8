# bitdrop_core/ai/metamodel/bitdrop_manager.py

from __future__ import annotations
from typing import Any, List, Dict, Tuple, Optional
import hashlib
import zlib
import struct
import json

from .bitdrop_kernel_adapter import BitDropKernelAdapter


# ------------------------------------------------------------
# MICRO HELPERS (SHARED)
# ------------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()

    @staticmethod
    def clean(text: str) -> str:
        return " ".join((text or "").split())


class MicroTokenLimiter:
    __slots__ = ()

    @staticmethod
    def limit(text: str, max_chars: int = 1_000_000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroFastHash:
    __slots__ = ()

    @staticmethod
    def h_bytes(data: bytes) -> int:
        return zlib.crc32(data)

    @staticmethod
    def h_text(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


# ------------------------------------------------------------
# BitDropManager (1D, maxed)
# ------------------------------------------------------------
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
        self.compression_level = max(1, min(9, compression_level))

        # Caches
        self._collapse_text_cache: Dict[int, bytes] = {}
        self._expand_text_cache: Dict[int, str] = {}
        self._collapse_bytes_cache: Dict[int, bytes] = {}
        self._expand_bytes_cache: Dict[int, bytes] = {}
        self._compress_json_cache: Dict[int, bytes] = {}
        self._decompress_json_cache: Dict[int, Any] = {}

    # ------------------------------------------------------------
    # CHUNKING / BLOOM / PATTERNS (for routing, not stored in blob)
    # ------------------------------------------------------------
    def chunk_text(self, text: str) -> List[str]:
        text = MicroStringStripper.clean(text or "")
        text = MicroTokenLimiter.limit(text)
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
        payload = data
        all_tags = bytearray()

        for _ in range(self.max_passes):
            payload, tags, count = self.kernel.collapse_pass(payload)
            all_tags.extend(tags)
            if count == 0:
                break

        return payload, bytes(all_tags)

    def _compute_crc32(self, payload: bytes, tags: bytes) -> int:
        return zlib.crc32(payload + tags) & 0xFFFFFFFF

    def _pack_pts_blob(self, payload: bytes, tags: bytes) -> bytes:
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
        header_size = 4 + 4 + 4 + 4
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

        expected_crc = self._compute_crc32(payload, tags)
        if expected_crc != crc:
            return b"", b""

        return payload, tags

    def is_valid_blob(self, blob: bytes) -> bool:
        if not blob:
            return False
        payload, tags = self._unpack_pts_blob(blob)
        return bool(payload or tags)

    # ------------------------------------------------------------
    # PUBLIC: text collapse / expand (binary-first)
    # ------------------------------------------------------------
    def collapse_text(self, text: str) -> bytes:
        if not text:
            return b""

        text = MicroStringStripper.clean(text)
        text = MicroTokenLimiter.limit(text)
        h = MicroFastHash.h_text(text)
        cached = self._collapse_text_cache.get(h)
        if cached is not None:
            return cached

        raw = text.encode("utf-8")
        payload, tags = self._multi_pass_collapse(raw)
        pts_blob = self._pack_pts_blob(payload, tags)
        compressed = zlib.compress(pts_blob, level=self.compression_level)

        self._collapse_text_cache[h] = compressed
        return compressed

    def expand_text(self, blob: bytes) -> str:
        if not blob:
            return ""

        h = MicroFastHash.h_bytes(blob)
        cached = self._expand_text_cache.get(h)
        if cached is not None:
            return cached

        try:
            pts_blob = zlib.decompress(blob)
        except Exception:
            pts_blob = blob

        payload, _tags = self._unpack_pts_blob(pts_blob)
        if not payload:
            self._expand_text_cache[h] = ""
            return ""

        try:
            txt = payload.decode("utf-8", errors="ignore")
        except Exception:
            txt = ""

        self._expand_text_cache[h] = txt
        return txt

    # ------------------------------------------------------------
    # PUBLIC: raw bytes collapse / expand
    # ------------------------------------------------------------
    def collapse_bytes(self, data: bytes) -> bytes:
        if not data:
            return b""

        h = MicroFastHash.h_bytes(data)
        cached = self._collapse_bytes_cache.get(h)
        if cached is not None:
            return cached

        payload, tags = self._multi_pass_collapse(data)
        pts_blob = self._pack_pts_blob(payload, tags)
        compressed = zlib.compress(pts_blob, level=self.compression_level)

        self._collapse_bytes_cache[h] = compressed
        return compressed

    def expand_bytes(self, blob: bytes) -> bytes:
        if not blob:
            return b""

        h = MicroFastHash.h_bytes(blob)
        cached = self._expand_bytes_cache.get(h)
        if cached is not None:
            return cached

        try:
            pts_blob = zlib.decompress(blob)
        except Exception:
            pts_blob = blob

        payload, _tags = self._unpack_pts_blob(pts_blob)
        self._expand_bytes_cache[h] = payload
        return payload

    # ------------------------------------------------------------
    # PUBLIC: JSON / struct compression (binary-first)
    # ------------------------------------------------------------
    def compress_json(self, obj: Any) -> bytes:
        txt = json.dumps(obj, separators=(",", ":"))
        txt = MicroStringStripper.clean(txt)
        txt = MicroTokenLimiter.limit(txt)
        h = MicroFastHash.h_text(txt)
        cached = self._compress_json_cache.get(h)
        if cached is not None:
            return cached

        blob = self.collapse_text(txt)
        self._compress_json_cache[h] = blob
        return blob

    def decompress_json(self, blob: bytes) -> Any:
        if not blob:
            return None

        h = MicroFastHash.h_bytes(blob)
        cached = self._decompress_json_cache.get(h)
        if cached is not None:
            return cached

        txt = self.expand_text(blob)
        if not txt:
            self._decompress_json_cache[h] = None
            return None
        try:
            obj = json.loads(txt)
        except Exception:
            obj = None

        self._decompress_json_cache[h] = obj
        return obj


# ------------------------------------------------------------
# BitDropManager3D (3D-max wrapper)
# ------------------------------------------------------------
class BitDropManager3D:
    """
    3D BitDrop manager:
        • Reuses BitDropManager core logic
        • Operates on 3D grids [D][H][W]
        • Amplifies caches across 3D space
    """

    def __init__(
        self,
        chunk_size: int = 256,
        bloom_size: int = 2048,
        bloom_hashes: int = 3,
        lib_path: Optional[str] = None,
        max_passes: int = 8,
        compression_level: int = 6,
    ) -> None:
        self.manager = BitDropManager(
            chunk_size=chunk_size,
            bloom_size=bloom_size,
            bloom_hashes=bloom_hashes,
            lib_path=lib_path,
            max_passes=max_passes,
            compression_level=compression_level,
        )

    # 3D text collapse
    def collapse_text_3d(
        self,
        texts_3d: List[List[List[str]]],
    ) -> List[List[List[bytes]]]:
        depth = len(texts_3d)
        out: List[List[List[bytes]]] = []

        for d in range(depth):
            plane = texts_3d[d]
            plane_out: List[List[bytes]] = []
            for row in plane:
                row_out: List[bytes] = []
                for t in row:
                    row_out.append(self.manager.collapse_text(t))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D text expand
    def expand_text_3d(
        self,
        blobs_3d: List[List[List[bytes]]],
    ) -> List[List[List[str]]]:
        depth = len(blobs_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = blobs_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for b in row:
                    row_out.append(self.manager.expand_text(b))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D bytes collapse
    def collapse_bytes_3d(
        self,
        data_3d: List[List[List[bytes]]],
    ) -> List[List[List[bytes]]]:
        depth = len(data_3d)
        out: List[List[List[bytes]]] = []

        for d in range(depth):
            plane = data_3d[d]
            plane_out: List[List[bytes]] = []
            for row in plane:
                row_out: List[bytes] = []
                for b in row:
                    row_out.append(self.manager.collapse_bytes(b))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D bytes expand
    def expand_bytes_3d(
        self,
        blobs_3d: List[List[List[bytes]]],
    ) -> List[List[List[bytes]]]:
        depth = len(blobs_3d)
        out: List[List[List[bytes]]] = []

        for d in range(depth):
            plane = blobs_3d[d]
            plane_out: List[List[bytes]] = []
            for row in plane:
                row_out: List[bytes] = []
                for b in row:
                    row_out.append(self.manager.expand_bytes(b))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D JSON compress
    def compress_json_3d(
        self,
        objs_3d: List[List[List[Any]]],
    ) -> List[List[List[bytes]]]:
        depth = len(objs_3d)
        out: List[List[List[bytes]]] = []

        for d in range(depth):
            plane = objs_3d[d]
            plane_out: List[List[bytes]] = []
            for row in plane:
                row_out: List[bytes] = []
                for obj in row:
                    row_out.append(self.manager.compress_json(obj))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    # 3D JSON decompress
    def decompress_json_3d(
        self,
        blobs_3d: List[List[List[bytes]]],
    ) -> List[List[List[Any]]]:
        depth = len(blobs_3d)
        out: List[List[List[Any]]] = []

        for d in range(depth):
            plane = blobs_3d[d]
            plane_out: List[List[Any]] = []
            for row in plane:
                row_out: List[Any] = []
                for b in row:
                    row_out.append(self.manager.decompress_json(b))
                plane_out.append(row_out)
            out.append(plane_out)

        return out


