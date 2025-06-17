#!/bin/bash

# Cross-validation test runner for cancensus vs pycancensus

set -e  # Exit on error

echo "==================================="
echo "Cross-Validation Test Suite"
echo "cancensus (R) vs pycancensus (Python)"
echo "==================================="
echo ""

# Check if API key is set
if [ -z "$CANCENSUS_API_KEY" ]; then
    echo "Error: CANCENSUS_API_KEY environment variable is not set"
    echo "Please set it with: export CANCENSUS_API_KEY='your_api_key_here'"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create results directory if it doesn't exist
mkdir -p results

# Install dependencies if needed
echo "Checking dependencies..."

# Check Python dependencies
echo "Checking Python dependencies..."
if ! python3 -c "import pycancensus" 2>/dev/null; then
    echo "Installing pycancensus..."
    cd ../../ && pip3 install -e . && cd tests/cross_validation
fi

if ! python3 -c "import rpy2" 2>/dev/null; then
    echo "Installing cross-validation Python dependencies..."
    pip3 install -e ../../[cross-validation]
fi

# Check R dependencies
echo "Checking R dependencies..."
Rscript -e "if (!require('cancensus')) stop('cancensus package not installed')" || {
    echo "Installing R dependencies..."
    Rscript install_r_deps.R
}

echo ""
echo "Starting tests..."
echo "================="

# Run the main test runner
echo ""
echo "Running comprehensive cross-validation tests..."
python3 utils/test_runner.py

# Run pytest tests for more detailed results
echo ""
echo "Running detailed pytest tests..."
cd ../../  # Go to project root
python3 -m pytest tests/cross_validation/tests/ -v --tb=short --color=yes
cd tests/cross_validation  # Return to cross_validation directory

# Generate summary report
echo ""
echo "Generating summary report..."
python3 -c "
from pathlib import Path
import json

results_dir = Path('results')
if (results_dir / 'overall_results.json').exists():
    with open(results_dir / 'overall_results.json', 'r') as f:
        results = json.load(f)
    
    print('\n=== FINAL SUMMARY ===')
    print(f\"Total test suites: {results['total_suites']}\")
    print(f\"Passed suites: {results['passed_suites']}\")
    print(f\"Success rate: {results['passed_suites']/results['total_suites']*100:.1f}%\")
    print('\nDetailed results saved in:', results_dir.absolute())
else:
    print('No overall results file found. Check individual test outputs.')
"

echo ""
echo "==================================="
echo "Cross-validation tests completed!"
echo "Check the results/ directory for detailed reports"
echo "===================================" 