#!/bin/bash

# Script to run all linting and reformatting steps from GitHub Actions locally
# This script mirrors the reformat and lint jobs from .github/workflows/ci.yaml

set -e  # Exit on error

echo "=========================================="
echo "Installing dependencies..."
echo "=========================================="
pip install --upgrade pip
pip install .[dev]

echo ""
echo "=========================================="
echo "Running isort on ./src..."
echo "=========================================="
isort ./src

echo ""
echo "=========================================="
echo "Running Ruff (linter)..."
echo "=========================================="
ruff check ./src

echo ""
echo "=========================================="
echo "All linting and formatting steps completed!"
echo "=========================================="
