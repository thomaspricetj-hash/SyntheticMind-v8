// bitdrop_benchmark.cpp
// Production-grade benchmark for BitDrop SoA + pipeline

#include "bitdrop_kernel_soa.h"
#include "bitdrop_pipeline.h"
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static inline void check(cudaError_t err, const char* msg) {
    if (err != cudaSuccess) {
        printf("[Benchmark] %s: %s\n", msg, cudaGetErrorString(err));
        exit(1);
    }
}

int main() {
    const int NUM_BLOCKS = 10'000'000;   // 10 million blocks
    const int PASSES     = 3;            // multi-pass collapse

    printf("=== BitDrop Benchmark ===\n");
    printf("Blocks: %d\n", NUM_BLOCKS);
    printf("Passes: %d\n", PASSES);

    // -----------------------------
    // Allocate host SoA buffers
    // -----------------------------
    uint32_t* h_headers     = (uint32_t*)malloc(NUM_BLOCKS * sizeof(uint32_t));
    uint32_t* h_t1          = (uint32_t*)malloc(NUM_BLOCKS * T1_WORDS * sizeof(uint32_t));
    uint32_t* h_t2          = (uint32_t*)malloc(NUM_BLOCKS * T2_WORDS * sizeof(uint32_t));
    uint32_t* h_t3          = (uint32_t*)malloc(NUM_BLOCKS * T3_WORDS * sizeof(uint32_t));
    uint32_t* h_graph       = (uint32_t*)malloc(NUM_BLOCKS * G_WORDS  * sizeof(uint32_t));
    uint32_t* h_payload     = (uint32_t*)malloc(NUM_BLOCKS * P_WORDS  * sizeof(uint32_t));

    uint32_t* h_out_headers = (uint32_t*)malloc(NUM_BLOCKS * sizeof(uint32_t));
    uint32_t* h_out_t1      = (uint32_t*)malloc(NUM_BLOCKS * T1_WORDS * sizeof(uint32_t));
    uint32_t* h_out_t2      = (uint32_t*)malloc(NUM_BLOCKS * T2_WORDS * sizeof(uint32_t));
    uint32_t* h_out_t3      = (uint32_t*)malloc(NUM_BLOCKS * T3_WORDS * sizeof(uint32_t));
    uint32_t* h_out_graph   = (uint32_t*)malloc(NUM_BLOCKS * G_WORDS  * sizeof(uint32_t));
    uint32_t* h_out_payload = (uint32_t*)malloc(NUM_BLOCKS * P_WORDS  * sizeof(uint32_t));

    Metrics* h_metrics = (Metrics*)malloc(NUM_BLOCKS * sizeof(Metrics));

    // -----------------------------
    // Fill with dummy data
    // -----------------------------
    for (int i = 0; i < NUM_BLOCKS; i++) {
        h_headers[i] = (0x01u << 24) | (0x02u << 16) | (0x03u << 8) | (i & 1);

        int t1b = i * T1_WORDS;
        int t2b = i * T2_WORDS;
        int t3b = i * T3_WORDS;
        int gb  = i * G_WORDS;
        int pb  = i * P_WORDS;

        for (int j = 0; j < T1_WORDS; j++) h_t1[t1b + j] = 0xFFFFFFFFu;
        for (int j = 0; j < T2_WORDS; j++) h_t2[t2b + j] = 0xAAAAAAAAu;
        for (int j = 0; j < T3_WORDS; j++) h_t3[t3b + j] = 0x55555555u;
        for (int j = 0; j < G_WORDS;  j++) h_graph[gb + j] = 0x0F0F0F0Fu;
        for (int j = 0; j < P_WORDS;  j++) h_payload[pb + j] = 0xFFFFFFFFu;
    }

    // -----------------------------
    // Upload rule bank + masks
    // -----------------------------
    RuleSet rules[RULE_BANK_SIZE] = {};
    uint32_t masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS] = {};

    for (int r = 0; r < RULE_BANK_SIZE; r++) {
        for (int i = 0; i < T1_WORDS; i++) rules[r].t1_protect_mask[i] = 0xFFFFFFFFu;
        for (int i = 0; i < T2_WORDS; i++) rules[r].t2_protect_mask[i] = 0xF0F0F0F0u;
        for (int i = 0; i < T3_WORDS; i++) rules[r].t3_drop_mask[i]    = 0x0F0F0F0Fu;
        for (int i = 0; i < P_WORDS; i++) rules[r].payload_base_mask[i]= 0xFFFFFFFFu;

        rules[r].max_compression_level = 128;
        rules[r].fragility_cap         = 96;

        for (int lvl = 0; lvl < LEVEL_TABLE_SIZE; lvl++) {
            float f = float(lvl + 1) / LEVEL_TABLE_SIZE;
            for (int w = 0; w < P_WORDS; w++) {
                uint32_t base = rules[r].payload_base_mask[w];
                uint32_t m = 0;
                if (f > 0.25f) m |= (base & 0x11111111u);
                if (f > 0.50f) m |= (base & 0x33333333u);
                if (f > 0.75f) m |= (base & 0x77777777u);
                if (f > 0.95f) m |= base;
                masks[r][lvl][w] = m;
            }
        }
    }

    upload_rule_bank(rules, RULE_BANK_SIZE);
    upload_payload_level_masks(masks);

    // -----------------------------
    // Create pipeline context
    // -----------------------------
    BitDropContext* ctx = bitdrop_create_context(NUM_BLOCKS, PASSES);

    // -----------------------------
    // Benchmark
    // -----------------------------
    cudaEvent_t start, stop;
    check(cudaEventCreate(&start), "event create");
    check(cudaEventCreate(&stop),  "event create");

    check(cudaEventRecord(start), "event record");

    bitdrop_run_multi_pass(
        ctx,
        NUM_BLOCKS,
        h_headers,
        h_t1,
        h_t2,
        h_t3,
        h_graph,
        h_payload,
        h_out_headers,
        h_out_t1,
        h_out_t2,
        h_out_t3,
        h_out_graph,
        h_out_payload,
        h_metrics
    );

    check(cudaEventRecord(stop), "event record");
    check(cudaEventSynchronize(stop), "event sync");

    float ms = 0;
    check(cudaEventElapsedTime(&ms, start, stop), "event elapsed");

    double total_bytes =
        double(NUM_BLOCKS) *
        double(sizeof(uint32_t) * (1 + T1_WORDS + T2_WORDS + T3_WORDS + G_WORDS + P_WORDS));

    double gb = total_bytes / (1024.0 * 1024.0 * 1024.0);
    double gbps = gb / (ms / 1000.0);

    printf("Time: %.3f ms\n", ms);
    printf("Throughput: %.2f GB/s\n", gbps);

    bitdrop_destroy_context(ctx);

    return 0;
}
