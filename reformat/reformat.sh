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
docformatter src/

echo ""
echo "=========================================="
echo "Running ruff --select I (import sorter)..."
echo "=========================================="
ruff check src/

echo ""
echo "=========================================="
echo "Formatting complete!"
echo "=========================================="
