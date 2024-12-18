import cv2
import pandas as pd
import numpy as np
from ultralytics import YOLO
from tracker import *
import cvzone
import datetime
import os
import time
import csv
import sys
import threading
import asyncio
import websockets
import json
import logging
import traceback

# WebSocket Manager
class WebSocketManager:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.websocket = None
        self.connected = False
        self._connect_thread = None
        self.lock = threading.Lock()

    def start_connection(self):
        """Start a background thread to maintain WebSocket connection"""
        self._connect_thread = threading.Thread(target=self._run_connection_loop, daemon=True)
        self._connect_thread.start()

    def _run_connection_loop(self):
        """Run the async connection loop in a separate thread"""
        asyncio.run(self._maintain_connection())

    async def _maintain_connection(self):
        """Continuously try to maintain a WebSocket connection"""
        while True:
            try:
                uri = f'ws://{self.host}:{self.port}'
                logging.info(f"Attempting to connect to {uri}")
                async with websockets.connect(uri) as websocket:
                    self.websocket = websocket
                    self.connected = True
                    logging.info(f"WebSocket connection established to {uri}")
                    
                    # Keep connection open and log any incoming messages
                    async for message in websocket:
                        logging.debug(f"Received message: {message}")
                    
            except Exception as e:
                logging.error(f"WebSocket connection error: {e}")
                logging.error(traceback.format_exc())
                self.connected = False
                self.websocket = None
            
            # Wait before attempting to reconnect
            await asyncio.sleep(5)

    def send_counts(self, day_count, existing_count, is_monitoring=False):
        """Send counts via WebSocket with detailed logging"""
        if not self.connected or not self.websocket:
            logging.warning("WebSocket not connected. Cannot send counts.")
            return

        async def _async_send():
            try:
                message = json.dumps({
                    'day_count': day_count,
                    'existing_count': existing_count,
                    'is_monitoring': is_monitoring
                })
                logging.info(f"Attempting to send message: {message}")
                await self.websocket.send(message)
                logging.info(f"Successfully sent counts: Day={day_count}, Existing={existing_count}")
            except Exception as e:
                logging.error(f"WebSocket send error: {e}")
                logging.error(traceback.format_exc())

        # Run async send in a thread
        threading.Thread(
            target=lambda: asyncio.run(_async_send()), 
            daemon=True
        ).start()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize WebSocket manager
ws_manager = WebSocketManager()
ws_manager.start_connection()

# Monitoring Log Functions
def get_monitoring_log_file():
    os.makedirs('logs', exist_ok=True)
    filename = f'logs/monitoring_timestamps.csv'
    
    if not os.path.exists(filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Event", "Count", "Monitoring_Active"])
    
    return filename

# Global variable to track monitoring state
is_monitoring = False

def log_monitoring_event(event, count):
    global is_monitoring
    filename = get_monitoring_log_file()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, event, count, is_monitoring])

# Modify send_counts function
def send_counts(day_count, existing_count):
    global is_monitoring
    ws_manager.send_counts(day_count, existing_count, is_monitoring)

# Function to get or create daily count file
def get_daily_count_file():
    os.makedirs('counts', exist_ok=True)
    filename = f'counts/daily_count.csv'
    
    if not os.path.exists(filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Total_Count", "Existing_count"])
    
    return filename

# Function to read existing day count from CSV
def read_existing_day_count(filename):
    try:
        with open(filename, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            rows = list(reader)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
            # Check if the last row's date matches today's date
            for row in reversed(rows):
                if len(row) >= 2 and len(row[0]) >= 10:
                    row_date = row[0][:10]  # Extract date part (YYYY-MM-DD)
                    if row_date == timestamp:
                        try:
                            return int(row[1])  # Return the count for today
                        except (ValueError, IndexError):
                            break
    except (FileNotFoundError, IndexError):
        pass
    
    return 0

def read_existing_count(filename):
    try:
        with open(filename, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            rows = list(reader)
            if rows:
                if rows and datetime.datetime.strptime(rows[-1][0][:10], "%Y-%m-%d").date() == datetime.date.today():       
                    return int(rows[-1][2])  # Return the existing count 
    except (FileNotFoundError, IndexError):
        pass
    
    return 0

# Function to log count
def log_count(filename, day_count, existing_count):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, 'r', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    # Remove last row if it's from today
    if len(rows)>1:
        if rows and datetime.datetime.strptime(rows[-1][0][:10], "%Y-%m-%d").date() == datetime.date.today():
            rows = rows[:-1]
    
    # Add new row
    rows.append([timestamp, str(day_count), str(existing_count)])
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

# Initialize YOLO model
model = YOLO('yolov8s.pt')

# Open webcam (0 is usually the default camera)
cap = cv2.VideoCapture(0)

# Set camera resolution (optional, adjust as needed)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1020)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 500)

# Optional: Video writer if you want to save the output
output = cv2.VideoWriter('output_webcam.avi', 
                         cv2.VideoWriter_fourcc(*'MPEG'), 
                         30, 
                         (1020, 500))

# Read COCO class names
with open('coco.names', 'r') as file:
    class_list = file.read().strip().split('\n')

# Tracking and counting variables
count = 0
tracker = Tracker()
tracked_persons = {}

# Get today's count file
daily_count_file = get_daily_count_file()

# Read existing day count if available
day_count = read_existing_day_count(daily_count_file)
existing_count = read_existing_count(daily_count_file)  # Initialize total count with existing day count
send_counts(day_count, existing_count)

# Set end time for daily counting (10:00 PM)
end_time = datetime.datetime.now().replace(hour=23, minute=1, second=0, microsecond=0)

# Crossing line coordinates
cy1 = 194  # Upper line
cy2 = 220  # Lower line
offset = 6

# Create window 
cv2.namedWindow('Webcam People Counter')

while True:
    # Check current time for daily logging
    current_time = datetime.datetime.now()
    if current_time >= end_time:
        # Log final count for the day
        log_count(daily_count_file, day_count, existing_count)
        print(f"Daily count logging completed. Total count: {day_count}")
        break
    
    # Capture frame from webcam
    ret, frame = cap.read()
    
    if not ret:
        break
    
    # Resize frame
    frame = cv2.resize(frame, (1020, 500))
    
    # Skip frames for performance (process every 3rd frame)
    count += 1
    if count % 3 != 0:
        continue
    
    # Detect people using YOLO
    results = model.predict(frame)
    
    # Convert detections to DataFrame
    a = results[0].boxes.data
    px = pd.DataFrame(a).astype("float")
    
    # List to store person detections
    list_detections = []
    
    # Process detections
    for index, row in px.iterrows():
        x1, y1 = int(row[0]), int(row[1])
        x2, y2 = int(row[2]), int(row[3])
        d = int(row[5])
        
        c = class_list[d]
        if 'person' in c:
            list_detections.append([x1, y1, x2, y2])
    
    # Update tracker
    bbox_id = tracker.update(list_detections)
    
    # Process tracked objects
    for bbox in bbox_id:
        x3, y3, x4, y4, id = bbox
        cx = int((x3 + x4) // 2)
        cy = int((y3 + y4) // 2)
        
        # Draw center point
        cv2.circle(frame, (cx, cy), 4, (255, 0, 255), -1)
        
        # Check if person is in tracking dictionary
        if id not in tracked_persons:
            tracked_persons[id] = {'state': None}
        
        # Downward movement detection (increment count)
        if (cy1 < (cy + offset) and (cy1 > cy - offset)):
            if tracked_persons[id]['state'] != 'down':
                # Only increment if not already counted this way
                existing_count += 1
                day_count +=1
                send_counts(day_count, existing_count)
                log_monitoring_event("Increment", existing_count)
                tracked_persons[id]['state'] = 'down'
                print(f"Increment count. Current count: {existing_count}")
            
            cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 0, 255), 2)
            cvzone.putTextRect(frame, f'{id}', (x3, y3), 1, 2)
        
        # Upward movement detection (decrement count)
        if (cy2 < (cy + offset) and (cy2 > cy - offset)):
            if tracked_persons[id]['state'] != 'up':
                # Only decrement if not already counted this way
                existing_count = max(0, existing_count - 1)
                send_counts(day_count, existing_count)
                log_monitoring_event("Decrement", existing_count)
                tracked_persons[id]['state'] = 'up'
                print(f"Decrement count. Current count: {existing_count}")
            
            cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 255, 0), 2)
            cvzone.putTextRect(frame, f'{id}', (x3, y3), 1, 2)
    
    # Draw crossing lines
    cv2.line(frame, (3, cy1), (1018, cy1), (0, 255, 0), 2)
    cv2.line(frame, (5, cy2), (1019, cy2), (0, 255, 255), 2)
    
    # Display current count and end time
    time_left = end_time - current_time
    cvzone.putTextRect(frame, f'Count: {existing_count}', (40, 200), 2, 2)
    cvzone.putTextRect(frame, f'Day Count: {day_count}', (50, 60), 2, 2)
    cvzone.putTextRect(frame, f'Time Left: {time_left}', (50, 100), 2, 2)
    
    # Add monitoring status to frame
    monitoring_text = "Monitoring: ON" if is_monitoring else "Monitoring: OFF"
    cvzone.putTextRect(frame, monitoring_text, (50, 140), 2, 2)
    
    # Write output video (optional)
    output.write(frame)
    
    # Display frame
    cv2.imshow('Webcam People Counter', frame)
    
    # Exit on ESC key (manual override)
    key = cv2.waitKey(1) & 0xff
    if key == 27:
        log_count(daily_count_file, day_count, existing_count)
        send_counts(day_count, existing_count)
        break
    elif key == ord('m'):  # Press 'm' to toggle monitoring
        is_monitoring = not is_monitoring
        print(f"Monitoring {'activated' if is_monitoring else 'deactivated'}")

# Cleanup
cap.release()
output.release()
cv2.destroyAllWindows()
