import mediapipe as mp
import cv2
import numpy as np
import pandas as pd
import csv
import os
import time
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

class TimeManager: # 타이머 클래스
    def __init__(self):
        self.last_times = {}

    def is_time_up(self, name, interval):
        now = time.time()
        # 처음 부르는 이름이면 0으로 초기화
        last_time = self.last_times.get(name, 0)
        
        if now - last_time > interval:
            self.last_times[name] = now # 시간 업데이트까지 한 번에
            return True
        return False

tm = TimeManager() # 원하는 시간마다 작동하게하는 함수

class GestureModel:
    """KNN 모델 학습 및 추론 담당 (AI 로직)"""
    
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.knn = None
        self.reload()
        # --- 2. MediaPipe 설정 및 유틸리티 ---
        self.mp_hands = mp.tasks.vision.HandLandmarksConnections
        self.mp_drawing = mp.tasks.vision.drawing_utils
        self.mp_drawing_styles = mp.tasks.vision.drawing_styles

        self.base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
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


class GestureApp:
    ''' 카메라, 키보드 리스너, 전체 흐름 제어 (엔진) '''

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.model = GestureModel(csv_path)
        self.cap = cv2.VideoCapture(0)
        self.file = None

        # 상태 관리 변수 (C의 static 변수들)
        self.flags = {"i": False, "d": False, "u": False}
        self.exit_program = False
        self.gesture_names = {i: chr(i) for i in range(ord('a'), ord('z')+1)}

        self.saved_count = 0
        self.update_count=0
        self.old_chr = ''
        self.output_interval = 2.0

    # insert
    def insert_data(self, label_chr):
        if len(self.model.insert_new_data) == 0: return

        self.saved_count+=1
        data = np.append(self.model.insert_new_data,ord(label_chr))
        self.file = open(self.csv_path, "a", newline="") 
        writer = csv.writer(self.file)
        writer.writerow(data)

        print(f"데이터 저장: {label_chr}")
        self.model.reload()

    # delete
    def delete_data(self, label_char):
        df = pd.read_csv(self.csv_path, header=None)
        if ord(label_char) in df.iloc[:, -1].values: # 만약 라벨이 있다면
            new_df = df[df.iloc[:, -1] != ord(label_char)] # 입력된 라벨 제외
            new_df.to_csv(self.csv_path, index=False, header=False)
            self.model.reload() # 갱신
            print(f"라벨 {label_char} 삭제 및 파일 갱신 완료!")

    # update
    def update_data(self,old,new):
        df = pd.read_csv(self.csv_path, header=None)
        # 마지막 열(라벨 열) 선택
        label_column = df.columns[-1]

        # 2. 존재 여부 확인 후 수정
        if ord(old) in df[label_column].values:
            # old_label인 행들을 찾아서 new_label로 교체
            df.loc[df[label_column] == ord(old), label_column] = ord(new)
            
            # 3. 덮어쓰기 저장
            df.to_csv(self.csv_path, index=False, header=False)
            print(f"라벨 수정 완료: {old} -> {new}")
            # 모델 갱신
            self.model.reload()

    # read
    def read_data(self):
        return self.model.insert_signal

    def on_press(self, key):
        try:
            if hasattr(key, 'char'):
                c = key.char

                # 리셋/저장 (-)
                if c == '-': # -를 누르면
                    if any(self.flags.values()): # true가 있다면 
                        self.flags = {k : False for k in self.flags}
                        if self.saved_count > 0:
                            self.file.flush()
                            os.fsync(self.file.fileno())
                            print(">>> 모든 데이터가 CSV 파일에 안전하게 저장되었습니다.")
                            self.saved_count = 0
                            self.file.close()
                            self.model.reload()

                # 모드별 동작 (Insert 등)
                if self.flags["i"]:
                    if ord(c) in self.gesture_names:
                        self.insert_data(c)
                elif self.flags["d"]:
                    self.delete_data(c) # 삭제함수
                elif self.flags["u"]:
                    if self.update_count == 0:
                        self.old_chr = c
                        self.update_count = 1
                        print(f"대상 라벨 {self.old_chr} 선택됨. 바꿀 라벨을 누르세요.")
                    elif self.update_count == 1:
                        new_chr = c
                        print(f"실행: {self.old_chr} -> {new_chr} 수정 중...")
                        
                        # 실제 데이터 수정 함수 호출
                        self.update_data(ord(self.old_chr), ord(new_chr))

                # 모드 전환
                if c in self.flags and not any(self.flags.values()): # true가 없다면
                    if c == 'i' :
                        self.flags["i"] = True
                        print("insert_mode 설정")
                    if self.model.knn is not None:
                        if c == 'd' :
                            self.flags["d"] = True
                            print("delete_mode 설정")
                        elif c == 'u':
                            self.flags["u"] = True
                            print("update_mode 설정")
                        elif c == 'q': # 임시
                            self.model.evaluate()
                
            if key == keyboard.Key.esc:
                self.exit_program = True
                return False  # 리스너 스레드 종료

        except AttributeError:
            print(f'{key} 특수키 눌림')

    def img_put_text(self,Image):
        Mode = ""
        if self.flags["i"]:
            Mode = "InsertMode"
        elif self.flags["d"]:
            Mode = "DeleteMode"
        elif self.flags["u"]:
            Mode = "UpdateMode"
            
        cv2.putText(
                Image, 
                Mode,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 
                FONT_SIZE, 
                (0, 0, 255), # 빨간색
                FONT_THICKNESS, 
                cv2.LINE_AA
            )

    def run(self):
        # 키보드 리스너 시작
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

        while self.cap.isOpened() and not self.exit_program:
            ret, frame = self.cap.read()
            if not ret: break

            frame = cv2.flip(frame, 1) # 좌우반전
            cvt_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy() # .copy() 추가
            image = mp.Image(mp.ImageFormat.SRGB, cvt_frame)

            # 손 탐지
            detection_result = self.model.detector.detect(image)

            if detection_result.hand_landmarks:
                # 랜드마크와 제스처를 모두 포함한 이미지 생성  
                annotated_image = self.model.draw_landmarks_on_image(image.numpy_view(), detection_result, self.gesture_names)
                display_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
            else: # 손이 없을때 일반 화면 출력
                display_image = frame

            self.img_put_text(display_image)
            if tm.is_time_up('output', self.output_interval) and len(self.model.insert_signal) > 0:
                self.read_data()
            cv2.imshow("Hand App", display_image)

            cv2.waitKey(1)

        self.cap.release()
        cv2.destroyAllWindows()
        self.model.detector.close()

if __name__ == "__main__":
    app = GestureApp("data_test.csv")
    app.run()