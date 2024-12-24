# Hailo UnixDomainSocketIntegration example

This exmaple is based on the detection pipeline. It is an example for converting a pipeline to event-based integration. 
The demo model is Object detection, but this can be applied to any model.

The server measures 'uptime' of each object, and takes only objects with enough 'uptime' (To ignore flicering due bad detection) 

## Installation
Follow the installation flow in the main README file, and then continue following this README file.

### Enable SPI
```bash
sudo raspi-config
```

- 3 Interface Options
- I4 SPI
- Yes
- reboot


### Navigate to the repository directory:
```bash
cd hailo-rpi5-examples
```

### Environment Configuration  (Required for Each New Terminal Session)
Ensure your environment is set up correctly by sourcing the provided script. This script sets the required environment variables and activates the Hailo virtual environment. If the virtual environment does not exist, it will be created automatically.
```bash
source setup_env.sh
```
### Navigate to the example directory:
```bash
cd community_projects/UnixDomainSocketIntegration/
```
### Requirements Installation
Within the activated virtual environment, install the necessary Python packages:
```bash
pip install -r requirements.txt
```

### To Run the Simple Example:
```bash
python detection_service.py
```
- To close the application, press `Ctrl+C`.
