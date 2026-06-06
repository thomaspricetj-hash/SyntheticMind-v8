#pragma once

#include <cstdint>
#include "bitdrop_kernel_soa.h"  // RuleSet, RULE_BANK_SIZE, LEVEL_TABLE_SIZE, P_WORDS

// -----------------------------------------------------------------------------
// DLL export/import macro
// -----------------------------------------------------------------------------
#if defined(_WIN32)
    #ifdef BITDROP_EXPORTS
        #define BITDROP_API __declspec(dllexport)
    #else
        #define BITDROP_API __declspec(dllimport)
    #endif
#else
    #define BITDROP_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

// -----------------------------------------------------------------------------
// Pointer-only runtime: no device/constant symbols are declared here.
// We keep only the verifier shim for ABI compatibility.
// -----------------------------------------------------------------------------
BITDROP_API bool verify_device_symbols();

// Convenience helpers for tools / pipelines
static inline bool bitdrop_verify() {
    return verify_device_symbols();
}

static inline bool bitdrop_tables_ready() {
    return verify_device_symbols();
}

#ifdef __cplusplus
} // extern "C"
#endif








