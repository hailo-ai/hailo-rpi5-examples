#!/bin/bash

# Path to your virtual environment
VENV_PATH="venv_hailo_rpi5_examples"

# Path to your setup_env.sh file
SETUP_ENV_PATH="setup_env.sh"

# Path to your tests directory
TESTS_DIR="tests"

# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Source the setup_env.sh file
echo "Sourcing setup_env.sh..."
source "$SETUP_ENV_PATH"

# Run pytest for all test files
echo "Running tests..."
pytest "$TESTS_DIR/test_sanity_check.py" \
       "$TESTS_DIR/test_hailo_rpi5_examples.py" \
       "$TESTS_DIR/test_edge_cases.py" \
       "$TESTS_DIR/test_advanced.py"

# Deactivate the virtual environment
deactivate

echo "All tests completed."