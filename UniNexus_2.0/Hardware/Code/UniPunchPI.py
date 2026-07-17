import cv2
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
import time
import UniLED

from security import validate_employee_qr

# --- NEW: GOOGLE SHEETS IMPORTS ---
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------
# Firebase & Sheets Setup
# ---------------------------
CRED_FILE = "uninexus-1aea7-firebase-adminsdk-fbsvc-91267f088c.json"

# 1. Initialize Firebase
cred = credentials.Certificate(CRED_FILE)
firebase_admin.initialize_app(cred)
db = firestore.client()

UniLED.initialize()
UniLED.booting()
time.sleep(2)

# 2. Initialize Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
sheets_creds = Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
gc = gspread.authorize(sheets_creds)

# PASTE YOUR GOOGLE SHEET ID HERE (From the URL)
SHEET_ID = "1B9ATIjF_c7q01fB4BuwDVlLHt41vYjdP5vZqJlLQ8Uo"
sh = gc.open_by_key(SHEET_ID)
daily_sheet = sh.worksheet("Daily_Logs")
summary_sheet = sh.worksheet("Monthly_Summary")

# Constants
SCAN_INTERVAL = 25
last_scans = {}

START_WORK = "09:00:00"
END_WORK = "17:00:00"

# ---------------------------
# Helpers
# ---------------------------

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

def parse_time_to_seconds(time_str):
    h, m, s = map(int, time_str.split(":"))
    return h*3600 + m*60 + s

def seconds_to_hms(total_seconds):
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

def to_datetime(time_str):
    return datetime.strptime(time_str, "%H:%M:%S")

def parse_qr(data):
    try:
        action, user_id = data.split("_")
        return action, user_id
    except:
        return None, None

def can_send(qr_data):
    current_time = time.time()
    if qr_data in last_scans:
        if current_time - last_scans[qr_data] < SCAN_INTERVAL:
            return False
    last_scans[qr_data] = current_time
    return True

# ---------------------------
# Employee Lookup
# ---------------------------

def find_employee(user_id):
    for col in ["staff", "faculty"]:
        docs = db.collection(col).where(
            filter=FieldFilter("ID", "==", user_id)
        ).stream()

        for doc in docs:
            data = doc.to_dict()
            return {
                "fName": data.get("fName", ""),
                "lName": data.get("lName", "")
            }
    return None

# ---------------------------
# Calculations
# ---------------------------

def calculate_metrics(punch_in, punch_out):
    start = to_datetime(START_WORK)
    end = to_datetime(END_WORK)

    late_arrival = (punch_in - start) if punch_in > start else timedelta(0)
    absence = late_arrival > timedelta(hours=1, minutes=30)

    diff = punch_out - end

    if diff.total_seconds() < 0:
        early_leave = abs(diff)
        overtime = timedelta(0)
    else:
        overtime = diff
        early_leave = timedelta(0)

    latency = abs((early_leave + late_arrival) - overtime)

    return {
        "latearrival": format_timedelta(late_arrival),
        "earlyleave": format_timedelta(early_leave),
        "overtime": format_timedelta(overtime),
        "latency": format_timedelta(latency),
        "absence": str(absence) # Convert boolean to string for Google Sheets
    }

def calculate_deduction(monthly_latency_str):
    h, m, s = map(int, monthly_latency_str.split(":"))
    hours = h + m/60 + s/3600

    if hours < 7: return 0.5
    elif hours < 11: return 1
    elif hours < 15: return 1.5
    elif hours < 18: return 2
    elif hours < 21: return 2.5
    elif hours < 24: return 3
    elif hours < 27: return 3.5
    elif hours < 30: return 4
    elif hours < 33: return 4.5
    elif hours < 36: return 5
    else: return 5.5

# ---------------------------
# Google Sheets Updaters
# ---------------------------

def update_daily_sheet(log_id, date, user_id, fname, lname, punchin, punchout, metrics=None):
    try:
        # Find if this specific day's log already exists in Column A
        cell = daily_sheet.find(log_id, in_column=3)
        
        if metrics is None:
            metrics = {"latearrival": "", "earlyleave": "", "overtime": "", "latency": "", "absence": ""}

        row_data = [
            fname, lname, log_id, date, user_id, punchin, punchout, 
            START_WORK, END_WORK, 
            metrics.get("latearrival", ""), metrics.get("earlyleave", ""), 
            metrics.get("overtime", ""), metrics.get("latency", ""), metrics.get("absence", "")
        ]

        if cell:
            # Update existing row (e.g., adding the punch-out time)
            # A = col 1, N = col 14
            cell_range = f"A{cell.row}:N{cell.row}"
            daily_sheet.update(range_name=cell_range, values=[row_data])
        else:
            # Append new row (First punch-in of the day)
            daily_sheet.append_row(row_data)
    except Exception as e:
        print(f"Sheets Daily Log Error: {e}")

def update_summary_sheet(user_id, fname, lname, monthly_latency, monthly_overtime, deduction):
    try:
        # Find if employee summary already exists in Column A
        cell = summary_sheet.find(user_id, in_column=1)
        row_data = [fname, lname, user_id, monthly_latency, monthly_overtime, deduction]

        if cell:
            # Update existing employee stats
            # A = col 1, F = col 6
            cell_range = f"A{cell.row}:F{cell.row}"
            summary_sheet.update(range_name=cell_range, values=[row_data])
        else:
            # Append new employee
            summary_sheet.append_row(row_data)
    except Exception as e:
        print(f"Sheets Summary Error: {e}")

# ---------------------------
# Core Logic
# ---------------------------

def handle_employee_scan(action, user_id):

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M:%S")

    log_doc_id = f"{user_id}_{today}"  # daily log
    main_doc_id = user_id              # single doc

    employee = find_employee(user_id)
    if not employee:
        print(f"Employee {user_id} not found")
        return

    main_ref = db.collection("EmpAttend").document(main_doc_id)
    log_ref = db.collection("employees_logs").document(log_doc_id)

    main_doc = main_ref.get()
    main_data = main_doc.to_dict() if main_doc.exists else {}

    log_doc = log_ref.get()
    log_data = log_doc.to_dict() if log_doc.exists else {}

    # ---------- IN ----------
    if action == "IN":

        # 1. Update Firebase
        log_ref.set({
            "ID": user_id,
            "fName": employee["fName"],
            "lName": employee["lName"],
            "date": today,
            "punchin": now_time,
            "startwork": START_WORK,
            "endwork": END_WORK
        }, merge=True)

        # 2. Update Google Sheets Daily Log
        # If they punch in multiple times, it updates the same row with the new punchin time
        update_daily_sheet(
            log_id=log_doc_id, date=today, user_id=user_id, 
            fname=employee["fName"], lname=employee["lName"], 
            punchin=now_time, punchout=log_data.get("punchout", "")
        )

        print(f"{user_id} IN at {now_time}")

    # ---------- OUT ----------
    elif action == "OUT":

        if "punchin" not in log_data:
            print(f"No punch-in found for {user_id} today. Cannot process OUT.")
            return

        punch_in_time = to_datetime(log_data["punchin"])
        punch_out_time = to_datetime(now_time)

        metrics = calculate_metrics(punch_in_time, punch_out_time)

        # 1. Save daily log to Firebase
        log_ref.set({
            **log_data,
            "punchout": now_time,
            **metrics
        }, merge=True)

        # 2. Save daily log to Google Sheets
        update_daily_sheet(
            log_id=log_doc_id, date=today, user_id=user_id, 
            fname=employee["fName"], lname=employee["lName"], 
            punchin=log_data["punchin"], punchout=now_time, metrics=metrics
        )

        # ---- INCREMENT MONTHLY ---- #
        prev_latency = parse_time_to_seconds(main_data.get("monthlyLatency", "00:00:00"))
        prev_overtime = parse_time_to_seconds(main_data.get("monthlyOvertime", "00:00:00"))

        today_latency = parse_time_to_seconds(metrics["latency"])
        today_overtime = parse_time_to_seconds(metrics["overtime"])

        new_latency = prev_latency + today_latency
        new_overtime = prev_overtime + today_overtime

        monthly_latency = seconds_to_hms(new_latency)
        monthly_overtime = seconds_to_hms(new_overtime)

        deduction = calculate_deduction(monthly_latency)

        # 3. Update main doc in Firebase
        main_ref.set({
            "ID": user_id,
            "fName": employee["fName"],
            "lName": employee["lName"],
            "monthlyLatency": monthly_latency,
            "monthlyOvertime": monthly_overtime,
            "deduction": deduction
        }, merge=True)

        # 4. Update Monthly Summary in Google Sheets
        update_summary_sheet(
            user_id=user_id, fname=employee["fName"], lname=employee["lName"], 
            monthly_latency=monthly_latency, monthly_overtime=monthly_overtime, deduction=deduction
        )

        print(f"{user_id} OUT at {now_time}")
        print("Latency:", monthly_latency)
        print("Overtime:", monthly_overtime)

# ---------------------------
# Scanner
# ---------------------------
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

print("UniPunch Scanner Started... Press X to exit")
UniLED.ready_scan()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera error")
        UniLED.heartbeat_lost()
        break

    data, bbox, _ = detector.detectAndDecode(frame)

    if bbox is not None and data:
        UniLED.qr_detected()
        time.sleep(0.15)

        if can_send(data):
            result = validate_employee_qr(data)

            if result:
                action, user_id = result
                handle_employee_scan(action, user_id)
                UniLED.access_granted()
            else:
                print("INVALID QR")
                UniLED.access_denied()
        else:
            UniLED.ready_scan()

        points = bbox[0].astype(int)
        for i in range(4):
            cv2.line(frame,
                     tuple(points[i]),
                     tuple(points[(i + 1) % 4]),
                     (0,255,0), 3)

        cv2.putText(frame, data,
                    (points[0][0], points[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0,255,0), 2)

    cv2.imshow("UniPunch Scanner", frame)

    if cv2.waitKey(1) & 0xFF == ord('x'):
        break
UniLED.turn_off()
cap.release()
cv2.destroyAllWindows()