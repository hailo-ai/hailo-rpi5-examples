#!/bin/bash

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <input_filename> [output_filename]"
    exit 1
fi

input_filename=$1
output_filename="${2:-${input_filename%.*}_converted.mp4}"

# Convert the input video
ffmpeg -y -i "$input_filename" -c:v h264 -s 640x640 -pix_fmt yuv420p -r 30 -c:a aac -b:a 128k -ar 48000 temp_output.mp4

# Create 5 seconds of blank video
ffmpeg -y -f lavfi -i color=c=black:s=640x640:r=30 -t 5 -c:v h264 -pix_fmt yuv420p blank.mp4

# Concatenate the converted video and the blank video
ffmpeg -y -f concat -safe 0 -i <(echo -e "file '$(pwd)/temp_output.mp4'\nfile '$(pwd)/blank.mp4'") -c copy "$output_filename"

# Clean up temporary files
rm temp_output.mp4 blank.mp4