import cv2
import threading
import time
from ultralytics import YOLO


class Cap:
    def __init__(self, cam_num=0, model_path="yolov8n.pt"):
        self.cap = cv2.VideoCapture(cam_num)
        self.frame = None
        self.display_frame = None
        self.detections = []
        self.lock = threading.Lock()

        # YOLO
        self.model = YOLO(model_path)
        self.confidence_threshold = 0.5
        self.frame_skip = 3

        t = threading.Thread(target=self._update, daemon=True)
        t.start()

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

    def _update(self):
        frame_count = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue

            frame_count += 1
            detections = []

            if frame_count % self.frame_skip == 0:
                results = self.model(frame, verbose=False, conf=self.confidence_threshold, imgsz=320)

                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        label = self.model.names[cls_id]

                        bbox_height = y2 - y1
                        distance_cm = self._estimate_distance(bbox_height, frame.shape[0])

                        detections.append({
                            "label": label,
                            "confidence": round(conf, 3),
                            "distance_cm": distance_cm,
                            "bbox": [x1, y1, x2, y2],
                        })

                        color = (0, 0, 255) if distance_cm < 30 else (0, 255, 255) if distance_cm < 60 else (0, 255, 0)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, f"{label} {conf:.2f} ~{distance_cm}cm",
                                    (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            with self.lock:
                self.frame = frame
                if detections:
                    self.detections = detections

    def _estimate_distance(self, bbox_height, frame_height):
        ratio = bbox_height / frame_height
        if ratio > 0.8:
            return 10
        elif ratio > 0.5:
            return 20
        elif ratio > 0.3:
            return 40
        elif ratio > 0.15:
            return 70
        else:
            return 100

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def get_detections(self):
        with self.lock:
            return self.detections.copy()

    def set_frame(self, frame):
        with self.lock:
            self.frame = frame

    def set_display_frame(self, frame):
        with self.lock:
            self.display_frame = frame

    def generate(self):
        last_frame = None
        fps = 0
        fps_update_time = time.time()
        frame_count = 0
        while True:
            with self.lock:
                frame = self.display_frame if self.display_frame is not None else self.frame

            if frame is None:
                time.sleep(0.01)
                continue

            if frame is last_frame:
                time.sleep(0.001)
                continue
            last_frame = frame

            frame = frame.copy()
            frame_count += 1

            curr_time = time.time()
            if curr_time - fps_update_time >= 0.5:
                fps = frame_count / (curr_time - fps_update_time)
                frame_count = 0
                fps_update_time = curr_time

            cv2.putText(frame, f'FPS: {fps:.1f}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.cap.release()