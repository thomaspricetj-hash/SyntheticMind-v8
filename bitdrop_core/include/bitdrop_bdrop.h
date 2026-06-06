#pragma once
#include <cstdint>
#include <cstddef>

#include "bitdrop_kernel_soa.h"  // RuleSet, constants

// ============================================================
//  .bdrop file header (canonical definition)
// ============================================================

struct BDropHeader {
    uint8_t  magic[8];            // "BDROP!\r\n"
    uint16_t version;             // file format version
    uint16_t flags;               // optional flags
    uint32_t rulebank_id;         // hash or ID of rule bank
    uint16_t num_passes;          // number of collapse passes
    uint32_t block_count;         // number of blocks
    uint64_t block_table_offset;  // offset to block table (if used)
    uint64_t payload_offset;      // reserved for future payload region
    uint8_t  reserved[32];        // padding / future use
};

// ============================================================
//  High-level result struct
// ============================================================

struct BitDropResult {
    bool        ok;               // success/failure
    const char* error;            // error message or nullptr
    double      elapsed_ms;       // GPU time
    double      throughput_gbps;  // effective throughput
};

// ============================================================
//  High-level compression API
// ============================================================

BitDropResult bitdrop_compress_to_file(
    const char* path,
    const RuleSet* rules,
    const uint32_t masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS],
    int num_passes,
    int num_blocks,
    const uint32_t* h_headers,
    const uint32_t* h_t1,
    const uint32_t* h_t2,
    const uint32_t* h_t3,
    const uint32_t* h_graph,
    const uint32_t* h_payload
);

// ============================================================
//  High-level decompression API
// ============================================================

BitDropResult bitdrop_decompress_from_file(
    const char* path,
    BDropHeader& hdr_out,
    uint32_t*& h_headers,
    uint32_t*& h_t1,
    uint32_t*& h_t2,
    uint32_t*& h_t3,
    uint32_t*& h_graph,
    uint32_t*& h_payload
);



