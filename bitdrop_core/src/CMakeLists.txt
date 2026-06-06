# ============================================================
# BitDrop v2 - Core Library Build (SHARED DLL)
# ============================================================

project(bitdrop_core LANGUAGES C CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 14)
set(CMAKE_CUDA_SEPARABLE_COMPILATION OFF)

set(BITDROP_ROOT_DIR "${CMAKE_SOURCE_DIR}")

include_directories("${BITDROP_ROOT_DIR}/include")
include_directories("${BITDROP_ROOT_DIR}/src")

# ------------------------------------------------------------
# Core CUDA/C++ sources (NO headers here)
# ------------------------------------------------------------
set(BITDROP_SOURCES
    "${BITDROP_ROOT_DIR}/src/bitdrop_kernel_soa.cu"
    "${BITDROP_ROOT_DIR}/src/bitdrop_decompress_kernel_soa.cu"
    "${BITDROP_ROOT_DIR}/src/bitdrop_cache_manager.cu"
    "${BITDROP_ROOT_DIR}/src/bitdrop_host_api.cu"
    "${BITDROP_ROOT_DIR}/src/bitdrop_collapse_kernel_soa.cu"
    "${BITDROP_ROOT_DIR}/src/bitdrop_expand_kernel_soa.cu"
)

# ------------------------------------------------------------
# Build SHARED library (DLL)
# ------------------------------------------------------------
add_library(bitdrop_lib SHARED ${BITDROP_SOURCES})

# Export symbols inside this library
target_compile_definitions(bitdrop_lib PRIVATE BITDROP_EXPORTS)

# Ensure Windows exports functions correctly
if (WIN32)
    target_compile_definitions(bitdrop_lib PRIVATE _CRT_SECURE_NO_WARNINGS)
    set_target_properties(bitdrop_lib PROPERTIES
        WINDOWS_EXPORT_ALL_SYMBOLS ON
        CUDA_RESOLVE_DEVICE_SYMBOLS ON
        OUTPUT_NAME "bitdrop_lib"
    )
endif()

target_include_directories(bitdrop_lib PUBLIC
    "${BITDROP_ROOT_DIR}/include"
    "${BITDROP_ROOT_DIR}/src"
)

target_link_libraries(bitdrop_lib PUBLIC CUDA::cudart)









