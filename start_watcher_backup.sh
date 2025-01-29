#!/bin/bash

cd /home/bower/hailo-rpi5-examples
source setup_env.sh

# Check if there is a process with the name "Hailo Detection"
if pgrep -x "Hailo Detection" > /dev/null
then
    echo "Hailo process is already running."
else
    echo "No Hailo process found. Starting the Python program."
    python ./basic_pipelines/watcher.py --input rpi  > /home/bower/watcher.log 2>&1 &
fi

