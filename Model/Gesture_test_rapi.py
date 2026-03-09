import mediapipe as mp
import cv2
import numpy as np
import csv
import os
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pynput import keyboard

# csv파일 경로설정
csv_file = "data_test.csv"

f = open(csv_file, "a", newline="")
writer = csv.writer(f)


# --- 1. KNN 모델 로드 및 학습 ---
file = np.genfromtxt(csv_file, delimiter=',')
angle_data = file[:, :-1].astype(np.float32)
label_data = file[:, -1].astype(np.float32)
knn = cv2.ml.KNearest_create()
knn.train(angle_data, cv2.ml.ROW_SAMPLE, label_data)

# 제스처 라벨 정의 (본인의 데이터셋에 맞게 수정 가능)
gesture_names = { i : chr(i) for i in range(ord('a'),ord('z')+1) } # a ~ z까지 제스쳐라벨 설정 

# --- 2. MediaPipe 설정 및 유틸리티 ---
mp_hands = mp.tasks.vision.HandLandmarksConnections
mp_drawing = mp.tasks.vision.drawing_utils
mp_drawing_styles = mp.tasks.vision.drawing_styles

# 옵션들
MAX_HAND = 1
MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)
output_interval = 2.0
press_i_interval = 3.0


exit_program = False # 종료 플래그
flag ={"press_i" : False, "press_d" : False}

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

def reload_Knn():
    global angle_data,label_data,knn
    new_file = np.genfromtxt(csv_file, delimiter=',')
    angle_data = new_file[:, :-1].astype(np.float32)
    label_data = new_file[:, -1].astype(np.float32)
    knn = cv2.ml.KNearest_create()
    knn.train(angle_data, cv2.ml.ROW_SAMPLE, label_data)

def on_press(key):
    global flag, exit_program
    
    try:
        if hasattr(key, 'char'): # key 객체가 char 속성을 가지고있는지 확인
            c = key.char

            if flag["press_i"]: 
                if ord(c) in gesture_names:
                    (c) # 저장 함수 호출

            if  key.char == 'i' and not flag["press_i"]:
                flag["press_i"]=True
                print("insert_mode 설정")

            if  key.char == '-': # -를 누르면
                if any(flag.values()): # true가 있다면 
                    for k, v in flag.items():
                        if v == True:
                            flag[k] = False # True인 경우에만 False로 변경
                    f.flush()
                    os.fsync(f.fileno())
                    reload_Knn()
                    print(">>> 모든 데이터가 CSV 파일에 안전하게 저장되었습니다.")

        elif key == keyboard.Key.esc:
            exit_program = True
            return False # Esc 누르면 리스너 종료

    except AttributeError:
        print(f'{key} 특수키 눌림')

def on_release(key):
    global press_i

    # if hasattr(key, 'char') and key.char == 'i':
    #         press_i=False


listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start() # 키보드 입력 함수 적용

insert_new_data = []

# [함수] 랜드마크 및 정보를 이미지 위에 그리기
def draw_landmarks_on_image(rgb_image, detection_result):
    global insert_new_data
    insert_new_data = []
    hand_landmarks_list = detection_result.hand_landmarks
    handedness_list = detection_result.handedness
    
    annotated_image = np.copy(rgb_image)
    insert_signal = '' # 가장 최근에 손으로 인식하였을 때 나오는 문자

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
        h, w, _ = annotated_image.shape
        for connection in mp.solutions.hands.HAND_CONNECTIONS:
            start = hand_landmarks[connection[0]]
            end   = hand_landmarks[connection[1]]
            x0, y0 = int(start.x * w), int(start.y * h)
            x1, y1 = int(end.x * w),   int(end.y * h)
            cv2.line(annotated_image, (x0, y0), (x1, y1), (0, 255, 0), 2)

        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(annotated_image, (cx, cy), 5, (255, 0, 0), -1)

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
        # KNN 추론
        data = np.array([full_data], dtype=np.float32)
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
        
        # if tm.is_time_up('output', output_interval) and len(display_text)>0: # 특정 손동작이 감지되었을 때만 신호보내기
        #     insert_signal = display_text
            
        insert_new_data = full_data
        cv2.putText(annotated_image, display_text, (text_x, text_y), 
                    cv2.FONT_HERSHEY_DUPLEX, FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

    return annotated_image

def insert_data(c):
    if len(insert_new_data) == 0:
        return
    
    data = np.append(insert_new_data, ord(c))
    
    # CSV 쓰기
    writer.writerow(data)
    print(f"데이터 저장됨: {c}")
    

# --- 3. 실행 엔진 초기화 ---
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=MAX_HAND)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0) # 처음 연결된 비디오 확인

tm = TimeManager() # 원하는 시간마다 작동하게하는 함수



while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break 

    frame = cv2.flip(frame, 1) # 좌우반전
    cvt_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(mp.ImageFormat.SRGB, cvt_frame)

    # 손 탐지
    detection_result = detector.detect(image)

    annotated_image = draw_landmarks_on_image(image.numpy_view(), detection_result)
    if detection_result.hand_landmarks:
        # 랜드마크와 제스처를 모두 포함한 이미지 생성  
        cv2.imshow("Hand Gesture Recognition", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
    else: # 손이 없을때 일반 화면 출력
        cv2.imshow("Hand Gesture Recognition", frame)

    if exit_program:
        break

    cv2.waitKey(1)

# 마무리작업
detector.close()
cap.release()
cv2.destroyAllWindows()
f.close()