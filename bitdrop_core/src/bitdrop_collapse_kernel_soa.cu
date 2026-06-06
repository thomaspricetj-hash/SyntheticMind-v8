#include "bitdrop_rules.h"
#include "bitdrop_helpers.h"

#ifdef __CUDACC__
#include <cuda_runtime.h>

// ================================================================
// BitDrop v2 — GPU Collapse Kernel (SoA + Bloom Filter)
// ================================================================
//
// This kernel performs a single collapse pass on the GPU.
//
// Each thread processes one byte offset. When a 4-byte pattern
// matches a rule, it writes the signature and emits a tag.
//
// Multi-pass collapse is handled by the host API.
//
// ================================================================

// ------------------------------------------------------------
// GPU Bloom Filter (simple, fast, warp-friendly)
// ------------------------------------------------------------
__device__ inline bool bloom_maybe_match(uint32_t pat,
                                         const uint32_t* bloom,
                                         int bloom_words)
{
    // Two hash functions (very cheap)
    uint32_t h1 = (pat * 0x45d9f3b) >> 5;
    uint32_t h2 = (pat * 0x119de1f3) >> 7;

    uint32_t idx1 = h1 & (bloom_words - 1);
    uint32_t idx2 = h2 & (bloom_words - 1);

    uint32_t b1 = bloom[idx1];
    uint32_t b2 = bloom[idx2];

    return (b1 | b2) != 0;
}

// ------------------------------------------------------------
// GPU collapse kernel (single pass)
// ------------------------------------------------------------
extern "C" __global__
void bitdrop_collapse_kernel_soa(
    const uint8_t* __restrict__ input,
    size_t size,
    const CollapseRule* __restrict__ rules,
    int rule_count,
    const uint32_t* __restrict__ bloom,
    int bloom_words,
    uint8_t* __restrict__ out_payload,
    uint8_t* __restrict__ out_tags,
    uint32_t* __restrict__ collapse_count)
{
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx + 4 > size)
        return;

    // Load 4-byte chunk
    uint32_t chunk = bd_load32_dev(input + idx);

    // Bloom filter quick reject
    if (!bloom_maybe_match(chunk, bloom, bloom_words))
        return;

    // Linear scan (rule_count <= 80)
    for (int r = 0; r < rule_count; r++) {
        const CollapseRule& rule = rules[r];

        if (chunk == rule.pattern) {
            // Write signature
            bd_store32_dev(out_payload + idx, rule.signature);

            // Emit tag
            out_tags[idx] = rule.tag;

            // Count collapse
            atomicAdd(collapse_count, 1u);
            return;
        }
    }
}

// ------------------------------------------------------------
// Kernel launcher (single pass)
// ------------------------------------------------------------
extern "C"
cudaError_t bitdrop_launch_collapse_pass(
    const uint8_t* d_input,
    size_t size,
    const CollapseRule* d_rules,
    int rule_count,
    const uint32_t* d_bloom,
    int bloom_words,
    uint8_t* d_out_payload,
    uint8_t* d_out_tags,
    uint32_t* d_collapse_count,
    cudaStream_t stream)
{
    const int threads = 128;
    const int blocks = (int)((size + threads - 1) / threads);

    bitdrop_collapse_kernel_soa<<<blocks, threads, 0, stream>>>(
        d_input,
        size,
        d_rules,
        rule_count,
        d_bloom,
        bloom_words,
        d_out_payload,
        d_out_tags,
        d_collapse_count
    );

    return cudaGetLastError();
}

#endif // __CUDACC__
