#pragma once
#include <cstdint>
#include <cstring>
#include <algorithm>

// ================================================================
// BitDrop v2 — Shared Helpers (CPU + GPU)
// ================================================================
//
// This header provides:
//   - fast 4-byte loads/stores
//   - branchless compare
//   - signature generation
//   - bloom filter helpers (CPU/GPU)
//   - SoA indexing helpers
//
// All collapse/expand engines include this file.
// ================================================================

// -------------------------------
// CPU: Fast 4-byte load
// -------------------------------
static inline uint32_t bd_load32(const uint8_t* p) {
    uint32_t v;
    std::memcpy(&v, p, sizeof(uint32_t));
    return v;
}

// -------------------------------
// CPU: Fast 4-byte store
// -------------------------------
static inline void bd_store32(uint8_t* p, uint32_t v) {
    std::memcpy(p, &v, sizeof(uint32_t));
}

// -------------------------------
// Branchless equality check
// -------------------------------
static inline bool bd_eq32(uint32_t a, uint32_t b) {
    return (a ^ b) == 0;
}

// -------------------------------
// Signature generator
// -------------------------------
static inline uint32_t bd_make_signature(uint32_t base, int index) {
    return base + static_cast<uint32_t>(index);
}

// -------------------------------
// Clamp helper
// -------------------------------
template<typename T>
static inline T bd_clamp(T v, T lo, T hi) {
    return std::min(hi, std::max(lo, v));
}

// ================================================================
// GPU Helpers (only active when compiling with NVCC)
// ================================================================
#ifdef __CUDACC__

// Warp-wide OR reduction
__device__ inline uint32_t bd_warp_or(uint32_t v) {
    for (int offset = 16; offset > 0; offset >>= 1)
        v |= __shfl_down_sync(0xFFFFFFFF, v, offset);
    return v;
}

// Warp-wide AND reduction
__device__ inline uint32_t bd_warp_and(uint32_t v) {
    for (int offset = 16; offset > 0; offset >>= 1)
        v &= __shfl_down_sync(0xFFFFFFFF, v, offset);
    return v;
}

// Device 4-byte load
__device__ inline uint32_t bd_load32_dev(const uint8_t* p) {
    return *reinterpret_cast<const uint32_t*>(p);
}

// Device 4-byte store
__device__ inline void bd_store32_dev(uint8_t* p, uint32_t v) {
    *reinterpret_cast<uint32_t*>(p) = v;
}

#endif // __CUDACC__
