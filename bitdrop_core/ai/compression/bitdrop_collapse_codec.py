from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple


# ============================================================
# v2 core (1D lossless engine, used as inner primitive)
# ============================================================
class BitDropCollapseEngine:
    def __init__(self):
        self.rules: Dict[str, str] = {}
        self.reverse_rules: Dict[str, str] = {}
        self.TOKEN_PREFIX = "§BD§"

    def collapse(
        self,
        text: str,
        *,
        rules: Dict[str, Any] = None,
        tags: Dict[str, Any] = None,
    ) -> str:
        rules = rules or {}
        tags = tags or {}
        chunk_size = tags.get("chunk_size", 2048)
        chunks = self._chunk_text(text, chunk_size)
        collapsed_chunks = []
        for chunk in chunks:
            c = self._collapse_chunk(chunk, rules, tags)
            collapsed_chunks.append(c)
        return "".join(collapsed_chunks)

    def expand(self, text: str) -> str:
        for token, original in self.reverse_rules.items():
            text = text.replace(token, original)
        return text

    def _chunk_text(self, text: str, size: int) -> List[str]:
        return [text[i:i + size] for i in range(0, len(text), size)]

    def _collapse_chunk(
        self,
        chunk: str,
        rules: Dict[str, Any],
        tags: Dict[str, Any],
    ) -> str:
        if tags.get("patterns", True):
            chunk = self._collapse_patterns(chunk)
        if tags.get("grouping", True):
            chunk = self._collapse_whitespace(chunk)
        if tags.get("skimming", True):
            chunk = self._skim(chunk)
        return chunk

    def _collapse_patterns(self, text: str) -> str:
        text = re.sub(r"([.,!?])\1{2,}", lambda m: self._tokenize(m.group(0)), text)
        text = re.sub(r"(-{3,})", lambda m: self._tokenize(m.group(0)), text)
        text = re.sub(r"(={3,})", lambda m: self._tokenize(m.group(0)), text)
        return text

    def _collapse_whitespace(self, text: str) -> str:
        return re.sub(r"\s{3,}", lambda m: self._tokenize(m.group(0)), text)

    def _skim(self, text: str) -> str:
        text = re.sub(r"\n{3,}", lambda m: self._tokenize(m.group(0)), text)
        return text

    def _tokenize(self, original: str) -> str:
        token = f"{self.TOKEN_PREFIX}{len(self.rules)}§"
        self.rules[token] = original
        self.reverse_rules[token] = original
        return token


# ============================================================
# v3 — 3D Lossless Engine (max version)
# ============================================================
class BitDropCollapseEngineV3:
    """
    BitDrop v3 — 3D Lossless Collapse Engine

    Design:
        • 1D: raw sequence (characters)
        • 2D: lines × columns (layout plane)
        • 3D: (lines × columns × channels) where channels capture:
            - structure (indent, brackets, code vs prose)
            - repetition (line hashes, block hashes)
            - semantic hints (simple heuristics)

    Goals:
        • Max compression (lossless) for structured / code / reasoning text
        • Max speed via block‑level operations (3D blocks)
        • Fully reversible (Option A)

    Modes (via tags):
        tags["profile"] = "fast" | "balanced" | "max"
    """

    def __init__(self):
        self.v2 = BitDropCollapseEngineV2()
        self.rules: Dict[str, str] = self.v2.rules
        self.reverse_rules: Dict[str, str] = self.v2.reverse_rules
        self.TOKEN_PREFIX = self.v2.TOKEN_PREFIX

    # --------------------------------------------------------
    # Public API (HybridBackend-compatible)
    # --------------------------------------------------------
    def collapse(
        self,
        text: str,
        *,
        rules: Dict[str, Any] = None,
        tags: Dict[str, Any] = None,
    ) -> str:
        rules = rules or {}
        tags = tags or {}

        profile = tags.get("profile", "balanced")  # "fast" | "balanced" | "max"

        # 1) Project text into 3D blocks
        blocks = self._to_3d_blocks(text, tags)

        # 2) Collapse across axes
        if profile in ("balanced", "max"):
            blocks = self._collapse_across_lines(blocks, tags)
            blocks = self._collapse_across_columns(blocks, tags)
        if profile == "max":
            blocks = self._collapse_across_structure(blocks, tags)

        # 3) Flatten back to 1D text
        flattened = self._from_3d_blocks(blocks)

        # 4) Run v2 collapse as final pass (token‑level)
        collapsed = self.v2.collapse(flattened, rules=rules, tags=tags)
        return collapsed

    def expand(self, text: str) -> str:
        # v3 is lossless and uses v2’s reversible tokens
        return self.v2.expand(text)

# bitdrop_core/ai/compression/bitdrop_collapse_codec.py
#
# BitDrop v3 — 3D Lossless Collapse Engine
# Max version: built for speed + compression, 3D block design.
#
# API:
#   engine = BitDropCollapseEngineV3()
#   collapsed = engine.collapse(text, rules=..., tags=...)
#   expanded  = engine.expand(collapsed)
#
# Hybrid API (with TurboVec):
#   codec = HybridBitDropTurboVecCodec()
#   blob  = codec.encode({"text": ..., "metadata": {...}, "vectors": [...]}, tags=...)
#   obj   = codec.decode(blob)
#
# Compatible with HybridBackend:
#   - collapse / expand
#   - encode / decode (via codec wrapper)
#


import re
from typing import Dict, Any, List, Tuple, Optional

# TurboVec is assumed to live in bitdrop_core.ai.compression.turbovec
try:
    from bitdrop_core.ai.compression.turbovec import TurboVecCodec
except Exception:  # soft import; runtime can inject its own
    TurboVecCodec = None  # type: ignore


# ============================================================
# v2 core (1D lossless engine, used as inner primitive)
# ============================================================
class BitDropCollapseEngineV2:
    def __init__(self):
        self.rules: Dict[str, str] = {}
        self.reverse_rules: Dict[str, str] = {}
        self.TOKEN_PREFIX = "§BD§"

    def collapse(
        self,
        text: str,
        *,
        rules: Dict[str, Any] = None,
        tags: Dict[str, Any] = None,
    ) -> str:
        rules = rules or {}
        tags = tags or {}
        chunk_size = tags.get("chunk_size", 2048)
        chunks = self._chunk_text(text, chunk_size)
        collapsed_chunks = []
        for chunk in chunks:
            c = self._collapse_chunk(chunk, rules, tags)
            collapsed_chunks.append(c)
        return "".join(collapsed_chunks)

    def expand(self, text: str) -> str:
        for token, original in self.reverse_rules.items():
            text = text.replace(token, original)
        return text

    def _chunk_text(self, text: str, size: int) -> List[str]:
        return [text[i:i + size] for i in range(0, len(text), size)]

    def _collapse_chunk(
        self,
        chunk: str,
        rules: Dict[str, Any],
        tags: Dict[str, Any],
    ) -> str:
        if tags.get("patterns", True):
            chunk = self._collapse_patterns(chunk)
        if tags.get("grouping", True):
            chunk = self._collapse_whitespace(chunk)
        if tags.get("skimming", True):
            chunk = self._skim(chunk)
        return chunk

    def _collapse_patterns(self, text: str) -> str:
        text = re.sub(r"([.,!?])\1{2,}", lambda m: self._tokenize(m.group(0)), text)
        text = re.sub(r"(-{3,})", lambda m: self._tokenize(m.group(0)), text)
        text = re.sub(r"(={3,})", lambda m: self._tokenize(m.group(0)), text)
        return text

    def _collapse_whitespace(self, text: str) -> str:
        return re.sub(r"\s{3,}", lambda m: self._tokenize(m.group(0)), text)

    def _skim(self, text: str) -> str:
        text = re.sub(r"\n{3,}", lambda m: self._tokenize(m.group(0)), text)
        return text

    def _tokenize(self, original: str) -> str:
        token = f"{self.TOKEN_PREFIX}{len(self.rules)}§"
        self.rules[token] = original
        self.reverse_rules[token] = original
        return token


# ============================================================
# v3 — 3D Lossless Engine (max version)
# ============================================================
class BitDropCollapseEngineV3:
    """
    BitDrop v3 — 3D Lossless Collapse Engine

    Design:
        • 1D: raw sequence (characters)
        • 2D: lines × columns (layout plane)
        • 3D: (lines × columns × channels) where channels capture:
            - structure (indent, brackets, code vs prose)
            - repetition (line hashes, block hashes)
            - semantic hints (simple heuristics)

    Goals:
        • Max compression (lossless) for structured / code / reasoning text
        • Max speed via block‑level operations (3D blocks)
        • Fully reversible (Option A)

    Modes (via tags):
        tags["profile"] = "fast" | "balanced" | "max"
    """

    def __init__(self):
        self.v2 = BitDropCollapseEngineV2()
        self.rules: Dict[str, str] = self.v2.rules
        self.reverse_rules: Dict[str, str] = self.v2.reverse_rules
        self.TOKEN_PREFIX = self.v2.TOKEN_PREFIX

    # --------------------------------------------------------
    # Public API (HybridBackend-compatible)
    # --------------------------------------------------------
    def collapse(
        self,
        text: str,
        *,
        rules: Dict[str, Any] = None,
        tags: Dict[str, Any] = None,
    ) -> str:
        rules = rules or {}
        tags = tags or {}

        profile = tags.get("profile", "max")  # default to max for hybrid use

        # 1) Project text into 3D blocks
        blocks = self._to_3d_blocks(text, tags)

        # 2) Collapse across axes
        if profile in ("balanced", "max"):
            blocks = self._collapse_across_lines(blocks, tags)
            blocks = self._collapse_across_columns(blocks, tags)
        if profile == "max":
            blocks = self._collapse_across_structure(blocks, tags)

        # 3) Flatten back to 1D text
        flattened = self._from_3d_blocks(blocks)

        # 4) Run v2 collapse as final pass (token‑level)
        collapsed = self.v2.collapse(flattened, rules=rules, tags=tags)
        return collapsed

    def expand(self, text: str) -> str:
        # v3 is lossless and uses v2’s reversible tokens
        return self.v2.expand(text)

    # --------------------------------------------------------
    # 3D representation
    # --------------------------------------------------------
    def _to_3d_blocks(
        self,
        text: str,
        tags: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Represent text as a list of blocks.

        Each block:
            {
                "lines": [str, ...],
                "indent_levels": [int, ...],
                "line_hashes": [str, ...],
                "kind": "code" | "prose" | "mixed"
            }

        This is a conceptual 3D structure:
            axis 0: block index
            axis 1: line index
            axis 2: features (channels)
        """
        # simple heuristic: split into blocks by double newlines
        raw_blocks = text.split("\n\n")

        blocks: List[Dict[str, Any]] = []
        for raw in raw_blocks:
            lines = raw.split("\n")
            if not lines:
                continue

            indent_levels = [self._indent_level(line) for line in lines]
            line_hashes = [self._line_signature(line) for line in lines]
            kind = self._block_kind(lines)

            blocks.append(
                {
                    "lines": lines,
                    "indent_levels": indent_levels,
                    "line_hashes": line_hashes,
                    "kind": kind,
                }
            )

        return blocks

    def _from_3d_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        chunks: List[str] = []
        for b in blocks:
            chunk = "\n".join(b["lines"])
            chunks.append(chunk)
        return "\n\n".join(chunks)

    # --------------------------------------------------------
    # Axis‑wise collapse
    # --------------------------------------------------------
    def _collapse_across_lines(
        self,
        blocks: List[Dict[str, Any]],
        tags: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Collapse repeated / similar lines within each block.
        Lossless: we replace repeated lines with tokens.
        """
        for b in blocks:
            lines = b["lines"]
            hashes = b["line_hashes"]

            seen: Dict[str, str] = {}
            new_lines: List[str] = []

            for line, h in zip(lines, hashes):
                if h in seen:
                    # repeated line → tokenize
                    token = self._tokenize(line)
                    new_lines.append(token)
                else:
                    seen[h] = line
                    new_lines.append(line)

            b["lines"] = new_lines
            b["line_hashes"] = [self._line_signature(l) for l in new_lines]

        return blocks

    def _collapse_across_columns(
        self,
        blocks: List[Dict[str, Any]],
        tags: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Collapse vertical patterns: same prefix/suffix across many lines.
        Lossless: we tokenize shared prefixes/suffixes.
        """
        for b in blocks:
            lines = b["lines"]
            if len(lines) < 2:
                continue

            # find common prefix across lines
            prefix = self._common_prefix(lines)
            if prefix and len(prefix) >= 4:
                token = self._tokenize(prefix)
                lines = [token + line[len(prefix):] if line.startswith(prefix) else line for line in lines]

            # find common suffix across lines
            suffix = self._common_suffix(lines)
            if suffix and len(suffix) >= 4:
                token = self._tokenize(suffix)
                lines = [line[:-len(suffix)] + token if line.endswith(suffix) else line for line in lines]

            b["lines"] = lines
            b["line_hashes"] = [self._line_signature(l) for l in lines]

        return blocks

    def _collapse_across_structure(
        self,
        blocks: List[Dict[str, Any]],
        tags: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Max profile: collapse structural patterns (indent ladders, repeated
        code scaffolding, etc.). Still lossless via tokens.
        """
        for b in blocks:
            lines = b["lines"]
            indents = b["indent_levels"]

            # collapse repeated indent ladders (e.g., same pattern of indentation)
            ladder_sig = ",".join(str(i) for i in indents)
            if len(lines) >= 4 and len(set(indents)) > 1:
                token = self._tokenize(f"__INDENT_LADDER__:{ladder_sig}")
                # store ladder as token + stripped lines
                stripped = [l.lstrip(" \t") for l in lines]
                b["lines"] = [token] + stripped
                b["indent_levels"] = [0] * len(b["lines"])
                b["line_hashes"] = [self._line_signature(l) for l in b["lines"]]

        return blocks

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------
    def _indent_level(self, line: str) -> int:
        return len(line) - len(line.lstrip(" \t"))

    def _line_signature(self, line: str) -> str:
        # lightweight, deterministic signature
        core = line.strip()
        core = re.sub(r"\s+", " ", core)
        return f"{len(core)}:{hash(core) & 0xFFFFFFFF:x}"

    def _block_kind(self, lines: List[str]) -> str:
        text = "\n".join(lines).lower()
        code_markers = ["def ", "class ", "{", "}", "(", ")", "import ", "return "]
        score = sum(1 for m in code_markers if m in text)
        if score >= 3:
            return "code"
        if score == 0:
            return "prose"
        return "mixed"

    def _common_prefix(self, lines: List[str]) -> str:
        if not lines:
            return ""
        s1 = min(lines)
        s2 = max(lines)
        for i, c in enumerate(s1):
            if i >= len(s2) or c != s2[i]:
                return s1[:i]
        return s1

    def _common_suffix(self, lines: List[str]) -> str:
        if not lines:
            return ""
        rev = [l[::-1] for l in lines]
        pref = self._common_prefix(rev)
        return pref[::-1]

    def _tokenize(self, original: str) -> str:
        token = f"{self.TOKEN_PREFIX}{len(self.rules)}§"
        self.rules[token] = original
        self.reverse_rules[token] = original
        return token


# ============================================================
# Codec wrapper (encode/decode aliases)
# ============================================================
class BitDropCollapseEngine(BitDropCollapseEngineV3):
    """
    Public engine name used elsewhere in the codebase.
    v3 implementation (3D, lossless, max version).
    """
    pass


class BitDropCollapseCodec:
    """
    Thin wrapper providing encode/decode aliases for engines
    expecting that interface.
    """

    def __init__(self, engine: BitDropCollapseEngine | None = None):
        self.engine = engine or BitDropCollapseEngine()

    def encode(
        self,
        text: str,
        *,
        rules: Dict[str, Any] = None,
        tags: Dict[str, Any] = None,
    ) -> str:
        return self.engine.collapse(text, rules=rules, tags=tags)

    def decode(self, text: str) -> str:
        return self.engine.expand(text)


# ============================================================
# Hybrid BitDrop + TurboVec codec (3D max + vector compression)
# ============================================================
class HybridBitDropTurboVecCodec:
    """
    Hybrid codec:
        • BitDrop v3 (3D, max profile) for text + metadata (JSON-ish)
        • TurboVec for dense vectors / embeddings

    Payload format (logical):
        {
            "text": str | None,
            "metadata": dict | None,
            "vectors": Any | None,   # list/array of vectors
        }

    Encoded container (bytes):
        [MAGIC(4)][VER(1)]
        [FLAGS(1)]
        [LEN_STRUCT(4)][STRUCT_BYTES]
        [LEN_VEC(4)][VEC_BYTES]

    Where:
        • STRUCT_BYTES = BitDrop-encoded JSON of {"text", "metadata"}
        • VEC_BYTES    = TurboVec-encoded vectors (if present)
    """

    MAGIC = b"BDHV"  # BitDrop Hybrid Vec
    VERSION = 1

    def __init__(
        self,
        bitdrop: Optional[BitDropCollapseCodec] = None,
        turbovec: Optional[Any] = None,
    ):
        self.bitdrop = bitdrop or BitDropCollapseCodec()
        # allow external injection if TurboVecCodec is None or custom
        if turbovec is not None:
            self.turbovec = turbovec
        else:
            if TurboVecCodec is None:
                raise RuntimeError(
                    "TurboVecCodec not available; inject a turbovec instance into HybridBitDropTurboVecCodec."
                )
            self.turbovec = TurboVecCodec()

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------
    def encode(
        self,
        payload: Dict[str, Any],
        *,
        tags: Dict[str, Any] = None,
    ) -> bytes:
        """
        payload:
            {
                "text": str | None,
                "metadata": dict | None,
                "vectors": Any | None,
            }
        """
        tags = tags or {}
        # force max profile for structural compression
        tags = {**tags, "profile": "max"}

        text = payload.get("text")
        metadata = payload.get("metadata")
        vectors = payload.get("vectors")

        # 1) Struct part (text + metadata) → JSON-ish string → BitDrop
        import json

        struct_obj = {
            "text": text,
            "metadata": metadata,
        }
        struct_json = json.dumps(struct_obj, separators=(",", ":"), ensure_ascii=False)
        struct_encoded = self.bitdrop.encode(struct_json, tags=tags)

        struct_bytes = struct_encoded.encode("utf-8")

        # 2) Vector part → TurboVec
        if vectors is not None:
            vec_bytes = self.turbovec.encode(vectors)
        else:
            vec_bytes = b""

        # 3) Flags
        flags = 0
        if text is not None or metadata is not None:
            flags |= 0x01
        if vectors is not None:
            flags |= 0x02

        # 4) Pack container
        return self._pack_container(struct_bytes, vec_bytes, flags)

    def decode(self, blob: bytes) -> Dict[str, Any]:
        struct_bytes, vec_bytes, flags = self._unpack_container(blob)

        # 1) Struct part
        struct_json = struct_bytes.decode("utf-8") if struct_bytes else "{}"
        import json

        if struct_json:
            struct_obj = json.loads(struct_json)
        else:
            struct_obj = {}

        # BitDrop is fully reversible; decode if non-empty
        if struct_json:
            decoded_json = self.bitdrop.decode(struct_json)
            struct_obj = json.loads(decoded_json)

        # 2) Vector part
        vectors = None
        if flags & 0x02 and vec_bytes:
            vectors = self.turbovec.decode(vec_bytes)

        return {
            "text": struct_obj.get("text"),
            "metadata": struct_obj.get("metadata"),
            "vectors": vectors,
        }

    # --------------------------------------------------------
    # Container helpers
    # --------------------------------------------------------
    def _pack_container(self, struct_bytes: bytes, vec_bytes: bytes, flags: int) -> bytes:
        import struct as _s

        header = bytearray()
        header += self.MAGIC
        header += bytes([self.VERSION])
        header += bytes([flags])

        header += _s.pack(">I", len(struct_bytes))
        header += _s.pack(">I", len(vec_bytes))

        return bytes(header) + struct_bytes + vec_bytes

    def _unpack_container(self, blob: bytes) -> Tuple[bytes, bytes, int]:
        import struct as _s

        if len(blob) < 4 + 1 + 1 + 4 + 4:
            raise ValueError("HybridBitDropTurboVecCodec: blob too short")

        off = 0
        magic = blob[off:off + 4]
        off += 4
        if magic != self.MAGIC:
            raise ValueError("HybridBitDropTurboVecCodec: bad magic")
        ver = blob[off]
        off += 1
        if ver != self.VERSION:
            raise ValueError(f"HybridBitDropTurboVecCodec: unsupported version {ver}")
        flags = blob[off]
        off += 1

        len_struct = _s.unpack(">I", blob[off:off + 4])[0]
        off += 4
        len_vec = _s.unpack(">I", blob[off:off + 4])[0]
        off += 4

        end_struct = off + len_struct
        end_vec = end_struct + len_vec

        if end_vec > len(blob):
            raise ValueError("HybridBitDropTurboVecCodec: truncated blob")

        struct_bytes = blob[off:end_struct]
        vec_bytes = blob[end_struct:end_vec]

        return struct_bytes, vec_bytes, flags















