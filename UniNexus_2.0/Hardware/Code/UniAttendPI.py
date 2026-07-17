import cv2
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import time
import re
import requests
import json

from security import validate_student_qr
from security import validate_session_qr

# PASTE YOUR GOOGLE APPS SCRIPT WEBHOOK URL HERE
GOOGLE_SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbw7CLkSg1wmzUdXEr3Mufbj7ZGflJf_C-V1PiX9Pa9sJN1jkTSfl4cb933lK2C1_P4/exec"

# ---------------- Scanner Config ---------------- #
# Hardcode the location of this specific scanner device
HALL_BUILDING = "A"
HALL_CODE = "101"


# ---------------- Firebase ---------------- #
cred = credentials.Certificate("uninexus-1aea7-firebase-adminsdk-fbsvc-91267f088c.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- Session State ---------------- #
session_active = False
current_session = None

last_scan_time = 0
FRAME_COOLDOWN = 0.2

student_last_scan = {}
SCAN_COOLDOWN = 30

session_students = {}

# ---------------- Week Logic (TIME-BASED) ---------------- #

def get_week(course_id, session_type):
    doc_ref = db.collection("system").document(course_id)
    doc = doc_ref.get()

    today = datetime.now()

    if not doc.exists:
        doc_ref.set({
            "LecWeek": 1,
            "SecWeek": 1,
            "LecDate": today.strftime("%Y-%m-%d"),
            "SecDate": today.strftime("%Y-%m-%d")
        })
        return 1

    data = doc.to_dict()

    if session_type == "L":
        last_date_str = data.get("LecDate")
        current_week = data.get("LecWeek", 1)
    else:
        last_date_str = data.get("SecDate")
        current_week = data.get("SecWeek", 1)

    if not last_date_str:
        return current_week

    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")

    if (today - last_date).days >= 7:
        return current_week + 1
    else:
        return current_week

def update_week(course_id, session_type, week):
    today_str = datetime.now().strftime("%Y-%m-%d")
    doc_ref = db.collection("system").document(course_id)

    if session_type == "L":
        doc_ref.set({
            "LecWeek": week,
            "LecDate": today_str
        }, merge=True)
    else:
        doc_ref.set({
            "SecWeek": week,
            "SecDate": today_str
        }, merge=True)

# ---------------- Gate Check ---------------- #

def checked_in_today(student_id):
    today = datetime.now().strftime("%Y-%m-%d")

    scans = db.collection("gate_scans") \
        .where("id", "==", student_id) \
        .where("date", "==", today) \
        .where("status", "==", "allowed") \
        .stream()

    for _ in scans:
        return True

    return False

def get_student_name_from_gate(student_id):
    today = datetime.now().strftime("%Y-%m-%d")

    scans = db.collection("gate_scans") \
        .where("id", "==", student_id) \
        .where("date", "==", today) \
        .where("status", "==", "allowed") \
        .stream()

    for doc in scans:
        data = doc.to_dict()
        return data.get("name", "Unknown")

    return "Unknown"

# ---------------- Helpers ---------------- #

def normalize_qr_data(data):
    return "".join(c for c in data.strip() if c.isprintable())

def normalize_student_id(student_id):
    return re.sub(r"\s+", "", student_id).upper()

def can_process_student(student_id):
    now = time.time()
    if student_id in student_last_scan:
        if now - student_last_scan[student_id] < SCAN_COOLDOWN:
            return False
    student_last_scan[student_id] = now
    return True

def parse_session_qr(data):
    try:
        course_id, session_type, duration, instructor_id = data.split("_")
        duration = int(duration.lower().replace("min", ""))
        return course_id.upper(), session_type.upper(), duration, instructor_id.upper()
    except:
        return None, None, None, None

def calculate_marks(start, complete):
    if start == "on time" and complete:
        return 1
    elif start == "late" and complete:
        return 0.5
    return 0

def get_doc_ref(course_id, student_id):
    week = current_session["week"]
    return db.collection(f"{course_id}_attend").document(f"{student_id}_Week{week}")

def initialize_doc(doc_ref, student_id):
    if doc_ref.get().exists:
        return

    doc_ref.set({
        "ID": student_id,
        "InstructorID": "",
        "Name":"",
        "LecStart": "DNA",
        "LecComplete": False,
        "LecMarks": 0,
        "LecDate": None,
        "SecStart": "DNA",
        "SecComplete": False,
        "SecMarks": 0,
        "SecDate": None
    })

def get_last_attendance(course_id, student_id, field):
    docs = db.collection(f"{course_id}_attend").stream()
    latest = None

    for doc in docs:
        data = doc.to_dict()
        if data.get("ID") != student_id:
            continue

        date_str = data.get(field)
        if not date_str:
            continue

        d = datetime.strptime(date_str, "%Y-%m-%d")
        if not latest or d > latest:
            latest = d

    return latest

# --- NEW: Update Hall Availability ---
def update_hall_availability(is_available):
    """Updates the isAvailable boolean for the hardcoded hall in Firestore"""
    try:
        # Search for the hall document matching the hardcoded building and code
        halls_query = db.collection("halls") \
            .where("building", "==", HALL_BUILDING) \
            .where("hallCode", "==", HALL_CODE) \
            .stream()
            
        updated = False
        for doc in halls_query:
            doc.reference.update({"isAvailable": is_available})
            updated = True
            print(f"[*] Hall {HALL_BUILDING} {HALL_CODE} isAvailable set to: {is_available}")
            
        if not updated:
            print(f"[!] Warning: Could not find Hall {HALL_BUILDING} {HALL_CODE} in Firestore.")
            
    except Exception as e:
        print(f"[!] Error updating hall availability: {e}")

# ---------------- Core Logic ---------------- #

def handle_start_scan(student_id):
    course_id = current_session["courseID"]
    session_type = current_session["type"]
    student_name = get_student_name_from_gate(student_id)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # GATE CHECK
    if not checked_in_today(student_id):
        print("Blocked (no gate entry):", student_id)
        return

    # 5-DAY RULE
    field = "LecDate" if session_type == "L" else "SecDate"
    last = get_last_attendance(course_id, student_id, field)

    if last and (now - last).days < 5:
        print("Blocked (5-day rule):", student_id)
        return

    # WEEK ASSIGNMENT
    if current_session["week"] is None:
        week = get_week(course_id, session_type)
        current_session["week"] = week
        update_week(course_id, session_type, week)

    doc_ref = get_doc_ref(course_id, student_id)
    initialize_doc(doc_ref, student_id)

    status = "on time" if now <= current_session["end_time"] else "late"

    if session_type == "L":
        doc_ref.set({
            "ID": student_id,
            "Name": student_name,
            "InstructorID": current_session["instructorID"],
            "LecStart": status,
            "LecDate": today
        }, merge=True)

    else:
        doc_ref.set({
            "ID": student_id,
            "Name": student_name,
            "InstructorID": current_session["instructorID"],
            "SecStart": status,
            "SecDate": today
        }, merge=True)

    print(student_id, "START →", status)

def mark_attendance_in_sheets(student_id, student_name, tab_name, column_header, instructor_id, mark):
    try:
        payload = {
            "studentId": student_id,
            "studentName": student_name, 
            "tabName": tab_name,
            "columnHeader": column_header,
            "instructorId": instructor_id,
            "mark": mark
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            GOOGLE_SHEET_WEBHOOK_URL, 
            data=json.dumps(payload), 
            headers=headers
        )

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "Success":
                pass 
            else:
                print(f"GOOGLE SCRIPT ERROR: {response_data.get('message')}")
        else:
            print(f"HTTP ERROR: Failed to reach Google. Status Code: {response.status_code}")

    except Exception as e:
        print(f"PYTHON HARDWARE ERROR: {e}")

def handle_end_scan(student_id):
    course_id = current_session["courseID"]
    session_type = current_session["type"]
    instructor_id = current_session["instructorID"]
    week_number = current_session["week"]

    doc_ref = get_doc_ref(course_id, student_id)
    doc = doc_ref.get()
    if not doc.exists:
        return

    data = doc.to_dict()
    student_name = data.get("Name", "Unknown")

    if session_type == "L":
        marks = calculate_marks(data.get("LecStart"), True)
        doc_ref.set({"LecComplete": True, "LecMarks": marks}, merge=True)
    else:
        marks = calculate_marks(data.get("SecStart"), True)
        doc_ref.set({"SecComplete": True, "SecMarks": marks}, merge=True)

    tab_name = f"{course_id} - {session_type}" 
    column_header = f"Week {week_number}"

    mark_attendance_in_sheets(student_id, student_name, tab_name, column_header, instructor_id, marks)

    print(f"{student_id} ({student_name}) END → completed. Mark: {marks}")

# ---------------- Scanner ---------------- #

cap = cv2.VideoCapture(
    "libcamerasrc ! video/x-raw,width=800,height=600,framerate=30/1 ! videoconvert ! appsink",
    cv2.CAP_GSTREAMER
)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

detector = cv2.QRCodeDetector()

print(f"UniAttend Scanner Started for Hall {HALL_BUILDING} {HALL_CODE}... Press X to exit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    data, bbox, _ = detector.detectAndDecode(frame)

    if bbox is not None and data:
        data = normalize_qr_data(data)
        now_time = time.time()

        if now_time - last_scan_time >= FRAME_COOLDOWN:

            session_data = validate_session_qr(data)

            if session_data:

                course_id, session_type, duration, instructor_id = session_data

                now = datetime.now()

                current_session = {
                    "courseID": course_id,
                    "type": session_type,
                    "instructorID": instructor_id,
                    "start_time": now,
                    "end_time": now + timedelta(minutes=duration),
                    "week": None
                }

                session_active = True
                student_last_scan.clear()
                session_students.clear()

                print("[SECURITY] Session QR Valid")
                print("Session started:", current_session)

                update_hall_availability(False)

            else:

                student_id = validate_student_qr(data)

                if session_active and student_id and can_process_student(student_id):

                    state = session_students.get(student_id, 0)

                    if state == 0:
                        handle_start_scan(student_id)
                        session_students[student_id] = 1

                    elif state == 1:
                        handle_end_scan(student_id)
                        session_students[student_id] = 2
            last_scan_time = now_time

        # Draw QR
        pts = bbox[0].astype(int)
        for i in range(4):
            cv2.line(frame, tuple(pts[i]), tuple(pts[(i+1)%4]), (0,255,0), 3)

        cv2.putText(frame, data, (pts[0][0], pts[0][1]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

    # UI
    if session_active:
        remaining = int((current_session["end_time"] - datetime.now()).total_seconds())
        timer = "Session Ended" if remaining <= 0 else f"{remaining//60:02}:{remaining%60:02}"

        cv2.putText(frame, f"{current_session['courseID']} {current_session['type']}",
                    (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

        cv2.putText(frame, f"Time Left: {timer}",
                    (20,80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

    cv2.imshow("UniAttend Scanner", frame)

    if cv2.waitKey(1) & 0xFF == ord('x'):
        # --- NEW: Free the hall when the program is manually closed ---
        print("Shutting down scanner...")
        update_hall_availability(True)
        break

cap.release()
cv2.destroyAllWindows()