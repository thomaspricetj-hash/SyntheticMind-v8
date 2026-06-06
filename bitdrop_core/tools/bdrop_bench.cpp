// tools/bdrop_bench.cpp
// Kernel-only BitDrop v2 benchmark (no file I/O, no host<->device copies in loop)

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>        // <-- added for std::strcmp, std::strtoull
#include <cuda_runtime.h>

#include "bitdrop_kernel_soa.h"   // P_WORDS, T1_WORDS, T2_WORDS, T3_WORDS, G_WORDS, RULE_BANK_SIZE, LEVEL_TABLE_SIZE, RuleSet, Metrics
#include "bitdrop_host_api.h"     // set_device_tables_from_host, get_uploaded_rule_bank_devptr, get_uploaded_payload_masks_devptr, launch_bitdrop_soa

#define CUDA_CHECK(expr) \
    do { \
        cudaError_t _err = (expr); \
        if (_err != cudaSuccess) { \
            std::fprintf(stderr, "[bdrop_bench] CUDA error %s:%d: %s\n", \
                         __FILE__, __LINE__, cudaGetErrorString(_err)); \
            std::exit(1); \
        } \
    } while (0)

static void print_usage(const char* prog) {
    std::fprintf(stderr,
        "BitDrop v2 Kernel Benchmark\n"
        "\n"
        "Usage:\n"
        "  %s [num_blocks] [iterations]\n"
        "\n"
        "Defaults:\n"
        "  num_blocks = 1048576 (64 MB payload)\n"
        "  iterations = 100\n"
        "\n",
        prog);
}

int main(int argc, char** argv) {
    size_t num_blocks = 1048576; // 1M blocks -> 64 MB payload
    int iterations    = 100;

    if (argc >= 2) {
        num_blocks = static_cast<size_t>(std::strtoull(argv[1], nullptr, 10));
    }
    if (argc >= 3) {
        iterations = std::atoi(argv[2]);
    }
    if (iterations <= 0) iterations = 1;

    if (argc == 2 && (std::strcmp(argv[1], "-h") == 0 || std::strcmp(argv[1], "--help") == 0)) {
        print_usage(argv[0]);
        return 0;
    }

    std::fprintf(stderr,
                 "[bdrop_bench] num_blocks = %zu, iterations = %d, P_WORDS = %d\n",
                 num_blocks, iterations, P_WORDS);

    const size_t headers_bytes = num_blocks * sizeof(uint32_t);
    const size_t t1_bytes      = num_blocks * T1_WORDS * sizeof(uint32_t);
    const size_t t2_bytes      = num_blocks * T2_WORDS * sizeof(uint32_t);
    const size_t t3_bytes      = num_blocks * T3_WORDS * sizeof(uint32_t);
    const size_t graph_bytes   = num_blocks * G_WORDS  * sizeof(uint32_t);
    const size_t payload_bytes = num_blocks * P_WORDS  * sizeof(uint32_t);

    std::fprintf(stderr,
                 "[bdrop_bench] payload_bytes = %zu (%.2f MB)\n",
                 payload_bytes,
                 payload_bytes / (1024.0 * 1024.0));

    // ------------------------------------------------------------
    // Allocate device buffers
    // ------------------------------------------------------------
    uint32_t *d_in_headers   = nullptr;
    uint32_t *d_in_t1        = nullptr;
    uint32_t *d_in_t2        = nullptr;
    uint32_t *d_in_t3        = nullptr;
    uint32_t *d_in_graph     = nullptr;
    uint32_t *d_in_payload   = nullptr;

    uint32_t *d_out_headers  = nullptr;
    uint32_t *d_out_t1       = nullptr;
    uint32_t *d_out_t2       = nullptr;
    uint32_t *d_out_t3       = nullptr;
    uint32_t *d_out_graph    = nullptr;
    uint32_t *d_out_payload  = nullptr;

    CUDA_CHECK(cudaMalloc(&d_in_headers,  headers_bytes));
    CUDA_CHECK(cudaMalloc(&d_in_t1,       t1_bytes));
    CUDA_CHECK(cudaMalloc(&d_in_t2,       t2_bytes));
    CUDA_CHECK(cudaMalloc(&d_in_t3,       t3_bytes));
    CUDA_CHECK(cudaMalloc(&d_in_graph,    graph_bytes));
    CUDA_CHECK(cudaMalloc(&d_in_payload,  payload_bytes));

    CUDA_CHECK(cudaMalloc(&d_out_headers, headers_bytes));
    CUDA_CHECK(cudaMalloc(&d_out_t1,      t1_bytes));
    CUDA_CHECK(cudaMalloc(&d_out_t2,      t2_bytes));
    CUDA_CHECK(cudaMalloc(&d_out_t3,      t3_bytes));
    CUDA_CHECK(cudaMalloc(&d_out_graph,   graph_bytes));
    CUDA_CHECK(cudaMalloc(&d_out_payload, payload_bytes));

    // Initialize inputs (simple pattern)
    CUDA_CHECK(cudaMemset(d_in_headers, 0, headers_bytes));
    CUDA_CHECK(cudaMemset(d_in_t1,      0, t1_bytes));
    CUDA_CHECK(cudaMemset(d_in_t2,      0, t2_bytes));
    CUDA_CHECK(cudaMemset(d_in_t3,      0, t3_bytes));
    CUDA_CHECK(cudaMemset(d_in_graph,   0, graph_bytes));
    CUDA_CHECK(cudaMemset(d_in_payload, 0xAA, payload_bytes)); // arbitrary non-zero pattern

    // ------------------------------------------------------------
    // Initialize rule tables on device
    // ------------------------------------------------------------
    RuleSet* host_rules =
        static_cast<RuleSet*>(std::calloc(RULE_BANK_SIZE, sizeof(RuleSet)));

    uint32_t* host_masks =
        static_cast<uint32_t*>(std::calloc(
            RULE_BANK_SIZE * LEVEL_TABLE_SIZE * P_WORDS,
            sizeof(uint32_t)));

    if (!host_rules || !host_masks) {
        std::fprintf(stderr, "[bdrop_bench] Failed to allocate host rule tables.\n");
        std::free(host_rules);
        std::free(host_masks);
        return 1;
    }

    // Example: set a simple non-trivial mask pattern
    for (int r = 0; r < RULE_BANK_SIZE; ++r) {
        host_rules[r].max_compression_level = 8; // mid-level
        for (int w = 0; w < P_WORDS; ++w) {
            host_rules[r].payload_base_mask[w] = 0xFFFFFFFFu;
        }
    }

    set_device_tables_from_host(
        host_rules,
        RULE_BANK_SIZE,
        reinterpret_cast<const uint32_t (*)[LEVEL_TABLE_SIZE][P_WORDS]>(
            host_masks));

    RuleSet*  d_rules  = get_uploaded_rule_bank_devptr();
    uint32_t* d_masks  = get_uploaded_payload_masks_devptr();

    if (!d_rules || !d_masks) {
        std::fprintf(stderr, "[bdrop_bench] Device rule pointers are null.\n");
        std::free(host_rules);
        std::free(host_masks);
        return 1;
    }

    // ------------------------------------------------------------
    // Metrics for all blocks
    // ------------------------------------------------------------
    Metrics* d_metrics = nullptr;
    CUDA_CHECK(cudaMalloc(&d_metrics, num_blocks * sizeof(Metrics)));
    CUDA_CHECK(cudaMemset(d_metrics, 0, num_blocks * sizeof(Metrics)));

    // ------------------------------------------------------------
    // Warm-up
    // ------------------------------------------------------------
    std::fprintf(stderr, "[bdrop_bench] Warm-up launch...\n");
    launch_bitdrop_soa(
        d_in_headers,
        d_in_t1,
        d_in_t2,
        d_in_t3,
        d_in_graph,
        d_in_payload,
        d_out_headers,
        d_out_t1,
        d_out_t2,
        d_out_t3,
        d_out_graph,
        d_out_payload,
        d_rules,
        d_masks,
        static_cast<int>(num_blocks),
        d_metrics);
    CUDA_CHECK(cudaDeviceSynchronize());

    // ------------------------------------------------------------
    // Timed loop
    // ------------------------------------------------------------
    std::fprintf(stderr, "[bdrop_bench] Benchmarking kernel...\n");

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    CUDA_CHECK(cudaEventRecord(start, 0));
    for (int i = 0; i < iterations; ++i) {
        launch_bitdrop_soa(
            d_in_headers,
            d_in_t1,
            d_in_t2,
            d_in_t3,
            d_in_graph,
            d_in_payload,
            d_out_headers,
            d_out_t1,
            d_out_t2,
            d_out_t3,
            d_out_graph,
            d_out_payload,
            d_rules,
            d_masks,
            static_cast<int>(num_blocks),
            d_metrics);
    }
    CUDA_CHECK(cudaEventRecord(stop, 0));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));

    const double total_bytes = static_cast<double>(payload_bytes) * static_cast<double>(iterations);
    const double total_gb    = total_bytes / (1024.0 * 1024.0 * 1024.0);
    const double total_s     = ms / 1000.0;
    const double gbps        = total_gb / total_s;

    std::printf("Kernel-only benchmark:\n");
    std::printf("  Blocks       : %zu\n", num_blocks);
    std::printf("  Iterations   : %d\n", iterations);
    std::printf("  Payload/iter : %.2f MB\n", payload_bytes / (1024.0 * 1024.0));
    std::printf("  Total time   : %.3f ms\n", ms);
    std::printf("  Throughput   : %.2f GB/s (payload only)\n", gbps);

    // ------------------------------------------------------------
    // Cleanup
    // ------------------------------------------------------------
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));

    std::free(host_rules);
    std::free(host_masks);

    CUDA_CHECK(cudaFree(d_in_headers));
    CUDA_CHECK(cudaFree(d_in_t1));
    CUDA_CHECK(cudaFree(d_in_t2));
    CUDA_CHECK(cudaFree(d_in_t3));
    CUDA_CHECK(cudaFree(d_in_graph));
    CUDA_CHECK(cudaFree(d_in_payload));

    CUDA_CHECK(cudaFree(d_out_headers));
    CUDA_CHECK(cudaFree(d_out_t1));
    CUDA_CHECK(cudaFree(d_out_t2));
    CUDA_CHECK(cudaFree(d_out_t3));
    CUDA_CHECK(cudaFree(d_out_graph));
    CUDA_CHECK(cudaFree(d_out_payload));

    CUDA_CHECK(cudaFree(d_metrics));

    return 0;
}

