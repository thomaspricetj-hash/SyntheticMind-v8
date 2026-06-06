// bitdrop_decompress_pipeline.cu
// GPU pipeline wrapper for bitdrop_inverse_kernel

#include "bitdrop_decompress.h"
#include "bitdrop_kernel_soa.h"
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>

// Optional debug toggle
//#define BITDROP_DECOMP_DEBUG 1

// Forward declarations for future reversible decompression (rule/mask tables)
extern "C" RuleSet*   get_uploaded_rule_bank_devptr();
extern "C" uint32_t*  get_uploaded_payload_masks_devptr();

// ---------------------------------------------------------------------------
// Pointer-only safety guard (future-proof for reversible decompression)
// ---------------------------------------------------------------------------
static inline void bitdrop_require_tables_decomp() {
    RuleSet*   rules = get_uploaded_rule_bank_devptr();
    uint32_t*  masks = get_uploaded_payload_masks_devptr();

#if BITDROP_DECOMP_DEBUG
    std::fprintf(stderr,
        "[BitDropDecompress] rule_bank=%p masks=%p\n",
        (void*)rules, (void*)masks);
#endif

    // Not fatal today (inverse kernel doesn’t use them yet),
    // but we enforce it now to keep architecture consistent.
    if (!rules || !masks) {
        std::fprintf(stderr,
            "[BitDropDecompress] ERROR: device tables missing — "
            "call set_device_tables_from_host() before decompression.\n");
        std::exit(1);
    }
}

// ---------------------------------------------------------------------------
// CUDA error helper
// ---------------------------------------------------------------------------
static inline bool check_cuda_local(cudaError_t err, const char* msg) {
    if (err != cudaSuccess) {
        std::fprintf(stderr, "[BitDropDecompress] %s: %s\n",
                     msg, cudaGetErrorString(err));
        return false;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Grid helper (same as compression pipeline)
// ---------------------------------------------------------------------------
static inline int bitdrop_grid_for_blocks(int num_blocks) {
    return (num_blocks > 0) ? num_blocks : 1;
}

// ---------------------------------------------------------------------------
// Kernel prototype
// ---------------------------------------------------------------------------
__global__ void bitdrop_inverse_kernel(
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
    int num_blocks
);

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
struct BitDropDecompressContext {
    int max_blocks;

    uint32_t* d_in_headers;
    uint32_t* d_in_t1;
    uint32_t* d_in_t2;
    uint32_t* d_in_t3;
    uint32_t* d_in_graph;
    uint32_t* d_in_payload;

    uint32_t* d_out_headers;
    uint32_t* d_out_t1;
    uint32_t* d_out_t2;
    uint32_t* d_out_t3;
    uint32_t* d_out_graph;
    uint32_t* d_out_payload;
};

// ---------------------------------------------------------------------------
// Context creation
// ---------------------------------------------------------------------------
BitDropDecompressContext* bitdrop_decompress_create_context(int max_blocks) {
    if (max_blocks <= 0) return nullptr;

    BitDropDecompressContext* ctx = new BitDropDecompressContext{};
    ctx->max_blocks = max_blocks;

    size_t h_sz = size_t(max_blocks) * sizeof(uint32_t);
    size_t t1_sz = size_t(max_blocks) * T1_WORDS * sizeof(uint32_t);
    size_t t2_sz = size_t(max_blocks) * T2_WORDS * sizeof(uint32_t);
    size_t t3_sz = size_t(max_blocks) * T3_WORDS * sizeof(uint32_t);
    size_t g_sz  = size_t(max_blocks) * G_WORDS  * sizeof(uint32_t);
    size_t p_sz  = size_t(max_blocks) * P_WORDS  * sizeof(uint32_t);

    if (!check_cuda_local(cudaMalloc(&ctx->d_in_headers,  h_sz), "cudaMalloc d_in_headers") ||
        !check_cuda_local(cudaMalloc(&ctx->d_in_t1,       t1_sz), "cudaMalloc d_in_t1") ||
        !check_cuda_local(cudaMalloc(&ctx->d_in_t2,       t2_sz), "cudaMalloc d_in_t2") ||
        !check_cuda_local(cudaMalloc(&ctx->d_in_t3,       t3_sz), "cudaMalloc d_in_t3") ||
        !check_cuda_local(cudaMalloc(&ctx->d_in_graph,    g_sz),  "cudaMalloc d_in_graph") ||
        !check_cuda_local(cudaMalloc(&ctx->d_in_payload,  p_sz),  "cudaMalloc d_in_payload") ||
        !check_cuda_local(cudaMalloc(&ctx->d_out_headers, h_sz),  "cudaMalloc d_out_headers") ||
        !check_cuda_local(cudaMalloc(&ctx->d_out_t1,      t1_sz), "cudaMalloc d_out_t1") ||
        !check_cuda_local(cudaMalloc(&ctx->d_out_t2,      t2_sz), "cudaMalloc d_out_t2") ||
        !check_cuda_local(cudaMalloc(&ctx->d_out_t3,      t3_sz), "cudaMalloc d_out_t3") ||
        !check_cuda_local(cudaMalloc(&ctx->d_out_graph,   g_sz),  "cudaMalloc d_out_graph") ||
        !check_cuda_local(cudaMalloc(&ctx->d_out_payload, p_sz),  "cudaMalloc d_out_payload")) {
        bitdrop_decompress_destroy_context(ctx);
        return nullptr;
    }

    return ctx;
}

// ---------------------------------------------------------------------------
// Destroy context
// ---------------------------------------------------------------------------
void bitdrop_decompress_destroy_context(BitDropDecompressContext* ctx) {
    if (!ctx) return;
    cudaFree(ctx->d_in_headers);
    cudaFree(ctx->d_in_t1);
    cudaFree(ctx->d_in_t2);
    cudaFree(ctx->d_in_t3);
    cudaFree(ctx->d_in_graph);
    cudaFree(ctx->d_in_payload);
    cudaFree(ctx->d_out_headers);
    cudaFree(ctx->d_out_t1);
    cudaFree(ctx->d_out_t2);
    cudaFree(ctx->d_out_t3);
    cudaFree(ctx->d_out_graph);
    cudaFree(ctx->d_out_payload);
    delete ctx;
}

// ---------------------------------------------------------------------------
// Main decompression entry
// ---------------------------------------------------------------------------
BitDropResult bitdrop_gpu_decompress_soa(
    BitDropDecompressContext* ctx,
    int num_blocks,
    const uint32_t* h_in_headers,
    const uint32_t* h_in_t1,
    const uint32_t* h_in_t2,
    const uint32_t* h_in_t3,
    const uint32_t* h_in_graph,
    const uint32_t* h_in_payload,
    uint32_t* h_out_headers,
    uint32_t* h_out_t1,
    uint32_t* h_out_t2,
    uint32_t* h_out_t3,
    uint32_t* h_out_graph,
    uint32_t* h_out_payload
) {
    BitDropResult r{true, nullptr, 0.0, 0.0};

    if (!ctx || num_blocks <= 0) {
        r.ok = false;
        r.error = "invalid context or num_blocks";
        return r;
    }

    if (num_blocks > ctx->max_blocks) {
        r.ok = false;
        r.error = "num_blocks > max_blocks in context";
        return r;
    }

    // Ensure rule/mask tables exist (future reversible decompression)
    bitdrop_require_tables_decomp();

    size_t h_sz = size_t(num_blocks) * sizeof(uint32_t);
    size_t t1_sz = size_t(num_blocks) * T1_WORDS * sizeof(uint32_t);
    size_t t2_sz = size_t(num_blocks) * T2_WORDS * sizeof(uint32_t);
    size_t t3_sz = size_t(num_blocks) * T3_WORDS * sizeof(uint32_t);
    size_t g_sz  = size_t(num_blocks) * G_WORDS  * sizeof(uint32_t);
    size_t p_sz  = size_t(num_blocks) * P_WORDS  * sizeof(uint32_t);

    auto cc = [&](cudaError_t e, const char* msg) {
        if (!check_cuda_local(e, msg)) {
            r.ok = false;
            r.error = cudaGetErrorString(e);
            return false;
        }
        return true;
    };

    cudaEvent_t start, stop;
    cc(cudaEventCreate(&start), "event create");
    cc(cudaEventCreate(&stop),  "event create");
    if (!r.ok) return r;

    cc(cudaEventRecord(start), "event record");
    if (!r.ok) return r;

    // H2D
    cc(cudaMemcpy(ctx->d_in_headers, h_in_headers, h_sz, cudaMemcpyHostToDevice), "H2D headers");
    cc(cudaMemcpy(ctx->d_in_t1,      h_in_t1,      t1_sz, cudaMemcpyHostToDevice), "H2D t1");
    cc(cudaMemcpy(ctx->d_in_t2,      h_in_t2,      t2_sz, cudaMemcpyHostToDevice), "H2D t2");
    cc(cudaMemcpy(ctx->d_in_t3,      h_in_t3,      t3_sz, cudaMemcpyHostToDevice), "H2D t3");
    cc(cudaMemcpy(ctx->d_in_graph,   h_in_graph,   g_sz,  cudaMemcpyHostToDevice), "H2D graph");
    cc(cudaMemcpy(ctx->d_in_payload, h_in_payload, p_sz,  cudaMemcpyHostToDevice), "H2D payload");
    if (!r.ok) return r;

    // Launch
    int threads = 256;
    int blocks  = bitdrop_grid_for_blocks(num_blocks);

    bitdrop_inverse_kernel<<<blocks, threads>>>(
        ctx->d_in_headers,
        ctx->d_in_t1,
        ctx->d_in_t2,
        ctx->d_in_t3,
        ctx->d_in_graph,
        ctx->d_in_payload,
        ctx->d_out_headers,
        ctx->d_out_t1,
        ctx->d_out_t2,
        ctx->d_out_t3,
        ctx->d_out_graph,
        ctx->d_out_payload,
        num_blocks
    );

    cc(cudaGetLastError(), "kernel launch");
    cc(cudaDeviceSynchronize(), "kernel sync");
    if (!r.ok) return r;

    // D2H
    cc(cudaMemcpy(h_out_headers, ctx->d_out_headers, h_sz,  cudaMemcpyDeviceToHost), "D2H headers");
    cc(cudaMemcpy(h_out_t1,      ctx->d_out_t1,      t1_sz, cudaMemcpyDeviceToHost), "D2H t1");
    cc(cudaMemcpy(h_out_t2,      ctx->d_out_t2,      t2_sz, cudaMemcpyDeviceToHost), "D2H t2");
    cc(cudaMemcpy(h_out_t3,      ctx->d_out_t3,      t3_sz, cudaMemcpyDeviceToHost), "D2H t3");
    cc(cudaMemcpy(h_out_graph,   ctx->d_out_graph,   g_sz,  cudaMemcpyDeviceToHost), "D2H graph");
    cc(cudaMemcpy(h_out_payload, ctx->d_out_payload, p_sz,  cudaMemcpyDeviceToHost), "D2H payload");
    if (!r.ok) return r;

    cc(cudaEventRecord(stop), "event record");
    cc(cudaEventSynchronize(stop), "event sync");
    if (!r.ok) return r;

    float ms = 0.0f;
    cc(cudaEventElapsedTime(&ms, start, stop), "event elapsed");
    if (!r.ok) return r;

    double total_bytes =
        double(num_blocks) *
        double(sizeof(uint32_t) * (1 + T1_WORDS + T2_WORDS + T3_WORDS + G_WORDS + P_WORDS));

    double gb = total_bytes / (1024.0 * 1024.0 * 1024.0);
    r.elapsed_ms = ms;
    r.throughput_gbps = gb / (ms / 1000.0);

    return r;
}

