from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import tensorflow as tf
import base64
import threading
import queue
import os
import tempfile
import platform
import time

from deep_translator import GoogleTranslator
from gtts import gTTS

# ===== MediaPipe Tasks (MODERN API) =====
from mediapipe import Image, ImageFormat
from mediapipe.tasks.python import vision
from mediapipe.tasks.python import vision, BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions
)

last_spoken_word = ""
last_spoken_time = 0


# ===== TensorFlow GPU Safe Init =====
gpus = tf.config.list_physical_devices("GPU")
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

app = Flask(__name__)
CORS(app)

# ============================================================
# ===================== LOAD MODEL ===========================
# ============================================================
print("Loading model and labels...")

labels = np.load("models/twohand_label_classes.npy", allow_pickle=True)
num_classes = len(labels)

model = tf.keras.models.Sequential([
    tf.keras.layers.Input(shape=(126,)),
    tf.keras.layers.Dense(256, activation="relu"),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(128, activation="relu"),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(num_classes, activation="softmax")
])

model.load_weights("models/twohand_mlp.h5")
print("✅ Model loaded successfully")

# Warmup
_ = model.predict(np.random.rand(1, 126).astype(np.float32), verbose=0)

# ============================================================
# ================= MediaPipe HandLandmarker =================
# ============================================================
print("Initializing MediaPipe HandLandmarker...")

options = HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="models/hand_landmarker.task"
    ),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

hand_landmarker = HandLandmarker.create_from_options(options)
print("✅ HandLandmarker ready")

# ============================================================
# ====================== LANGUAGES ===========================
# ============================================================
LANGUAGES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "pa": "Punjabi",
}

# ============================================================
# ======================== TTS ===============================
# ============================================================
def speak_text(text, lang_code):
    """Immediate, low-latency TTS"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(f.name)

        if platform.system() == "Windows":
            os.startfile(f.name)
        elif platform.system() == "Darwin":
            os.system(f'afplay "{f.name}"')
        else:
            os.system(f'mpg123 "{f.name}"')

        # cleanup
        threading.Timer(4, lambda: os.remove(f.name)).start()

    except Exception as e:
        print("TTS error:", e)


# ============================================================
# ======================== ROUTES ============================
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/translator")
def translator():
    return render_template("translator.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/api/languages")
def get_languages():
    return jsonify(LANGUAGES)

# ============================================================
# ======================= PREDICT ============================
# ============================================================
@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        img_data = data["frame"].split(",")[1]
        img = cv2.imdecode(
            np.frombuffer(base64.b64decode(img_data), np.uint8),
            cv2.IMREAD_COLOR
        )

        img = cv2.flip(img, 1)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        mp_image = Image(
            image_format=ImageFormat.SRGB,
            data=rgb
        )

        timestamp = int(time.time() * 1000)
        result = hand_landmarker.detect_for_video(mp_image, timestamp)

        word = "None"
        confidence = 0.0

        if result.hand_landmarks:
            landmarks = []

            for hand in result.hand_landmarks[:2]:
                for lm in hand:
                    landmarks.extend([lm.x, lm.y, lm.z])

            if len(landmarks) < 126:
                landmarks.extend([0.0] * (126 - len(landmarks)))

            x = np.array(landmarks, dtype=np.float32).reshape(1, -1)
            probs = model.predict(x, verbose=0)[0]
            idx = np.argmax(probs)
            confidence = float(probs[idx])

            if confidence > 0.6:
                word = str(labels[idx])

        # ====================================================
        # ✅ ADD THIS BLOCK **RIGHT HERE**
        # ====================================================
        global last_spoken_word, last_spoken_time
        now = time.time()

        if (
            word != "None"
            and word != last_spoken_word
            and now - last_spoken_time > 1.0   # debounce (1 sec)
        ):
            last_spoken_word = word
            last_spoken_time = now
        # ====================================================

        _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
        frame_b64 = base64.b64encode(buffer).decode()

        return jsonify({
            "success": True,
            "gesture": word,
            "confidence": round(confidence, 3),
            "frame": f"data:image/jpeg;base64,{frame_b64}"
        })

    except Exception as e:
        print("Prediction error:", e)
        return jsonify({"success": False, "error": str(e)})


# ============================================================
# ======================= TRANSLATE ==========================
# ============================================================
@app.route("/api/translate", methods=["POST"])
def translate():
    data = request.json
    text = data.get("text", "")
    lang = data.get("lang", "en")

    if not text or lang == "en":
        return jsonify({"translated": text})

    translated = GoogleTranslator(source="en", target=lang).translate(text)
    return jsonify({"translated": translated})

@app.route("/api/speak", methods=["POST"])
def speak():
    data = request.json
    text = data.get("text", "").strip()
    lang = data.get("lang", "en")

    if not text or text == "None":
        return jsonify({"success": False})

    try:
        # Translate first
        if lang != "en":
            text = GoogleTranslator(source="en", target=lang).translate(text)

        # Speak translated text
        speak_text(text, lang)

    except Exception as e:
        print("Speak error:", e)

    return jsonify({"success": True})


# ============================================================
# ======================== MAIN ==============================
# ============================================================
if __name__ == "__main__":
    def open_browser():
        time.sleep(2)
        import webbrowser
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser, daemon=True).start()

    print("\n🚀 Sign Language Translator Running")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
