import cv2
import mediapipe as mp
import numpy as np
from tensorflow.keras.models import load_model
from mediapipe.tasks.python import vision
from mediapipe.tasks import python

# 1. 모델 로드
model = load_model('./LSTM_TEST/test_lstm_model.h5')

# 2. MediaPipe Tasks API 구성 (solutions 없이)
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# 님이 말씀하신 tasks.vision 내부의 그리기 도구
mp_drawing = mp.tasks.vision.drawing_utils
mp_drawing_styles = mp.tasks.vision.drawing_styles
# 연결선 정의는 HandLandmarker 결과 구조 내의 상수를 참조하거나 별도 지정이 필요할 수 있습니다.
# (대부분의 Tasks 환경에서도 연결 정보는 mp.tasks.vision.HandLandmarksConnections에 있습니다)
mp_hands_connections = mp.tasks.vision.HandLandmarksConnections

# 3. Tasks 옵션 설정
options = HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path='hand_landmarker.task'),
    num_hands=1
)


detector = vision.HandLandmarker.create_from_options(options)

seq_length = 10
sequence = []

cap = cv2.VideoCapture(0)

with HandLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        cvt_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy() # .copy() 추가
        image = mp.Image(mp.ImageFormat.SRGB, cvt_frame)
        detection_result = detector.detect(image)
        current_label = ""
        if detection_result.hand_landmarks:
            
            hand_landmarks_list = detection_result.hand_landmarks
            
            handedness_list = detection_result.handedness
            annotated_image = np.copy(image.numpy_view())
                
            for idx in range(len(hand_landmarks_list)):
                hand_landmarks = hand_landmarks_list[idx]
                hand_label = handedness_list[idx][0].category_name

                hand_side = -1 
                if hand_label == "Right": # 좌우반전기준으로 해서
                    hand_side = 0 # 왼손
                elif hand_label == "Left":
                    hand_side = 1 # 오른손
                hand_side = hand_side * 100

                mp_drawing.draw_landmarks(
                    annotated_image,
                    hand_landmarks,
                    mp_hands_connections.HAND_CONNECTIONS, # mp.tasks.vision 버전 연결 정보
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # --- 데이터 추출 로직 ---
                joint = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks])
                v1 = joint[[0,1,2,3,0,5,6,7,0,9,10,11,0,13,14,15,0,17,18,19],:] 
                v2 = joint[[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],:] 
                v = v2 - v1 
                v = v / np.linalg.norm(v, axis=1)[:, np.newaxis]

                angle = np.arccos(np.einsum('nt,nt->n',
                    v[[0,1,2,4,5,6,8,9,10,12,13,14,16,17,18],:], 
                    v[[1,2,3,5,6,7,9,10,11,13,14,15,17,18,19],:])) 
                angle = np.degrees(angle) 

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
                
                sequence.append(full_data)
                sequence = sequence[-seq_length:]
            
            # --- 시퀀스 쌓기 및 예측 ---
            if len(sequence) == seq_length:
                seq_np = np.array(sequence)
                # 각 프레임 간의 차이의 절대값 평균을 구함 (움직임 수치)
                motion_value = np.mean(np.abs(np.diff(seq_np, axis=0)))
                input_data = np.expand_dims(sequence, axis=0).astype(np.float32)
                res = model.predict(input_data, verbose=0)[0]
                
                idx = np.argmax(res) # 가장 높은 확률의 인덱스 
                confidence = res[idx] # 해당 확률 값

                if confidence > 0.98 and motion_value > 0.65:
                    current_label = idx
                else:
                    # 확신이 없으면 즉시 라벨을 비움
                    current_label = ""
            else:
                current_label = ""

            display_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
        else: # 손이 없을때 일반 화면 출력
            sequence = []
            current_label = ""
            display_image = frame

        if current_label != "":
                cv2.putText(display_image, f'{current_label}', (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow('Gesture Recognition', display_image)
 
        if cv2.waitKey(1) & 0xFF == ord('q'): break


detector.close() # 여기서 명시적으로 닫아주면 __del__ 에러를 줄일 수 있습니다.
cap.release()
cv2.destroyAllWindows()