import cv2
import json
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime
from security import secure_validate
import time
import UniLED

cred = credentials.Certificate("uninexus-1aea7-firebase-adminsdk-fbsvc-91267f088c.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

UniLED.initialize()
UniLED.booting()
time.sleep(2)

SCAN_INTERVAL = 25
last_scans = {}

SCANNER_ID = "scanner_G01"
SCANNER_ROLE = "main_gate"

# ---------------- Firestore ---------------- #
def send_to_firestore(user_id, status, note, user_type, user_name, faculty, year, photo):
    log = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "id": user_id,
        "name": user_name,
        "type": user_type,
        "status": status,
        "faculty": faculty,
        "year": year,
        "note": note,
        "photo": photo  
    }

    db.collection("gate_scans").add(log)

# ---------------- Anti-spam ---------------- #
def can_send(qr_data):
    current_time = time.time()

    if qr_data in last_scans:
        elapsed = current_time - last_scans[qr_data]
        if elapsed < SCAN_INTERVAL:
            print("Duplicate scan ignored")
            return False

    last_scans[qr_data] = current_time
    return True

# ---------------- Access Check ---------------- #
def check_access(student_id):
    students_ref = db.collection("students")
    query = students_ref.where(
        filter=FieldFilter("ID", "==", student_id)
    ).stream()

    for doc in query:
        data = doc.to_dict()

        user_name = data.get("fName", "") + " " + data.get("lName", "")
        user_type = "student"

        faculty = data.get("faculty", "unknown")
        year = data.get("year", "unknown")
        note = data.get("note", "")
        photo = data.get("photo", "")  # 🔥 NEW

        if data.get("entry") == True:
            return "allowed", note, user_type, user_name, faculty, year, photo
        else:
            return "denied", note, user_type, user_name, faculty, year, photo

    return "denied", "User not found", "unknown", "Unknown User", "unknown", "unknown", ""

# ---------------- Local Logging ---------------- #
def log_entry(user_id, status, note, user_type, user_name, faculty, year, photo):
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = "logs"
    file_path = f"{log_dir}/{SCANNER_ID}_{today}.json"

    log = {
        "date": today,
        "time": datetime.now().strftime("%H:%M:%S"),
        "id": user_id,
        "name": user_name,
        "type": user_type,
        "status": status,
        "faculty": faculty,
        "year": year,
        "note": note,
        "photo": photo  
    }

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            data = json.load(file)
    else:
        data = {
            "scannerID": SCANNER_ID,
            "scannerRole": SCANNER_ROLE,
            "logs": []
        }

    data["logs"].append(log)

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

# ---------------- Scanner ---------------- #
cap = cv2.VideoCapture(
    "libcamerasrc ! video/x-raw,width=800,height=600,framerate=30/1 ! videoconvert ! appsink",
    cv2.CAP_GSTREAMER
)

if not cap.isOpened():
    print("Failed to open camera")
    UniLED.heartbeat_lost()
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
detector = cv2.QRCodeDetector()

print("Scanner started... Press X to exit")
UniLED.ready_scan()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera error")
        UniLED.heartbeat_lost()
        break

    data, bbox, _ = detector.detectAndDecode(frame)

    if bbox is not None and data:
        print("QR detected:", data)
        UniLED.qr_detected()
        time.sleep(0.15)

        if can_send(data):
            student_id = secure_validate(data)
            if student_id:
                print("Validated Student:", student_id)
                status, note, user_type, user_name, faculty, year, photo = check_access(student_id)

                if status == "allowed":
                    UniLED.access_granted()
                else:
                    UniLED.access_denied()

                log_entry(student_id, status, note, user_type, user_name, faculty, year, photo)

                send_to_firestore(student_id, status, note, user_type, user_name, faculty, year, photo)
            else:
                print("INVALID QR")
                UniLED.access_denied()

        points = bbox[0].astype(int)
        for i in range(4):
            pt1 = tuple(points[i])
            pt2 = tuple(points[(i + 1) % 4])
            cv2.line(frame, pt1, pt2, (0, 255, 0), 3)

        cv2.putText(frame, data,
                    (points[0][0], points[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 255, 0), 2)

    cv2.imshow("UniNexus Scanner", frame)

    if cv2.waitKey(1) & 0xFF == ord('x'):
        break

UniLED.turn_off()
cap.release()
cv2.destroyAllWindows()