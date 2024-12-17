# How To Add a Community Project
Follow these step-by-step instructions to create and structure your community project correctly.

## Run the Basic Pipeline 
Make sure you have followed the repository instructions and can run the basic pipelines.
```bash
python basic_pipelines/pose_estimation.py
```
This verifies that your environment is set up properly.


## Create Your Project Directory
Navigate to the community_projects folder and create a directory for your project.
```bash
cd community_projects
mkdir <your project name>
```
Replace <your_project_name> with the name of your project.

## Use the Hailo Applications Infrastructure 
To use Hailo Applications Infrastructure, import the hailo_apps_infra module as shown in the template example:
```bash
from hailo_apps_infra.hailo_rpi_common import (
    app_callback_class
)
```
This allows you to access essential classes and methods for your project.

## Use Built-In Pipelines
If you want to use one of the built-in pipelines, import it like this:
```bash
from hailo_apps_infra.detection_pipeline import GStreamerDetectionApp
```
Change detection_pipeline and GStreamerDetectionApp as needed to fit the pipeline you want to use.

## Create a Callback Class
Create a callback class that inherits from app_callback_class.
```bash
from hailo_apps_infra.hailo_rpi_common import (
    app_callback_class
)

class UserAppCallbackClass(app_callback_class):
    pass  # Add your custom logic here
```
This is the structure where you will customize the logic for handling pipeline data.

## Create a Callback Function
Define the callback function inside your class. This function will be called whenever data is available from the pipeline.
```bash
# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    # Add your custom logic here
    pass
```
You can implement whatever logic you need inside this callback function.

## Create the Main Function
Create a main function to initialize and run the application.
```bash
if __name__ == "__main__":
    # Add any data you want to pass to the application in 'user_data'
    user_data = UserAppCallbackClass()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
```
This structure ensures your project can be executed as a standalone script.

## Add a README File
Create a README.md file in your project directory. This file should include:

- Overview: A summary of your project.

- Setup Instructions: How to install dependencies and run the project.

- Usage: Examples of how to run the script.

A good README ensures that others can understand and use your project.

## Add a Requirements File
If your code imports Python packages not included in the virtual environment, create a requirements.txt file in your project directory. List all required packages, one per line, like this:
```bash
    numpy
    opencv-python-headless
```

## Add Resources (Optional)
If your project requires additional resources (like models, images, or datasets), follow these steps:
### Create a Resources Directory
```bash
    mkdir <your_project_name>/resources
```
### Create a download_resources.sh Script
Write a script to download the required resources. For example:
```bash
    #!/bin/bash

    echo "Downloading resources..."
    wget -O resources/input.mp4 https://example.com/path/to/input.mp4
    echo "Download complete!"
```
This script will ensure all required files are downloaded when someone sets up the project.