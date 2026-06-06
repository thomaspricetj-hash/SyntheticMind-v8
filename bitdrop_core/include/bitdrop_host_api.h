#pragma once

#include <cstdint>
#include <cstddef>
#include "bitdrop_kernel_soa.h"   // RuleSet, Metrics, constants

// ------------------------------------------------------------
// Export macro (DLL‑friendly on Windows)
// ------------------------------------------------------------
#ifdef _WIN32
    #ifdef BITDROP_EXPORTS
        // When building bitdrop_lib (DLL)
        #define BITDROP_API __declspec(dllexport)
    #else
        // When consuming bitdrop_lib
        #define BITDROP_API __declspec(dllimport)
    #endif
#else
    #define BITDROP_API
#endif

// Core types are defined in bitdrop_kernel_soa.h
struct RuleSet;
struct Metrics;

// ------------------------------------------------------------
// Host API wrapper class used by bdropc and bdropd.
// Implemented in src/bitdrop_host_api.cu
// ------------------------------------------------------------
class BitDropHostAPI {
public:
    BitDropHostAPI();
    ~BitDropHostAPI();

    bool load_input(const char* path);
    bool load_output(const char* path);
    bool compress_to(const char* out_path);
    void inspect();

private:
    uint32_t* d_headers   = nullptr;
    uint32_t* d_t1        = nullptr;
    uint32_t* d_t2        = nullptr;
    uint32_t* d_t3        = nullptr;
    uint32_t* d_graph     = nullptr;
    uint32_t* d_payload   = nullptr;

    uint32_t* d_out_headers = nullptr;
    uint32_t* d_out_t1      = nullptr;
    uint32_t* d_out_t2      = nullptr;
    uint32_t* d_out_t3      = nullptr;
    uint32_t* d_out_graph   = nullptr;
    uint32_t* d_out_payload = nullptr;

    Metrics*  d_metrics     = nullptr;

    size_t num_blocks = 0;

    bool allocate_device_buffers(size_t blocks);
    void free_device_buffers();
};

//
//  C‑linkage API
//
extern "C" {

// High‑level entry: initialize all caches from host tables
BITDROP_API void set_device_tables_from_host(
    const RuleSet* host_rules,
    int rule_count,
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
);

// Legacy direct upload entry points
BITDROP_API void upload_rule_bank(
    const RuleSet* host_rules,
    int count
);

BITDROP_API void upload_payload_level_masks(
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
);

// Runtime getters
BITDROP_API RuleSet*   get_uploaded_rule_bank_devptr();
BITDROP_API uint32_t*  get_uploaded_payload_masks_devptr();

// Compression kernel launcher
BITDROP_API void launch_bitdrop_soa(
    uint32_t* in_headers,
    uint32_t* in_t1,
    uint32_t* in_t2,
    uint32_t* in_t3,
    uint32_t* in_graph,
    uint32_t* in_payload,
    uint32_t* out_headers,
    uint32_t* out_t1,
    uint32_t* out_t2,
    uint32_t* out_t3,
    uint32_t* out_graph,
    uint32_t* out_payload,
    RuleSet*  rule_bank_ptr,
    uint32_t* payload_masks_ptr,
    int       num_blocks,
    Metrics*  out_metrics
);

// Decompression kernel launcher
BITDROP_API void launch_bitdrop_decompress_soa(
    uint32_t* in_headers,
    uint32_t* in_t1,
    uint32_t* in_t2,
    uint32_t* in_t3,
    uint32_t* in_graph,
    uint32_t* in_payload,
    uint32_t* out_headers,
    uint32_t* out_t1,
    uint32_t* out_t2,
    uint32_t* out_t3,
    uint32_t* out_graph,
    uint32_t* out_payload,
    const RuleSet*  rule_bank_ptr,
    const uint32_t* payload_masks_ptr,
    int             num_blocks,
    Metrics*        out_metrics
);

// ------------------------------------------------------------
// Flat C API used by Python (ctypes)
// ------------------------------------------------------------
// (c_void_p, c_size_t, c_void_p, POINTER(c_size_t), c_int) -> c_int
BITDROP_API int bdrop_compress(
    const void* input,
    size_t      input_size,
    void*       output,
    size_t*     output_size,
    int         level
);

BITDROP_API int bdrop_decompress(
    const void* input,
    size_t      input_size,
    void*       output,
    size_t*     output_size,
    int         level
);

} // extern "C"








