// src/bitdrop_kernel_soa.cu
#include <cuda_runtime.h>
#include "bitdrop_kernel_soa.h"

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

__device__ __forceinline__
void decode_rule_and_level(const uint32_t* headers,
                           int block_idx,
                           int& rule_id,
                           int& level)
{
    const uint32_t h0 = headers[static_cast<size_t>(block_idx)];
    rule_id = static_cast<int>(h0 & 0xFFFFu);
    level   = static_cast<int>((h0 >> 16) & 0xFFu);

    if (rule_id < 0) rule_id = 0;
    if (rule_id >= RULE_BANK_SIZE) rule_id = RULE_BANK_SIZE - 1;
    if (level < 0) level = 0;
    if (level >= LEVEL_TABLE_SIZE) level = LEVEL_TABLE_SIZE - 1;
}

// -----------------------------------------------------------------------------
// v3 optimized core (device function)
// -----------------------------------------------------------------------------

template<int BLOCK_THREADS>
__device__ void bitdrop_soa_kernel_v3_device(
    const uint32_t* __restrict__ in_headers,
    const uint32_t* __restrict__ in_t1,
    const uint32_t* __restrict__ in_t2,
    const uint32_t* __restrict__ in_t3,
    const uint32_t* __restrict__ in_graph,
    const uint32_t* __restrict__ in_payload,

    uint32_t* __restrict__ out_headers,
    uint32_t* __restrict__ out_t1,
    uint32_t* __restrict__ out_t2,
    uint32_t* __restrict__ out_t3,
    uint32_t* __restrict__ out_graph,
    uint32_t* __restrict__ out_payload,

    const RuleSet* __restrict__ rule_bank,
    const uint32_t* __restrict__ payload_masks,
    int num_blocks,
    Metrics* __restrict__ metrics
)
{
    const int block_idx = blockIdx.x;
    if (block_idx >= num_blocks) return;

    extern __shared__ uint32_t shmem[];
    uint32_t* sh_fused_mask = shmem;

    int rule_id = 0;
    int level   = 0;
    if (threadIdx.x == 0) {
        decode_rule_and_level(in_headers, block_idx, rule_id, level);
    }
    rule_id = __shfl_sync(0xFFFFFFFFu, rule_id, 0);
    level   = __shfl_sync(0xFFFFFFFFu, level,   0);

    const RuleSet& rule = rule_bank[rule_id];

    const size_t mask_offset =
        (static_cast<size_t>(rule_id) * LEVEL_TABLE_SIZE + static_cast<size_t>(level)) * P_WORDS;
    const uint32_t* level_mask = &payload_masks[mask_offset];

    // Load fused mask into shared memory
    for (int w = threadIdx.x; w < P_WORDS; w += BLOCK_THREADS) {
        sh_fused_mask[w] = rule.payload_base_mask[w] & level_mask[w];
    }
    __syncthreads();

    const size_t payload_base = static_cast<size_t>(block_idx) * P_WORDS;
    const size_t t1_base      = static_cast<size_t>(block_idx) * T1_WORDS;
    const size_t t2_base      = static_cast<size_t>(block_idx) * T2_WORDS;
    const size_t t3_base      = static_cast<size_t>(block_idx) * T3_WORDS;
    const size_t graph_base   = static_cast<size_t>(block_idx) * G_WORDS;

    if (threadIdx.x == 0) {
        out_headers[block_idx] = in_headers[block_idx];
    }

    // Payload
    for (int w = threadIdx.x; w < P_WORDS; w += BLOCK_THREADS) {
        const size_t idx = payload_base + static_cast<size_t>(w);
        out_payload[idx] = in_payload[idx] & sh_fused_mask[w];
    }

#if T1_WORDS > 0
    for (int w = threadIdx.x; w < T1_WORDS; w += BLOCK_THREADS) {
        const size_t idx = t1_base + static_cast<size_t>(w);
        out_t1[idx] = in_t1[idx] & sh_fused_mask[w % P_WORDS];
    }
#endif

#if T2_WORDS > 0
    for (int w = threadIdx.x; w < T2_WORDS; w += BLOCK_THREADS) {
        const size_t idx = t2_base + static_cast<size_t>(w);
        out_t2[idx] = in_t2[idx] & sh_fused_mask[w % P_WORDS];
    }
#endif

#if T3_WORDS > 0
    for (int w = threadIdx.x; w < T3_WORDS; w += BLOCK_THREADS) {
        const size_t idx = t3_base + static_cast<size_t>(w);
        out_t3[idx] = in_t3[idx] & sh_fused_mask[w % P_WORDS];
    }
#endif

#if G_WORDS > 0
    for (int w = threadIdx.x; w < G_WORDS; w += BLOCK_THREADS) {
        const size_t idx = graph_base + static_cast<size_t>(w);
        out_graph[idx] = in_graph[idx] & sh_fused_mask[w % P_WORDS];
    }
#endif
}

// -----------------------------------------------------------------------------
// Kernel with original symbol name (host API calls this)
// -----------------------------------------------------------------------------
//
// IMPORTANT:
// Signature MUST MATCH bitdrop_kernel_soa.h EXACTLY.
// No const on rule_bank_ptr or payload_masks_ptr.
//

extern "C" __global__ void bitdrop_kernel_soa(
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
    RuleSet*        rule_bank_ptr,
    uint32_t*       payload_masks_ptr,
    int             num_blocks,
    Metrics*        out_metrics
)
{
    const RuleSet*   rule_bank     = rule_bank_ptr;
    const uint32_t*  payload_masks = payload_masks_ptr;

    bitdrop_soa_kernel_v3_device<128>(
        in_headers, in_t1, in_t2, in_t3, in_graph, in_payload,
        out_headers, out_t1, out_t2, out_t3, out_graph, out_payload,
        rule_bank, payload_masks, num_blocks, out_metrics
    );
}























