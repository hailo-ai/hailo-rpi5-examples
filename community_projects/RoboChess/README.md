![](../../resources/Hackathon-banner-2024.png)

# ChessMate

An open-source, innovative chess-playing robotic system that combines cutting-edge AI, robotics, and sleek design. ChessMate uses the Hailo8 AI processor, Raspberry Pi 5, a robotic arm, and a camera to fully automate the game of chess. This project is designed to be fun, engaging, and easy to replicate for any AI or chess enthusiast.

The hackathon journey is presented in the following link:

[![watch the video](https://img.youtube.com/vi/aXNgmYCEgDc/0.jpg)](https://youtu.be/aXNgmYCEgDc)

---

## Disclaimer
**This example is for reference only and requires a customized version of PyHailort to run. It will not work with the standard release.**
**If you are interested in this project, add a comment in the community and we will help bringing it up.**


## The Build

Our journey started by designing the robotic arm. The arm is a 3D-printed, six-servo robotic mechanism powered by an ESP32 chip. The robotic arm is fully independent and can be controlled over HTTP for simplicity, thanks to the ESP32's built-in Wi-Fi capabilities.

For motor positioning, we utilized the `Fabrik2DArduino` library, making small modifications to ensure compatibility with the ESP-IDF framework. *(Consider specifying the modifications for clarity.)*

To determine the chessboard state, we used the neural network `Xception`, running on the Hailo8 AI accelerator. Images captured by a USB camera are divided into 64 smaller images, each representing a single cell on the chessboard. *(Adding details about the cropping algorithm would be helpful.)* These images are processed by the Hailo8 to identify the chess piece on each square. The resulting board state is passed to **Stockfish**, an open-source chess engine renowned for its high-level gameplay and analysis.

The robotic arm executes the moves calculated by Stockfish, playing its turn with precision and often emerging victorious.

---

## Challenges

### This section is crucial as it highlights the obstacles we overcame during the project.

1. **Motor Failures:**
   - Initially, we selected motors that were too weak to handle the arm’s size and weight. This led to frequent failures, and we eventually ran out of spare parts.

2. **Image Quality Issues:**
   - Accurate chessboard state detection was highly dependent on image clarity. To address this, we added additional lighting to enhance the camera’s performance.

3. **AI for Move Decision:**
   - While we planned to use a neural network on the Hailo8 for move decision-making, time constraints led us to rely on Stockfish running on the Raspberry Pi, which proved to be sufficient.

---

## How to Build Your Own

### Robotic Arm:
- **3D Printing:**
  - STL files are available [here](<link>). Print them using PLA, ABS, or PETG filaments. Ensure a 0.15 mm horizontal expansion tolerance for hole fittings. Testing with a small piece is recommended.
  - Choose a futuristic color for a sleek design.

- **Shopping List:**
  - A complete list of components can be found [here](<link>). *(Highlight any critical or challenging components for the build.)*

- **Assembly:**
  - Pass all wires through the arm’s base before closing the lids.

- **Soldering:**
  - Follow the provided schematic [here](<link>).

- **Programming:**
  - Use VS Code with PlatformIO.
  - Clone the sub-repository [here](<link>) and upload the firmware to your ESP32 board. Remember to update the Wi-Fi SSID and password in the code.

---

## Things We Would Do Differently

Hindsight is invaluable, especially after a hackathon. Here are lessons learned:

1. **Motion System:**
   - A planar motion system such as Core XY would likely have been more reliable, easier to control, and simpler to build compared to a robotic arm. *(Expanding on the benefits of Core XY would enhance this section.)*

2. **Better Planning:**
   - Prioritizing robust components and pre-testing would have saved time and minimized failures.

---

We hope this inspires others to create their own ChessMate! Feel free to contribute, fork, or share your thoughts on the project. Let’s make chess even more fun and accessible with robotics and AI!
