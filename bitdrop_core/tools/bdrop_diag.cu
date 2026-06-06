// tools/bdrop_diag.cu
#include <cstdio>
#include <cstdint>
#include <cuda_runtime.h>

#include "bitdrop_kernel_soa.h"
#include "bitdrop_host_api.h"

static void print_cuda(const char* label) {
    cudaError_t e = cudaGetLastError();
    std::fprintf(stderr, "%s: %d (%s)\n", label, static_cast<int>(e), cudaGetErrorString(e));
}

int main() {
    std::fprintf(stderr, "=== BitDrop CUDA Diagnostic ===\n");

    // 1) Basic device info
    int dev = 0;
    cudaDeviceProp prop{};
    cudaError_t e = cudaGetDeviceProperties(&prop, dev);
    std::fprintf(stderr, "cudaGetDeviceProperties: %d (%s)\n",
                 static_cast<int>(e), cudaGetErrorString(e));
    if (e == cudaSuccess) {
        std::fprintf(stderr, "Device %d: %s, CC %d.%d\n",
                     dev, prop.name, prop.major, prop.minor);
    }

    // Clear any prior error
    cudaGetLastError();

    // 2) Build trivial host tables and upload via runtime path
    RuleSet rules[RULE_BANK_SIZE]{};
    static uint32_t masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]{};

    // Fill something non-zero so we can see it's used if needed
    rules[0].payload_base_mask[0] = 0xFFFFFFFFu;
    masks[0][0][0] = 0xAAAAAAAAu;

    // Use the high-level host API to initialize tables
    set_device_tables_from_host(rules, RULE_BANK_SIZE, masks);
    print_cuda("after set_device_tables_from_host");

    RuleSet* d_rules = get_uploaded_rule_bank_devptr();
    uint32_t* d_masks = get_uploaded_payload_masks_devptr();
    std::fprintf(stderr, "cache rule ptr = %p\n", static_cast<void*>(d_rules));
    std::fprintf(stderr, "cache mask ptr = %p\n", static_cast<void*>(d_masks));

    // Clear error before launch
    cudaGetLastError();

    // 3) Minimal launch using the HOST LAUNCHER
    launch_bitdrop_soa(
        nullptr, nullptr, nullptr, nullptr,
        nullptr, nullptr,
        nullptr, nullptr, nullptr, nullptr,
        nullptr, nullptr,
        d_rules,
        d_masks,
        0,          // num_blocks = 0
        nullptr     // no metrics buffer
    );

    print_cuda("after launch_bitdrop_soa");

    e = cudaDeviceSynchronize();
    std::fprintf(stderr, "cudaDeviceSynchronize: %d (%s)\n",
                 static_cast<int>(e), cudaGetErrorString(e));

    std::fprintf(stderr, "=== End BitDrop CUDA Diagnostic ===\n");
    return 0;
}






