#pragma once
#include <cstdint>
#include <vector>

// ================================================================
// BitDrop v2 — Rule Definitions (Learned + Fallback)
// ================================================================
//
// This header defines the reversible collapse rule format used by
// both the CPU reference engine and the GPU collapse/expand kernels.
//
// A rule is a 4-byte pattern that can be collapsed into a 4-byte
// signature, with a 1-byte tag identifying which rule fired.
//
// The rule bank contains:
//   - learned rules (from input analysis)
//   - fallback rules (static, always valid)
//   - metadata for GPU upload
//
// ================================================================

// -------------------------------
// Rule counts
// -------------------------------
static constexpr int BITDROP_LEARNED_RULES = 64;   // learned per-file
static constexpr int BITDROP_FALLBACK_RULES = 16;  // static fallback
static constexpr int BITDROP_MAX_RULES =
    BITDROP_LEARNED_RULES + BITDROP_FALLBACK_RULES;

// -------------------------------
// Collapse Rule Format
// -------------------------------
//
// pattern    = 4-byte sequence to collapse
// signature  = 4-byte reversible replacement
// tag        = 1-byte rule ID (0..N-1)
//
// All rules are reversible:
//   signature -> pattern
//
// -------------------------------
struct CollapseRule {
    uint32_t pattern;     // original 4-byte sequence
    uint32_t signature;   // reversible replacement
    uint8_t  tag;         // rule ID
};

// -------------------------------
// Rule Bank
// -------------------------------
//
// Contains:
//   - learned rules
//   - fallback rules
//   - total count
//
// This is what gets uploaded to GPU and stored in the file header.
// -------------------------------
struct RuleBank {
    CollapseRule rules[BITDROP_MAX_RULES];
    int learned_count = 0;
    int fallback_count = 0;

    inline int total() const {
        return learned_count + fallback_count;
    }
};

// -------------------------------
// Signature Space
// -------------------------------
//
// We reserve a signature range that is guaranteed NOT to collide
// with real data. This ensures reversibility.
//
// Example strategy:
//   - signatures start at 0xFF000000
//   - increment for each rule
//
// -------------------------------
static constexpr uint32_t BITDROP_SIGNATURE_BASE = 0xFF000000;

// -------------------------------
// API Prototypes (implemented in .cpp files)
// -------------------------------

// CPU rule learner
void bitdrop_learn_rules(const uint8_t* data, size_t size, RuleBank& out_bank);

// CPU collapse / expand reference implementations
void bitdrop_collapse_cpu(const uint8_t* input, size_t size,
                          const RuleBank& bank,
                          std::vector<uint8_t>& out_payload,
                          std::vector<uint8_t>& out_tags);

void bitdrop_expand_cpu(const uint8_t* collapsed, size_t collapsed_size,
                        const uint8_t* tags, size_t tag_count,
                        const RuleBank& bank,
                        std::vector<uint8_t>& out_original);

