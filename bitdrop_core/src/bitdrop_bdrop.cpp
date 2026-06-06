// bitdrop_bdrop.cpp
// High-level BitDrop compression/decompression API

#include "bitdrop_bdrop.h"
#include "bitdrop_pipeline.h"
#include "bdrop_writer.h"
#include "bdrop_reader.h"
#include "bitdrop_host_api.h"

#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// ------------------------------------------------------------
// CUDA error helper
// ------------------------------------------------------------
static inline bool check_cuda(cudaError_t err, const char* msg, BitDropResult& r) {
    if (err != cudaSuccess) {
        r.ok = false;
        r.error = cudaGetErrorString(err);
        std::fprintf(stderr, "[BitDrop] %s: %s\n", msg, r.error);
        return false;
    }
    return true;
}

// ------------------------------------------------------------
// High-level compression API
// ------------------------------------------------------------
BitDropResult bitdrop_compress_to_file(
    const char* path,
    const RuleSet* rules,
    const uint32_t masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS],
    int num_passes,
    int num_blocks,
    const uint32_t* h_headers,
    const uint32_t* h_t1,
    const uint32_t* h_t2,
    const uint32_t* h_t3,
    const uint32_t* h_graph,
    const uint32_t* h_payload
) {
    BitDropResult res{true, nullptr, 0.0, 0.0};

    if (!path || !rules || !h_headers || !h_t1 || !h_t2 || !h_t3 || !h_graph || !h_payload) {
        res.ok = false;
        res.error = "invalid arguments";
        return res;
    }
    if (num_blocks <= 0) {
        res.ok = false;
        res.error = "num_blocks <= 0";
        return res;
    }

    // Upload rule bank + masks
    upload_rule_bank(rules, RULE_BANK_SIZE);
    upload_payload_level_masks(masks);

    // Create pipeline context
    BitDropContext* ctx = bitdrop_create_context(num_blocks, num_passes);
    if (!ctx) {
        res.ok = false;
        res.error = "failed to create BitDropContext";
        return res;
    }

    // Allocate output buffers
    uint32_t* h_out_headers = (uint32_t*)std::malloc(num_blocks * sizeof(uint32_t));
    uint32_t* h_out_t1      = (uint32_t*)std::malloc(num_blocks * T1_WORDS * sizeof(uint32_t));
    uint32_t* h_out_t2      = (uint32_t*)std::malloc(num_blocks * T2_WORDS * sizeof(uint32_t));
    uint32_t* h_out_t3      = (uint32_t*)std::malloc(num_blocks * T3_WORDS * sizeof(uint32_t));
    uint32_t* h_out_graph   = (uint32_t*)std::malloc(num_blocks * G_WORDS  * sizeof(uint32_t));
    uint32_t* h_out_payload = (uint32_t*)std::malloc(num_blocks * P_WORDS  * sizeof(uint32_t));
    Metrics*  h_metrics     = (Metrics*) std::malloc(num_blocks * sizeof(Metrics));

    // Benchmark timing
    cudaEvent_t start, stop;
    check_cuda(cudaEventCreate(&start), "event create", res);
    check_cuda(cudaEventCreate(&stop),  "event create", res);
    if (!res.ok) return res;

    check_cuda(cudaEventRecord(start), "event record", res);
    if (!res.ok) return res;

    // Run multi-pass collapse
    bitdrop_run_multi_pass(
        ctx,
        num_blocks,
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

    check_cuda(cudaEventRecord(stop), "event record", res);
    check_cuda(cudaEventSynchronize(stop), "event sync", res);
    if (!res.ok) return res;

    float ms = 0.0f;
    check_cuda(cudaEventElapsedTime(&ms, start, stop), "event elapsed", res);
    if (!res.ok) return res;

    // Compute throughput
    double total_bytes =
        double(num_blocks) *
        double(sizeof(uint32_t) * (1 + T1_WORDS + T2_WORDS + T3_WORDS + G_WORDS + P_WORDS));

    double gb = total_bytes / (1024.0 * 1024.0 * 1024.0);
    res.elapsed_ms = ms;
    res.throughput_gbps = gb / (ms / 1000.0);

    // Build .bdrop header
    BDropHeader hdr{};
    static const uint8_t MAGIC[8] = { 'B','D','R','O','P','!','\r','\n' };
    std::memcpy(hdr.magic, MAGIC, sizeof(MAGIC));
    hdr.version          = 0x0001;
    hdr.flags            = 0; // optional flags
    hdr.rulebank_id      = 0; // user may hash rules here
    hdr.num_passes       = (uint16_t)num_passes;
    hdr.block_count      = (uint32_t)num_blocks;
    hdr.block_table_offset = sizeof(BDropHeader);
    hdr.payload_offset     = 0;
    std::memset(hdr.reserved, 0, sizeof(hdr.reserved));

    // Write .bdrop file
    if (!bdrop_write(path, hdr,
                     h_out_headers, h_out_t1, h_out_t2, h_out_t3, h_out_graph, h_out_payload)) {
        res.ok = false;
        res.error = "bdrop_write failed";
    }

    // Cleanup
    bitdrop_destroy_context(ctx);

    std::free(h_out_headers);
    std::free(h_out_t1);
    std::free(h_out_t2);
    std::free(h_out_t3);
    std::free(h_out_graph);
    std::free(h_out_payload);
    std::free(h_metrics);

    return res;
}

// ------------------------------------------------------------
// High-level decompression API
// ------------------------------------------------------------
BitDropResult bitdrop_decompress_from_file(
    const char* path,
    BDropHeader& hdr_out,
    uint32_t*& h_headers,
    uint32_t*& h_t1,
    uint32_t*& h_t2,
    uint32_t*& h_t3,
    uint32_t*& h_graph,
    uint32_t*& h_payload
) {
    BitDropResult res{true, nullptr, 0.0, 0.0};

    if (!path) {
        res.ok = false;
        res.error = "invalid path";
        return res;
    }

    // Read .bdrop file
    if (!bdrop_read(path, hdr_out, h_headers, h_t1, h_t2, h_t3, h_graph, h_payload)) {
        res.ok = false;
        res.error = "bdrop_read failed";
        return res;
    }

    // NOTE:
    // BitDrop collapse is currently one-way (semantic lossy).
    // When you add an inverse kernel, wire it here.

    return res;
}
