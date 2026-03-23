from time import sleep

import numpy as np
import tensorflow as tf
import pickle
import threading
from copy import deepcopy


class Pre_DNN:
    def __init__(self):
        # 1. 모델 로드 (Interpreter 생성)
        self.interpreter = tf.lite.Interpreter(
            model_path="./Model/gesture_model.tflite"
        )
        self.interpreter.allocate_tensors()

        # 2. 입출력 텐서 정보 가져오기 (데이터를 넣고 뺄 위치 확인)
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # 3. Scaler는 기존과 동일하게 로드
        with open("./Model/gesture_scaler.pkl", "rb") as f:
            self.scaler = pickle.load(f)

        self.lock = threading.Lock()
        self._is_running = threading.Lock()
        self._stop_event = threading.Event()
        self._dnn_thread = None
        self._data = None
        self._pred = None

        self.start_dnn()

    def dnn_process(self):
        while not self._stop_event.is_set():
            with self.lock:
                data = self._data

            if not data:
                sleep(0.1)
                continue

            with self._is_running:
                pred = {}

                for k, v in data.items():
                    if k == 'center':
                        pred[k] = v
                        continue
                    x = np.array(v, dtype=np.float32).reshape(1, -1)
                    x = self.scaler.transform(x)
                    # x = np.array(v, dtype=np.float32).reshape(1, -1)
                    
                    
                    self.interpreter.set_tensor(self.input_details[0]["index"], x)
                    self.interpreter.invoke()
                    pred[k] = self.interpreter.get_tensor(
                        self.output_details[0]["index"]
                    )[0]

                with self.lock:
                    self._data = None

                self._pred = pred

            # --------------------------------

    def predict_gesture(self, feature):
        self._is_running.acquire()
        with self.lock:
            self._data = deepcopy(feature)
        pred = None if self._pred is None else self._pred.copy()
        self._pred = None

        self._is_running.release()
        return pred

    def start_dnn(self):
        if self._dnn_thread is None or not self._dnn_thread.is_alive():
            self._stop_event.clear()
            self._dnn_thread = threading.Thread(target=self.dnn_process, daemon=True)
            self._dnn_thread.start()

    def stop_dnn(self):
        self._stop_event.set()
        if self._dnn_thread is not None:
            self._dnn_thread.join()
