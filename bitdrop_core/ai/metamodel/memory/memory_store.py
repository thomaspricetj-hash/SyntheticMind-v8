from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os
import json
import time


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Store3D:
    op: str
    path: str
    count: int
    latency_ms: float
    extra: Dict[str, Any]


_last_3d_store: Optional[Store3D] = None


def _3d(op: str, path: str, count: int, start: float, extra: Dict[str, Any] | None = None):
    global _last_3d_store
    latency = (time.time() - start) * 1000.0
    _last_3d_store = Store3D(
        op=op,
        path=path,
        count=count,
        latency_ms=latency,
        extra=extra or {},
    )
    return _last_3d_store


# ============================================================
# MEMORY STORE (STRICT‑M2 + HYBRID BITDROP)
# ============================================================

class MemoryStore:
    """
    Strict‑M2 storage layer.
    Stores MemoryItem objects as JSON files with hybrid BitDrop V2 binary payloads.
    Fully 3D‑MAX instrumented.
    """

    def __init__(self, helper=None, bitdrop=None, folder: str = "memory_store"):
        self.helper = helper
        self.bitdrop = bitdrop
        self.folder = folder

        if not os.path.exists(folder):
            os.makedirs(folder)

    # -------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------

    def save(self, item):
        start = time.time()

        idx = int(time.time() * 1000000)
        path = os.path.join(self.folder, f"{idx}.json")

        payload = {
            "embedding": item.embedding,
            "bloom": list(item.bloom),
            "patterns": item.patterns,
            "bitdrop_binary": item.bitdrop_binary,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        _3d("save", path, 1, start, {"item_id": idx})
        return True

    # -------------------------------------------------------------
    # LOAD SINGLE
    # -------------------------------------------------------------

    def load(self, filename: str):
        start = time.time()
        path = os.path.join(self.folder, filename)

        if not os.path.exists(path):
            _3d("load_missing", path, 0, start)
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        from bitdrop_core.ai.metamodel.memory.memory_item import MemoryItem

        item = MemoryItem(
            embedding=data.get("embedding", []),
            bloom=set(data.get("bloom", [])),
            patterns=data.get("patterns", {}),
            bitdrop_binary=data.get("bitdrop_binary", ""),
        )

        _3d("load", path, 1, start)
        return item

    # -------------------------------------------------------------
    # LOAD ALL
    # -------------------------------------------------------------

    def load_all(self) -> List[Any]:
        start = time.time()

        files = [
            f for f in os.listdir(self.folder)
            if f.endswith(".json")
        ]

        items = []
        from bitdrop_core.ai.metamodel.memory.memory_item import MemoryItem

        for fname in files:
            path = os.path.join(self.folder, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                item = MemoryItem(
                    embedding=data.get("embedding", []),
                    bloom=set(data.get("bloom", [])),
                    patterns=data.get("patterns", {}),
                    bitdrop_binary=data.get("bitdrop_binary", ""),
                )
                items.append(item)

            except Exception:
                continue

        _3d("load_all", self.folder, len(items), start, {"files": len(files)})
        return items

    # -------------------------------------------------------------
    # CLEAR
    # -------------------------------------------------------------

    def clear(self):
        start = time.time()

        count = 0
        for f in os.listdir(self.folder):
            if f.endswith(".json"):
                try:
                    os.remove(os.path.join(self.folder, f))
                    count += 1
                except Exception:
                    pass

        _3d("clear", self.folder, count, start)
        return count








