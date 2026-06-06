// bitdrop_decompress.cpp
// High-level GPU decompression from .bdrop file

#include "bitdrop_decompress.h"
#include "bdrop_reader.h"

#include <cstdlib>
#include <cstdio>

// Forward declarations for pointer-only rule/mask tables
extern "C" RuleSet*   get_uploaded_rule_bank_devptr();
extern "C" uint32_t*  get_uploaded_payload_masks_devptr();

// Optional debug toggle
//#define BITDROP_DECOMP_DEBUG 1

// ---------------------------------------------------------------------------
// Pointer-only safety guard (future reversible decompression)
// ---------------------------------------------------------------------------
static inline void bitdrop_require_tables_decomp() {
    RuleSet*   rules = get_uploaded_rule_bank_devptr();
    uint32_t*  masks = get_uploaded_payload_masks_devptr();

#if BITDROP_DECOMP_DEBUG
    std::fprintf(stderr,
        "[BitDropDecompress] rule_bank=%p masks=%p\n",
        (void*)rules, (void*)masks);
#endif

    if (!rules || !masks) {
        std::fprintf(stderr,
            "[BitDropDecompress] ERROR: device tables missing — "
            "call set_device_tables_from_host() before decompression.\n");
        std::exit(1);
    }
}

// ---------------------------------------------------------------------------
// High-level decompression entry
// ---------------------------------------------------------------------------
BitDropResult bitdrop_gpu_decompress_from_file(
    const char* path,
    BDropHeader& hdr_out,
    uint32_t*& h_out_headers,
    uint32_t*& h_out_t1,
    uint32_t*& h_out_t2,
    uint32_t*& h_out_t3,
    uint32_t*& h_out_graph,
    uint32_t*& h_out_payload
) {
    BitDropResult r{true, nullptr, 0.0, 0.0};

    if (!path) {
        r.ok = false;
        r.error = "invalid path";
        return r;
    }

    // Ensure rule/mask tables exist before any GPU work
    bitdrop_require_tables_decomp();

    // First: read .bdrop into SoA (host)
    uint32_t* h_in_headers = nullptr;
    uint32_t* h_in_t1      = nullptr;
    uint32_t* h_in_t2      = nullptr;
    uint32_t* h_in_t3      = nullptr;
    uint32_t* h_in_graph   = nullptr;
    uint32_t* h_in_payload = nullptr;

    if (!bdrop_read(path, hdr_out,
                    h_in_headers, h_in_t1, h_in_t2, h_in_t3, h_in_graph, h_in_payload)) {
        r.ok = false;
        r.error = "bdrop_read failed";
        return r;
    }

    const int num_blocks = (int)hdr_out.block_count;
    if (num_blocks <= 0) {
        r.ok = false;
        r.error = "block_count <= 0";
        return r;
    }

    // Allocate output SoA
    h_out_headers = (uint32_t*)std::malloc(size_t(num_blocks) * sizeof(uint32_t));
    h_out_t1      = (uint32_t*)std::malloc(size_t(num_blocks) * T1_WORDS * sizeof(uint32_t));
    h_out_t2      = (uint32_t*)std::malloc(size_t(num_blocks) * T2_WORDS * sizeof(uint32_t));
    h_out_t3      = (uint32_t*)std::malloc(size_t(num_blocks) * T3_WORDS * sizeof(uint32_t));
    h_out_graph   = (uint32_t*)std::malloc(size_t(num_blocks) * G_WORDS  * sizeof(uint32_t));
    h_out_payload = (uint32_t*)std::malloc(size_t(num_blocks) * P_WORDS  * sizeof(uint32_t));

    if (!h_out_headers || !h_out_t1 || !h_out_t2 || !h_out_t3 || !h_out_graph || !h_out_payload) {
        r.ok = false;
        r.error = "out of memory";
        return r;
    }

    // Create GPU context
    BitDropDecompressContext* ctx = bitdrop_decompress_create_context(num_blocks);
    if (!ctx) {
        r.ok = false;
        r.error = "failed to create BitDropDecompressContext";
        return r;
    }

    // Run GPU inverse
    BitDropResult r2 = bitdrop_gpu_decompress_soa(
        ctx,
        num_blocks,
        h_in_headers,
        h_in_t1,
        h_in_t2,
        h_in_t3,
        h_in_graph,
        h_in_payload,
        h_out_headers,
        h_out_t1,
        h_out_t2,
        h_out_t3,
        h_out_graph,
        h_out_payload
    );

    bitdrop_decompress_destroy_context(ctx);

    // Free intermediate host buffers
    std::free(h_in_headers);
    std::free(h_in_t1);
    std::free(h_in_t2);
    std::free(h_in_t3);
    std::free(h_in_graph);
    std::free(h_in_payload);

    return r2;
}

