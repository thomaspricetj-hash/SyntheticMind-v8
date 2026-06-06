#include "bdrop_writer.h"
#include "bitdrop_kernel_soa.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

// ---------------------------------------------------------------------------
// Helper: validate header + pointers before writing
// ---------------------------------------------------------------------------
static inline bool bdrop_validate_header_and_buffers(
    const char* path,
    const BDropHeader& hdr,
    const uint32_t* h_headers,
    const uint32_t* h_t1,
    const uint32_t* h_t2,
    const uint32_t* h_t3,
    const uint32_t* h_graph,
    const uint32_t* h_payload
) {
    if (!path) {
        std::fprintf(stderr, "[bdrop_write] ERROR: path is null\n");
        return false;
    }

    if (hdr.block_count == 0) {
        std::fprintf(stderr, "[bdrop_write] ERROR: block_count == 0\n");
        return false;
    }

    if (!h_headers || !h_t1 || !h_t2 || !h_t3 || !h_graph || !h_payload) {
        std::fprintf(stderr, "[bdrop_write] ERROR: one or more SoA pointers are null\n");
        return false;
    }

    // Check for overflow in size computations
    const uint64_t N = hdr.block_count;

    uint64_t headers_bytes = N * sizeof(uint32_t);
    uint64_t t1_bytes      = N * uint64_t(T1_WORDS) * sizeof(uint32_t);
    uint64_t t2_bytes      = N * uint64_t(T2_WORDS) * sizeof(uint32_t);
    uint64_t t3_bytes      = N * uint64_t(T3_WORDS) * sizeof(uint32_t);
    uint64_t g_bytes       = N * uint64_t(G_WORDS)  * sizeof(uint32_t);
    uint64_t p_bytes       = N * uint64_t(P_WORDS)  * sizeof(uint32_t);

    uint64_t total = headers_bytes + t1_bytes + t2_bytes + t3_bytes + g_bytes + p_bytes;

    if (total == 0 || total > (1ull << 40)) { // arbitrary 1 TB sanity cap
        std::fprintf(stderr, "[bdrop_write] ERROR: computed payload size is invalid\n");
        return false;
    }

    return true;
}

// ---------------------------------------------------------------------------
// Writer
// ---------------------------------------------------------------------------
bool bdrop_write(
    const char* path,
    const BDropHeader& hdr_in,
    const uint32_t* h_headers,
    const uint32_t* h_t1,
    const uint32_t* h_t2,
    const uint32_t* h_t3,
    const uint32_t* h_graph,
    const uint32_t* h_payload
) {
    // Validate inputs
    if (!bdrop_validate_header_and_buffers(
            path, hdr_in, h_headers, h_t1, h_t2, h_t3, h_graph, h_payload))
    {
        return false;
    }

    FILE* f = nullptr;
#if defined(_MSC_VER)
    if (fopen_s(&f, path, "wb") != 0 || !f) {
        std::fprintf(stderr, "[bdrop_write] ERROR: fopen_s failed\n");
        return false;
    }
#else
    f = std::fopen(path, "wb");
    if (!f) {
        std::fprintf(stderr, "[bdrop_write] ERROR: fopen failed\n");
        return false;
    }
#endif

    BDropHeader hdr = hdr_in;

    const uint8_t magic[8] = { 'B','D','R','O','P','!','\r','\n' };
    std::memcpy(hdr.magic, magic, sizeof(magic));

    const uint32_t N = hdr.block_count;

    const std::size_t headers_bytes = std::size_t(N) * sizeof(uint32_t);
    const std::size_t t1_bytes      = std::size_t(N) * T1_WORDS * sizeof(uint32_t);
    const std::size_t t2_bytes      = std::size_t(N) * T2_WORDS * sizeof(uint32_t);
    const std::size_t t3_bytes      = std::size_t(N) * T3_WORDS * sizeof(uint32_t);
    const std::size_t g_bytes       = std::size_t(N) * G_WORDS  * sizeof(uint32_t);
    const std::size_t p_bytes       = std::size_t(N) * P_WORDS  * sizeof(uint32_t);

    hdr.block_table_offset = sizeof(BDropHeader);
    hdr.payload_offset     = hdr.block_table_offset +
                             headers_bytes + t1_bytes + t2_bytes + t3_bytes + g_bytes;

    if (std::fwrite(&hdr, sizeof(BDropHeader), 1, f) != 1) {
        std::fprintf(stderr, "[bdrop_write] ERROR: failed to write header\n");
        std::fclose(f);
        return false;
    }

    if (std::fwrite(h_headers, headers_bytes, 1, f) != 1) { std::fprintf(stderr, "[bdrop_write] ERROR: write headers\n"); std::fclose(f); return false; }
    if (std::fwrite(h_t1,      t1_bytes,      1, f) != 1) { std::fprintf(stderr, "[bdrop_write] ERROR: write t1\n");      std::fclose(f); return false; }
    if (std::fwrite(h_t2,      t2_bytes,      1, f) != 1) { std::fprintf(stderr, "[bdrop_write] ERROR: write t2\n");      std::fclose(f); return false; }
    if (std::fwrite(h_t3,      t3_bytes,      1, f) != 1) { std::fprintf(stderr, "[bdrop_write] ERROR: write t3\n");      std::fclose(f); return false; }
    if (std::fwrite(h_graph,   g_bytes,       1, f) != 1) { std::fprintf(stderr, "[bdrop_write] ERROR: write graph\n");   std::fclose(f); return false; }
    if (std::fwrite(h_payload, p_bytes,       1, f) != 1) { std::fprintf(stderr, "[bdrop_write] ERROR: write payload\n"); std::fclose(f); return false; }

    std::fclose(f);
    return true;
}



