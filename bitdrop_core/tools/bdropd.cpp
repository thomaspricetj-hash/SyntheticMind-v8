// tools/bdropd.cpp
// BitDrop Inspector — v2 host-API aligned version

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#include "bitdrop_kernel_soa.h"
#include "bitdrop_host_api.h"

// CUDA safety macro
#define CUDA_CHECK(expr) \
    do { \
        cudaError_t _err = (expr); \
        if (_err != cudaSuccess) { \
            std::fprintf(stderr, "[bdropd] CUDA error %s:%d: %s\n", \
                         __FILE__, __LINE__, cudaGetErrorString(_err)); \
            return 1; \
        } \
    } while (0)

int main(int argc, char** argv) {
    std::fprintf(stderr, "BitDrop Inspector (v2)\n");

    if (argc < 2) {
        std::fprintf(stderr, "Usage: %s <file>\n", argv[0]);
        return 1;
    }

    const char* in_path = argv[1];

    // ------------------------------------------------------------
    // Load payload file
    // ------------------------------------------------------------
    FILE* f = std::fopen(in_path, "rb");
    if (!f) {
        std::fprintf(stderr, "[bdropd] Failed to open file: %s\n", in_path);
        return 1;
    }

    std::fseek(f, 0, SEEK_END);
    long fsize = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);

    if (fsize <= 0 || (fsize % (P_WORDS * sizeof(uint32_t))) != 0) {
        std::fprintf(stderr, "[bdropd] Invalid file size.\n");
        std::fclose(f);
        return 1;
    }

    size_t num_blocks = static_cast<size_t>(fsize) / (P_WORDS * sizeof(uint32_t));

    uint32_t* h_payload = static_cast<uint32_t*>(std::malloc(fsize));
    if (!h_payload) {
        std::fprintf(stderr, "[bdropd] Host allocation failed.\n");
        std::fclose(f);
        return 1;
    }

    std::fread(h_payload, 1, fsize, f);
    std::fclose(f);

    // ------------------------------------------------------------
    // Upload payload to device
    // ------------------------------------------------------------
    uint32_t* d_payload = nullptr;
    CUDA_CHECK(cudaMalloc(&d_payload, fsize));
    CUDA_CHECK(cudaMemcpy(d_payload, h_payload, fsize, cudaMemcpyHostToDevice));

    // ------------------------------------------------------------
    // Initialize device tables via v2 host API
    // ------------------------------------------------------------
    RuleSet* host_rules =
        static_cast<RuleSet*>(std::calloc(RULE_BANK_SIZE, sizeof(RuleSet)));

    auto* host_masks =
        static_cast<uint32_t*>(std::calloc(
            RULE_BANK_SIZE * LEVEL_TABLE_SIZE * P_WORDS,
            sizeof(uint32_t)));

    if (!host_rules || !host_masks) {
        std::fprintf(stderr, "[bdropd] Failed to allocate host rule tables.\n");
        CUDA_CHECK(cudaFree(d_payload));
        std::free(h_payload);
        std::free(host_rules);
        std::free(host_masks);
        return 1;
    }

    set_device_tables_from_host(
        host_rules,
        RULE_BANK_SIZE,
        reinterpret_cast<const uint32_t (*)[LEVEL_TABLE_SIZE][P_WORDS]>(
            host_masks));

    std::fprintf(stderr,
                 "[bdropd] Device tables initialized via v2 cache manager.\n");

    RuleSet* d_rules = get_uploaded_rule_bank_devptr();
    uint32_t* d_masks = get_uploaded_payload_masks_devptr();

    std::fprintf(stderr, "[bdropd] d_rules = %p\n", static_cast<void*>(d_rules));
    std::fprintf(stderr, "[bdropd] d_masks = %p\n", static_cast<void*>(d_masks));
    std::fprintf(stderr, "Blocks: %zu\n", num_blocks);
    std::fprintf(stderr, "Payload words per block: %d\n", P_WORDS);

    // ------------------------------------------------------------
    // Cleanup
    // ------------------------------------------------------------
    CUDA_CHECK(cudaFree(d_payload));
    std::free(h_payload);
    std::free(host_rules);
    std::free(host_masks);

    return 0;
}












