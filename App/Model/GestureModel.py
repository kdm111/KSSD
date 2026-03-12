import mediapipe as mp
import cv2
import numpy as np
import os
import tensorflow as tf
import threading
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


MAX_HAND = 1
MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (255, 0, 0) # cv2에 보이는 라벨 색

class GestureModel:
    """KNN 모델 학습 및 추론 담당 (AI 로직)"""
    
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.lstm_path = './Model/test_lstm_model.h5'
        self.knn = None
        self.AIModel = tf.keras.models.load_model(self.lstm_path)
        self.reload()
        # --- 2. MediaPipe 설정 및 유틸리티 ---
        self.mp_hands = mp.tasks.vision.HandLandmarksConnections
        self.mp_drawing = mp.tasks.vision.drawing_utils
        self.mp_drawing_styles = mp.tasks.vision.drawing_styles

        self.base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        self.options = vision.HandLandmarkerOptions(base_options=self.base_options, num_hands=MAX_HAND)
        self.detector = vision.HandLandmarker.create_from_options(self.options)

        self.insert_signal = ''
        self.insert_new_data = [] # 실시간 랜드마크 앵글확인

        self.is_predicting = False
        self.still_frames = 0 # 초기화프레임
        self.sequence = [] # 카메라에서 받아오는 프레임
        self.seq_length = 10 # 몇개의 프레임으로 확인할 건지 
        self.current_label = ''
        self.action_length = 5 # 액션시퀀스를 몇개를 볼건지
        self.action_seq=[] # 모델이 예측한 라벨이 뭔지
        self.action = ['L','R','S'] # 모델에서 나오는 라벨 이름

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
            self.mp_drawing.draw_landmarks(
                annotated_image,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style())

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

            # 손목 회전 각도
            v_p1 = joint[[0, 0], :]   # 시작점: 손목, 손목
            v_p2 = joint[[5, 17], :]  # 끝점: 검지뿌리, 새끼뿌리
            v_palm = v_p2 - v_p1

            # 3. 외적(Cross Product)으로 손바닥 법선 벡터 계산
            # v_palm[0]은 손목->검지, v_palm[1]은 손목->새끼
            palm_normal = np.cross(v_palm[0], v_palm[1])
            palm_normal = palm_normal / np.linalg.norm(palm_normal)
            palm_normal = palm_normal * 500 # 가중치를 확실히줘서 어떻게 회전해 있는지 확인

            full_data = np.append(angle, palm_normal)
            full_data = np.append(full_data,hand_side)

            self.sequence.append(full_data)
            self.sequence = self.sequence[-self.seq_length:] 

            if hand_label == "Left": # 좌우반전기준 오른손
                if not self.is_predicting and len(self.sequence) == self.seq_length:
                    # 별도 스레드에서 돌려서 메인 루프(화면 출력)를 방해하지 않음
                    thread = threading.Thread(target=self.LSTM_Predict)
                    thread.daemon = True
                    thread.start()
                else:
                    self.current_label=''
            else:
                if len(self.action_seq) > self.action_length:
                    self.action_seq.pop(0)
                    
                self.action_seq.append(-1)
            

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
            
            if self.current_label != "":
                cv2.putText(annotated_image, f'{self.current_label}', (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

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

    def LSTM_Predict(self): # LSTM모델 예측
            self.is_predicting = True
            try:
                seq_np = np.array(self.sequence)

                # 각 프레임 간의 차이의 절대값 평균을 구함 (움직임 수치)
                motion_value = np.mean(np.abs(np.diff(seq_np, axis=0)))
                input_data = np.expand_dims(self.sequence, axis=0).astype(np.float32)

                if motion_value < 6 :
                    self.still_frames += 1
                    if self.still_frames > 5:
                        self.action_seq.append(-1)
                        self.current_label = "" 
                        if len(self.action_seq) > self.action_length: self.action_seq.pop(0)
                    return
                
                res = self.AIModel(input_data, training=False).numpy()[0]
                
                idx = np.argmax(res) # 가장 높은 확률의 인덱스 
                confidence = res[idx] # 해당 확률 값

                if confidence > 0.99 :
                    self.action_seq.append(idx)
                else:
                    self.action_seq.append(-1) # 확신 없으면 무효값(-1) 기록
                
                if len(self.action_seq) > self.action_length:
                    self.action_seq.pop(0)


                if len(self.action_seq) == self.action_length:
                    most_common = max(set(self.action_seq), key=self.action_seq.count)
                    if self.action_seq.count(most_common) >= self.action_length-1 and most_common != -1:
                        self.current_label = self.action[most_common]
                else:
                    self.current_label = "" # 셋 중 하나라도 다르거나 확신 없으면 빈값
            finally:
                self.is_predicting = False

    def reset_memory(self):
        self.sequence = []  # 기억 삭제
        self.current_label = ''
