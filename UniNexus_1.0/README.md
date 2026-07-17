# UniNexus

**UniNexus** is an integrated campus-management mobile software platform developed specifically for **New Cairo Technological University (NCTU)**. It modernizes traditional, manual higher-education operational workflows into a secure, unified digital campus ecosystem by bridging high-performance mobile software with local edge IoT hardware.

---

## 🛠️ Tech Stack & Hardware Components

### Software Ecosystem
*   **Frontend:** Android Studio (Native Java)
*   **UI/UX Design:** Figma
*   **Local Server Environment:** XAMPP (Apache Server)
*   **Database Engine:** MySQL managed via phpMyAdmin
*   **Networking:** Asynchronous HTTP POST communication utilizing the custom `PutData` protocol framework

### Edge Hardware Scanning Station
*   **Microprocessing Unit:** Raspberry Pi 4 Model B (4GB LPDDR4)
*   **Optical Input Sensor:** Raspberry Pi NoIR v2 Camera Board (Sony IMX219PQ CMOS image sensor) optimized for dynamic QR code parsing
*   **Thermal Management & Power:** Dual cooling fans, grooved aluminum radiators, and an official 5.1V/3A USB-C power supply

---

## 📐 System Modeling & Architecture

The platform architecture relies on strict relational integrity and precise user role segmentation. Complete architectural visual maps can be found in the system documentation repository across the following structural models:

*   **Use Case Diagram:** Defines interactions between system actors (Students, Faculty, and IT Staff) and backend endpoints.
*   **Class & Sequence Diagrams:** Maps entity relationships and sequential execution flows during runtime actions.
*   **Entity-Relationship Diagram (ERD):** Configures database constraints to safeguard absolute relational integrity across all fields.
*   **Data Flow Diagrams (DFD):** Traces data streams handling credential matching, hardware error logging, and communication routing.

### User Access Matrices
| User Role | Primary System Interactions & Capabilities |
| :--- | :--- |
| **Students** | View course matrices, access syllabi/course materials, engage in direct-messaging channels with staff, and log academic attendance. |
| **Faculty** | Disseminate academic materials, review automated student rosters, record/verify attendance, and generate infrastructure malfunction tickets. |
| **Staff (IT)** | Route and process equipment malfunction tickets, adjust active lab allocation timetables, and manage building permissions. |

---

## 💻 Codebase Core Modules

The application frontend leverages native Java for Android to manage state persistence, asynchronous data routing, and hardware interaction:

### 1. Dynamic Token Generation (`attend_act.java`)
Manages automated academic attendance logging by capturing parameters from localized spinner UI controls (Subject, Session Time, Access Mode) alongside user session parameters from `SharedPreferences`. It evaluates occupation types to build custom payloads, transforming raw string metrics into an on-screen 300x300 pixel visual matrix using the Google ZXing library:
```java
BitMatrix bitMatrix = multiFormatWriter.encode(qr.toString(), BarcodeFormat.QR_CODE, 300, 300);
BarcodeEncoder barcodeEncoder = new BarcodeEncoder();
Bitmap bitmap = barcodeEncoder.createBitmap(bitMatrix);
qrcode.setImageBitmap(bitmap);