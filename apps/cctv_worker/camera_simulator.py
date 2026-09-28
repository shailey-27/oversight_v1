import cv2
from ultralytics import YOLO
import requests
import time
import sys

# Configuration
API_URL = "http://localhost:8000/api/v1/institutions/{}/occupancy"
INSTITUTION_ID = "replace_with_actual_id"  # Replace with a real ID later
VIDEO_SOURCE = "sample.mp4" # Or 0 for webcam
PROCESS_EVERY_N_FRAMES = 30 # Process 1 frame every 30 frames (e.g., 1 per second)

def main():
    if len(sys.argv) > 1:
        global INSTITUTION_ID
        INSTITUTION_ID = sys.argv[1]
    
    print("Loading YOLOv8 Nano model...")
    # This will automatically download yolov8n.pt if not found locally
    model = YOLO("yolov8n.pt") 
    
    print(f"Opening video stream: {VIDEO_SOURCE}")
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    
    if not cap.isOpened():
        print(f"Error: Could not open video source {VIDEO_SOURCE}")
        print("Please ensure you have a video file named sample.mp4 in this folder, or change VIDEO_SOURCE to 0 for webcam.")
        return

    frame_count = 0
    
    print("Starting CCTV Simulation. Press 'q' to quit.")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("End of video stream or error. Looping...")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        frame_count += 1
        
        # Only process every N frames to save CPU and simulate sampling
        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            # Run YOLOv8 inference on the frame
            # classes=[0] filters results to ONLY detect 'person'
            results = model(frame, classes=[0], verbose=False)
            
            # Count the number of bounding boxes (people)
            person_count = len(results[0].boxes)
            
            # Prepare payload for backend
            payload = {
                "estimated_count": person_count,
                "confidence_score": 0.95,
                "method": "opencv_headcount"
            }
            
            # Send to backend
            if INSTITUTION_ID != "replace_with_actual_id":
                url = API_URL.format(INSTITUTION_ID)
                try:
                    response = requests.post(url, json=payload)
                    if response.status_code == 200:
                        print(f"SUCCESS: Transmitted {person_count} people detected to backend.")
                    else:
                        print(f"FAILED: Backend returned {response.status_code}")
                except Exception as e:
                    print(f"ERROR: Could not connect to backend - {e}")
            else:
                print(f"[DRY RUN] Detected: {person_count} people (Set INSTITUTION_ID to transmit)")

            # Draw bounding boxes on the frame to show the user
            annotated_frame = results[0].plot()
            
            # Add timestamp and count text
            cv2.putText(annotated_frame, f"Occupancy: {person_count}", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            cv2.imshow("Fake CCTV AI Pipeline", annotated_frame)
            
        # Break loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
