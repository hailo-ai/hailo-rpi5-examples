#!/bin/bash

cd /home/bower/hailo-rpi5-examples
source setup_env.sh
python ./basic_pipelines/watcher.py --input rpi  > /home/bower/watcher.log 2>&1 &


