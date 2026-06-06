#pragma once
#include "bitdrop_host_api.h"

// This header forces the pipeline to use the correct C linkage
// and prevents accidental C++ redeclarations.
extern "C" {
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
}
