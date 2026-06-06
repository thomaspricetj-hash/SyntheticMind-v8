#pragma once
#include <cstdint>

#include "bitdrop_bdrop.h"   // BDropHeader

// ============================================================
//  Reader API
// ============================================================
//
// Reads the layout written by bdrop_write (see bdrop_writer.h).
// Allocates host buffers; caller must free() them.
//

bool bdrop_read(
    const char* path,
    BDropHeader& hdr,
    uint32_t*& h_headers,
    uint32_t*& h_t1,
    uint32_t*& h_t2,
    uint32_t*& h_t3,
    uint32_t*& h_graph,
    uint32_t*& h_payload
);


