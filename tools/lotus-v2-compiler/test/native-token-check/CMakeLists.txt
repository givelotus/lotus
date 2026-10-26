cmake_minimum_required(VERSION 3.18)
project(lotus_v2_compiler_native_token_fixture LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)
if(NOT DEFINED LOTUS_V2_CPP OR NOT EXISTS "${LOTUS_V2_CPP}/signing.cpp" OR NOT EXISTS "${LOTUS_V2_CPP}/vm.cpp")
  message(FATAL_ERROR "Set LOTUS_V2_CPP to the native candidate src/lotus_v2 directory with VM")
endif()
if(NOT DEFINED LOTUS_SECP_LIBRARY OR NOT EXISTS "${LOTUS_SECP_LIBRARY}")
  message(FATAL_ERROR "Set LOTUS_SECP_LIBRARY to a built libsecp256k1.a")
endif()
get_filename_component(LOTUS_SRC "${LOTUS_V2_CPP}/.." ABSOLUTE)
add_library(token_fixture_blake3 STATIC
  "${LOTUS_V2_CPP}/vendor/blake3/blake3.c"
  "${LOTUS_V2_CPP}/vendor/blake3/blake3_dispatch.c"
  "${LOTUS_V2_CPP}/vendor/blake3/blake3_portable.c")
target_compile_definitions(token_fixture_blake3 PRIVATE BLAKE3_NO_SSE2 BLAKE3_NO_SSE41 BLAKE3_NO_AVX2 BLAKE3_NO_AVX512 BLAKE3_USE_NEON=0)
add_executable(compiler_token_native_check
  native-token-check.cpp
  "${LOTUS_V2_CPP}/output.cpp" "${LOTUS_V2_CPP}/transaction.cpp"
  "${LOTUS_V2_CPP}/commitment.cpp" "${LOTUS_V2_CPP}/tagged_hash.cpp" "${LOTUS_V2_CPP}/signing.cpp"
  "${LOTUS_V2_CPP}/vm.cpp")
target_include_directories(compiler_token_native_check PRIVATE "${LOTUS_V2_CPP}" "${LOTUS_SRC}/secp256k1/include")
target_link_libraries(compiler_token_native_check PRIVATE token_fixture_blake3 OpenSSL::Crypto "${LOTUS_SECP_LIBRARY}")
target_compile_options(compiler_token_native_check PRIVATE -Wall -Wextra -Wpedantic -Werror)
