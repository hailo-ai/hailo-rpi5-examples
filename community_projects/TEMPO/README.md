TEMPO
================================================================

Song generation based on heart rate. The code generates music according to your hear rate.

![Pipeline](https://i.imgur.com/VhYneIl.png)


Based on the work of [SkyTNT Midi-Model](https://github.com/SkyTNT/midi-model)

The model we compiled to Hailo is [midi-model-tv2o-medium](https://huggingface.co/skytnt/midi-model-tv2o-medium)


[![VIDEO](https://img.youtube.com/vi/xX3PSgciWHs/1.jpg)](https://www.youtube.com/watch?v=xX3PSgciWHs)


Requirements
------------

The packages are described in the requirements (additionally to the requirements of the whole repo)

Run Options
-----------
You can run either with a heart monitor which will choose the initial BPM in the generation or by choosing the generation manually.

Setup
-----

1. Setup virtual environment
    - From hailo-rpi-example top directory run `. setup_env.sh`
    - `cd community_projects/TEMPO`
    - `pip install -r requirements.txt`
    - `sudo chmod +x download_files.sh`
    - `./download_files.sh`

2. Hardware Setup (for using heart monitor)
    2.1 Hardware Requirements:
        - Heart monitor - https://pulsesensor.com/
        - A2D - part number ADS1115
        - Jumpers to connect raspberry header to the sensor.
    2.2 Hardware Connections:
        2.2.1 Connect the hear monitor to the analog input A0 of the A2D.
            - Prepare the sensor according to the official site - https://cdn.shopify.com/s/files/1/0100/6632/files/PulseSensor_Datasheet_2024-Nov.pdf?v=1732032216
            - Connect red wire to 3.3V pin of A2D.
            - Connect black wire to ground pin of A2D.
            - Connect purple wire to A0 pin of A2D.
        2.2.2 Conect the A2D to the raspberry pi in the correct GPIO of I2C0.
            - Image of pinout is availiable at https://community.element14.com/products/raspberry-pi/m/files/148385
            - Pin1 is 3.3V of the A2D.
            - Pin3 is SDA.
            - Pin 5 is SCL.
            - Pin 6 is Ground.
    2.3 Put the heart monitor on the your finger using the velcro tape provided in you purchase (see 2.2.1).
        The tape should be strong enough to not fall from the finger but not too strong for a reliable read as the monitor uses the light reflection coming from the veins.

Running the program
-------------------

1. Run the web application(not using heart monitor):
    - run `python app_hailo.py --port 8080 --batch 1`
    - After the web ui opens click "generate". This will load the hef file which is located in a google drive folder.
    - In this version you can control all the sliders.

2. Run using heart monitor:
    - run 'python app_heart_bit.py'
    - When running with the heart monitor, the music is then generated and then is played.

Additional Notes
----------------

- On the heart monitor application, BPM measurements are printed for about 20 seconds, you can ignore them as the final result will be calculated on the whole 20 seconds.
- If the heart monitor is not put correctly the BPM will be 0 for all measurements and the program will not work.

Disclaimer
----------
This code example is provided by Hailo solely on an “AS IS” basis and “with all faults”. No responsibility or liability is accepted or shall be imposed upon Hailo regarding the accuracy, merchantability, completeness or suitability of the code example. Hailo shall not have any liability or responsibility for errors or omissions in, or any business decisions made by you in reliance on this code example or any part of it. If an error occurs when running this example, please open a ticket in the "Issues" tab.

This example was tested on specific versions and we can only guarantee the expected results using the exact version mentioned above on the exact environment. The example might work for other versions, other environment or other HEF file, but there is no guarantee that it will.