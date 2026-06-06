// src/bitdrop_runtime_upload.h
#pragma once

#include <cstddef>
#include <cstdint>
#include "bitdrop_device_symbols.h"   // RuleSet, RULE_BANK_SIZE, etc.

#ifdef __cplusplus
extern "C" {
#endif

// -----------------------------------------------------------------------------
// Upload host tables to device memory (fallback path)
// MUST be exported so bdropc can link
// -----------------------------------------------------------------------------
extern BITDROP_API bool upload_runtime_tables(
    const RuleSet* host_rules,
    size_t host_rules_bytes,
    const uint32_t* host_masks,
    size_t host_masks_bytes
);

// -----------------------------------------------------------------------------
// Free runtime-uploaded device tables
// MUST be exported so bdropc can link
// -----------------------------------------------------------------------------
extern BITDROP_API void free_runtime_tables();

// -----------------------------------------------------------------------------
// Setters for runtime-uploaded device pointers
// These do NOT need to be exported unless bdropc calls them
// -----------------------------------------------------------------------------
extern BITDROP_API void set_uploaded_rule_bank_devptr(RuleSet* ptr);
extern BITDROP_API void set_uploaded_payload_masks_devptr(uint32_t* ptr);

#ifdef __cplusplus
}
#endif

