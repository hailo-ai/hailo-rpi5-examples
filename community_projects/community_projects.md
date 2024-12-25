# How To Add a Community Project
Follow these step-by-step instructions to create and structure your community project correctly.

## Run the Basic Pipeline
Make sure you have followed the repository instructions and can run the basic pipelines.
```bash
python basic_pipelines/pose_estimation.py
```
This verifies that your environment is set up properly.

## Go Over the Basic Pipelines Documentation
Click [here](../doc/basic-pipelines.md) for the Basic Pipeline Documentation

## Create Your Project Directory
Navigate to the community_projects folder and create a directory for your project.
```bash
cd community_projects
mkdir <your project name>
cd <your project name>
```
Replace <your_project_name> with the name of your project.

## Copy the template example
```bash
cp ../template_example/* .
```

## Modify the Callback Class
Modify the callback class that inherits from app_callback_class.
Add to the class you needed members and methods.

## Modify the Callback Function
Define the callback function inside your class. This function will be called whenever data is available from the pipeline.
You can implement whatever logic you need inside this callback function.

## Modify the Main Function
Modify the main function to initialize and run the application.
Choose the Gstreamer all you are laying on instead GStreamerDetectionApp.
This structure ensures your project can be executed as a standalone script.

## Modify the README File, requirements File, Add Resources
If your project requires additional resources (like models, images, or datasets), follow these steps:
If your code imports Python packages not included in the virtual environment, modify the requirements.txt.

# IMPORTANT: No binary files
Do not add non-code files (e.g., images, HEFs, videos, etc.) to the repository. If needed, you can include a download_resources.sh script to download such files from Google Drive.​
For Model Zoo HEFs, you can download them directly from Hailo's server.​