// src/bitdrop_cache_manager.cu
#include "bitdrop_cache_manager.h"
#include <cuda_runtime.h>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <memory>

// Opaque mutex implementation to avoid exposing <mutex> in header
struct BitDropCacheManager::ImplMutex {
    std::mutex m;
};

// ---------------------------------------------------------------------------
// Safe CUDA free helpers: ignore shutdown, log real errors
// ---------------------------------------------------------------------------
static inline void safe_cuda_free(void* p, const char* label) {
    if (!p) return;
    cudaError_t e = cudaFree(p);
    if (e == cudaErrorCudartUnloading) {
        // Context/driver is shutting down; ignore and clear sticky error.
        (void)cudaGetLastError();
        return;
    }
    if (e != cudaSuccess) {
        std::fprintf(stderr, "[BitDropCache] cudaFree %s failed: %s\n",
                     label, cudaGetErrorString(e));
    }
}

static inline void safe_cuda_free_host(void* p, const char* label) {
    if (!p) return;
    cudaError_t e = cudaFreeHost(p);
    if (e == cudaErrorCudartUnloading) {
        (void)cudaGetLastError();
        return;
    }
    if (e != cudaSuccess) {
        std::fprintf(stderr, "[BitDropCache] cudaFreeHost %s failed: %s\n",
                     label, cudaGetErrorString(e));
    }
}

BitDropCacheManager& BitDropCacheManager::instance() {
    static BitDropCacheManager inst;
    return inst;
}

BitDropCacheManager::BitDropCacheManager()
    : h_rule_bank_pinned_(nullptr)
    , h_payload_masks_pinned_(nullptr)
    , d_rule_bank_hot_(nullptr)
    , d_payload_masks_hot_(nullptr)
    , initialized_(false)
    , impl_mutex_(new ImplMutex())
{
}

BitDropCacheManager::~BitDropCacheManager() {
    if (h_rule_bank_pinned_) {
        safe_cuda_free_host(h_rule_bank_pinned_, "rules");
        h_rule_bank_pinned_ = nullptr;
    }
    if (h_payload_masks_pinned_) {
        safe_cuda_free_host(h_payload_masks_pinned_, "masks");
        h_payload_masks_pinned_ = nullptr;
    }
    if (d_rule_bank_hot_) {
        safe_cuda_free(d_rule_bank_hot_, "rules");
        d_rule_bank_hot_ = nullptr;
    }
    if (d_payload_masks_hot_) {
        safe_cuda_free(d_payload_masks_hot_, "masks");
        d_payload_masks_hot_ = nullptr;
    }
    delete impl_mutex_;
    impl_mutex_ = nullptr;
}

bool BitDropCacheManager::init_from_host(
    const RuleSet* host_rules,
    int rule_count,
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
) {
    // Guard initialization to be thread-safe
    std::lock_guard<std::mutex> lk(impl_mutex_->m);

    if (!host_rules || rule_count <= 0 || !host_masks) {
        std::fprintf(stderr, "[BitDropCache] init_from_host: invalid inputs\n");
        return false;
    }

    if (rule_count > RULE_BANK_SIZE) {
        rule_count = RULE_BANK_SIZE;
    }

    const size_t rules_bytes = sizeof(RuleSet) * static_cast<size_t>(RULE_BANK_SIZE);
    const size_t masks_bytes = sizeof(uint32_t) * static_cast<size_t>(RULE_BANK_SIZE) * LEVEL_TABLE_SIZE * P_WORDS;

    // Allocate pinned host buffers once
    if (!h_rule_bank_pinned_) {
        cudaError_t e = cudaHostAlloc((void**)&h_rule_bank_pinned_, rules_bytes, cudaHostAllocDefault);
        if (e != cudaSuccess) {
            std::fprintf(stderr, "[BitDropCache] cudaHostAlloc rules failed: %s\n", cudaGetErrorString(e));
            return false;
        }
    }

    if (!h_payload_masks_pinned_) {
        cudaError_t e = cudaHostAlloc((void**)&h_payload_masks_pinned_, masks_bytes, cudaHostAllocDefault);
        if (e != cudaSuccess) {
            std::fprintf(stderr, "[BitDropCache] cudaHostAlloc masks failed: %s\n", cudaGetErrorString(e));
            return false;
        }
    }

    // Copy host → pinned host
    std::memcpy(h_rule_bank_pinned_, host_rules, rules_bytes);
    std::memcpy(h_payload_masks_pinned_, host_masks, masks_bytes);

    // Allocate hot device buffers once
    if (!d_rule_bank_hot_) {
        cudaError_t e = cudaMalloc((void**)&d_rule_bank_hot_, rules_bytes);
        if (e != cudaSuccess) {
            std::fprintf(stderr, "[BitDropCache] cudaMalloc rules failed: %s\n", cudaGetErrorString(e));
            return false;
        }
    }

    if (!d_payload_masks_hot_) {
        cudaError_t e = cudaMalloc((void**)&d_payload_masks_hot_, masks_bytes);
        if (e != cudaSuccess) {
            std::fprintf(stderr, "[BitDropCache] cudaMalloc masks failed: %s\n", cudaGetErrorString(e));
            return false;
        }
    }

    // Pinned host → device hot buffers
    cudaError_t e1 = cudaMemcpy(d_rule_bank_hot_, h_rule_bank_pinned_, rules_bytes, cudaMemcpyHostToDevice);
    if (e1 != cudaSuccess) {
        std::fprintf(stderr, "[BitDropCache] cudaMemcpy rules failed: %s\n", cudaGetErrorString(e1));
        return false;
    }

    cudaError_t e2 = cudaMemcpy(d_payload_masks_hot_, h_payload_masks_pinned_, masks_bytes, cudaMemcpyHostToDevice);
    if (e2 != cudaSuccess) {
        std::fprintf(stderr, "[BitDropCache] cudaMemcpy masks failed: %s\n", cudaGetErrorString(e2));
        return false;
    }

    // Pointer-only mode: no device symbols, no cudaMemcpyToSymbol.
    initialized_ = true;
    return true;
}

RuleSet* BitDropCacheManager::device_rule_bank_ptr() const {
    return d_rule_bank_hot_;
}

uint32_t* BitDropCacheManager::device_payload_masks_ptr() const {
    return d_payload_masks_hot_;
}

// ---------------------------------------------------------------------------
// Debug helper — uses public getters only
// ---------------------------------------------------------------------------
extern "C" void bitdrop_cache_debug() {
    RuleSet* rules_dev   = BitDropCacheManager::instance().device_rule_bank_ptr();
    uint32_t* masks_dev  = BitDropCacheManager::instance().device_payload_masks_ptr();

    std::fprintf(stderr, "[BitDropCache] debug: device_rule_bank_ptr=%p\n",
        (void*)rules_dev);
    std::fprintf(stderr, "[BitDropCache] debug: device_payload_masks_ptr=%p\n",
        (void*)masks_dev);
}

// ---------------------------------------------------------------------------
// Unified verification helper — pointer-only
// ---------------------------------------------------------------------------
extern "C" bool bitdrop_cache_verify_all() {
    bool ok = true;

    RuleSet* rules_dev   = BitDropCacheManager::instance().device_rule_bank_ptr();
    uint32_t* masks_dev  = BitDropCacheManager::instance().device_payload_masks_ptr();

    if (!rules_dev || !masks_dev) {
        std::fprintf(stderr,
            "[BitDropCache] verify_all: device hot buffers missing\n");
        ok = false;
    }

    return ok;
}

// C-linkage wrappers
extern "C" {

int bitdrop_cache_init_from_host(
    const RuleSet* host_rules,
    int rule_count,
    const uint32_t host_masks[RULE_BANK_SIZE][LEVEL_TABLE_SIZE][P_WORDS]
) {
    return BitDropCacheManager::instance().init_from_host(host_rules, rule_count, host_masks) ? 0 : 1;
}

RuleSet* bitdrop_cache_get_rule_bank_devptr() {
    return BitDropCacheManager::instance().device_rule_bank_ptr();
}

uint32_t* bitdrop_cache_get_payload_masks_devptr() {
    return BitDropCacheManager::instance().device_payload_masks_ptr();
}

} // extern "C"







