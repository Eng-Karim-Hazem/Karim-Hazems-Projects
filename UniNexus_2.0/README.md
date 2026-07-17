# UniNexus: Enterprise Campus Management & Smart IoT Access Control System

**UniNexus** is an integrated ecosystem designed to modernize educational institutions by unifying campus management software with edge-computing hardware security layers. The platform has evolved from a foundational architecture powered by Java and PHP into a highly scalable, cross-platform ecosystem driven by a **Flutter** mobile infrastructure, **Firebase** backend, and a decoupled **IoT Gate Control Layer**.

---

## 🚀 Key Modules & Ecosystem Architecture

The UniNexus platform bridges high-level administrative software with resilient physical automation through three core tiers:

### 1. Cross-Platform Mobile Suite (UniNexus 2)
* **Frontend Framework**: Built using **Flutter** for a uniform, high-performance user experience across iOS and Android devices.
* **Backend Infrastructure**: Powered by **Firebase** for real-time authentication, push notifications, and serverless data streaming.
* **Dynamic Access Tokens**: Generates dynamic, cryptographically signed QR codes within the app to grant authorized entry into physical campus zones.

### 2. Core Campus Backend
* **Legacy & Integration Components**: Leverages robust **Java** and **PHP** structures to handle foundational university administration tasks, student records, and relational data management.

### 3. IoT Edge Gate Control Layer
An edge-computing hardware and firmware subsystem deployed directly at campus boundary lines to process physical entry validation securely and autonomously[cite: 4].

---

## 🏗️ IoT Hardware Architecture

The IoT layer relies on a decoupled, multi-tier processing model where image capture, edge verification, and electro-mechanical control are separated into specialized layers to prevent terminal lockouts and mitigate peripheral strain[cite: 4].


### Component Breakdown
* **Raspberry Pi 4 Model B (Master Node)**: Acts as the high-throughput master gateway controller[cite: 4]. It executes edge decryption, runs cryptographic signature validations on captured QR tokens, and handles direct data synchronization with **Cloud Firestore**[cite: 4].
* **ESP32 Microcontroller (Auxiliary Node)**: Functions as an isolated co-processor to ensure constant localized security monitoring[cite: 4]. It runs a localized offline logging cache and a continuous heartbeat supervision link with the Raspberry Pi 4 to keep hardware operational during localized software freezes[cite: 4].
* **Pi Camera Module v2**: Positioned securely at entry lines to capture incoming token data[cite: 4].
* **Relay Module (Gate Control)**: Serves as an electrical isolation layer between low-power control circuitry and high-power physical gate actuation components[cite: 4]. It sends a low-voltage pulse to release the physical turnstile lock barrier upon receiving an "Access Granted" signal[cite: 4].
* **Physical Tamper Switch**: Monitored continuously by the ESP32 to instantly capture, flag, and log physical enclosure breach events for administrative review[cite: 4].

---

## 🚦 UI Status Indicator Guide

The system features a programmable **WS2812 RGB LED Ring** positioned symmetrically around the camera module to provide immediate operational feedback to approaching users and security personnel[cite: 4]:

| LED Color Pattern | System State | Meaning & Actuation |
| :--- | :--- | :--- |
| **Solid Green** | `ACCESS_GRANTED` | Entry approved. Relay closes the internal circuit to actuate the gate[cite: 4]. |
| **Flashing Red** | `ACCESS_DENIED` | Invalid, unverified, or expired token flag; gate remains locked[cite: 4]. |
| **Steady Blue Pulse** | `SYSTEM_READY` | Scanner is active, online, and waiting to process upcoming credentials[cite: 4]. |

---

## 🛠️ Environmental & Power Management

To maintain continuous, stable operation across extended enterprise shifts without thermal throttling, the system integrates a rugged physical infrastructure:
* **Active Cooling**: A 5V dual-fan kit paired with an aluminum heatsink framework pulls cool air through side intake vents and exhausts heat through an escape slit located under the LED ring[cite: 4].
* **Power Regulation**: A dedicated power supply unit isolates hardware units against voltage fluctuations caused by active camera sensors, communication radios, and electromechanical relay triggers[cite: 4].

---

## ⚙️ Core Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Mobile Applications** | Flutter, Dart |
| **Backend & Database** | Firebase (Auth, Cloud Firestore), PHP, Java |
| **Edge Compute Node** | Raspberry Pi 4 Model B, Linux environment |
| **Peripherals & Safety** | ESP32, FreeRTOS/C++ Firmware, Pi Camera v2, WS2812 NeoPixel |