import numpy as np
import tensorflow as tf
import pickle

class Pre_DNN:
    def __init__(self):
        self.model = tf.keras.models.load_model("./Model/gesture_model.keras", safe_mode=False)
        with open("./Model/gesture_scaler.pkl", "rb") as f:
            self.scaler = pickle.load(f)
        
    def predict_gesture(self, feature):

        x = np.array(feature, dtype=np.float32).reshape(1, -1)

        x = self.scaler.transform(x)

        pred = self.model(x, traning = False).numpy()[0]

        return pred
