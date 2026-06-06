from __future__ import annotations
from typing import Any, Dict, Optional, List
import zlib


# ------------------------------------------------------------
# MICRO HELPERS
# ------------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()
    @staticmethod
    def clean(text: str) -> str:
        return " ".join(text.split())


class MicroTokenLimiter:
    __slots__ = ()
    @staticmethod
    def limit(text: str, max_chars: int = 6000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroFastHash:
    __slots__ = ()
    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


class MicroEntityExtractor:
    __slots__ = ()
    @staticmethod
    def extract(query: str) -> List[str]:
        tokens = query.strip().split()
        entities: List[str] = []
        current: List[str] = []

        for tok in tokens:
            if tok[:1].isupper():
                current.append(tok)
            else:
                if current:
                    entities.append(" ".join(current))
                    current = []
        if current:
            entities.append(" ".join(current))

        seen = set()
        uniq = []
        for e in entities:
            if e not in seen:
                uniq.append(e)
                seen.add(e)
        return uniq


class MicroSafeCall:
    __slots__ = ()
    @staticmethod
    def call(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return e


class MicroListExtend:
    __slots__ = ()
    @staticmethod
    def extend_safe(target: List[Any], value: Any):
        if isinstance(value, list):
            target.extend(value)
        elif value:
            target.append(value)


# ------------------------------------------------------------
# MAIN HELPER
# ------------------------------------------------------------
class WorldModelHelper:
    """
    Ultra-fast WorldModelHelper with integrated micro-helpers.
    """

    def __init__(self, world_model: Optional[Any]) -> None:
        self.world_model = world_model
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:

        if self.world_model is None:
            return {"enabled": False}

        query = (query or "").strip()
        if not query:
            return {"enabled": True, "entities": [], "relations": [], "freeform": None, "errors": []}

        # Micro: normalize + limit
        query = MicroStringStripper.clean(query)
        query = MicroTokenLimiter.limit(query)

        # Micro: fast dedupe
        h = MicroFastHash.h(query)
        if h in self.cache:
            return self.cache[h]

        out: Dict[str, Any] = {
            "enabled": True,
            "entities": [],
            "relations": [],
            "freeform": None,
            "errors": [],
        }

        try:
            # 1) Extract entities
            entities = MicroEntityExtractor.extract(query)
            out["entities"] = entities

            # 2) Query graph relations
            relations: List[Any] = []

            for ent in entities:
                result = MicroSafeCall.call(self.world_model.query, ent)

                if isinstance(result, Exception):
                    out["errors"].append(f"relation({ent}): {result}")
                else:
                    MicroListExtend.extend_safe(relations, result)

            out["relations"] = relations

            # 3) Freeform reasoning
            if hasattr(self.world_model, "query_freeform"):
                result = MicroSafeCall.call(self.world_model.query_freeform, query)

                if isinstance(result, Exception):
                    out["errors"].append(f"freeform: {result}")
                else:
                    out["freeform"] = result

        except Exception as e:
            out["errors"].append(f"fatal: {e}")

        # Cache
        self.cache[h] = out
        return out


