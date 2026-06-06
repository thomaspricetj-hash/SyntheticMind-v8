#pragma once

#include "bitdrop_kernel_soa.h"
#include <cstdint>
#include <cstring>

// Small example rule bank and payload masks.
// Edit these values to tune behavior or replace with a loader that reads a file.

static inline void populate_default_rules(RuleSet* out_rules, int count) {
    if (!out_rules || count <= 0) return;
    int n = (count > RULE_BANK_SIZE) ? RULE_BANK_SIZE : count;
    for (int i = 0; i < n; ++i) {
        // Zero everything first
        std::memset(&out_rules[i], 0, sizeof(RuleSet));
        // Example: protect first word of tier1 for rule 0..n-1
        out_rules[i].t1_protect_mask[0] = 0xFFFFFFFFu;
        // Example: set a simple payload base mask pattern
        for (int w = 0; w < P_WORDS; ++w) {
            out_rules[i].payload_base_mask[w] = (uint32_t)((w + 1) * (i + 1));
        }
        out_rules[i].max_compression_level = 4;
        out_rules[i].fragility_cap = 2;
    }
}

static inline void populate_default_masks(uint32_t out_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]) {
    if (!out_masks) return;
    for (int r = 0; r < RULE_BANK_SIZE; ++r) {
        for (int l = 0; l < LEVEL_TABLE_SIZE; ++l) {
            for (int w = 0; w < P_WORDS; ++w) {
                // Example pattern: rule index xor level index shifted into mask
                out_masks[r][l][w] = (uint32_t)((r << 8) ^ (l << 4) ^ w);
            }
        }
    }
}
