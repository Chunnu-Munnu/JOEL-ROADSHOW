import cv2
from ultralytics import YOLO
import torch

# --- CONFIGURATION ---
PERSON_MODEL_PATH = 'models/yolov8n.pt'
POSE_MODEL_PATH = 'models/yolov8n-pose.pt'
WEAPON_MODEL_PATH = 'models/weapon_yolov8.pt'

# Use GPU if available, otherwise CPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")

try:
    # --- LOAD MODELS ---
    print("Loading models...")
    person_model = YOLO(PERSON_MODEL_PATH)
    pose_model = YOLO(POSE_MODEL_PATH)
    weapon_model = YOLO(WEAPON_MODEL_PATH)
    print("✅ Models loaded successfully!")

    # --- START VIDEO CAPTURE ---
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("Cannot open webcam")

    print("\n🚀 Starting live feed. Press 'q' to quit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        annotated_frame = frame.copy()

        # --- RUN INFERENCE (PERSON) ---
        person_results = person_model(frame, verbose=False, device=device)
        for res in person_results:
            for box in res.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_name = person_model.names[int(box.cls[0])]
                # Only draw target classes
                if cls_name in ['person', 'car', 'truck', 'bus', 'motorcycle', 'bicycle']:
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 0, 0), 2) # Blue for persons/vehicles
                    cv2.putText(annotated_frame, cls_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)


        # --- RUN INFERENCE (POSE) ---
        pose_results = pose_model(frame, verbose=False, device=device)
        for res in pose_results:
            # Check if keypoints are detected
            if res.keypoints and res.keypoints.xy is not None:
                for keypoints in res.keypoints.xy:
                    for x, y in keypoints:
                        if x > 0 and y > 0: # Draw only valid keypoints
                            cv2.circle(annotated_frame, (int(x), int(y)), 2, (0, 255, 0), -1) # Green for keypoints


        # --- RUN INFERENCE (WEAPON) ---
        weapon_results = weapon_model(frame, verbose=False, device=device)
        for res in weapon_results:
            for box in res.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_name = weapon_model.names[int(box.cls[0])]
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 2) # Red for weapons
                cv2.putText(annotated_frame, f"WEAPON: {cls_name}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)


        # --- DISPLAY THE FRAME ---
        cv2.imshow("Multi-Model Live Feed", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # --- CLEANUP ---
    cap.release()
    cv2.destroyAllWindows()
    print("Stream stopped.")

except Exception as e:
    print(f"❌ An error occurred: {e}")