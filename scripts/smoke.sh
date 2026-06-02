#!/usr/bin/env bash
set -euo pipefail

echo "zig-PY smoke: cleaning generated files"
rm -rf build .pytest_cache
find . -type d -name __pycache__ -prune -exec rm -rf {} +

echo "zig-PY smoke: running doctor"
make doctor

echo "zig-PY smoke: building add example"
make build-example

echo "zig-PY smoke: running add example"
python examples/add/run.py

echo "zig-PY smoke: running tests"
make test

echo "zig-PY smoke: success - Python called Zig and tests passed"
