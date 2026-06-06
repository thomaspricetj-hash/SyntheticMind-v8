#pragma once
#include <cstdint>
#include "bitdrop_kernel_soa.h"

// Opaque pipeline context
struct BitDropContext;

// Create a pipeline context for up to max_blocks and num_passes passes.
BitDropContext* bitdrop_create_context(int max_blocks, int num_passes);

// Destroy a pipeline context.
void bitdrop_destroy_context(BitDropContext* ctx);

// Single-pass collapse over host SoA buffers.
void bitdrop_run_single_pass(
    BitDropContext* ctx,
    int num_blocks,
    const uint32_t* h_headers,
    const uint32_t* h_tier1,
    const uint32_t* h_tier2,
    const uint32_t* h_tier3,
    const uint32_t* h_graph,
    const uint32_t* h_payload,
    uint32_t* h_out_headers,
    uint32_t* h_out_tier1,
    uint32_t* h_out_tier2,
    uint32_t* h_out_tier3,
    uint32_t* h_out_graph,
    uint32_t* h_out_payload,
    Metrics* h_metrics // can be nullptr
);

// Multi-pass collapse in-place on device, only final result returned.
void bitdrop_run_multi_pass(
    BitDropContext* ctx,
    int num_blocks,
    const uint32_t* h_headers,
    const uint32_t* h_tier1,
    const uint32_t* h_tier2,
    const uint32_t* h_tier3,
    const uint32_t* h_graph,
    const uint32_t* h_payload,
    uint32_t* h_out_headers,
    uint32_t* h_out_tier1,
    uint32_t* h_out_tier2,
    uint32_t* h_out_tier3,
    uint32_t* h_out_graph,
    uint32_t* h_out_payload,
    Metrics* h_metrics // metrics from last pass
);
