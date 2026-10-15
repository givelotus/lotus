#!/bin/sh
set -eu
# Run from tools/lotus-v2-reference; use Python 3.13 venv containing
# coverage==7.16.2, requirements-vm.txt and jsonschema for compiler tests.
: "${COVERAGE_PYTHON:?Set the isolated coverage Python executable}"
: "${COVERAGE_OUTPUT:?Set a fresh absolute output directory}"
mkdir -p "$COVERAGE_OUTPUT"
export COVERAGE_FILE="$COVERAGE_OUTPUT/reference.data"
"$COVERAGE_PYTHON" -m coverage run --branch --source=lotus_v2_reference -m unittest discover -s tests
"$COVERAGE_PYTHON" -m coverage json -o "$COVERAGE_OUTPUT/reference.json"
"$COVERAGE_PYTHON" -m coverage lcov -o "$COVERAGE_OUTPUT/reference.lcov"
"$COVERAGE_PYTHON" -m coverage html -d "$COVERAGE_OUTPUT/html"
