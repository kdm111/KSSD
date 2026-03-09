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
HANDEDNESS_TEXT_COLOR = (88, 205, 54) # cv2에 보이는 라벨 색
output_interval = 2.0

exit_program = False # 종료 플래그
flag ={"press_i" : False, "press_d" : False, "press_u": False} # insert, delete, update

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

def reload_Knn(): # KNN 재갱신
    global angle_data,label_data,knn
    new_file = np.genfromtxt(csv_file, delimiter=',')
    angle_data = new_file[:, :-1].astype(np.float32)
    label_data = new_file[:, -1].astype(np.float32)
    knn = cv2.ml.KNearest_create()
    knn.train(angle_data, cv2.ml.ROW_SAMPLE, label_data)

saved_count = 0 # save가 된 횟수
update_count = 0 # 업데이트 변수 0 -> 아무것도 입력 x, 1 -> old_chr는 이미 받음음
old_chr = ''

def on_press(key): # 키가 눌렸을때 이벤트 리스너너
    global flag, exit_program, saved_count, update_count, old_chr
    
    try:
        if hasattr(key, 'char'): # key 객체가 char 속성을 가지고있는지 확인
            c = key.char

            if  key.char == '-': # -를 누르면
                if any(flag.values()): # true가 있다면 
                    for k, v in flag.items():
                        if v == True:
                            flag[k] = False # True인 경우에만 False로 변경
                    if saved_count>0:
                        f.flush()
                        os.fsync(f.fileno())
                        reload_Knn()
                        print(">>> 모든 데이터가 CSV 파일에 안전하게 저장되었습니다.")
                        saved_count = 0

            if flag["press_i"]: # i키를 눌렀을 경우
                if ord(c) in gesture_names:
                    insert_data(c) # 저장 함수 호출
            elif flag["press_d"]: # d키를 눌렀을 경우
                delete_data(c) # 삭제함수
            elif flag["press_u"]: # u키를 눌렀을 경우
                if update_count == 0:
                    old_chr = c
                    update_count = 1
                    print(f"대상 라벨 {old_chr} 선택됨. 바꿀 라벨을 누르세요.")
                elif update_count == 1:
                    new_chr = c
                    print(f"실행: {old_chr} -> {new_chr} 수정 중...")
                    
                    # 실제 데이터 수정 함수 호출
                    update_data(old_chr, new_chr)
                    
                    # 작업 완료 후 초기화
                    update_count = 0
                    old_chr = None
            
            if not any(flag.values()): # True값이 하나도 없을경우만 동작작
                if key.char == 'i' :
                    flag["press_i"] = True
                    print("insert_mode 설정")
                if key.char == 'd' :
                    flag["press_d"] = True
                    print("delete_mode 설정")
                if key.char == 'u':
                    flag["press_u"] = True
                    print("update_mode 설정")
            
    except AttributeError:
        print(f'{key} 특수키 눌림')

def on_release(key): # 키를 땠을 때 이벤트 리스터터
    global exit_program
    if key == keyboard.Key.esc:
        exit_program = True
        return False # Esc 누르면 리스너 종료


listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start() # 키보드 입력 함수 적용

insert_new_data = [] # 손의 랜드마크를 읽어서 리스트에 저장 (save용)

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
        
        if tm.is_time_up('output', output_interval) and len(display_text)>0: # 특정 손동작이 감지되었을 때만 신호보내기
            insert_signal = display_text
            read_data(insert_signal)

        insert_new_data = full_data
        
        cv2.putText(annotated_image, display_text, (text_x, text_y), 
                    cv2.FONT_HERSHEY_DUPLEX, FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
        
    return annotated_image

def insert_data(c): # 손으로 포즈를 취하고 입력하고싶은 데이터를 넣으면 입력됨
    global saved_count

    if len(insert_new_data) == 0:
        return

    saved_count += 1

    data = np.append(insert_new_data, ord(c))
    
    # CSV 쓰기
    writer.writerow(data)
    print(f"데이터 저장됨: {c}")

def read_data(signal):
    print(signal)

def delete_data(c): # delete mode 키고 키보드로 라벨 입력하면 지워짐
    global f, writer
    f.close() # 기존에 열려있던 파일 닫고 작업 

    df = pd.read_csv(csv_file, header=None)
    if ord(c) in df.iloc[:, -1].values: # 만약 라벨이 없다면 
        new_df = df[df.iloc[:, -1] != ord(c)] # 입력된 라벨 제외
        new_df.to_csv(csv_file, index=False, header=False)
        f = open(csv_file, mode='a', newline='')
        writer = csv.writer(f)

        reload_Knn() # 갱신
        print(f"라벨 {c} 삭제 및 파일 갱신 완료!")

def update_data(old, new) : # old -> new로 라벨 업데이트트
    global f, writer
    f.close() # 기존에 열려있던 파일 닫고 작업 

    df = pd.read_csv(csv_file, header=None)
    # 마지막 열(라벨 열) 선택
    label_column = df.columns[-1]

    # 2. 존재 여부 확인 후 수정
    if ord(old) in df[label_column].values:
        # old_label인 행들을 찾아서 new_label로 교체
        df.loc[df[label_column] == ord(old), label_column] = ord(new)
        
        # 3. 덮어쓰기 저장
        df.to_csv(csv_file, index=False, header=False)
        print(f"라벨 수정 완료: {old} -> {new}")

        f = open(csv_file, mode='a', newline='')
        writer = csv.writer(f)
        # 모델 갱신
        reload_Knn()

def img_put_text(Image):
    Mode = ""
    if flag["press_i"]:
        Mode = "InsertMode"
    elif flag["press_d"]:
        Mode = "DeleteMode"
    elif flag["press_u"]:
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

# --- 3. 실행 엔진 초기화 ---
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=MAX_HAND)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0) # 처음 연결된 비디오 확인

tm = TimeManager() # 원하는 시간마다 작동하게하는 함수

def Start():
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
            display_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
        else: # 손이 없을때 일반 화면 출력
            display_image = frame

        img_put_text(display_image)
        cv2.imshow("Hand Gesture Recognition", display_image)

        if exit_program:
            break

        cv2.waitKey(1)

    # 마무리작업
    detector.close()
    cap.release()
    cv2.destroyAllWindows()
    f.close()

if __name__ == "__main__":
    Start()