
import cv2
import threading
import time

class Cap:
    def __init__(self, cam_num):
        self.cap = cv2.VideoCapture(cam_num)
        self.frame = None
        self.lock = threading.Lock()
        self.display_frame = None

        t = threading.Thread(target=self._update, daemon=True)
        t.start()
        
    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

    def _update(self):
        while True:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
        
    def set_frame(self, frame):
        with self.lock:
            self.frame = frame

    def set_display_frame(self, frame):
        with self.lock:
            self.display_frame = frame

    def generate(self):
        prev_time = time.time()
        last_frame = None
        fps = 0
        fps_update_time = time.time()
        frame_count = 0
        frame_update_period_time = 0.5
        while True:
            with self.lock:
                frame = self.display_frame if self.display_frame is not None else self.frame
                # check frame
            if frame is None:
                time.sleep(0.01)
                continue
            # FPS 계산 및 오버레이
            # 이전 프레임과 동일하면 스킵 (새 프레임 올 때만 전송)
            if frame is last_frame:
                time.sleep(0.001)
                continue
            last_frame = frame

            frame = frame.copy()
            frame_count += 1

            curr_time = time.time()
            if curr_time - fps_update_time >= frame_update_period_time:
                fps = frame_count / (curr_time - fps_update_time)
                frame_count = 0
                fps_update_time = curr_time
            
            frame = frame.copy()
            cv2.putText(frame, f'FPS: {fps:.1f}', (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # frame jpg
            _, buffer = cv2.imencode('.jpg', frame)  
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.cap.release()
