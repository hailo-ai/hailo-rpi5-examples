#!/bin/bash

# Set the project directory name
PROJECT_DIR="."

# Get the build mode from the command line (default to release)
if [ "$1" = "debug" ]; then
    BUILD_MODE="debug"
else
    BUILD_MODE="release"
fi

# Create the build directory
BUILD_DIR="$PROJECT_DIR/build.$BUILD_MODE"
mkdir -p $BUILD_DIR
cd $BUILD_DIR

# Configure the project with Meson
meson setup .. --buildtype=$BUILD_MODE

# Compile the project
ninja

# Install the project (optional)
ninja install
