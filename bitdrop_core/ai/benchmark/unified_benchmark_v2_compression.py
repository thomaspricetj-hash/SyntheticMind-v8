# ============================================================
# unified_benchmark_v2_compression.py
# Unified Benchmark for:
#   - BitDrop (JSON text/metadata only, uncompressed here)
#   - TurboVec (vectors only)
#   - Dual-field JSON + TV total size
#   - 3D BitDropCollapseEngineV2 over combined bytes
# ============================================================

import json
import random
import time

from bitdrop_core.ai.compression.bitdrop_collapse_codec import (
    BitDropCollapseEngineV2,
)


from python_wrapper import PyTurboVecEncoder


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _make_vectors(n, dim):
    return [[random.random() for _ in range(dim)] for _ in range(n)]


def _make_text_block():
    lines = []
    for i in range(200):
        lines.append("INFO 2026-06-08T12:00:00Z Processing request id=12345")
        lines.append("INFO 2026-06-08T12:00:00Z Processing request id=12345")
        lines.append("DEBUG compute_value(x, y): entering function")
        lines.append("DEBUG compute_value(x, y): exiting function")
        lines.append("WARN retrying operation due to timeout")
        lines.append("")
    return "\n".join(lines)


def _time(fn):
    t0 = time.perf_counter()
    out = fn()
    t1 = time.perf_counter()
    return out, (t1 - t0) * 1000.0


# ------------------------------------------------------------
# Unified Benchmark
# ------------------------------------------------------------
def run_unified_benchmark():
    print("\n============================================================")
    print(" Unified BitDrop + TurboVec Benchmark (v2 + 3D BitDrop)")
    print("============================================================\n")

    # --------------------------------------------------------
    # Test Payload
    # --------------------------------------------------------
    dim = 1536
    n_vec = 256

    vectors = _make_vectors(n_vec, dim)
    text = _make_text_block()
    metadata = {"source": "logs+mixed", "entries": 2000, "note": "unified test"}

    payload = {"text": text, "metadata": metadata, "vectors": vectors}
    orig_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    orig_bytes = orig_json.encode("utf-8")
    orig_size = len(orig_bytes)

    print(f"Original JSON size: {orig_size:,} bytes\n")

    # --------------------------------------------------------
    # Engines
    # --------------------------------------------------------
    turbovec = PyTurboVecEncoder(dim, bit_width=4)
    bitdrop3d = BitDropCollapseEngineV2(block_shape=(4, 4, 64), level=9)

    # --------------------------------------------------------
    # TurboVec-only (vectors only)
    # --------------------------------------------------------
    def turbovec_run():
        tv_raw = turbovec.encode(vectors)
        tv_bytes = bytes(tv_raw) if isinstance(tv_raw, list) else tv_raw
        return len(tv_bytes)

    tv_size, tv_time = _time(turbovec_run)

    print("[TurboVec] Vector compression:")
    print(f"  Size: {tv_size:,} bytes")
    print(f"  Time: {tv_time:.3f} ms\n")

    # --------------------------------------------------------
    # Dual-field (JSON + TurboVec)
    # --------------------------------------------------------
    def dualfield():
        struct_json = json.dumps(
            {"text": text, "metadata": metadata},
            separators=(",", ":"),
            ensure_ascii=False,
        )
        struct_bytes = struct_json.encode("utf-8")

        tv_raw = turbovec.encode(vectors)
        tv_bytes = bytes(tv_raw) if isinstance(tv_raw, list) else tv_raw

        return len(struct_bytes) + len(tv_bytes)

    dual_size, dual_time = _time(dualfield)

    print("[Dual-field] JSON + TurboVec (separate):")
    print(f"  Size: {dual_size:,} bytes")
    print(f"  Time: {dual_time:.3f} ms\n")

    # --------------------------------------------------------
    # 3D BitDropCollapseEngineV2 over combined bytes
    # (JSON text+metadata bytes + TurboVec bytes)
    # --------------------------------------------------------
    def bitdrop3d_run():
        struct_json = json.dumps(
            {"text": text, "metadata": metadata},
            separators=(",", ":"),
            ensure_ascii=False,
        )
        struct_bytes = struct_json.encode("utf-8")

        tv_raw = turbovec.encode(vectors)
        tv_bytes = bytes(tv_raw) if isinstance(tv_raw, list) else tv_raw

        combined = struct_bytes + tv_bytes
        blob = bitdrop3d.encode(combined)
        return len(blob)

    hybrid3d_size, hybrid3d_time = _time(bitdrop3d_run)

    print("[3D BitDropCollapseEngineV2] (JSON+TV combined → 3D BitDrop + TurboQuant):")
    print(f"  Size: {hybrid3d_size:,} bytes")
    print(f"  Time: {hybrid3d_time:.3f} ms\n")

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------
    print("============================================================")
    print(" Summary")
    print("============================================================")
    print(f"Original:              {orig_size:,} bytes (1.0000x)")
    print(f"TurboVec-only:         {tv_size:,} bytes ({orig_size / tv_size:.4f}x)")
    print(f"Dual-field JSON+TV:    {dual_size:,} bytes ({orig_size / dual_size:.4f}x)")
    print(f"3D BitDrop (combined): {hybrid3d_size:,} bytes ({orig_size / hybrid3d_size:.4f}x)")
    print("============================================================\n")


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
if __name__ == "__main__":
    run_unified_benchmark()







