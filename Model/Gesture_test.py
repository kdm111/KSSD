import mediapipe as mp
import cv2
import numpy as np
import os
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pynput import keyboard

# csv파일 경로설정정
csv_file = "data_test.csv"
file_exists = os.path.isfile(csv_file)

import csv
f = open(csv_file, "a", newline="")
writer = csv.writer(f)


# --- 1. KNN 모델 로드 및 학습 ---
file = np.genfromtxt('data_test.csv', delimiter=',')
angle_data = file[:, :-1].astype(np.float32)
label_data = file[:, -1].astype(np.float32)
knn = cv2.ml.KNearest_create()
knn.train(angle_data, cv2.ml.ROW_SAMPLE, label_data)

# 제스처 라벨 정의 (본인의 데이터셋에 맞게 수정 가능)
gesture_names = {ord('a'): 'a', ord('b'): 'b', 3: 'half_heart'}

# --- 2. MediaPipe 설정 및 유틸리티 ---
mp_hands = mp.tasks.vision.HandLandmarksConnections
mp_drawing = mp.tasks.vision.drawing_utils
mp_drawing_styles = mp.tasks.vision.drawing_styles

# 옵션들
MAX_HAND = 2
MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)

exit_program = False # 종료 플래그
press_i = False

class TimeManager: # 타이머 클래스
    def __init__(self):
        self.last_times = {}

    def is_time_up(self, name, interval):
        now = time.time()
        # 처음 부르는 이름이면 0으로 초기화
        last_time = self.last_times.get(name, interval)
        
        if now - last_time > interval:
            self.last_times[name] = now # 시간 업데이트까지 한 번에
            return True
        return False

tm = TimeManager()


def on_press(key):
    global press_i, exit_program

    try:
        # key 객체가 char 속성을 가지고있는지 확인
        if hasattr(key, 'char') and key.char == 'i':
            press_i=True
        elif key == keyboard.Key.esc:
            exit_program = True
            return False # Esc 누르면 리스너 종료
    except AttributeError:
        print(f'{key} 특수키 눌림')

def on_release(key):
    global press_i

    if hasattr(key, 'char') and key.char == 'i':
            press_i=False

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# [함수] 랜드마크 및 정보를 이미지 위에 그리기
def draw_landmarks_on_image(rgb_image, detection_result):
    global press_i
    hand_landmarks_list = detection_result.hand_landmarks
    # handedness_list = detection_result.handedness
    annotated_image = np.copy(rgb_image)

    for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]
        # handedness = handedness_list[idx] # 여기서는 필요없어서 잠시 주석

        # 랜드마크 시각화
        mp_drawing.draw_landmarks(
            annotated_image,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style())

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
        
        current_time = time.time()
        if press_i:
            if tm.is_time_up('save', 1.0):
                d = np.append(angle,ord('b'))
                writer.writerow(d)
                print("저장됨")
        
        # KNN 추론
        data = np.array([angle], dtype=np.float32)
        ret, results, neighbours, dist = knn.findNearest(data, 3)

        
        idx = int(results[0][0])
        # 텍스트 위치 선정 (바운딩 박스 상단)
        height, width, _ = annotated_image.shape
        x_coords = [landmark.x for landmark in hand_landmarks]
        y_coords = [landmark.y for landmark in hand_landmarks]
        text_x = int(min(x_coords) * width)
        text_y = int(min(y_coords) * height) - MARGIN
        
        threshold = 2000.0 # 손 제스처가 비슷함을 나타내는 임계값
        display_text = ""

        if dist[0][0] < threshold:
            if idx in gesture_names:
                display_text += f"{gesture_names[idx]}"
        
        if tm.is_time_up('output', 2.0):
            print(display_text)

        cv2.putText(annotated_image, display_text, (text_x, text_y), 
                    cv2.FONT_HERSHEY_DUPLEX, FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

    return annotated_image

# --- 3. 실행 엔진 초기화 ---
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=MAX_HAND)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0) # 처음 연결된 비디오 확인

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break 

    frame = cv2.flip(frame, 1) # 좌우반전
    cvt_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(mp.ImageFormat.SRGB, cvt_frame)

    # 손 탐지
    detection_result = detector.detect(image)

    if detection_result.hand_landmarks:
        # 랜드마크와 제스처를 모두 포함한 이미지 생성
        annotated_image = draw_landmarks_on_image(image.numpy_view(), detection_result)
        cv2.imshow("Hand Gesture Recognition", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
    else: # 손이 없을때 일반 화면 출력력
        cv2.imshow("Hand Gesture Recognition", frame)

    if exit_program:
        break

    cv2.waitKey(1)

# 마무리작업
detector.close()
cap.release()
cv2.destroyAllWindows()
f.close()