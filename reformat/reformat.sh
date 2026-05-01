#!/bin/bash
set -e

echo ""
echo "=========================================="
echo "Running Black (code formatter)..."
echo "=========================================="
black src/

echo ""
echo "=========================================="
echo "Running docformatter (docstring formatter)..."
echo "=========================================="
docformatter --in-place -r src/

echo ""
echo "=========================================="
echo "Running ruff (import sorter / linter)..."
echo "=========================================="
ruff check --fix src/

echo ""
echo "=========================================="
echo "Formatting complete!"
echo "=========================================="
