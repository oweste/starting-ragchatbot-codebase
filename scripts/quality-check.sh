#!/bin/bash
# Run all quality checks

echo "=== Code Quality Checks ==="
echo ""

echo "1. Checking import sorting with isort..."
uv run isort --check-only backend/
ISORT_EXIT=$?

echo ""
echo "2. Checking code formatting with black..."
uv run black --check backend/
BLACK_EXIT=$?

echo ""
echo "3. Running linting with flake8..."
uv run flake8 backend/
FLAKE8_EXIT=$?

echo ""
echo "=== Results ==="
if [ $ISORT_EXIT -eq 0 ] && [ $BLACK_EXIT -eq 0 ] && [ $FLAKE8_EXIT -eq 0 ]; then
    echo "✓ All quality checks passed!"
    exit 0
else
    echo "✗ Some quality checks failed:"
    [ $ISORT_EXIT -ne 0 ] && echo "  - isort found import sorting issues"
    [ $BLACK_EXIT -ne 0 ] && echo "  - black found formatting issues"
    [ $FLAKE8_EXIT -ne 0 ] && echo "  - flake8 found linting issues"
    echo ""
    echo "Run './scripts/format.sh' to fix formatting issues automatically."
    exit 1
fi
