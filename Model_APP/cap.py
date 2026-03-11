
import cv2
import threading

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
        while True:
            frame = self.display_frame if self.display_frame is not None else self.frame
            # check frame
            if frame is None: 
                continue
            # frame jpg
            _, buffer = cv2.imencode('.jpg', frame)  
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.cap.release()
