# bitdrop_core/ai/metamodel/book_metadata.py

from __future__ import annotations
from typing import List, Dict, Optional, Any
import zlib

from .book_index import MODEL_BOOK


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
# CACHES (1D)
# ------------------------------------------------------------
_role_cache: Dict[int, Optional[Dict[str, Any]]] = {}
_intent_cache: Dict[int, Optional[Dict[str, Any]]] = {}
_describe_cache: Optional[str] = None


# ------------------------------------------------------------
# ORIGINAL 1D API (max-improved)
# ------------------------------------------------------------
def get_all_pages() -> List[Dict[str, Any]]:
    return MODEL_BOOK


def find_by_role(role: str) -> Optional[Dict[str, Any]]:
    role_clean = MicroStringStripper.clean(role or "")
    if not role_clean:
        return None

    key = role_clean.lower()
    h = MicroFastHash.h(key)
    cached = _role_cache.get(h)
    if cached is not None:
        return cached

    for page in MODEL_BOOK:
        if (page.get("role") or "").lower() == key:
            _role_cache[h] = page
            return page

    _role_cache[h] = None
    return None


def find_by_intent(intent: str) -> Optional[Dict[str, Any]]:
    intent_clean = MicroStringStripper.clean(intent or "")
    if not intent_clean:
        return None

    key = intent_clean.lower()
    h = MicroFastHash.h(key)
    cached = _intent_cache.get(h)
    if cached is not None:
        return cached

    for page in MODEL_BOOK:
        if (page.get("intent") or "").lower() == key:
            _intent_cache[h] = page
            return page

    _intent_cache[h] = None
    return None


def describe_book() -> str:
    global _describe_cache
    if _describe_cache is not None:
        return _describe_cache

    lines: List[str] = []
    for page in MODEL_BOOK:
        lines.append(
            f"- {page['name']} ({page['role']} / {page['chapter']}): {page['summary']}"
        )
    _describe_cache = "\n".join(lines)
    return _describe_cache


# ------------------------------------------------------------
# 3D MAX WRAPPER
# ------------------------------------------------------------
class BookMetadata3D:
    """
    3D-max metadata helper over MODEL_BOOK:
        • Reuses 1D functions (cached)
        • Accepts 3D grids [D][H][W] of roles/intents
        • Returns 3D grids of pages
    """

    @staticmethod
    def find_by_role_3d(
        roles_3d: List[List[List[str]]],
    ) -> List[List[List[Optional[Dict[str, Any]]]]]:
        depth = len(roles_3d)
        out: List[List[List[Optional[Dict[str, Any]]]]] = []

        for d in range(depth):
            plane = roles_3d[d]
            plane_out: List[List[Optional[Dict[str, Any]]]] = []
            for row in plane:
                row_out: List[Optional[Dict[str, Any]]] = []
                for role in row:
                    row_out.append(find_by_role(role))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    @staticmethod
    def find_by_intent_3d(
        intents_3d: List[List[List[str]]],
    ) -> List[List[List[Optional[Dict[str, Any]]]]]:
        depth = len(intents_3d)
        out: List[List[List[Optional[Dict[str, Any]]]]] = []

        for d in range(depth):
            plane = intents_3d[d]
            plane_out: List[List[Optional[Dict[str, Any]]]] = []
            for row in plane:
                row_out: List[Optional[Dict[str, Any]]] = []
                for intent in row:
                    row_out.append(find_by_intent(intent))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    @staticmethod
    def describe_book_3d(
        depth: int,
        height: int,
        width: int,
    ) -> List[List[List[str]]]:
        """
        Returns a 3D grid filled with the same book description.
        Useful when you want a broadcast-style description across a 3D mesh.
        """
        desc = describe_book()
        return [
            [
                [desc for _ in range(width)]
                for _ in range(height)
            ]
            for _ in range(depth)
        ]
