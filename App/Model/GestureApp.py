import mediapipe as mp
import cv2
import numpy as np
import pandas as pd
import csv
import os
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
# from pynput import keyboard
from gcc import Keyboard
from DB import get_gesture_action
from DB import insert_log
from DB import insert_gesture_log
from DB import delete_gesture_log
from DB import update_gesture_log
from DB import get_gesture_id
from DB import check_gesture_exists
from DB import get_gesture_all
from DB import get_id_action
from DB import get_id_gesture

from .GestureModel import GestureModel
from .TimeManager import TimeManager

FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (255, 0, 0) # cv2에 보이는 라벨 색

class GestureApp:
    ''' 카메라, 키보드 리스너, 전체 흐름 제어 (엔진) '''

    def __init__(self, csv_path, cap):
        base_dir = os.getcwd() # 현재 터미널이 열려있는 위치
        base_dir = os.path.join(base_dir,"Model")
        csv_path = os.path.join(base_dir,csv_path)
        if not os.path.exists(csv_path):
            with open(csv_path, 'w', encoding='utf-8') as f:
                pass

        self.csv_path = csv_path
        self.model = GestureModel(csv_path)
        #self.cap = cv2.VideoCapture(0)
        self.cap = cap
        self.file = None

        # 상태 관리 변수 (C의 static 변수들)   
        self.flags = {"i": False, "d": False, "u": False,"reset":False}
        self.action_flags = {
            # 기본동작 기본값 forward
            'FOR' : True,
            'BAK' : False,
            # 'LFT' : False,
            # 'RIT' : False,
            'STP' : False,

            # 속도 제어
            'SLW' : False,
            'FST' : False,
            # 제자리 회전
            'SPN' : False
        }
        self.exit_program = False
        self.gesture_names = {}
        self.load_gestures()

        self.saved_count = 0
        self.update_count=0
        self.old_chr = ''
        self.output_interval = 2.0

    def load_gestures(self):
        gestures = get_gesture_all()
        self.gesture_names = {item.id: item.gesture for item in gestures}

    # insert
    def insert_data(self, label_chr):
        if len(self.model.insert_new_data) == 0: return

        self.saved_count+=1
        if not check_gesture_exists(label_chr): # DB에 없다면 저장해라
            action = next(k for k, v in self.action_flags.items() if v)
            insert_gesture_log(label_chr,action)
            self.load_gestures()

        id = get_gesture_id(label_chr)
        
        data = np.append(self.model.insert_new_data, id)
        self.file = open(self.csv_path, "a", newline="") 
        writer = csv.writer(self.file)
        writer.writerow(data)

        print(f"데이터 저장: {label_chr}")
        self.model.reload()

    # delete
    def delete_data(self, label_char):
        id=get_gesture_id(label_char)
        if check_gesture_exists(label_char): # DB에 있다면 삭제해라
            delete_gesture_log(label_char)
            self.load_gestures()
        
        df = pd.read_csv(self.csv_path, header=None)
        if id in df.iloc[:, -1].values: # 만약 라벨이 있다면
            new_df = df[df.iloc[:, -1] != id] # 입력된 라벨 제외
            new_df.to_csv(self.csv_path, index=False, header=False)
            self.model.reload() # 갱신
            print(f"라벨 {label_char} 삭제 및 파일 갱신 완료!")

    # update
    def update_data(self,old,new):
        id = get_gesture_id(old)
        
        df = pd.read_csv(self.csv_path, header=None)
        # 마지막 열(라벨 열) 선택
        label_column = df.columns[-1]

        # 2. 존재 여부 확인 후 수정
        if id in df[label_column].values:
            # old_label인 행들을 찾아서 new_label로 교체
            update_gesture_log(old,new)
            self.load_gestures()

    # read
    def read_data(self):
        return self.model.insert_signal

    # def on_press(self, key):
    #     try:
    #         c = None

    #         if key == keyboard.Key.esc:
    #             self.exit_program = True
    #             return False  # 리스너 스레드 종료

    #         if hasattr(key, 'char') and key.char is not None:
    #             c = key.char

    #         if c is None:
    #             return

    #         # 모드별 동작 (Insert 등)
    #         if self.flags["i"]:
    #             self.insert_data(c)
    #         elif self.flags["d"]:
    #             self.delete_data(c) # 삭제함수
    #         elif self.flags["u"]:
    #             if self.update_count == 0:
    #                 self.old_chr = c
    #                 self.update_count = 1
    #                 print(f"대상 라벨 {self.old_chr} 선택됨. 바꿀 라벨을 누르세요.")
    #             elif self.update_count == 1:
    #                 new_chr = c
    #                 # 실제 데이터 수정 함수 호출
    #                 self.update_data(self.old_chr, new_chr)
    #                 self.update_count=0

    #     except AttributeError:
    #         import traceback
    #         traceback.print_exc()

    def run(self):
        prev = None
        # 키보드 리스너 시작
        # listener = keyboard.Listener(on_press=self.on_press)
        # listener.start()
        tm = TimeManager() # 원하는 시간마다 작동하게하는 함수

        while self.cap.isOpened() and not self.exit_program:
            
            # 리셋/저장
            if self.flags["reset"]:
                # if any(self.flags.values()): # true가 있다면 
                #     self.flags = {k : False for k in self.flags}
                if self.saved_count > 0:
                    self.file.flush()
                    os.fsync(self.file.fileno())
                    print(">>> 모든 데이터가 CSV 파일에 안전하게 저장되었습니다.")
                    self.saved_count = 0
                    self.file.close()
                    self.model.reload()
                self.flags["reset"]=False

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
                self.model.reset_memory()
                self.model.gesture_controller.update({}, None)
                display_image = frame
            
            # todo
            if self.model.get_key()!=None:
                print(self.model.gesture_controller.device)
                # print(self.model.gesture_controller.device is not None)
                # print('RPi' in self.model.gesture_controller.device)
                if (self.model.gesture_controller.device is not None) and ('RPi' in self.model.gesture_controller.device):
                    action = get_id_action(self.model.get_key()+1)
                    print(action)
                    if action is not None:
                        Keyboard.send_cmd(str(action))
                #자동차모드가 아니면
                else:
                    action = get_id_gesture(self.model.get_key()+1)
                    print(action)
                    if action is not None:
                        Keyboard.press_key(str(action))

                # Keyboard.send_string(str())

            current_result = self.read_data()
            if prev != current_result and tm.is_time_up('output', self.output_interval) and len(self.model.insert_signal) > 0:
                action = get_gesture_action(current_result)
                prev = current_result
                insert_log(current_result)
                print(action) # 여기를 보내는 부분으로 바꾸면 됨
                # Keyboard.press_key(current_result)

            self.cap.set_display_frame(display_image)
            # if tm.is_time_up('output', self.output_interval) and len(self.model.insert_signal) > 0:
            #     print(self.read_data())

        self.cap.release()
        cv2.destroyAllWindows()
        self.model.detector.close()