# Smart Bluetooth RC Car & Line Follower Robot

A dual-mode, multi-functional 4WD robotic vehicle built on the **Arduino Uno** platform. This project integrates wireless smartphone control via **Bluetooth (RemoteXY)** with an autonomous **infrared (IR) line-following system**, alongside real-time speed/power modulation, visual indicator lights, and an audible horn.

---

## 🛠️ Features

- **Dual Operation Modes**:
  - **Manual Bluetooth Control**: Steer the robot in real-time using a customized virtual joystick/buttons on the RemoteXY mobile application.
  - **Autonomous Line Following**: Activate autonomous mode to follow dark/light paths using a 3-sensor infrared arrays.
- **Dynamic Speed Tuning**: Multi-level PWM duty cycle adjustment via RemoteXY dashboard interface slider (translating 0-100% input into direct analog motor drive voltages).
- **Interactive Auxiliaries**:
  - Integrated 5V Buzzer acting as an audible horn.
  - Headlight LEDs for low-light visualization.
- **Hardware Stabilized Sensor Readings**: Custom multi-sample noise-filtering routine to prevent IR sensor jitter.

---

## 🔌 Hardware Configuration & Pin Mapping

Based on the schematic diagram and codebase, here is the official system routing:

| Component Category | Arduino Pin | Component Pin / Label | Description |
| :--- | :---: | :--- | :--- |
| **Microcontroller** | Arduino Uno | Rev3 | Main System Controller |
| **Bluetooth Module** | D2 (RX) <br> D3 (TX) | TXD <br> RXD | SoftwareSerial Connection (9600 Baud) to HC-05/06 |
| **Line Sensors (IR)** | D11 <br> D12 <br> D13 | OUT (Left Sensor) <br> OUT (Center Sensor) <br> OUT (Right Sensor) | FC-51 Obstacle Avoidance / Line tracking modules |
| **Motor Driver (L298N)**| D9 <br> D8 <br> D7 <br> D6 <br> D10 (PWM) <br> D5 (PWM) | IN1 (Motor 1) <br> IN2 (Motor 1) <br> IN3 (Motor 2) <br> IN4 (Motor 2) <br> enA (Enable A) <br> enB (Enable B) | Bridges H-Bridge logic with directional outputs and PWM speed lines. |
| **Indicators & Alarm** | D4 <br> D14 (A0) | LED Anode (+)<br> Buzzer (+) | Visual headlights and Horn signaling |
| **Power Supply** | - | 18650 Batteries x3 (11.1V Nominal) | Main system current source through physical rocker switch |

---

## ⚙️ Software Dependencies

This project relies on the following Arduino libraries:
1. **RemoteXY** (v3.1.13 or newer) - For rendering and receiving command packets from the mobile dashboard app.
2. **SoftwareSerial** (Built-in) - For hosting secondary UART serial ports to communicate with the Bluetooth transceiver on Pins 2 and 3.

---

## 📱 Mobile App Configuration (RemoteXY)

The graphical interface is built using the RemoteXY online editor. Key interface elements declared within the `RemoteXY_CONF` binary configuration stream include:
- **Directional Buttons**: Forward, Backward, Sharp Left, Sharp Right.
- **Power Slider**: Modulates speed duty cycle dynamically.
- **Switches**: Toggle buttons for `Line Follow` mode and `Lights` control.
- **Buttons**: Push-to-sound button for the `Horn` (Buzzer).

---

## 🏁 Getting Started

1. **Wiring**: Wire all components together according to the pin mappings above or reference the `schematic_diagram.jpg` file.
2. **Install Libraries**: Open your Arduino IDE, go to `Sketch -> Include Library -> Manage Libraries...`, search for `RemoteXY`, and install the latest version.
3. **Upload Code**: Open the `.ino` sketch containing the provided source code, select your `Arduino Uno` board and correct COM port, and hit **Upload**.
4. **App Connection**: 
   - Download the **RemoteXY** app from the Google Play Store or Apple App Store.
   - Power on the vehicle.
   - Enable Bluetooth on your smartphone, find your transceiver module (e.g., `HC-05`), and pair using the app to load the control interface instantly.
