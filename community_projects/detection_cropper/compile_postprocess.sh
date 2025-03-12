#!/bin/bash

# Set the project directory name
PROJECT_DIR="."

# Enable strict error handling
set -e

# Check if Meson and Ninja are installed
if ! command -v meson &> /dev/null; then
    echo "Error: Meson is not installed. Please install it and try again."
    exit 1
fi

if ! command -v ninja &> /dev/null; then
    echo "Error: Ninja is not installed. Please install it and try again."
    exit 1
fi

# Get the build mode from the command line (default to release)
if [ "$1" = "debug" ]; then
    BUILD_MODE="debug"
elif [ "$1" = "clean" ]; then
    BUILD_MODE="release"  # Default to release for cleanup
    CLEAN=true
else
    BUILD_MODE="release"
fi

# Set up the build directory
BUILD_DIR="$PROJECT_DIR/build.$BUILD_MODE"

# Handle cleanup
if [ "$CLEAN" = true ]; then
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    exit 0
fi

# Create the build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure the project with Meson if not already configured
if [ ! -f "build.ninja" ]; then
    echo "Configuring project with Meson..."
    meson setup .. --buildtype="$BUILD_MODE"
else
    echo "Build directory already configured. Skipping setup."
fi

# Compile the project using Ninja with parallel jobs
echo "Building project with Ninja..."
ninja -j$(nproc)

# Install the project (optional)
echo "Installing project..."
ninja install

echo "Build completed successfully!"
