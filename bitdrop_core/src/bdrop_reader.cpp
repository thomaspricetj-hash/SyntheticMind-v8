#include "bdrop_reader.h"
#include "bitdrop_kernel_soa.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/stat.h>

// ---------------------------------------------------------------------------
// Helper: get file size
// ---------------------------------------------------------------------------
static inline long long bdrop_filesize(const char* path) {
    struct stat st;
    if (stat(path, &st) != 0) return -1;
    return (long long)st.st_size;
}

// ---------------------------------------------------------------------------
// Helper: validate header + file structure before reading payload
// ---------------------------------------------------------------------------
static inline bool bdrop_validate_header_and_file(
    const char* path,
    const BDropHeader& hdr
) {
    if (!path) {
        std::fprintf(stderr, "[bdrop_read] ERROR: path is null\n");
        return false;
    }

    long long fsize = bdrop_filesize(path);
    if (fsize < 0) {
        std::fprintf(stderr, "[bdrop_read] ERROR: cannot stat file\n");
        return false;
    }

    // Magic check
    const uint8_t expected_magic[8] = { 'B','D','R','O','P','!','\r','\n' };
    if (std::memcmp(hdr.magic, expected_magic, 8) != 0) {
        std::fprintf(stderr, "[bdrop_read] ERROR: invalid magic bytes\n");
        return false;
    }

    if (hdr.block_count == 0) {
        std::fprintf(stderr, "[bdrop_read] ERROR: block_count == 0\n");
        return false;
    }

    // Compute expected sizes
    const uint64_t N = hdr.block_count;

    uint64_t headers_bytes = N * sizeof(uint32_t);
    uint64_t t1_bytes      = N * uint64_t(T1_WORDS) * sizeof(uint32_t);
    uint64_t t2_bytes      = N * uint64_t(T2_WORDS) * sizeof(uint32_t);
    uint64_t t3_bytes      = N * uint64_t(T3_WORDS) * sizeof(uint32_t);
    uint64_t g_bytes       = N * uint64_t(G_WORDS)  * sizeof(uint32_t);
    uint64_t p_bytes       = N * uint64_t(P_WORDS)  * sizeof(uint32_t);

    uint64_t total_payload =
        headers_bytes + t1_bytes + t2_bytes + t3_bytes + g_bytes + p_bytes;

    uint64_t expected_end = sizeof(BDropHeader) + total_payload;

    if (expected_end > (uint64_t)fsize) {
        std::fprintf(stderr,
            "[bdrop_read] ERROR: file too small (%lld bytes) for expected payload (%llu bytes)\n",
            fsize, (unsigned long long)expected_end);
        return false;
    }

    return true;
}

// ---------------------------------------------------------------------------
// Reader
// ---------------------------------------------------------------------------
bool bdrop_read(
    const char* path,
    BDropHeader& hdr,
    uint32_t*& h_headers,
    uint32_t*& h_t1,
    uint32_t*& h_t2,
    uint32_t*& h_t3,
    uint32_t*& h_graph,
    uint32_t*& h_payload
) {
    h_headers = h_t1 = h_t2 = h_t3 = h_graph = h_payload = nullptr;

    if (!path) return false;

    FILE* f = nullptr;
#if defined(_MSC_VER)
    if (fopen_s(&f, path, "rb") != 0 || !f) {
        return false;
    }
#else
    f = std::fopen(path, "rb");
    if (!f) return false;
#endif

    // Read header
    if (std::fread(&hdr, sizeof(BDropHeader), 1, f) != 1) {
        std::fclose(f);
        return false;
    }

    // Validate header + file structure
    if (!bdrop_validate_header_and_file(path, hdr)) {
        std::fclose(f);
        return false;
    }

    const uint32_t N = hdr.block_count;

    const std::size_t headers_bytes = std::size_t(N) * sizeof(uint32_t);
    const std::size_t t1_bytes      = std::size_t(N) * T1_WORDS * sizeof(uint32_t);
    const std::size_t t2_bytes      = std::size_t(N) * T2_WORDS * sizeof(uint32_t);
    const std::size_t t3_bytes      = std::size_t(N) * T3_WORDS * sizeof(uint32_t);
    const std::size_t g_bytes       = std::size_t(N) * G_WORDS  * sizeof(uint32_t);
    const std::size_t p_bytes       = std::size_t(N) * P_WORDS  * sizeof(uint32_t);

    // Allocate host buffers
    h_headers = (uint32_t*)std::malloc(headers_bytes);
    h_t1      = (uint32_t*)std::malloc(t1_bytes);
    h_t2      = (uint32_t*)std::malloc(t2_bytes);
    h_t3      = (uint32_t*)std::malloc(t3_bytes);
    h_graph   = (uint32_t*)std::malloc(g_bytes);
    h_payload = (uint32_t*)std::malloc(p_bytes);

    if (!h_headers || !h_t1 || !h_t2 || !h_t3 || !h_graph || !h_payload) {
        std::fprintf(stderr, "[bdrop_read] ERROR: out of memory\n");
        std::fclose(f);
        return false;
    }

    // Read contiguous payload
    if (std::fread(h_headers, headers_bytes, 1, f) != 1) { std::fclose(f); return false; }
    if (std::fread(h_t1,      t1_bytes,      1, f) != 1) { std::fclose(f); return false; }
    if (std::fread(h_t2,      t2_bytes,      1, f) != 1) { std::fclose(f); return false; }
    if (std::fread(h_t3,      t3_bytes,      1, f) != 1) { std::fclose(f); return false; }
    if (std::fread(h_graph,   g_bytes,       1, f) != 1) { std::fclose(f); return false; }
    if (std::fread(h_payload, p_bytes,       1, f) != 1) { std::fclose(f); return false; }

    std::fclose(f);
    return true;
}

