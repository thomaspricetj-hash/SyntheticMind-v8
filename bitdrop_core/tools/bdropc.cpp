// tools/bdropc.cpp
// BitDrop v2 compressor CLI using C API (no BitDropHostAPI class)

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>

#include <cuda_runtime.h>

#include "bitdrop_kernel_soa.h"   // P_WORDS, T1_WORDS, T2_WORDS, T3_WORDS, G_WORDS, RULE_BANK_SIZE, LEVEL_TABLE_SIZE, RuleSet, Metrics
#include "bitdrop_host_api.h"     // C API: set_device_tables_from_host, getters, launch_bitdrop_soa

// ------------------------------------------------------------
// CUDA safety macro
// ------------------------------------------------------------
#define CUDA_CHECK(expr) \
    do { \
        cudaError_t _err = (expr); \
        if (_err != cudaSuccess) { \
            std::fprintf(stderr, "[bdropc] CUDA error %s:%d: %s\n", \
                         __FILE__, __LINE__, cudaGetErrorString(_err)); \
            std::exit(1); \
        } \
    } while (0)

static void print_usage(const char* prog) {
    std::fprintf(stderr,
        "BitDrop v2 Compressor\n"
        "\n"
        "Usage:\n"
        "  %s <input.bin> <output.bdrop>\n"
        "\n"
        "Notes:\n"
        "  - Input is interpreted as blocks of %d 32-bit words (64 bytes per block).\n"
        "  - File size must be a multiple of %zu bytes.\n"
        "\n",
        prog,
        P_WORDS,
        static_cast<size_t>(P_WORDS * sizeof(uint32_t)));
}

int main(int argc, char** argv) {
    if (argc < 3) {
        print_usage(argv[0]);
        return 1;
    }

    const char* in_path  = argv[1];
    const char* out_path = argv[2];

    // ------------------------------------------------------------
    // Load input file
    // ------------------------------------------------------------
    FILE* f = std::fopen(in_path, "rb");
    if (!f) {
        std::fprintf(stderr, "[bdropc] Failed to open input: %s\n", in_path);
        return 1;
    }

    std::fseek(f, 0, SEEK_END);
    long fsize = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);

    if (fsize <= 0 || (fsize % (P_WORDS * sizeof(uint32_t))) != 0) {
        std::fprintf(stderr,
                     "[bdropc] Invalid input size. Must be a multiple of %zu bytes.\n",
                     static_cast<size_t>(P_WORDS * sizeof(uint32_t)));
        std::fclose(f);
        return 1;
    }

    size_t num_blocks = static_cast<size_t>(fsize) / (P_WORDS * sizeof(uint32_t));
    std::fprintf(stderr, "[bdropc] Input blocks: %zu (P_WORDS = %d)\n", num_blocks, P_WORDS);

    uint32_t* h_payload_in = static_cast<uint32_t*>(std::malloc(fsize));
    if (!h_payload_in) {
        std::fprintf(stderr, "[bdropc] Host allocation failed.\n");
        std::fclose(f);
        return 1;
    }

    size_t read_bytes = std::fread(h_payload_in, 1, fsize, f);
    std::fclose(f);

    if (read_bytes != static_cast<size_t>(fsize)) {
        std::fprintf(stderr, "[bdropc] Short read: expected %ld, got %zu\n", fsize, read_bytes);
        std::free(h_payload_in);
        return 1;
    }

    // ------------------------------------------------------------
    // Compute per-stream sizes based on kernel layout
    // ------------------------------------------------------------
    const size_t headers_bytes = num_blocks * sizeof(uint32_t); // one header word per block
    const size_t t1_bytes      = num_blocks * T1_WORDS * sizeof(uint32_t);
    const size_t t2_bytes      = num_blocks * T2_WORDS * sizeof(uint32_t);
    const size_t t3_bytes      = num_blocks * T3_WORDS * sizeof(uint32_t);
    const size_t graph_bytes   = num_blocks * G_WORDS  * sizeof(uint32_t);
    const size_t payload_bytes = num_blocks * P_WORDS  * sizeof(uint32_t);

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

    // Initialize inputs: zero everything except payload
    CUDA_CHECK(cudaMemset(d_in_headers, 0, headers_bytes));
    CUDA_CHECK(cudaMemset(d_in_t1,      0, t1_bytes));
    CUDA_CHECK(cudaMemset(d_in_t2,      0, t2_bytes));
    CUDA_CHECK(cudaMemset(d_in_t3,      0, t3_bytes));
    CUDA_CHECK(cudaMemset(d_in_graph,   0, graph_bytes));

    CUDA_CHECK(cudaMemcpy(d_in_payload,
                          h_payload_in,
                          payload_bytes,
                          cudaMemcpyHostToDevice));

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
        std::fprintf(stderr, "[bdropc] Failed to allocate host rule tables.\n");
        std::free(h_payload_in);
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
        return 1;
    }

    // For now, host_rules/host_masks are zero-initialized.
    set_device_tables_from_host(
        host_rules,
        RULE_BANK_SIZE,
        reinterpret_cast<const uint32_t (*)[LEVEL_TABLE_SIZE][P_WORDS]>(
            host_masks));

    RuleSet*  d_rules  = get_uploaded_rule_bank_devptr();
    uint32_t* d_masks  = get_uploaded_payload_masks_devptr();

    if (!d_rules || !d_masks) {
        std::fprintf(stderr, "[bdropc] Device rule pointers are null.\n");
        std::free(h_payload_in);
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
        return 1;
    }

    // ------------------------------------------------------------
    // Allocate metrics for ALL blocks
    // ------------------------------------------------------------
    Metrics* d_metrics = nullptr;
    CUDA_CHECK(cudaMalloc(&d_metrics, num_blocks * sizeof(Metrics)));
    CUDA_CHECK(cudaMemset(d_metrics, 0, num_blocks * sizeof(Metrics)));

    std::fprintf(stderr, "[bdropc] Launching BitDrop SoA compressor...\n");

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
    // Copy compressed payload back
    // ------------------------------------------------------------
    uint32_t* h_payload_out = static_cast<uint32_t*>(std::malloc(payload_bytes));
    if (!h_payload_out) {
        std::fprintf(stderr, "[bdropc] Host allocation for output failed.\n");
        std::free(h_payload_in);
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
        return 1;
    }

    CUDA_CHECK(cudaMemcpy(h_payload_out,
                          d_out_payload,
                          payload_bytes,
                          cudaMemcpyDeviceToHost));

    // ------------------------------------------------------------
    // Write output file
    // ------------------------------------------------------------
    FILE* g = std::fopen(out_path, "wb");
    if (!g) {
        std::fprintf(stderr, "[bdropc] Failed to open output: %s\n", out_path);
        std::free(h_payload_in);
        std::free(h_payload_out);
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
        return 1;
    }

    size_t written = std::fwrite(h_payload_out, 1, payload_bytes, g);
    std::fclose(g);

    if (written != payload_bytes) {
        std::fprintf(stderr,
                     "[bdropc] Short write: expected %zu, wrote %zu\n",
                     payload_bytes, written);
        std::free(h_payload_in);
        std::free(h_payload_out);
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
        return 1;
    }

    std::fprintf(stderr,
                 "[bdropc] Compression completed: %s -> %s (blocks=%zu)\n",
                 in_path, out_path, num_blocks);

    // ------------------------------------------------------------
    // Cleanup
    // ------------------------------------------------------------
    std::free(h_payload_in);
    std::free(h_payload_out);
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













