#!/bin/bash

# Step 1: Set up the environment
echo "Setting up the environment..."
source setup_env.sh || { echo "Failed to set up the environment"; exit 1; }

# Step 2: Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt || { echo "Dependency installation failed"; exit 1; }

# Step 3: Run pytest tests
echo "Running tests..."
pytest tests/ --maxfail=1 --disable-warnings || { echo "Tests failed"; exit 1; }

echo "All tests passed successfully!"
