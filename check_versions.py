import sys
import mediapipe as mp
import google.protobuf
import tensorflow as tf

print("Python exe:", sys.executable)
print("TensorFlow:", tf.__version__)
print("MediaPipe:", mp.__version__)
print("Protobuf:", google.protobuf.__version__)

from google.protobuf.internal import builder
print("builder import: OK")

print("solutions:", mp.solutions)
