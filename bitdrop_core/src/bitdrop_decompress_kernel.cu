// src/bitdrop_decompress_kernel_soa.cu
// BitDrop GPU decompressor — SoA, pointer-only, symbol-free.
// Currently behaves as structural identity: it mirrors the stored layout.
// Any future reversible transforms in the compressor should be inverted here.

#include "bitdrop_kernel_soa.h"
#include <cuda_runtime.h>
#include <cstdint>

// ---------------------------------------------------------------------------
// SoA index helpers (must match bitdrop_kernel_soa.cu)
// ---------------------------------------------------------------------------
__device__ inline int idx_t1(int block_id, int w) { return block_id * T1_WORDS + w; }
__device__ inline int idx_t2(int block_id, int w) { return block_id * T2_WORDS + w; }
__device__ inline int idx_t3(int block_id, int w) { return block_id * T3_WORDS + w; }
__device__ inline int idx_g (int block_id, int w) { return block_id * G_WORDS  + w; }
__device__ inline int idx_p (int block_id, int w) { return block_id * P_WORDS  + w; }

// ---------------------------------------------------------------------------
// Decompression kernel
// ---------------------------------------------------------------------------
// NOTE: This mirrors the signature declared in bitdrop_kernel_soa.h and
// used by launch_bitdrop_decompress_soa in bitdrop_host_api.cu.
extern "C" __global__ void bitdrop_decompress_kernel_soa(
    const uint32_t* in_headers,
    const uint32_t* in_t1,
    const uint32_t* in_t2,
    const uint32_t* in_t3,
    const uint32_t* in_graph,
    const uint32_t* in_payload,
    uint32_t*       out_headers,
    uint32_t*       out_t1,
    uint32_t*       out_t2,
    uint32_t*       out_t3,
    uint32_t*       out_graph,
    uint32_t*       out_payload,
    const RuleSet*  rule_bank_ptr,
    const uint32_t* payload_masks_ptr,
    int             num_blocks,
    Metrics*        out_metrics
) {
    const int bid    = blockIdx.x;
    const int tid    = threadIdx.x;
    const int stride = blockDim.x;

    if (bid >= num_blocks) return;

    // We currently treat decompression as structural identity:
    // whatever is stored in the compressed representation is passed through.
    // If you later introduce reversible transforms in the compressor,
    // mirror the inverse logic here.

    // -----------------------------------------------------------------------
    // Headers / tiers / graph — thread 0 copies SoA slices
    // -----------------------------------------------------------------------
    if (tid == 0) {
        if (in_headers && out_headers)
            out_headers[bid] = in_headers[bid];

        if (in_t1 && out_t1)
            for (int w = 0; w < T1_WORDS; ++w)
                out_t1[idx_t1(bid, w)] = in_t1[idx_t1(bid, w)];

        if (in_t2 && out_t2)
            for (int w = 0; w < T2_WORDS; ++w)
                out_t2[idx_t2(bid, w)] = in_t2[idx_t2(bid, w)];

        if (in_t3 && out_t3)
            for (int w = 0; w < T3_WORDS; ++w)
                out_t3[idx_t3(bid, w)] = in_t3[idx_t3(bid, w)];

        if (in_graph && out_graph)
            for (int w = 0; w < G_WORDS; ++w)
                out_graph[idx_g(bid, w)] = in_graph[idx_g(bid, w)];
    }

    __syncthreads();

    // -----------------------------------------------------------------------
    // Payload — identity copy across threads
    // -----------------------------------------------------------------------
    if (in_payload && out_payload) {
        for (int w = tid; w < P_WORDS; w += stride) {
            int idx = idx_p(bid, w);
            out_payload[idx] = in_payload[idx];
        }
    }

    __syncthreads();

    // -----------------------------------------------------------------------
    // Metrics — optional, simple passthrough / marker
    // -----------------------------------------------------------------------
    if (tid == 0 && out_metrics) {
        Metrics& m = out_metrics[bid];
        // For now, mark decompression as neutral cost.
        m.X_compression = 0.0f;
        m.Y_fidelity    = 1.0f;
        m.Z_cost        = 0.0f;
    }

    (void)rule_bank_ptr;
    (void)payload_masks_ptr;
}


