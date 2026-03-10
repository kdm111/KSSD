import mediapipe as mp
import cv2
import numpy as np
import pandas as pd
import csv
import os
import time
import platform
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pynput import keyboard
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

MAX_HAND = 1
MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (255, 0, 0) # cv2에 보이는 라벨 색
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

class GestureModel:
    """KNN 모델 학습 및 추론 담당 (AI 로직)"""
    
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.knn = None
        self.reload()
        # --- 2. MediaPipe 설정 및 유틸리티 ---
        self.mp_hands = mp.tasks.vision.HandLandmarksConnections
        
        if hasattr(mp.tasks.vision, 'drawing_utils'):
            self.mp_drawing = mp.tasks.vision.drawing_utils
            self.mp_drawing_styles = mp.tasks.vision.drawing_styles
        else:
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles

        
        hand_landmarker_path = os.path.join(BASE_DIR, 'hand_landmarker.task')
        self.base_options = python.BaseOptions(model_asset_path=hand_landmarker_path)
        self.options = vision.HandLandmarkerOptions(base_options=self.base_options, num_hands=MAX_HAND)
        self.detector = vision.HandLandmarker.create_from_options(self.options)

        self.insert_signal = ''
        self.insert_new_data = [] # 실시간 랜드마크 앵글확인인

    def draw_landmarks_on_image(self,rgb_image, detection_result, gesture_names):
        hand_landmarks_list = detection_result.hand_landmarks
        handedness_list = detection_result.handedness
        
        annotated_image = np.copy(rgb_image)
        self.insert_signal = '' # 가장 최근에 손으로 인식하였을 때 나오는 문자

        for idx in range(len(hand_landmarks_list)):
            hand_landmarks = hand_landmarks_list[idx]
            hand_label = handedness_list[idx][0].category_name
            # handedness = handedness_list[idx] # 여기서는 필요없어서 잠시 주석

            # 왼손 오른손 판별
            hand_side = -1 
            if hand_label == "Right": # 좌우반전기준으로 해서
                hand_side = 0 # 왼손
            elif hand_label == "Left":
                hand_side = 1 # 오른손
            hand_side = hand_side * 100

            # 랜드마크 시각화
            if hasattr(mp.tasks.vision, 'drawing_utils'):
                self.mp_drawing.draw_landmarks(
                    annotated_image,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
            else:
                # Raspberry Pi - solutions API (NormalizedLandmarkList ȯ ʿ)
                from mediapipe.framework.formats import landmark_pb2
                
                hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                hand_landmarks_proto.landmark.extend([
                    landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z)
                    for lm in hand_landmarks
                ])
                
                self.mp_drawing.draw_landmarks(
                    annotated_image,
                    hand_landmarks_proto,
                    mp.solutions.hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )

            # 제스처 판정을 위한 각도 계산 (핵심 로직 추가)
            joint = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks])
            
            # 벡터 계산 (0-1, 1-2, 2-3... 관절 쌍)
            v1 = joint[[0,1,2,3,0,5,6,7,0,9,10,11,0,13,14,15,0,17,18,19],:] 
            v2 = joint[[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],:] 
            v = v2 - v1 
            v = v / np.linalg.norm(v, axis=1)[:, np.newaxis]

            # 각도 추출 (15개 주요 관절 사이의 각도)
            angle = np.arccos(np.einsum('nt,nt->n',
                v[[0,1,2,4,5,6,8,9,10,12,13,14,16,17,18],:], 
                v[[1,2,3,5,6,7,9,10,11,13,14,15,17,18,19],:])) 
            angle = np.degrees(angle) # Convert radian to degree
            full_data = np.append(angle, hand_side)

            threshold = 2000.0 # 손 제스처가 비슷함을 나타내는 임계값
            display_text = ""
            # KNN 추론
            if self.knn is not None:
                data = np.array([full_data], dtype=np.float32)
                ret, results, neighbours, dist = self.knn.findNearest(data, 3)
                idx = int(results[0][0])

                if dist[0][0] < threshold:
                    if idx in gesture_names:
                        display_text += f"{gesture_names[idx]}"
            
            # 텍스트 위치 선정 (바운딩 박스 상단)
            height, width, _ = annotated_image.shape
            x_coords = [landmark.x for landmark in hand_landmarks]
            y_coords = [landmark.y for landmark in hand_landmarks]
            text_x = int(min(x_coords) * width)
            text_y = int(min(y_coords) * height) - MARGIN

            if len(display_text)>0: # 특정 손동작이 감지되었을 때만 신호보내기
                self.insert_signal = display_text

            self.insert_new_data = full_data
            
            cv2.putText(annotated_image, display_text, (text_x, text_y), 
                        cv2.FONT_HERSHEY_DUPLEX, FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
            
        return annotated_image

    def reload(self):
        if os.path.exists(self.csv_path) and os.path.getsize(self.csv_path) > 0:
            file = np.genfromtxt(self.csv_path, delimiter=',')
            if file.ndim == 1: file = np.array([file])
            X = file[:, :-1].astype(np.float32)
            y = file[:, -1].astype(np.float32)
            self.knn = cv2.ml.KNearest_create()
            self.knn.train(X, cv2.ml.ROW_SAMPLE, y)
        else:
            self.knn = None

    def evaluate(self):
        file = np.genfromtxt('data_test.csv', delimiter=',')
        X = file[:, :-1].astype(np.float32) # 특징값 (각도 등)
        y = file[:, -1].astype(np.float32)  # 정답 (라벨)

        # 2. 데이터 쪼개기 (random_state를 주면 매번 똑같이 섞여서 비교하기 좋습니다)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 3. KNN 학습 (학습용 데이터만 사용!)
        self.knn = cv2.ml.KNearest_create()
        self.knn.train(X_train, cv2.ml.ROW_SAMPLE, y_train)

        # 4. 모델에게 시험 문제 내기 (테스트용 데이터 사용)
        # k=3은 주변 이웃 3개를 보고 판단하라는 뜻
        ret, results, neighbours, dist = self.knn.findNearest(X_test, k=3)
        
        # 5. 채점 (실제 정답 y_test와 모델의 답 results 비교)
        predicted_labels = results.flatten()
        final_score = accuracy_score(y_test, predicted_labels)

        print(f"--- 모델 성능 평가 ---")
        print(f"전체 데이터 개수: {len(X)}")
        print(f"학습 데이터 개수: {len(X_train)}")
        print(f"테스트 데이터 개수: {len(X_test)}")
        print(f"최종 검증 정확도: {final_score * 100:.2f}%")

