// src/bitdrop_host_api.cu
// Host-side helpers for uploading device tables and providing runtime pointers.

#include "bitdrop_host_api.h"      // BITDROP_API, RuleSet, Metrics, prototypes
#include "bitdrop_kernel_soa.h"
#include "bitdrop_cache_manager.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cuda_runtime.h>

extern "C" {

// High-level entry: initialize all caches from host tables
BITDROP_API void set_device_tables_from_host(
    const RuleSet* host_rules,
    int rule_count,
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
) {
    bitdrop_cache_init_from_host(host_rules, rule_count, host_masks);
}

// Host getters (C linkage) used by tools / pipeline
BITDROP_API RuleSet* get_uploaded_rule_bank_devptr() {
    return bitdrop_cache_get_rule_bank_devptr();
}

BITDROP_API uint32_t* get_uploaded_payload_masks_devptr() {
    return bitdrop_cache_get_payload_masks_devptr();
}

// ---------------------------------------------------------------------------
// Debug helper — dump host-side cache state
// ---------------------------------------------------------------------------
BITDROP_API void bitdrop_debug_dump_cache_state() {
    RuleSet* rules_dev   = bitdrop_cache_get_rule_bank_devptr();
    uint32_t* masks_dev  = bitdrop_cache_get_payload_masks_devptr();

    std::fprintf(stderr,
        "[BitDropHostAPI] cache rule_bank_devptr=%p\n", (void*)rules_dev);
    std::fprintf(stderr,
        "[BitDropHostAPI] cache payload_masks_devptr=%p\n", (void*)masks_dev);
}

// ---------------------------------------------------------------------------
// Unified verification helper — pointer-only
// ---------------------------------------------------------------------------
BITDROP_API bool bitdrop_verify_all() {
    bool ok = true;

    RuleSet* rules_dev   = bitdrop_cache_get_rule_bank_devptr();
    uint32_t* masks_dev  = bitdrop_cache_get_payload_masks_devptr();

    if (!rules_dev || !masks_dev) {
        std::fprintf(stderr,
            "[BitDropHostAPI] verify_all: cache pointers missing\n");
        ok = false;
    }

    return ok;
}

// Optional helper: dump cache + verify in one call
BITDROP_API bool bitdrop_hostapi_debug_verify() {
    bitdrop_debug_dump_cache_state();
    return bitdrop_verify_all();
}

} // extern "C"

// ---------------------------------------------------------------------------
// Kernel prototypes
// ---------------------------------------------------------------------------
extern "C" __global__ void bitdrop_kernel_soa(
    const uint32_t* in_headers,
    const uint32_t* in_t1,
    const uint32_t* in_t2,
    const uint32_t* in_t3,
    const uint32_t* in_graph,
    const uint32_t* in_payload,
    uint32_t* out_headers,
    uint32_t* out_t1,
    uint32_t* out_t2,
    uint32_t* out_t3,
    uint32_t* out_graph,
    uint32_t* out_payload,
    RuleSet* rule_bank_ptr,
    uint32_t* payload_masks_ptr,
    int num_blocks,
    Metrics* out_metrics
);

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
);

// Small helper: clamp grid to at least 1 block
static inline int bitdrop_grid_for_blocks(int num_blocks) {
    return (num_blocks > 0) ? num_blocks : 1;
}

// ---------------------------------------------------------------------------
// Compression launcher — MUST MATCH HEADER EXACTLY
// ---------------------------------------------------------------------------
extern "C" BITDROP_API void launch_bitdrop_soa(
    uint32_t* in_headers,
    uint32_t* in_t1,
    uint32_t* in_t2,
    uint32_t* in_t3,
    uint32_t* in_graph,
    uint32_t* in_payload,
    uint32_t* out_headers,
    uint32_t* out_t1,
    uint32_t* out_t2,
    uint32_t* out_t3,
    uint32_t* out_graph,
    uint32_t* out_payload,
    RuleSet*  rule_bank_ptr,
    uint32_t* payload_masks_ptr,
    int       num_blocks,
    Metrics*  out_metrics
) {
    const int threads = 128;
    const int grid    = bitdrop_grid_for_blocks(num_blocks);

    if (!rule_bank_ptr)
        rule_bank_ptr = bitdrop_cache_get_rule_bank_devptr();

    if (!payload_masks_ptr)
        payload_masks_ptr = bitdrop_cache_get_payload_masks_devptr();

    if (!rule_bank_ptr || !payload_masks_ptr) {
        std::fprintf(stderr,
            "[BitDropHostAPI] launch_bitdrop_soa: device tables unavailable; aborting launch\n");
        return;
    }

    (void)cudaGetLastError();

    bitdrop_kernel_soa<<<grid, threads>>>(
        in_headers, in_t1, in_t2, in_t3, in_graph, in_payload,
        out_headers, out_t1, out_t2, out_t3, out_graph, out_payload,
        rule_bank_ptr, payload_masks_ptr, num_blocks, out_metrics
    );

    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        std::fprintf(stderr,
            "[BitDropHostAPI] kernel launch failed: %s (code=%d)\n",
            cudaGetErrorString(err), static_cast<int>(err));
        return;
    }

    err = cudaDeviceSynchronize();
    if (err != cudaSuccess) {
        std::fprintf(stderr,
            "[BitDropHostAPI] kernel execution failed: %s (code=%d)\n",
            cudaGetErrorString(err), static_cast<int>(err));
    }
}

// ---------------------------------------------------------------------------
// Decompression launcher — mirror of launch_bitdrop_soa
// ---------------------------------------------------------------------------
extern "C" BITDROP_API void launch_bitdrop_decompress_soa(
    uint32_t* in_headers,
    uint32_t* in_t1,
    uint32_t* in_t2,
    uint32_t* in_t3,
    uint32_t* in_graph,
    uint32_t* in_payload,
    uint32_t* out_headers,
    uint32_t* out_t1,
    uint32_t* out_t2,
    uint32_t* out_t3,
    uint32_t* out_graph,
    uint32_t* out_payload,
    const RuleSet*  rule_bank_ptr,
    const uint32_t* payload_masks_ptr,
    int             num_blocks,
    Metrics*        out_metrics
) {
    const int threads = 128;
    const int grid    = bitdrop_grid_for_blocks(num_blocks);

    if (!rule_bank_ptr)
        rule_bank_ptr = bitdrop_cache_get_rule_bank_devptr();

    if (!payload_masks_ptr)
        payload_masks_ptr = bitdrop_cache_get_payload_masks_devptr();

    if (!rule_bank_ptr || !payload_masks_ptr) {
        std::fprintf(stderr,
            "[BitDropHostAPI] launch_bitdrop_decompress_soa: device tables unavailable; aborting launch\n");
        return;
    }

    (void)cudaGetLastError();

    bitdrop_decompress_kernel_soa<<<grid, threads>>>(
        in_headers, in_t1, in_t2, in_t3, in_graph, in_payload,
        out_headers, out_t1, out_t2, out_t3, out_graph, out_payload,
        rule_bank_ptr, payload_masks_ptr, num_blocks, out_metrics
    );

    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        std::fprintf(stderr,
            "[BitDropHostAPI] decompress kernel launch failed: %s (code=%d)\n",
            cudaGetErrorString(err), static_cast<int>(err));
        return;
    }

    err = cudaDeviceSynchronize();
    if (err != cudaSuccess) {
        std::fprintf(stderr,
            "[BitDropHostAPI] decompress kernel execution failed: %s (code=%d)\n",
            cudaGetErrorString(err), static_cast<int>(err));
    }
}

// ---------------------------------------------------------------------------
// Flat C API: bdrop_compress — used by Python (ctypes)
// ---------------------------------------------------------------------------
extern "C" BITDROP_API int bdrop_compress(
    const void* input,
    size_t      input_size,
    void*       output,
    size_t*     output_size,
    int         level
) {
    if (!input || !output || !output_size)
        return -1;

    size_t num_blocks = input_size / (P_WORDS * sizeof(uint32_t));
    if (num_blocks == 0)
        return -2;

    RuleSet*  d_rules = get_uploaded_rule_bank_devptr();
    uint32_t* d_masks = get_uploaded_payload_masks_devptr();
    if (!d_rules || !d_masks)
        return -3;

    uint32_t *d_in_headers=nullptr, *d_in_t1=nullptr, *d_in_t2=nullptr,
             *d_in_t3=nullptr, *d_in_graph=nullptr, *d_in_payload=nullptr;

    uint32_t *d_out_headers=nullptr, *d_out_t1=nullptr, *d_out_t2=nullptr,
             *d_out_t3=nullptr, *d_out_graph=nullptr, *d_out_payload=nullptr;

    size_t payload_bytes = num_blocks * P_WORDS * sizeof(uint32_t);

    cudaMalloc(&d_in_payload,  payload_bytes);
    cudaMalloc(&d_out_payload, payload_bytes);
    cudaMemcpy(d_in_payload, input, payload_bytes, cudaMemcpyHostToDevice);

    cudaMalloc(&d_in_headers,  num_blocks * sizeof(uint32_t));
    cudaMalloc(&d_in_t1,       num_blocks * T1_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_in_t2,       num_blocks * T2_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_in_t3,       num_blocks * T3_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_in_graph,    num_blocks * G_WORDS  * sizeof(uint32_t));

    cudaMalloc(&d_out_headers, num_blocks * sizeof(uint32_t));
    cudaMalloc(&d_out_t1,      num_blocks * T1_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_out_t2,      num_blocks * T2_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_out_t3,      num_blocks * T3_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_out_graph,   num_blocks * G_WORDS  * sizeof(uint32_t));

    Metrics* d_metrics = nullptr;
    cudaMalloc(&d_metrics, num_blocks * sizeof(Metrics));
    cudaMemset(d_metrics, 0, num_blocks * sizeof(Metrics));

    launch_bitdrop_soa(
        d_in_headers, d_in_t1, d_in_t2, d_in_t3, d_in_graph, d_in_payload,
        d_out_headers, d_out_t1, d_out_t2, d_out_t3, d_out_graph, d_out_payload,
        d_rules, d_masks, static_cast<int>(num_blocks), d_metrics
    );

    cudaDeviceSynchronize();

    cudaMemcpy(output, d_out_payload, payload_bytes, cudaMemcpyDeviceToHost);
    *output_size = payload_bytes;

    cudaFree(d_in_headers); cudaFree(d_in_t1); cudaFree(d_in_t2);
    cudaFree(d_in_t3); cudaFree(d_in_graph); cudaFree(d_in_payload);

    cudaFree(d_out_headers); cudaFree(d_out_t1); cudaFree(d_out_t2);
    cudaFree(d_out_t3); cudaFree(d_out_graph); cudaFree(d_out_payload);

    cudaFree(d_metrics);

    return 0;
}

// ---------------------------------------------------------------------------
// Flat C API: bdrop_decompress — used by Python (ctypes)
// ---------------------------------------------------------------------------
extern "C" BITDROP_API int bdrop_decompress(
    const void* input,
    size_t      input_size,
    void*       output,
    size_t*     output_size,
    int         level
) {
    if (!input || !output || !output_size)
        return -1;

    size_t num_blocks = input_size / (P_WORDS * sizeof(uint32_t));
    if (num_blocks == 0)
        return -2;

    RuleSet*  d_rules = get_uploaded_rule_bank_devptr();
    uint32_t* d_masks = get_uploaded_payload_masks_devptr();
    if (!d_rules || !d_masks)
        return -3;

    uint32_t *d_in_headers=nullptr, *d_in_t1=nullptr, *d_in_t2=nullptr,
             *d_in_t3=nullptr, *d_in_graph=nullptr, *d_in_payload=nullptr;

    uint32_t *d_out_headers=nullptr, *d_out_t1=nullptr, *d_out_t2=nullptr,
             *d_out_t3=nullptr, *d_out_graph=nullptr, *d_out_payload=nullptr;

    size_t payload_bytes = num_blocks * P_WORDS * sizeof(uint32_t);

    cudaMalloc(&d_in_payload,  payload_bytes);
    cudaMalloc(&d_out_payload, payload_bytes);
    cudaMemcpy(d_in_payload, input, payload_bytes, cudaMemcpyHostToDevice);

    cudaMalloc(&d_in_headers,  num_blocks * sizeof(uint32_t));
    cudaMalloc(&d_in_t1,       num_blocks * T1_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_in_t2,       num_blocks * T2_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_in_t3,       num_blocks * T3_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_in_graph,    num_blocks * G_WORDS  * sizeof(uint32_t));

    cudaMalloc(&d_out_headers, num_blocks * sizeof(uint32_t));
    cudaMalloc(&d_out_t1,      num_blocks * T1_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_out_t2,      num_blocks * T2_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_out_t3,      num_blocks * T3_WORDS * sizeof(uint32_t));
    cudaMalloc(&d_out_graph,   num_blocks * G_WORDS  * sizeof(uint32_t));

    Metrics* d_metrics = nullptr;
    cudaMalloc(&d_metrics, num_blocks * sizeof(Metrics));
    cudaMemset(d_metrics, 0, num_blocks * sizeof(Metrics));

    launch_bitdrop_decompress_soa(
        d_in_headers, d_in_t1, d_in_t2, d_in_t3, d_in_graph, d_in_payload,
        d_out_headers, d_out_t1, d_out_t2, d_out_t3, d_out_graph, d_out_payload,
        d_rules, d_masks, static_cast<int>(num_blocks), d_metrics
    );

    cudaDeviceSynchronize();

    cudaMemcpy(output, d_out_payload, payload_bytes, cudaMemcpyDeviceToHost);
    *output_size = payload_bytes;

    cudaFree(d_in_headers); cudaFree(d_in_t1); cudaFree(d_in_t2);
    cudaFree(d_in_t3); cudaFree(d_in_graph); cudaFree(d_in_payload);

    cudaFree(d_out_headers); cudaFree(d_out_t1); cudaFree(d_out_t2);
    cudaFree(d_out_t3); cudaFree(d_out_graph); cudaFree(d_out_payload);

    cudaFree(d_metrics);

    return 0;
}





















