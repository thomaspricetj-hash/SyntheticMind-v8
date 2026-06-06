cmake_minimum_required(VERSION 3.22)

project(bitdrop LANGUAGES C CXX CUDA)

# CUDA toolkit
find_package(CUDAToolkit REQUIRED)

# ------------------------------------------------------------
# MSVC flag sanitization
# ------------------------------------------------------------
if (MSVC)
    foreach(flag_var
        CMAKE_C_FLAGS CMAKE_C_FLAGS_DEBUG CMAKE_C_FLAGS_RELEASE
        CMAKE_C_FLAGS_RELWITHDEBINFO CMAKE_C_FLAGS_MINSIZEREL
        CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_DEBUG CMAKE_CXX_FLAGS_RELEASE
        CMAKE_CXX_FLAGS_RELWITHDEBINFO CMAKE_CXX_FLAGS_MINSIZEREL
        CMAKE_CUDA_FLAGS
    )
        if(DEFINED ${flag_var})
            string(REPLACE "/MP" "" cleaned "${${flag_var}}")
            set(${flag_var} "${cleaned}" CACHE STRING "Sanitized MSVC flags" FORCE)
        endif()
    endforeach()
endif()

# ------------------------------------------------------------
# CUDA configuration
# ------------------------------------------------------------
enable_language(CUDA)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 14)
set(CMAKE_CUDA_ARCHITECTURES native)
set(CMAKE_CUDA_SEPARABLE_COMPILATION OFF)

# ------------------------------------------------------------
# Include directories
# ------------------------------------------------------------
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/include")
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/src")

# ------------------------------------------------------------
# Subdirectories — CORRECT ORDER
# ------------------------------------------------------------
add_subdirectory(src)      # defines bitdrop_lib
add_subdirectory(tools)    # tools link against bitdrop_lib

# ------------------------------------------------------------
# Install rules
# ------------------------------------------------------------
install(DIRECTORY include/ DESTINATION include)

































