#!/bin/bash

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <input_filename> [output_filename]"
    exit 1
fi

input_filename=$1
output_filename="${2:-${input_filename%.*}_converted.mp4}"

# Convert the input video
ffmpeg -y -i "$input_filename" -c:v h264 -s 640x640 -pix_fmt yuv420p -r 30 -c:a aac -b:a 128k -ar 48000 "$output_filename"