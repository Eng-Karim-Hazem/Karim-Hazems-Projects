import serial
import json
import time
from datetime import datetime
import UniLED

import firebase_admin
from firebase_admin import credentials, firestore

# ------------------------
# Firebase
# ------------------------

cred = credentials.Certificate("uninexus-1aea7-firebase-adminsdk-fbsvc-91267f088c.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
UniLED.initialize()
UniLED.booting()
time.sleep(2)


# ------------------------
# Serial
# ------------------------

ser = serial.Serial('/dev/ttyUSB0', 115200)

# ------------------------
# Settings
# ------------------------

TIMEOUT = 10

# ------------------------
# Runtime Storage
# ------------------------

devices = {}

device_status = {}

# ------------------------
# Startup
# ------------------------

print("Heartbeat + Tamper monitor started")

# ------------------------
# Main Loop
# ------------------------

while True:

    # --------------------
    # Read Serial
    # --------------------

    if ser.in_waiting:

        try:

            line = ser.readline().decode().strip()

            print("RAW:", line)

            data = json.loads(line)

            # ----------------
            # HEARTBEAT
            # ----------------

            if data["type"] == "heartbeat":

                scanner = data["scanner"]

                devices[scanner] = time.time()

                # initialize status if first time
                if scanner not in device_status:
                    device_status[scanner] = "fixed"

                heartbeat_doc = {

                    "scanner": scanner,
                    "device": data["device"],
                    "firmware": data["firmware"],

                    "lastHeartbeatUnix": int(time.time()),
                    "lastSeen": datetime.now().isoformat(),

                    "uptime": data["uptime"],

                    "status": device_status[scanner]
                }

                db.collection("Devices").document(scanner).set(
                    heartbeat_doc,
                    merge=True
                )

                print(f"{scanner} heartbeat updated")

            # ----------------
            # TAMPER
            # ----------------

            elif data["type"] == "tamper":
                UniLED.tamper_alert()
                current_time = datetime.now()

                formatted_timestamp = current_time.strftime(
                    "%d %B %Y at %H:%M:%S UTC+2"
                )

                scanner = data["scanner"]

                # update status
                device_status[scanner] = "tampered"

                # ------------------------
                # Update Devices Collection
                # ------------------------

                db.collection("Devices").document(scanner).set({

                    "lastOpened": formatted_timestamp,
                    "status": "tampered"

                }, merge=True)

                # ------------------------
                # IT Logs
                # ------------------------

                it_log = {

                    "message": f"The case of {scanner} is exposed",

                    "timestamp": datetime.now()
                }

                db.collection("IT_Logs").add(it_log)

                print(f"TAMPER DETECTED: {scanner}")

            # ----------------
            # CASE CLOSED
            # ----------------

            elif data["type"] == "case_closed":
                UniLED.ready_scan()
                scanner = data["scanner"]

                device_status[scanner] = "fixed"

                db.collection("Devices").document(scanner).set({

                    "status": "fixed"

                }, merge=True)

                print(f"{scanner} case closed")

        except Exception as e:

            print("Error:", e)

    # --------------------
    # Timeout Detection
    # --------------------

    current_time = time.time()

    for scanner, last_seen in devices.items():

        elapsed = current_time - last_seen

        if elapsed > TIMEOUT:

            print(f"{scanner} heartbeat timeout")
            UniLED.heartbeat_lost()

    time.sleep(0.1)