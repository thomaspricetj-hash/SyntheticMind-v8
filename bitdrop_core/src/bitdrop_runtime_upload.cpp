// src/bitdrop_runtime_upload.cpp
// Runtime upload for rule bank and payload masks.
// Pointer-only version: delegates to cache manager via host API.

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "bitdrop_device_symbols.h"   // RuleSet, RULE_BANK_SIZE, LEVEL_TABLE_SIZE, P_WORDS
#include "bitdrop_host_api.h"         // BITDROP_API, set_device_tables_from_host, getters

// -----------------------------------------------------------------------------
// INTERNAL DEVICE POINTER STORAGE (for logging / legacy access only)
// -----------------------------------------------------------------------------
static RuleSet*   g_uploaded_rule_bank_devptr      = nullptr;
static uint32_t*  g_uploaded_payload_masks_devptr  = nullptr;

// -----------------------------------------------------------------------------
// EXPORTED SETTERS (kept for ABI compatibility; now just mirror cache pointers)
// -----------------------------------------------------------------------------
extern "C" BITDROP_API void set_uploaded_rule_bank_devptr(RuleSet* ptr) {
    g_uploaded_rule_bank_devptr = ptr;
}

extern "C" BITDROP_API void set_uploaded_payload_masks_devptr(uint32_t* ptr) {
    g_uploaded_payload_masks_devptr = ptr;
}

// -----------------------------------------------------------------------------
// INTERNAL GETTERS (not used by core runtime; kept for legacy callers)
// -----------------------------------------------------------------------------
RuleSet* runtime_get_rule_bank_ptr() {
    return g_uploaded_rule_bank_devptr;
}

uint32_t* runtime_get_payload_masks_ptr() {
    return g_uploaded_payload_masks_devptr;
}

// -----------------------------------------------------------------------------
// upload_runtime_tables()
// Pointer-only: initialize cache manager and mirror its pointers.
// -----------------------------------------------------------------------------
extern "C" BITDROP_API bool upload_runtime_tables(
    const RuleSet* host_rules, size_t host_rules_bytes,
    const uint32_t* host_masks, size_t host_masks_bytes
) {
    // Fallback: allocate zeroed host tables if caller passes nullptr/0
    RuleSet*   local_rules = nullptr;
    uint32_t*  local_masks = nullptr;

    // ------------------------------
    // Rules fallback
    // ------------------------------
    int rule_count = 0;
    if (!host_rules || host_rules_bytes == 0) {
        host_rules_bytes = sizeof(RuleSet) * RULE_BANK_SIZE;
        local_rules = static_cast<RuleSet*>(std::calloc(1, host_rules_bytes));
        if (!local_rules) {
            std::fprintf(stderr, "[BitDropRuntimeUpload] Failed to allocate local_rules\n");
            return false;
        }
        host_rules = local_rules;
        rule_count = RULE_BANK_SIZE;
    } else {
        rule_count = static_cast<int>(host_rules_bytes / sizeof(RuleSet));
        if (rule_count <= 0 || rule_count > RULE_BANK_SIZE) {
            std::fprintf(stderr, "[BitDropRuntimeUpload] Invalid rule_count derived from bytes\n");
            if (local_rules) std::free(local_rules);
            return false;
        }
    }

    // ------------------------------
    // Masks fallback
    // ------------------------------
    size_t expected_masks_bytes =
        sizeof(uint32_t) * RULE_BANK_SIZE * LEVEL_TABLE_SIZE * P_WORDS;

    if (!host_masks || host_masks_bytes == 0) {
        host_masks_bytes = expected_masks_bytes;
        local_masks = static_cast<uint32_t*>(std::calloc(1, host_masks_bytes));
        if (!local_masks) {
            std::fprintf(stderr, "[BitDropRuntimeUpload] Failed to allocate local_masks\n");
            if (local_rules) std::free(local_rules);
            return false;
        }
        host_masks = local_masks;
    } else if (host_masks_bytes != expected_masks_bytes) {
        std::fprintf(stderr,
            "[BitDropRuntimeUpload] WARNING: host_masks_bytes (%zu) != expected (%zu); "
            "proceeding but layout must match [RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]\n",
            host_masks_bytes, expected_masks_bytes);
    }

    // Reinterpret flat masks as SoA for cache initializer
    const uint32_t (*masks_soa)[LEVEL_TABLE_SIZE][P_WORDS] =
        reinterpret_cast<const uint32_t (*)[LEVEL_TABLE_SIZE][P_WORDS]>(host_masks);

    // Initialize cache manager via host API
    set_device_tables_from_host(host_rules, rule_count, masks_soa);

    // Mirror cache pointers into our legacy globals
    g_uploaded_rule_bank_devptr     = get_uploaded_rule_bank_devptr();
    g_uploaded_payload_masks_devptr = get_uploaded_payload_masks_devptr();

    // Cleanup local host buffers
    if (local_rules) std::free(local_rules);
    if (local_masks) std::free(local_masks);

    std::fprintf(stderr,
        "[BitDropRuntimeUpload] Uploaded rule_bank_devptr=%p payload_masks_devptr=%p\n",
        (void*)g_uploaded_rule_bank_devptr,
        (void*)g_uploaded_payload_masks_devptr
    );

    return g_uploaded_rule_bank_devptr && g_uploaded_payload_masks_devptr;
}

// -----------------------------------------------------------------------------
// free_runtime_tables()
// Pointer-only: just clear our mirrors; cache manager owns device memory.
// -----------------------------------------------------------------------------
extern "C" BITDROP_API void free_runtime_tables() {
    g_uploaded_rule_bank_devptr     = nullptr;
    g_uploaded_payload_masks_devptr = nullptr;
}





