#pragma once

#include <cstdint>
#include <cstddef>
#include "bitdrop_kernel_soa.h"   // RuleSet, RULE_BANK_SIZE, LEVEL_TABLE_SIZE, P_WORDS

// Opaque cache manager type (implementation in .cu)
struct BitDropCacheManager {
    struct ImplMutex;

    static BitDropCacheManager& instance();

    bool init_from_host(
        const RuleSet* host_rules,
        int rule_count,
        const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
    );

    RuleSet*   device_rule_bank_ptr() const;
    uint32_t*  device_payload_masks_ptr() const;

private:
    BitDropCacheManager();
    ~BitDropCacheManager();

    BitDropCacheManager(const BitDropCacheManager&) = delete;
    BitDropCacheManager& operator=(const BitDropCacheManager&) = delete;

    RuleSet*   h_rule_bank_pinned_;
    uint32_t*  h_payload_masks_pinned_;
    RuleSet*   d_rule_bank_hot_;
    uint32_t*  d_payload_masks_hot_;
    bool       initialized_;
    ImplMutex* impl_mutex_;
};

extern "C" {

int bitdrop_cache_init_from_host(
    const RuleSet* host_rules,
    int rule_count,
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
);

RuleSet*   bitdrop_cache_get_rule_bank_devptr();
uint32_t*  bitdrop_cache_get_payload_masks_devptr();

} // extern "C"





