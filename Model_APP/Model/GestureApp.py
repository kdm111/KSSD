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

from .GestureModel import GestureModel
from .TimeManager import TimeManager

FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (255, 0, 0) # cv2에 보이는 라벨 색

class GestureApp:
    ''' 카메라, 키보드 리스너, 전체 흐름 제어 (엔진) '''

    def __init__(self, csv_path, cap):
        base_dir = os.getcwd() # 현재 터미널이 열려있는 위치
        csv_path = os.path.join(base_dir, csv_path)
        if not os.path.exists(csv_path):
            with open(csv_path, 'w', encoding='utf-8') as f:
                pass
        
        self.csv_path = csv_path
        self.model = GestureModel(csv_path)
        #self.cap = cv2.VideoCapture(0)
        self.cap = cap
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
        tm = TimeManager() # 원하는 시간마다 작동하게하는 함수

        while self.cap.isOpened() and not self.exit_program:
            #ret, frame = self.cap.read()
            frame = self.cap.get_frame()
            if frame is None:
                continue

            frame = cv2.flip(frame, 1) # 좌우반전
            cvt_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy() # .copy() 추가
            image = mp.Image(mp.ImageFormat.SRGB, cvt_frame)

            # 손 탐지
            detection_result = self.model.detector.detect(image)

            if detection_result.hand_landmarks:
                # 랜드마크와 제스처를 모두 포함한 이미지 생성  
                annotated_image = self.model.draw_landmarks_on_image(
                    image.numpy_view(), detection_result, self.gesture_names)
                display_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
            else: # 손이 없을때 일반 화면 출력
                display_image = frame

            self.img_put_text(display_image)
            self.cap.set_display_frame(display_image)
            if tm.is_time_up('output', self.output_interval) and len(self.model.insert_signal) > 0:
                print(self.read_data())
                
            #cv2.imshow("Hand App", display_image)

            #cv2.waitKey(1)

        self.cap.release()
        cv2.destroyAllWindows()
        self.model.detector.close()