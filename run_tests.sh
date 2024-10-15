#!/bin/bash

# Path to your setup_env.sh file
SETUP_ENV_PATH="setup_env.sh"

# Path to your tests directory
TESTS_DIR="tests"

# Source the setup_env.sh file (it will handle virtual environment activation)
echo "Sourcing setup_env.sh..."
source "$SETUP_ENV_PATH"

# Run pytest for all test files
echo "Running tests..."
pytest "$TESTS_DIR/test_sanity_check.py" \
       "$TESTS_DIR/test_hailo_rpi5_examples.py" \
       "$TESTS_DIR/test_edge_cases.py" \
       "$TESTS_DIR/test_advanced.py"

echo "All tests completed."
