import os
import time
import ctypes
import random

# ------------------------------------------------------------
# Load DLL
# ------------------------------------------------------------
DLL_PATH = os.path.join("build", "src", "Release", "bitdrop.dll")
bitdrop = ctypes.CDLL(DLL_PATH)

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
P_WORDS = 16

# ------------------------------------------------------------
# Metrics struct (REAL one from your DLL)
# ------------------------------------------------------------
class Metrics(ctypes.Structure):
    _fields_ = [
        ("X_compression", ctypes.c_float),
        ("Y_fidelity", ctypes.c_float),
        ("Z_cost", ctypes.c_float),
    ]

# ------------------------------------------------------------
# Bind kernel launcher
# ------------------------------------------------------------
bitdrop.launch_bitdrop_soa.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_int,
    ctypes.POINTER(Metrics)
]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def make_payload(blocks):
    total = blocks * P_WORDS
    arr = (ctypes.c_uint32 * total)()
    for i in range(total):
        arr[i] = random.getrandbits(32)
    return arr

def run_kernel(blocks):
    payload = make_payload(blocks)
    metrics = Metrics()

    t0 = time.perf_counter()

    bitdrop.launch_bitdrop_soa(
        None, None, None, None, None,                     # in headers/tables
        ctypes.cast(payload, ctypes.c_void_p),            # in_payload
        None, None, None, None, None,                     # out headers/tables
        ctypes.cast(payload, ctypes.c_void_p),            # out_payload
        None, None,                                       # rule bank, masks
        blocks,
        ctypes.byref(metrics)
    )

    t1 = time.perf_counter()
    return t1 - t0, metrics

# ------------------------------------------------------------
# Benchmark
# ------------------------------------------------------------
def bench():
    for name, blocks in [
        ("small", 32768),
        ("medium", 262144),
        ("large", 1_000_000),
    ]:
        t, m = run_kernel(blocks)
        print(f"{name:>6}: {blocks:,} blocks  time={t:.6f}s  X={m.X_compression:.3f}")

if __name__ == "__main__":
    bench()


