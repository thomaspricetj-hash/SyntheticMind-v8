#pragma once
#include <cstdint>
#include "bitdrop_kernel_soa.h"
#include "bitdrop_bdrop.h"   // <-- defines BitDropResult and BDropHeader

// GPU decompression context (opaque)
struct BitDropDecompressContext;

BitDropDecompressContext* bitdrop_decompress_create_context(int max_blocks);
void bitdrop_decompress_destroy_context(BitDropDecompressContext* ctx);

BitDropResult bitdrop_gpu_decompress_soa(
    BitDropDecompressContext* ctx,
    int num_blocks,
    const uint32_t* h_in_headers,
    const uint32_t* h_in_t1,
    const uint32_t* h_in_t2,
    const uint32_t* h_in_t3,
    const uint32_t* h_in_graph,
    const uint32_t* h_in_payload,
    uint32_t* h_out_headers,
    uint32_t* h_out_t1,
    uint32_t* h_out_t2,
    uint32_t* h_out_t3,
    uint32_t* h_out_graph,
    uint32_t* h_out_payload
);

BitDropResult bitdrop_gpu_decompress_from_file(
    const char* path,
    BDropHeader& hdr_out,
    uint32_t*& h_out_headers,
    uint32_t*& h_out_t1,
    uint32_t*& h_out_t2,
    uint32_t*& h_out_t3,
    uint32_t*& h_out_graph,
    uint32_t*& h_out_payload
);


