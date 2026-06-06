#include "bitdrop_rules.h"
#include "bitdrop_helpers.h"

#ifdef __CUDACC__
#include <cuda_runtime.h>

// ================================================================
// BitDrop v2 — GPU Expand Kernel (SoA)
// ================================================================
//
// Reverses the collapse performed by bitdrop_collapse_kernel_soa.
//
// Each thread checks if the 4-byte chunk at its index is a signature.
// If so, it uses the tag stream to restore the original pattern.
//
// Multi-pass expansion is handled by the host API.
//
// ================================================================

// ------------------------------------------------------------
// GPU expand kernel (single pass)
// ------------------------------------------------------------
extern "C" __global__
void bitdrop_expand_kernel_soa(
    const uint8_t* __restrict__ collapsed,
    size_t size,
    const CollapseRule* __restrict__ rules,
    const uint8_t* __restrict__ tags,
    uint8_t* __restrict__ out_payload,
    uint32_t* __restrict__ tag_index_global)
{
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx + 4 > size)
        return;

    // Load 4-byte chunk
    uint32_t chunk = bd_load32_dev(collapsed + idx);

    // Check if this is a signature
    if ((chunk & 0xFF000000) == BITDROP_SIGNATURE_BASE) {
        // Get next tag index atomically
        uint32_t tag_idx = atomicAdd(tag_index_global, 1u);
        uint8_t tag = tags[tag_idx];

        // Restore original pattern
        const CollapseRule& rule = rules[tag];
        uint32_t pat = rule.pattern;

        bd_store32_dev(out_payload + idx, pat);
        return;
    }

    // Not a signature → copy 1 byte
    out_payload[idx] = collapsed[idx];
}

// ------------------------------------------------------------
// Kernel launcher (single pass)
// ------------------------------------------------------------
extern "C"
cudaError_t bitdrop_launch_expand_pass(
    const uint8_t* d_collapsed,
    size_t size,
    const CollapseRule* d_rules,
    const uint8_t* d_tags,
    uint8_t* d_out_payload,
    uint32_t* d_tag_index,
    cudaStream_t stream)
{
    const int threads = 128;
    const int blocks = (int)((size + threads - 1) / threads);

    bitdrop_expand_kernel_soa<<<blocks, threads, 0, stream>>>(
        d_collapsed,
        size,
        d_rules,
        d_tags,
        d_out_payload,
        d_tag_index
    );

    return cudaGetLastError();
}

#endif // __CUDACC__
