cmake_minimum_required(VERSION 3.25)
# This file is also the always-run source verification script; no auxiliary
# script or externally supplied interpreter archive is used.
function(verify_exact_abc)
    if(NOT IS_ABSOLUTE "${ABC_SOURCE_DIR}" OR NOT IS_DIRECTORY "${ABC_SOURCE_DIR}/.git")
        message(FATAL_ERROR "ABC_SOURCE_DIR must be a fresh real-.git clone at the exact acceptance pin")
    endif()
    find_program(ECASH_GIT git REQUIRED)
    execute_process(COMMAND "${ECASH_GIT}" -C "${ABC_SOURCE_DIR}" rev-parse HEAD
        OUTPUT_VARIABLE revision OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE result)
    if(NOT result EQUAL 0 OR NOT revision STREQUAL "1fb7db17c176cdea8a2c60d887891589382ee4e3")
        message(FATAL_ERROR "ABC source revision does not match the eCash acceptance pin")
    endif()
    execute_process(COMMAND "${ECASH_GIT}" -C "${ABC_SOURCE_DIR}" rev-parse "HEAD^{tree}"
        OUTPUT_VARIABLE tree OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE result)
    if(NOT result EQUAL 0 OR NOT tree STREQUAL "b2e4a0a9f57c593129028352d5dbb0c4ff294cdb")
        message(FATAL_ERROR "ABC source tree does not match the eCash acceptance pin")
    endif()
    execute_process(COMMAND "${ECASH_GIT}" -C "${ABC_SOURCE_DIR}" ls-files --others
        OUTPUT_VARIABLE untracked OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE result)
    if(NOT result EQUAL 0 OR NOT untracked STREQUAL "")
        message(FATAL_ERROR "Untracked or ignored files in ABC source are unsupported; use a fresh pristine clone")
    endif()
    execute_process(COMMAND "${ECASH_GIT}" -C "${ABC_SOURCE_DIR}" diff --quiet HEAD --
        RESULT_VARIABLE result)
    if(NOT result EQUAL 0)
        message(FATAL_ERROR "ABC tracked source/header changes are unsupported")
    endif()
endfunction()
verify_exact_abc()
if(ECASH_VERIFY_ONLY)
    return()
endif()
project(ecash_compiler_native LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(DEFINED ABC_BUILD_DIR OR DEFINED ABC_LIBRARIES)
    message(FATAL_ERROR "Prebuilt ABC libraries are unsupported; this target builds its own pinned dependencies")
endif()
include(ExternalProject)
set(ECASH_BUILD_JOBS 4 CACHE STRING "Parallel jobs in the isolated ABC dependency build")
set(ABC_BINARY_DIR "${CMAKE_CURRENT_BINARY_DIR}/abc-build")
set(B "${ABC_BINARY_DIR}/src")
set(ABC_LIBRARIES_LOCAL
    "${B}/libbitcoinconsensus.a" "${B}/libscript.a" "${B}/libcommon.a"
    "${B}/libutil.a" "${B}/crypto/libcrypto.a" "${B}/secp256k1/libsecp256k1.a"
    "${B}/univalue/libunivalue.a")
add_custom_target(verify-ecash-source
    COMMAND "${CMAKE_COMMAND}" "-DABC_SOURCE_DIR=${ABC_SOURCE_DIR}" -DECASH_VERIFY_ONLY=ON
        -P "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt")
ExternalProject_Add(pinned-abc
    SOURCE_DIR "${ABC_SOURCE_DIR}"
    BINARY_DIR "${ABC_BINARY_DIR}"
    DOWNLOAD_COMMAND "" UPDATE_COMMAND "" PATCH_COMMAND ""
    CMAKE_GENERATOR Ninja
    CMAKE_ARGS -DCMAKE_BUILD_TYPE=Release -DBUILD_CHRONIK=OFF -DBUILD_QT=OFF
        -DBUILD_WALLET=OFF -DBUILD_ZMQ=OFF -DBUILD_LIBBITCOINCONSENSUS=OFF
        -DBUILD_IGUANA=OFF -DBUILD_CLI=OFF -DBUILD_TX=OFF -DBUILD_CHAINSTATE=OFF
        -DBUILD_SEEDER=OFF -DBUILD_PROOF_MANAGER_CLI=OFF
    BUILD_COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target bitcoinconsensus script common
        --parallel "${ECASH_BUILD_JOBS}"
    BUILD_ALWAYS TRUE
    INSTALL_COMMAND ""
    BUILD_BYPRODUCTS ${ABC_LIBRARIES_LOCAL})
add_dependencies(pinned-abc verify-ecash-source)
file(SHA256 "${ABC_SOURCE_DIR}/src/script/interpreter.cpp" INTERPRETER_SHA256)
file(SHA256 "${ABC_SOURCE_DIR}/src/script/script_flags.h" FLAGS_SHA256)
file(SHA256 "${ABC_SOURCE_DIR}/src/policy/policy.h" POLICY_SHA256)
find_path(ECASH_BOOST_INCLUDE boost/range/adaptor/sliced.hpp
    HINTS /opt/homebrew/opt/boost/include /opt/homebrew/include REQUIRED)
add_executable(ecash-native runner.cpp)
add_dependencies(ecash-native pinned-abc verify-ecash-source)
target_include_directories(ecash-native PRIVATE "${ABC_SOURCE_DIR}/src" "${B}" "${ECASH_BOOST_INCLUDE}")
target_compile_definitions(ecash-native PRIVATE HAVE_CONFIG_H=1
    ECASH_INTERPRETER_SHA256="${INTERPRETER_SHA256}" ECASH_FLAGS_SHA256="${FLAGS_SHA256}"
    ECASH_POLICY_SHA256="${POLICY_SHA256}")
target_compile_options(ecash-native PRIVATE -Wall -Wextra -Werror -Wno-unused-parameter)
target_link_libraries(ecash-native PRIVATE ${ABC_LIBRARIES_LOCAL})
