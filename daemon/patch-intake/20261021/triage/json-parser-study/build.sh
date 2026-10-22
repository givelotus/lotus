#!/bin/sh
set -eu
study_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$study_dir"
# Benchmark-only cache, exact pins recorded in sources.json and univalue-source.json.
clang -O3 -std=c11 -c cache/yyjson.c -o cache/yyjson.o
clang++ -O3 -std=c++20 -Icache -c cache/simdjson.cpp -o cache/simdjson.o
clang++ -O3 -std=c++20 -Icache -Icache/univalue parser_bench.cpp \
 cache/univalue/univalue.cpp cache/univalue/univalue_get.cpp \
 cache/univalue/univalue_read.cpp cache/univalue/univalue_write.cpp \
 cache/yyjson.o cache/simdjson.o -o parser_bench
