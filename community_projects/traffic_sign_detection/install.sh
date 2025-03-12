#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
echo "Installing required Python dependencies..."
pip install -r requirements.txt
echo "Installation completed successfully."
