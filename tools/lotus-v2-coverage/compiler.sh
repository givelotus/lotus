#!/bin/sh
set -eu
# Run from tools/lotus-v2-compiler after npm ci. No native stages are implied.
: "${LOTUS_V2_PYTHON:?Set Python with reference requirements and jsonschema}"
: "${COVERAGE_OUTPUT:?Set fresh absolute output directory}"
mkdir -p "$COVERAGE_OUTPUT"
npm run build
export NODE_V8_COVERAGE="$COVERAGE_OUTPUT/v8"
node --experimental-test-coverage '--test-coverage-include=dist/**/*.js' --test-coverage-include-all --test test/*.test.mjs
npx --yes c8@10.1.3 report --temp-directory="$NODE_V8_COVERAGE" --report-dir="$COVERAGE_OUTPUT/report" --all --src=dist --include='dist/**/*.js' --reporter=json --reporter=lcov --reporter=html
