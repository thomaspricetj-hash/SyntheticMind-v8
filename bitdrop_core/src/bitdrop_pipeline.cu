// src/bitdrop_pipeline.cu
// BitDrop multi-pass GPU pipeline (SoA, streams, pinned buffers)

#include "bitdrop_kernel_soa.h"
#include "bitdrop_host_api.h"
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// Forward declarations for host-side getters
extern "C" RuleSet*   get_uploaded_rule_bank_devptr();
extern "C" uint32_t*  get_uploaded_payload_masks_devptr();

// =========================
//  CONTEXT
// =========================

struct BitDropContext {
    int    max_blocks;
    int    num_passes;

    // Device buffers (double-buffered for multi-pass)
    uint32_t *d_headers[2];
    uint32_t *d_tier1[2];
    uint32_t *d_tier2[2];
    uint32_t *d_tier3[2];
    uint32_t *d_graph[2];
    uint32_t *d_payload[2];

    Metrics* d_metrics;

    cudaStream_t stream;
};

// =========================
//  INTERNAL HELPERS
// =========================

static inline void check_cuda_pipe(cudaError_t err, const char* msg) {
    if (err != cudaSuccess) {
        std::fprintf(stderr, "[BitDropPipeline] %s: %s\n", msg, cudaGetErrorString(err));
        std::exit(1);
    }
}

// Ensure rule/mask tables exist before running pipeline
static inline void bitdrop_require_tables() {
    RuleSet*   rules = get_uploaded_rule_bank_devptr();
    uint32_t*  masks = get_uploaded_payload_masks_devptr();

    if (!rules || !masks) {
        std::fprintf(stderr,
            "[BitDropPipeline] ERROR: device tables missing — did you call set_device_tables_from_host()?\n");
        std::exit(1);
    }
}

// =========================
//  PUBLIC API
// =========================

BitDropContext* bitdrop_create_context(int max_blocks, int num_passes) {
    if (max_blocks <= 0) {
        std::fprintf(stderr, "bitdrop_create_context: max_blocks must be > 0\n");
        return nullptr;
    }
    if (num_passes <= 0) num_passes = 1;
    if (num_passes > 8)  num_passes = 8;

    BitDropContext* ctx = (BitDropContext*)std::calloc(1, sizeof(BitDropContext));
    ctx->max_blocks = max_blocks;
    ctx->num_passes = num_passes;

    check_cuda_pipe(cudaStreamCreate(&ctx->stream), "cudaStreamCreate");

    for (int b = 0; b < 2; ++b) {
        check_cuda_pipe(cudaMalloc(&ctx->d_headers[b], max_blocks * sizeof(uint32_t)), "malloc d_headers");
        check_cuda_pipe(cudaMalloc(&ctx->d_tier1[b],  max_blocks * T1_WORDS * sizeof(uint32_t)), "malloc d_tier1");
        check_cuda_pipe(cudaMalloc(&ctx->d_tier2[b],  max_blocks * T2_WORDS * sizeof(uint32_t)), "malloc d_tier2");
        check_cuda_pipe(cudaMalloc(&ctx->d_tier3[b],  max_blocks * T3_WORDS * sizeof(uint32_t)), "malloc d_tier3");
        check_cuda_pipe(cudaMalloc(&ctx->d_graph[b],  max_blocks * G_WORDS  * sizeof(uint32_t)), "malloc d_graph");
        check_cuda_pipe(cudaMalloc(&ctx->d_payload[b],max_blocks * P_WORDS  * sizeof(uint32_t)), "malloc d_payload");
    }

    check_cuda_pipe(cudaMalloc(&ctx->d_metrics, max_blocks * sizeof(Metrics)), "malloc d_metrics");

    return ctx;
}

void bitdrop_destroy_context(BitDropContext* ctx) {
    if (!ctx) return;

    for (int b = 0; b < 2; ++b) {
        cudaFree(ctx->d_headers[b]);
        cudaFree(ctx->d_tier1[b]);
        cudaFree(ctx->d_tier2[b]);
        cudaFree(ctx->d_tier3[b]);
        cudaFree(ctx->d_graph[b]);
        cudaFree(ctx->d_payload[b]);
    }
    cudaFree(ctx->d_metrics);
    cudaStreamDestroy(ctx->stream);
    std::free(ctx);
}

// =========================
//  SINGLE PASS
// =========================

void bitdrop_run_single_pass(
    BitDropContext* ctx,
    int num_blocks,
    const uint32_t* h_headers,
    const uint32_t* h_tier1,
    const uint32_t* h_tier2,
    const uint32_t* h_tier3,
    const uint32_t* h_graph,
    const uint32_t* h_payload,
    uint32_t* h_out_headers,
    uint32_t* h_out_tier1,
    uint32_t* h_out_tier2,
    uint32_t* h_out_tier3,
    uint32_t* h_out_graph,
    uint32_t* h_out_payload,
    Metrics* h_metrics
) {
    if (!ctx) return;
    if (num_blocks > ctx->max_blocks) {
        std::fprintf(stderr, "bitdrop_run_single_pass: num_blocks > max_blocks\n");
        std::exit(1);
    }

    bitdrop_require_tables();

    size_t sz_headers = num_blocks * sizeof(uint32_t);
    size_t sz_t1      = num_blocks * T1_WORDS * sizeof(uint32_t);
    size_t sz_t2      = num_blocks * T2_WORDS * sizeof(uint32_t);
    size_t sz_t3      = num_blocks * T3_WORDS * sizeof(uint32_t);
    size_t sz_graph   = num_blocks * G_WORDS  * sizeof(uint32_t);
    size_t sz_payload = num_blocks * P_WORDS  * sizeof(uint32_t);

    // H2D
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_headers[0], h_headers, sz_headers,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy headers");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_tier1[0],   h_tier1,   sz_t1,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy t1");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_tier2[0],   h_tier2,   sz_t2,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy t2");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_tier3[0],   h_tier3,   sz_t3,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy t3");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_graph[0],   h_graph,   sz_graph,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy graph");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_payload[0], h_payload, sz_payload,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy payload");

    RuleSet*   d_rules = get_uploaded_rule_bank_devptr();
    uint32_t*  d_masks = get_uploaded_payload_masks_devptr();

    // Kernel
    launch_bitdrop_soa(
        ctx->d_headers[0],
        ctx->d_tier1[0],
        ctx->d_tier2[0],
        ctx->d_tier3[0],
        ctx->d_graph[0],
        ctx->d_payload[0],
        ctx->d_headers[1],
        ctx->d_tier1[1],
        ctx->d_tier2[1],
        ctx->d_tier3[1],
        ctx->d_graph[1],
        ctx->d_payload[1],
        d_rules,
        d_masks,
        num_blocks,
        ctx->d_metrics
    );

    check_cuda_pipe(cudaGetLastError(), "kernel launch");

    // D2H
    check_cuda_pipe(cudaMemcpyAsync(h_out_headers, ctx->d_headers[1], sz_headers,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out headers");
    check_cuda_pipe(cudaMemcpyAsync(h_out_tier1,   ctx->d_tier1[1],   sz_t1,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out t1");
    check_cuda_pipe(cudaMemcpyAsync(h_out_tier2,   ctx->d_tier2[1],   sz_t2,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out t2");
    check_cuda_pipe(cudaMemcpyAsync(h_out_tier3,   ctx->d_tier3[1],   sz_t3,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out t3");
    check_cuda_pipe(cudaMemcpyAsync(h_out_graph,   ctx->d_graph[1],   sz_graph,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out graph");
    check_cuda_pipe(cudaMemcpyAsync(h_out_payload, ctx->d_payload[1], sz_payload,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out payload");

    if (h_metrics) {
        check_cuda_pipe(cudaMemcpyAsync(h_metrics, ctx->d_metrics,
                                        num_blocks * sizeof(Metrics),
                                        cudaMemcpyDeviceToHost, ctx->stream),
                        "cpy metrics");
    }

    check_cuda_pipe(cudaStreamSynchronize(ctx->stream), "stream sync");
}

// =========================
//  MULTI PASS
// =========================

void bitdrop_run_multi_pass(
    BitDropContext* ctx,
    int num_blocks,
    const uint32_t* h_headers,
    const uint32_t* h_tier1,
    const uint32_t* h_tier2,
    const uint32_t* h_tier3,
    const uint32_t* h_graph,
    const uint32_t* h_payload,
    uint32_t* h_out_headers,
    uint32_t* h_out_tier1,
    uint32_t* h_out_tier2,
    uint32_t* h_out_tier3,
    uint32_t* h_out_graph,
    uint32_t* h_out_payload,
    Metrics* h_metrics
) {
    if (!ctx) return;
    if (num_blocks > ctx->max_blocks) {
        std::fprintf(stderr, "bitdrop_run_multi_pass: num_blocks > max_blocks\n");
        std::exit(1);
    }

    bitdrop_require_tables();

    size_t sz_headers = num_blocks * sizeof(uint32_t);
    size_t sz_t1      = num_blocks * T1_WORDS * sizeof(uint32_t);
    size_t sz_t2      = num_blocks * T2_WORDS * sizeof(uint32_t);
    size_t sz_t3      = num_blocks * T3_WORDS * sizeof(uint32_t);
    size_t sz_graph   = num_blocks * G_WORDS  * sizeof(uint32_t);
    size_t sz_payload = num_blocks * P_WORDS  * sizeof(uint32_t);

    // Initial H2D
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_headers[0], h_headers, sz_headers,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy headers");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_tier1[0],   h_tier1,   sz_t1,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy t1");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_tier2[0],   h_tier2,   sz_t2,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy t2");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_tier3[0],   h_tier3,   sz_t3,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy t3");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_graph[0],   h_graph,   sz_graph,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy graph");
    check_cuda_pipe(cudaMemcpyAsync(ctx->d_payload[0], h_payload, sz_payload,
                                    cudaMemcpyHostToDevice, ctx->stream), "cpy payload");

    int in_buf  = 0;
    int out_buf = 1;

    RuleSet*   d_rules = get_uploaded_rule_bank_devptr();
    uint32_t*  d_masks = get_uploaded_payload_masks_devptr();

    for (int pass = 0; pass < ctx->num_passes; ++pass) {
        launch_bitdrop_soa(
            ctx->d_headers[in_buf],
            ctx->d_tier1[in_buf],
            ctx->d_tier2[in_buf],
            ctx->d_tier3[in_buf],
            ctx->d_graph[in_buf],
            ctx->d_payload[in_buf],
            ctx->d_headers[out_buf],
            ctx->d_tier1[out_buf],
            ctx->d_tier2[out_buf],
            ctx->d_tier3[out_buf],
            ctx->d_graph[out_buf],
            ctx->d_payload[out_buf],
            d_rules,
            d_masks,
            num_blocks,
            ctx->d_metrics
        );

        check_cuda_pipe(cudaGetLastError(), "kernel launch");

        int tmp = in_buf;
        in_buf  = out_buf;
        out_buf = tmp;
    }

    // Final D2H
    check_cuda_pipe(cudaMemcpyAsync(h_out_headers, ctx->d_headers[in_buf], sz_headers,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out headers");
    check_cuda_pipe(cudaMemcpyAsync(h_out_tier1,   ctx->d_tier1[in_buf],   sz_t1,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out t1");
    check_cuda_pipe(cudaMemcpyAsync(h_out_tier2,   ctx->d_tier2[in_buf],   sz_t2,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out t2");
    check_cuda_pipe(cudaMemcpyAsync(h_out_tier3,   ctx->d_tier3[in_buf],   sz_t3,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out t3");
    check_cuda_pipe(cudaMemcpyAsync(h_out_graph,   ctx->d_graph[in_buf],   sz_graph,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out graph");
    check_cuda_pipe(cudaMemcpyAsync(h_out_payload, ctx->d_payload[in_buf], sz_payload,
                                    cudaMemcpyDeviceToHost, ctx->stream), "cpy out payload");

    if (h_metrics) {
        check_cuda_pipe(cudaMemcpyAsync(h_metrics, ctx->d_metrics,
                                        num_blocks * sizeof(Metrics),
                                        cudaMemcpyDeviceToHost, ctx->stream),
                        "cpy metrics");
    }

    check_cuda_pipe(cudaStreamSynchronize(ctx->stream), "stream sync");
}







