cmake_minimum_required(VERSION 3.22)

project(bitdrop_tools LANGUAGES C CXX CUDA)

# CUDA runtime for tools
find_package(CUDAToolkit REQUIRED)

# Put tool binaries under build/tools/<Config>
set(TOOLS_RUNTIME_OUTPUT_DIR "${CMAKE_BINARY_DIR}/tools/$<CONFIG>")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${TOOLS_RUNTIME_OUTPUT_DIR})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${TOOLS_RUNTIME_OUTPUT_DIR})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# ------------------------------------------------------------
# bdropc
# ------------------------------------------------------------
add_executable(bdropc
    ${CMAKE_CURRENT_SOURCE_DIR}/bdropc.cpp
)

target_link_libraries(bdropc
    PRIVATE
        bitdrop_lib
        CUDA::cudart
)

target_include_directories(bdropc PRIVATE
    ${PROJECT_SOURCE_DIR}/include
    ${PROJECT_SOURCE_DIR}/src
)

target_compile_features(bdropc PRIVATE cxx_std_17)

set_target_properties(bdropc PROPERTIES
    CXX_STANDARD 17
)

target_compile_options(bdropc PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:/W3>
)

target_compile_definitions(bdropc PRIVATE _CRT_SECURE_NO_WARNINGS)

# ------------------------------------------------------------
# bdropd
# ------------------------------------------------------------
add_executable(bdropd
    ${CMAKE_CURRENT_SOURCE_DIR}/bdropd.cpp
)

target_link_libraries(bdropd
    PRIVATE
        bitdrop_lib
        CUDA::cudart
)

target_include_directories(bdropd PRIVATE
    ${PROJECT_SOURCE_DIR}/include
    ${PROJECT_SOURCE_DIR}/src
)

target_compile_features(bdropd PRIVATE cxx_std_17)

set_target_properties(bdropd PROPERTIES
    CXX_STANDARD 17
)

target_compile_options(bdropd PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:/W3>
)

target_compile_definitions(bdropd PRIVATE _CRT_SECURE_NO_WARNINGS)

# ------------------------------------------------------------
# bdrop_diag  (DIAGNOSTIC EXECUTABLE — MUST BE CUDA)
# ------------------------------------------------------------
add_executable(bdrop_diag
    ${CMAKE_CURRENT_SOURCE_DIR}/bdrop_diag.cu
)

set_source_files_properties(
    ${CMAKE_CURRENT_SOURCE_DIR}/bdrop_diag.cu
    PROPERTIES LANGUAGE CUDA
)

target_link_libraries(bdrop_diag
    PRIVATE
        bitdrop_lib
        CUDA::cudart
)

target_include_directories(bdrop_diag
    PRIVATE
        ${PROJECT_SOURCE_DIR}/include
        ${PROJECT_SOURCE_DIR}/src
)

target_compile_features(bdrop_diag PRIVATE cxx_std_17)

set_target_properties(bdrop_diag PROPERTIES
    CXX_STANDARD 17
)

target_compile_options(bdrop_diag PRIVATE
    $<$<COMPILE_LANGUAGE:CUDA>:-Xcompiler="/W3">
)

target_compile_definitions(bdrop_diag PRIVATE _CRT_SECURE_NO_WARNINGS)

# ------------------------------------------------------------
# bdrop_bench  (KERNEL-ONLY BENCHMARK)
# ------------------------------------------------------------
add_executable(bdrop_bench
    ${CMAKE_CURRENT_SOURCE_DIR}/bdrop_bench.cpp
)

target_link_libraries(bdrop_bench
    PRIVATE
        bitdrop_lib
        CUDA::cudart
)

target_include_directories(bdrop_bench PRIVATE
    ${PROJECT_SOURCE_DIR}/include
    ${PROJECT_SOURCE_DIR}/src
)

target_compile_features(bdrop_bench PRIVATE cxx_std_17)

set_target_properties(bdrop_bench PROPERTIES
    CXX_STANDARD 17
)

target_compile_options(bdrop_bench PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:/W3>
)

target_compile_definitions(bdrop_bench PRIVATE _CRT_SECURE_NO_WARNINGS)

# ------------------------------------------------------------
# Install
# ------------------------------------------------------------
install(TARGETS bdropc bdropd bdrop_diag bdrop_bench
    RUNTIME DESTINATION bin
)















