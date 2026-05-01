#!/bin/bash
set -e

CHECK_ONLY="${CHECK_ONLY:-false}"

echo ""
echo "=========================================="
echo "Running Black (code formatter)..."
echo "=========================================="
if [ "$CHECK_ONLY" = "true" ]; then
  black --check src/
else
  black src/
fi

echo ""
echo "=========================================="
echo "Running docformatter (docstring formatter)..."
echo "=========================================="
if [ "$CHECK_ONLY" = "true" ]; then
  docformatter src/
else
  # Exit code 3 means "files were reformatted" — that's success in apply mode.
  docformatter --in-place -r src/ || test $? -eq 3
fi

echo ""
echo "=========================================="
echo "Running ruff (import sorter / linter)..."
echo "=========================================="
if [ "$CHECK_ONLY" = "true" ]; then
  ruff check src/
else
  ruff check --fix src/
fi

echo ""
echo "=========================================="
echo "Formatting complete!"
echo "=========================================="
