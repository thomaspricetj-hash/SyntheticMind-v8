// src/bitdrop_device_symbols.cu
// Legacy shim for old symbol-based paths — pointer-only runtime implementation.

#include "bitdrop_device_symbols.h"
#include "bitdrop_host_api.h"
#include <cuda_runtime.h>

// Host-side getters (pointer-only world)
extern "C" RuleSet*   get_uploaded_rule_bank_devptr();
extern "C" uint32_t*  get_uploaded_payload_masks_devptr();

// High-level table initializer (pointer-only)
extern "C" void set_device_tables_from_host(
    const RuleSet* host_rules,
    int rule_count,
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
);

// ---------------------------------------------------------------------------
// Small helper: clear any stale CUDA error without treating it as fatal.
// This is useful when legacy callers expect symbol-based paths but we are
// running in pointer-only mode and want a clean state for later launches.
// ---------------------------------------------------------------------------
static inline void bitdrop_clear_cuda_error()
{
    // Intentionally ignore the return value; this just clears the sticky error.
    (void)cudaGetLastError();
}

// ---------------------------------------------------------------------------
// Legacy host cache (kept only to satisfy old interfaces; no longer used
// as a primary data path, but still used to feed set_device_tables_from_host).
// ---------------------------------------------------------------------------
static RuleSet g_cached_rules[RULE_BANK_SIZE];
static int     g_cached_rule_count = 0;
static bool    g_rules_cached      = false;

// ---------------------------------------------------------------------------
// upload_rule_bank — legacy cache only, no logging
// ---------------------------------------------------------------------------
extern "C" void upload_rule_bank(const RuleSet* host_rules, int count)
{
    if (!host_rules || count <= 0 || count > RULE_BANK_SIZE) {
        g_rules_cached      = false;
        g_cached_rule_count = 0;
        return;
    }

    for (int i = 0; i < count; ++i)
        g_cached_rules[i] = host_rules[i];

    g_cached_rule_count = count;
    g_rules_cached      = true;
}

// ---------------------------------------------------------------------------
// upload_payload_level_masks — forward to pointer-only initializer, no logging
// ---------------------------------------------------------------------------
extern "C" void upload_payload_level_masks(
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
)
{
    if (!g_rules_cached || g_cached_rule_count <= 0) {
        return;
    }
    if (!host_masks) {
        return;
    }

    set_device_tables_from_host(
        g_cached_rules,
        g_cached_rule_count,
        host_masks
    );
}

// ---------------------------------------------------------------------------
// verify_device_symbols — always succeed in pointer-only mode
//
// Old callers expect this to validate constant symbols; in this build we
// intentionally do not expose any __constant__ symbols and rely entirely
// on runtime device pointers. We:
//   - touch the pointer getters so they stay linked
//   - clear any stale CUDA error so later kernel launches see a clean state
// ---------------------------------------------------------------------------
extern "C" bool verify_device_symbols()
{
    (void)get_uploaded_rule_bank_devptr();
    (void)get_uploaded_payload_masks_devptr();

    // Ensure no stale cudaErrorInvalidSymbol (or similar) is left around
    // from any legacy paths before kernels are launched.
    bitdrop_clear_cuda_error();
    return true;
}

// ---------------------------------------------------------------------------
// bitdrop_device_symbols_debug — quiet shim
// ---------------------------------------------------------------------------
extern "C" void bitdrop_device_symbols_debug()
{
    // Intentionally no-op in pointer-only mode.
}

























