#pragma once

#include <cstdint>

#ifdef _WIN32
    #ifdef BITDROP_EXPORTS
        // Building the DLL
        #define BITDROP_KERNEL_API __declspec(dllexport)
    #else
        // Using the DLL
        #define BITDROP_KERNEL_API __declspec(dllimport)
    #endif
#else
    #define BITDROP_KERNEL_API
#endif

static constexpr int T1_WORDS = 2;
static constexpr int T2_WORDS = 4;
static constexpr int T3_WORDS = 4;
static constexpr int G_WORDS  = 4;
static constexpr int P_WORDS  = 16;

static constexpr int RULE_BANK_SIZE   = 16;
static constexpr int LEVEL_TABLE_SIZE = 16;

struct RuleSet {
    uint32_t t1_protect_mask[T1_WORDS];
    uint32_t t2_protect_mask[T2_WORDS];
    uint32_t t3_drop_mask[T3_WORDS];
    uint32_t payload_base_mask[P_WORDS];
    uint8_t  max_compression_level;
    uint8_t  fragility_cap;
    uint8_t  reserved[2];
};

struct Metrics {
    float X_compression;
    float Y_fidelity;
    float Z_cost;
};

#ifdef __cplusplus
extern "C" {
#endif

// NOTE:
// The legacy host API functions upload_rule_bank and
// upload_payload_level_masks are now declared and exported
// only in bitdrop_host_api.h and implemented in the DLL.
// They are intentionally NOT declared here anymore.

#ifdef __CUDACC__
// Compression kernel — must match definition in bitdrop_kernel_soa.cu.
extern "C" __global__ void bitdrop_kernel_soa(
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
    RuleSet*        rule_bank_ptr,
    uint32_t*       payload_masks_ptr,
    int             num_blocks,
    Metrics*        out_metrics
);

// Decompression kernel — mirror signature, defined in bitdrop_decompress_kernel_soa.cu.
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
#endif

#ifdef __cplusplus
}
#endif












