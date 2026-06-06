#pragma once
#include <cstdint>

//
// ============================================================
// BitDrop v2 - Rule + RuleSet + Metrics Header
// ============================================================
//
// This header defines the rule layout, rule bank layout, payload
// mask tables, and the host‑side upload/launch API used by
// bitdrop_bdrop.cpp and the CUDA kernels.
//
// It is C‑compatible so it can be included from both C++ and
// CUDA translation units.
//

// ------------------------------------------------------------
// Rule + Payload Constants
// ------------------------------------------------------------
static constexpr int T1_WORDS = 2;     // Tier‑1 protect mask (64 bits)
static constexpr int T2_WORDS = 4;     // Tier‑2 protect mask (128 bits)
static constexpr int T3_WORDS = 4;     // Tier‑3 drop mask    (128 bits)
static constexpr int G_WORDS  = 4;     // Graph link mask     (128 bits)
static constexpr int P_WORDS  = 16;    // Payload base mask   (512 bits)

static constexpr int RULE_BANK_SIZE   = 16;   // Max rules in bank
static constexpr int LEVEL_TABLE_SIZE = 16;   // Max compression levels

// Signature base used in kernels (bitdrop_expand_kernel_soa.cu)
static constexpr uint32_t BITDROP_SIGNATURE_BASE = 0xFF000000;

// ------------------------------------------------------------
// CollapseRule — per‑rule structure used directly by kernels
// ------------------------------------------------------------
struct CollapseRule
{
    // Header-level pattern/signature/tag used by kernels
    uint32_t pattern;                 // 32-bit pattern to match
    uint32_t signature;               // 32-bit signature to write
    uint8_t  tag;                     // small tag index
    uint8_t  pad_rule_[3];            // padding for alignment

    // Masks (same logical layout as RuleSet)
    uint32_t t1_protect_mask[T1_WORDS];   // 64‑bit protect mask
    uint32_t t2_protect_mask[T2_WORDS];   // 128‑bit protect mask
    uint32_t t3_drop_mask[T3_WORDS];      // 128‑bit drop mask
    uint32_t payload_base_mask[P_WORDS];  // 512‑bit payload mask

    uint8_t  max_compression_level;       // 0–15
    uint8_t  fragility_cap;               // 0–255
    uint8_t  reserved[2];                 // alignment padding
};

// ------------------------------------------------------------
// RuleSet — alias / bank entry (kept for host API compatibility)
// ------------------------------------------------------------
struct RuleSet
{
    uint32_t t1_protect_mask[T1_WORDS];   // 64‑bit protect mask
    uint32_t t2_protect_mask[T2_WORDS];   // 128‑bit protect mask
    uint32_t t3_drop_mask[T3_WORDS];      // 128‑bit drop mask
    uint32_t payload_base_mask[P_WORDS];  // 512‑bit payload mask

    uint8_t  max_compression_level;       // 0–15
    uint8_t  fragility_cap;               // 0–255
    uint8_t  reserved[2];                 // alignment padding
};

// ------------------------------------------------------------
// Metrics — returned by GPU kernel
// ------------------------------------------------------------
struct Metrics
{
    float X_compression;   // compression ratio
    float Y_fidelity;      // fidelity score
    float Z_cost;          // compute cost
};

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================
// Host‑side API (implemented in bitdrop_bdrop.cpp)
// ============================================================

// Upload rule bank to GPU global memory
void upload_rule_bank(const RuleSet* host_rules, int count);

// Upload per‑level payload masks
void upload_payload_level_masks(
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
);

// Launch the SoA kernel (existing implementation)
void launch_bitdrop_soa(
    uint32_t* d_headers,
    uint32_t* d_tier1,
    uint32_t* d_tier2,
    uint32_t* d_tier3,
    uint32_t* d_graph_links,
    uint32_t* d_payload,

    uint32_t* d_out_headers,
    uint32_t* d_out_tier1,
    uint32_t* d_out_tier2,
    uint32_t* d_out_tier3,
    uint32_t* d_out_graph_links,
    uint32_t* d_out_payload,

    RuleSet*   d_rule_bank_ptr_arg,
    uint32_t*  d_payload_level_masks_ptr_arg,

    int num_blocks,
    Metrics* d_metrics
);

#ifdef __cplusplus
}
#endif


