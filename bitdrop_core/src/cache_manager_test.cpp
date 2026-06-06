#include "bitdrop_cache_manager.h"
#include <cstdio>
#include <cstring>

// Minimal smoke test
int main() {
    std::fprintf(stderr, "sizeof(RuleSet)=%zu RULE_BANK_SIZE=%d LEVEL_TABLE_SIZE=%d P_WORDS=%d\n",
                 sizeof(RuleSet), RULE_BANK_SIZE, LEVEL_TABLE_SIZE, P_WORDS);

    static RuleSet rules[RULE_BANK_SIZE];
    static uint32_t masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS];
    std::memset(rules, 0, sizeof(rules));
    std::memset(masks, 0, sizeof(masks));

    int rc = bitdrop_cache_init_from_host(rules, RULE_BANK_SIZE, masks);
    std::fprintf(stderr, "bitdrop_cache_init_from_host returned %d\n", rc);

    RuleSet* devptr = bitdrop_cache_get_rule_bank_devptr();
    uint32_t* maskptr = bitdrop_cache_get_payload_masks_devptr();
    std::fprintf(stderr, "devptr=%p maskptr=%p\n", (void*)devptr, (void*)maskptr);

    extern bool verify_device_symbols();
    bool ok = verify_device_symbols();
    std::fprintf(stderr, "verify_device_symbols => %d\n", ok ? 1 : 0);

    return rc;
}

