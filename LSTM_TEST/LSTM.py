import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input, Dropout
from tensorflow.keras.utils import to_categorical
from sklearn.preprocessing import StandardScaler

# 1. 데이터 로드 (헤더가 없는 경우 header=None)
df = pd.read_csv("LSTM.csv", header=None)

# df_features = df.iloc[:, :-1]
# df_labels = df.iloc[:, -1]

# scaler = StandardScaler()
# # 특성 데이터만 0~1 사이로 변환
# features_scaled = scaler.fit_transform(df_features)

# df = pd.DataFrame(features_scaled)
# df['label'] = df_labels.values

# 2. 파라미터 설정
seq_length = 10  # 한 번에 볼 시계열 길이 (35행)
feature_length = 19
data_list = []
label_list = []

# 3. 슬라이딩 윈도우로 데이터 전처리
# 한 줄에 17개(데이터 16개 + 라벨 1개)가 있는 경우를 가정합니다.
for i in range(0, len(df) - seq_length + 1, seq_length): # step을 seq_length(35)만큼 줌
    # 35줄의 16개 특성
    x = df.iloc[i : i + seq_length, :-1].values.astype(np.float32)
    
    # 이 35줄 뭉치를 대표하는 라벨 하나 (보통 첫 번째나 마지막 줄 라벨 사용)
    y = df.iloc[i, -1]
    
    data_list.append(x)
    label_list.append(y)

X_data = np.array(data_list) # (샘플수, 35, 16)
y_data = np.array(label_list)


# 4. 라벨 인코딩 (문자 'o' 등을 숫자로 변환하고 원-핫 인코딩)
# 여기서는 예시로 'o'가 111.0 등의 숫자로 이미 되어있다고 가정하거나 변환이 필요합니다.
unique_labels = np.unique(y_data)
label_map = {label: i for i, label in enumerate(unique_labels)}
y_encoded = np.array([label_map[l] for l in y_data])
y_onehot = to_categorical(y_encoded)

print(y_onehot)
# 학습용 80%, 검증용 20%로 무작위로 섞어서 분할
X_train, X_test, y_train, y_test = train_test_split(
    X_data, y_onehot, test_size=0.2, random_state=42, stratify=y_encoded
)

# 6. LSTM 모델 구성
num_classes = len(unique_labels) # 출력개수

model = Sequential()
model.add(Input(shape=(seq_length, feature_length)))
model.add(LSTM(128, activation='tanh',return_sequences=True)) 
model.add(Dropout(0.1))
model.add(LSTM(64, activation='tanh')) 
model.add(Dropout(0.1))

# 3. 두 번째 층: 중간 은닉층 (Dense)
# LSTM이 추출한 특징을 가지고 더 복잡한 판단을 할 수 있게 돕습니다.
model.add(Dense(32, activation='relu'))

# 4. 세 번째 층: 출력층 (Output)
model.add(Dense(num_classes, activation='softmax'))

model.compile(
    optimizer='adam', 
    loss='categorical_crossentropy', 
    metrics=['accuracy']
)

model.summary()

# 7. 학습 실행
print("\n--- 학습 시작 ---")
history = model.fit(
    X_train,     # 전체(X_data)가 아니라 쪼갠 '훈련용'만 넣기!
    y_train,        # 정답도 '훈련용'만 넣기!
    epochs=100,  # 반복 횟수
    batch_size=32, # 한 번에 넣을 샘플 수
    validation_data=(X_test, y_test),
    verbose=1    # 학습 과정을 화면에 출력 (0은 생략, 1은 상세히)
)
print("\n--- 학습 완료 ---")

loss, accuracy = model.evaluate(X_data, y_onehot)
# 학습 종료 후 history 객체에서 검증 정확도 기록 추출
val_acc = history.history['val_accuracy']
val_loss = history.history['val_loss']

print(f"\n최종 검증 정확도 (Val Accuracy): {val_acc[-1]:.4f}")
print(f"최종 검증 손실 (Val Loss): {val_loss[-1]:.4f}")
print(f"\n(Accuracy): {accuracy:.4f}")
print(f"(Loss): {loss:.4f}")

model.save('test_lstm_model.h5')