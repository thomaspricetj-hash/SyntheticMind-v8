#pragma once
#include <cstdint>
#include <cstddef>

#include "bitdrop_bdrop.h"   // BDropHeader, BitDropResult, constants via bitdrop_kernel_soa.h

// ============================================================
//  Writer API
// ============================================================
//
// Layout (simple, contiguous, matches reader):
//   [BDropHeader]
//   [headers   : block_count * 1        * 4 bytes]
//   [tier1     : block_count * T1_WORDS * 4 bytes]
//   [tier2     : block_count * T2_WORDS * 4 bytes]
//   [tier3     : block_count * T3_WORDS * 4 bytes]
//   [graph     : block_count * G_WORDS  * 4 bytes]
//   [payload   : block_count * P_WORDS  * 4 bytes]
//

bool bdrop_write(
    const char* path,
    const BDropHeader& hdr,
    const uint32_t* h_headers,
    const uint32_t* h_t1,
    const uint32_t* h_t2,
    const uint32_t* h_t3,
    const uint32_t* h_graph,
    const uint32_t* h_payload
);

