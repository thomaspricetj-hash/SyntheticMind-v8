from __future__ import annotations
from typing import Dict, Any, Callable, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import time
import zlib
import threading
from collections import OrderedDict


# ------------------------------------------------------------
# MICRO HELPERS
# ------------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()

    @staticmethod
    def clean(text: str) -> str:
        return " ".join(text.split())


class MicroFastHash:
    __slots__ = ()

    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


class MicroLatency:
    __slots__ = ()

    @staticmethod
    def wrap(start: float) -> int:
        return int((time.time() - start) * 1000)


class MicroWorkerSelector:
    __slots__ = ()

    @staticmethod
    def workers(n: int) -> int:
        # Cap threads to avoid oversubscription
        return max(1, min(n, 16))


class MicroSafeResult:
    __slots__ = ()

    @staticmethod
    def normalize(result: Any, latency_ms: int) -> Dict[str, Any]:
        if isinstance(result, dict):
            env = dict(result)
            env["latency_ms"] = latency_ms
            return env
        return {
            "error": "invalid helper output",
            "detected": False,
            "latency_ms": latency_ms,
        }


# ------------------------------------------------------------
# LRU CACHE (PER HELPER)
# ------------------------------------------------------------
class LRUCache:
    """
    Simple thread-safe LRU cache for helper-level caching.
    Key: int (query hash)
    Value: Dict[str, Any] (helper envelope)
    """

    def __init__(self, max_size: int = 256):
        self.max_size = max_size
        self._data: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def set(self, key: int, value: Dict[str, Any]) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._data[key] = value
            else:
                self._data[key] = value
            if len(self._data) > self.max_size:
                self._data.popitem(last=False)


# ------------------------------------------------------------
# CIRCUIT BREAKER
# ------------------------------------------------------------
class CircuitBreaker:
    """
    Simple per-helper circuit breaker:
        • opens after N consecutive failures
        • half-open after cooldown
    """

    def __init__(self, failure_threshold: int = 3, cooldown_sec: int = 30):
        self.failure_threshold = failure_threshold
        self.cooldown_sec = cooldown_sec
        self.fail_count = 0
        self.state = "closed"  # closed | open | half_open
        self.last_failure_ts: float = 0.0
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.state == "closed":
                return True

            now = time.time()
            if self.state == "open":
                if now - self.last_failure_ts >= self.cooldown_sec:
                    self.state = "half_open"
                    return True
                return False

            if self.state == "half_open":
                return True

            return True

    def record_success(self) -> None:
        with self._lock:
            self.fail_count = 0
            self.state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self.fail_count += 1
            self.last_failure_ts = time.time()
            if self.fail_count >= self.failure_threshold:
                self.state = "open"


# ------------------------------------------------------------
# HELPER CONFIG
# ------------------------------------------------------------
class HelperConfig:
    """
    Per-helper configuration:
        • timeout_ms
        • priority (lower = earlier scheduling)
        • enabled flag
        • cache_size (LRU entries)
    """

    def __init__(
        self,
        timeout_ms: int = 2000,
        priority: int = 10,
        enabled: bool = True,
        cache_size: int = 256,
    ):
        self.timeout_ms = timeout_ms
        self.priority = priority
        self.enabled = enabled
        self.cache_size = cache_size
        self.breaker = CircuitBreaker()


# ------------------------------------------------------------
# MAIN PARALLEL HELPER MESH V3 (1D)
# ------------------------------------------------------------
class HelperMesh:
    """
    HelperMesh v3:
        • parallel execution
        • per-helper timeouts
        • per-helper circuit breakers
        • priority scheduling
        • helper-level LRU caching
        • fail-soft, deterministic merge
        • routing helpers for NeuralPredictor
    """

    def __init__(
        self,
        helpers: Dict[str, Callable],
        configs: Optional[Dict[str, HelperConfig]] = None,
    ):
        """
        helpers: name -> helper_instance (must expose process(query, lang_info, memory_info))
        configs: optional name -> HelperConfig
        """
        self.helpers = helpers
        self.configs: Dict[str, HelperConfig] = configs or {
            name: HelperConfig() for name in helpers.keys()
        }
        self.max_workers = MicroWorkerSelector.workers(len(helpers))

        # Per-helper LRU caches
        self.caches: Dict[str, LRUCache] = {}
        for name in helpers.keys():
            cfg = self._get_config(name)
            self.caches[name] = LRUCache(max_size=cfg.cache_size)

    def _get_config(self, name: str) -> HelperConfig:
        cfg = self.configs.get(name)
        if cfg is None:
            cfg = HelperConfig()
            self.configs[name] = cfg
        return cfg

    # --------------------------------------------------------
    # Core parallel execution (1D query)
    # --------------------------------------------------------
    def run(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        query = MicroStringStripper.clean(query or "")
        q_hash = MicroFastHash.h(query)

        results: Dict[str, Any] = {}

        # Priority scheduling
        ordered = sorted(
            self.helpers.items(),
            key=lambda kv: self._get_config(kv[0]).priority,
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_map: Dict[Future, str] = {}
            start_times: Dict[str, float] = {}
            timeouts: Dict[str, float] = {}

            # Submit helpers or serve from cache
            for name, helper in ordered:
                cfg = self._get_config(name)
                cache = self.caches[name]

                # 1) Circuit breaker / enabled
                if not cfg.enabled or not cfg.breaker.allow():
                    results[name] = {
                        "detected": False,
                        "skipped": True,
                        "reason": "disabled_or_open_breaker",
                        "latency_ms": 0,
                    }
                    continue

                # 2) Helper-level cache
                cached = cache.get(q_hash)
                if cached is not None:
                    results[name] = cached
                    continue

                # 3) Submit helper
                start = time.time()
                fut = pool.submit(helper.process, query, lang_info, memory_info)
                future_map[fut] = name
                start_times[name] = start
                timeouts[name] = cfg.timeout_ms / 1000.0

            # Collect results
            for fut in as_completed(future_map):
                name = future_map[fut]
                cfg = self._get_config(name)
                cache = self.caches[name]
                start = start_times[name]
                timeout_sec = timeouts[name]

                try:
                    result = fut.result(timeout=timeout_sec)
                    latency_ms = MicroLatency.wrap(start)
                    cfg.breaker.record_success()

                    normalized = MicroSafeResult.normalize(result, latency_ms)
                    results[name] = normalized
                    cache.set(q_hash, normalized)

                except Exception as e:
                    latency_ms = MicroLatency.wrap(start)
                    cfg.breaker.record_failure()

                    error_env = {
                        "error": str(e),
                        "detected": False,
                        "timeout_ms": cfg.timeout_ms,
                        "latency_ms": latency_ms,
                    }
                    results[name] = error_env
                    cache.set(q_hash, error_env)

        return results

    # --------------------------------------------------------
    # Deterministic merge for routing / features
    # --------------------------------------------------------
    def run_and_merge(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run all helpers and merge their envelopes into a single
        feature dict suitable for routing / NeuralPredictor.
        """
        envelopes = self.run(query, lang_info, memory_info)
        merged: Dict[str, Any] = {}

        # Deterministic merge: first non-None value wins per key
        for env in envelopes.values():
            if not isinstance(env, dict):
                continue
            for k, v in env.items():
                if k in (
                    "latency_ms",
                    "error",
                    "detected",
                    "skipped",
                    "reason",
                    "timeout_ms",
                ):
                    continue
                if v is None:
                    continue
                if k not in merged:
                    merged[k] = v

        return merged

    # --------------------------------------------------------
    # Routing helpers for NeuralPredictor
    # --------------------------------------------------------
    def get_backend_hint(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Optional[str]:
        merged = self.run_and_merge(query, lang_info, memory_info)
        hint = merged.get("backend_hint")
        if hint in ("R", "L", "Z"):
            return hint
        return None

    def get_shape_hint(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Optional[str]:
        merged = self.run_and_merge(query, lang_info, memory_info)
        shape = merged.get("shape") or merged.get("shape_hint")
        if isinstance(shape, str):
            return shape
        return None

    def get_semantic_kind(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Optional[str]:
        merged = self.run_and_merge(query, lang_info, memory_info)
        kind = merged.get("semantic_kind")
        if isinstance(kind, str):
            return kind
        return None


# ------------------------------------------------------------
# 3D HELPER MESH (MAXED, BUT BACKWARD-COMPATIBLE)
# ------------------------------------------------------------
class HelperMesh3D:
    """
    3D HelperMesh:
        • Reuses HelperMesh core logic
        • Adds 3D batching: (depth, row, col) grid of queries
        • Per-cell parallelism + per-helper parallelism
        • Deterministic 3D merge for routing / features
    """

    def __init__(
        self,
        helpers: Dict[str, Callable],
        configs: Optional[Dict[str, HelperConfig]] = None,
    ):
        # One shared mesh; we treat 3D as a batch over the same helper set
        self.mesh = HelperMesh(helpers=helpers, configs=configs)

    # queries_3d: List[ List[ List[str] ] ]  -> [D][H][W]
    def run_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        Run helpers over a 3D grid of queries:
            queries_3d[d][h][w] = query string

        Returns:
            results_3d[d][h][w] = { helper_name -> envelope }
        """
        depth = len(queries_3d)
        results_3d: List[List[List[Dict[str, Any]]]] = []

        # Outer dimension: depth
        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []

            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    envs = self.mesh.run(q, lang_info, memory_info)
                    row_out.append(envs)
                plane_out.append(row_out)

            results_3d.append(plane_out)

        return results_3d

    def run_and_merge_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        Same as run_3d, but merges helper envelopes per cell into a single feature dict.
        """
        depth = len(queries_3d)
        results_3d: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []

            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    merged = self.mesh.run_and_merge(q, lang_info, memory_info)
                    row_out.append(merged)
                plane_out.append(row_out)

            results_3d.append(plane_out)

        return results_3d

    def get_backend_hint_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Optional[str]]]]:
        depth = len(queries_3d)
        out: List[List[List[Optional[str]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Optional[str]]] = []
            for row in plane:
                row_out: List[Optional[str]] = []
                for q in row:
                    row_out.append(self.mesh.get_backend_hint(q, lang_info, memory_info))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def get_shape_hint_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Optional[str]]]]:
        depth = len(queries_3d)
        out: List[List[List[Optional[str]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Optional[str]]] = []
            for row in plane:
                row_out: List[Optional[str]] = []
                for q in row:
                    row_out.append(self.mesh.get_shape_hint(q, lang_info, memory_info))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def get_semantic_kind_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Optional[str]]]]:
        depth = len(queries_3d)
        out: List[List[List[Optional[str]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Optional[str]]] = []
            for row in plane:
                row_out = []
                for q in row:
                    row_out.append(self.mesh.get_semantic_kind(q, lang_info, memory_info))
                plane_out.append(row_out)
            out.append(plane_out)

        return out


