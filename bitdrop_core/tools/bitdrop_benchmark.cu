// bitdrop_benchmark.cu
// Benchmark harness for BitDrop SoA + uint4 kernel

#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>

extern void upload_rule_bank(const RuleSet* host_rules, int count);
extern void upload_payload_level_masks(const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]);

extern void launch_bitdrop_soa(
    const uint32_t* d_headers,
    const uint32_t* d_tier1,
    const uint32_t* d_tier2,
    const uint32_t* d_tier3,
    const uint32_t* d_graph_links,
    const uint32_t* d_payload,
    uint32_t* d_out_headers,
    uint32_t* d_out_tier1,
    uint32_t* d_out_tier2,
    uint32_t* d_out_tier3,
    uint32_t* d_out_graph_links,
    uint32_t* d_out_payload,
    int num_blocks
#ifdef BITDROP_ENABLE_METRICS
    , Metrics* d_metrics
#endif
);

static inline void check(cudaError_t err, const char* msg) {
    if (err != cudaSuccess) {
        printf("CUDA ERROR %s: %s\n", msg, cudaGetErrorString(err));
        exit(1);
    }
}

int main() {
    const int N = 10'000'000;   // 10 million blocks (≈10 GB of data)
    const int BYTES_PER_BLOCK = 
        sizeof(uint32_t) + 
        (T1_WORDS + T2_WORDS + T3_WORDS + G_WORDS + P_WORDS) * sizeof(uint32_t);

    printf("Benchmarking BitDrop SoA kernel on %d blocks (%.2f GB)\n",
           N, N * BYTES_PER_BLOCK / (1024.0 * 1024.0 * 1024.0));

    // Allocate device buffers
    uint32_t *d_headers, *d_t1, *d_t2, *d_t3, *d_graph, *d_payload;
    uint32_t *d_out_headers, *d_out_t1, *d_out_t2, *d_out_t3, *d_out_graph, *d_out_payload;

    check(cudaMalloc(&d_headers, N * sizeof(uint32_t)), "malloc headers");
    check(cudaMalloc(&d_t1, N * T1_WORDS * sizeof(uint32_t)), "malloc t1");
    check(cudaMalloc(&d_t2, N * T2_WORDS * sizeof(uint32_t)), "malloc t2");
    check(cudaMalloc(&d_t3, N * T3_WORDS * sizeof(uint32_t)), "malloc t3");
    check(cudaMalloc(&d_graph, N * G_WORDS * sizeof(uint32_t)), "malloc graph");
    check(cudaMalloc(&d_payload, N * P_WORDS * sizeof(uint32_t)), "malloc payload");

    check(cudaMalloc(&d_out_headers, N * sizeof(uint32_t)), "malloc out headers");
    check(cudaMalloc(&d_out_t1, N * T1_WORDS * sizeof(uint32_t)), "malloc out t1");
    check(cudaMalloc(&d_out_t2, N * T2_WORDS * sizeof(uint32_t)), "malloc out t2");
    check(cudaMalloc(&d_out_t3, N * T3_WORDS * sizeof(uint32_t)), "malloc out t3");
    check(cudaMalloc(&d_out_graph, N * G_WORDS * sizeof(uint32_t)), "malloc out graph");
    check(cudaMalloc(&d_out_payload, N * P_WORDS * sizeof(uint32_t)), "malloc out payload");

    // Fill with dummy data
    check(cudaMemset(d_headers, 0x01, N * sizeof(uint32_t)), "memset headers");
    check(cudaMemset(d_t1, 0xFF, N * T1_WORDS * sizeof(uint32_t)), "memset t1");
    check(cudaMemset(d_t2, 0xAA, N * T2_WORDS * sizeof(uint32_t)), "memset t2");
    check(cudaMemset(d_t3, 0x55, N * T3_WORDS * sizeof(uint32_t)), "memset t3");
    check(cudaMemset(d_graph, 0x0F, N * G_WORDS * sizeof(uint32_t)), "memset graph");
    check(cudaMemset(d_payload, 0xFF, N * P_WORDS * sizeof(uint32_t)), "memset payload");

    // Upload rule bank + masks (you already have this)
    RuleSet host_rules[RULE_BANK_SIZE] = {};
    uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS] = {};
    upload_rule_bank(host_rules, RULE_BANK_SIZE);
    upload_payload_level_masks(host_masks);

    // Warm-up
    for (int i = 0; i < 5; i++) {
        launch_bitdrop_soa(
            d_headers, d_t1, d_t2, d_t3, d_graph, d_payload,
            d_out_headers, d_out_t1, d_out_t2, d_out_t3, d_out_graph, d_out_payload,
            N
        );
    }
    cudaDeviceSynchronize();

    // Benchmark
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    const int RUNS = 10;
    float total_ms = 0;

    for (int i = 0; i < RUNS; i++) {
        cudaEventRecord(start);
        launch_bitdrop_soa(
            d_headers, d_t1, d_t2, d_t3, d_graph, d_payload,
            d_out_headers, d_out_t1, d_out_t2, d_out_t3, d_out_graph, d_out_payload,
            N
        );
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);

        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        total_ms += ms;
    }

    float avg_ms = total_ms / RUNS;
    float gb = (double)N * BYTES_PER_BLOCK / (1024.0 * 1024.0 * 1024.0);
    float gbps = gb / (avg_ms / 1000.0);

    printf("\n===== BitDrop SoA Benchmark =====\n");
    printf("Blocks: %d\n", N);
    printf("Data size: %.2f GB\n", gb);
    printf("Avg time: %.3f ms\n", avg_ms);
    printf("Throughput: %.2f GB/s\n", gbps);
    printf("=================================\n");

    return 0;
}
