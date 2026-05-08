#!/bin/bash
# ToxiGuard-AI Regulatory Validation Harness

echo "🚀 Starting Regulatory Validation..."
echo "------------------------------------"

# 1. Environment Check
echo "🔍 Checking Python and RDKit..."
python3 -c "import rdkit; print('✅ RDKit Version:', rdkit.__version__)" || { echo "❌ RDKit not found!"; exit 1; }

# 2. Run Regulatory Core Tests
echo "🧪 Running tests/test_regulatory.py..."
python3 tests/test_regulatory.py || { echo "❌ Regulatory tests failed!"; exit 1; }

echo "------------------------------------"
echo "✅ All Regulatory Checks Passed! [Harness Active]"
