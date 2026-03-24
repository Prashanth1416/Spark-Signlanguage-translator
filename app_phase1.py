# ============================================================
# ===================== PHASE 1 APP ==========================
# ============================================================

from phase1.enhancements import (
    get_stable_gesture,
    update_sentence,
    check_auto_pause,
    clear_sentence
)

from phase1.grammar import apply_basic_grammar
from flask import session, redirect, url_for
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import tensorflow as tf
import base64
import threading
import os
import tempfile
import platform
import time
import json
from deep_translator import GoogleTranslator
from gtts import gTTS

# ================= MediaPipe Tasks API ======================
from mediapipe import Image, ImageFormat
from mediapipe.tasks.python import vision, BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions
)


# ============================================================
# ================== GPU SAFE INIT ===========================
# ============================================================
gpus = tf.config.list_physical_devices("GPU")
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

# ============================================================
# ================== FLASK APP ===============================
# ============================================================
app = Flask(__name__)
CORS(app)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_PORT"] = 3306
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "123456"
app.config["MYSQL_DB"] = "sign_language_app"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

app.secret_key = "spark_secret_key_change_later"

mysql = MySQL(app)
# ============================================================
# ================== LOAD MODEL ==============================
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

# Warm-up
_ = model.predict(np.random.rand(1, 126).astype(np.float32), verbose=0)

# ============================================================
# ============ MEDIAPIPE HAND LANDMARKER =====================
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
# ==================== LANGUAGES =============================
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
# ===================== TTS =================================
# ============================================================
def speak_text(text, lang_code):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            gTTS(text=text, lang=lang_code, slow=False).save(f.name)

        if platform.system() == "Windows":
            os.startfile(f.name)
        elif platform.system() == "Darwin":
            os.system(f'afplay "{f.name}"')
        else:
            os.system(f'mpg123 "{f.name}"')

        threading.Timer(4, lambda: os.remove(f.name)).start()

    except Exception as e:
        print("TTS error:", e)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# ===================== ROUTES ===============================
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dictionary_page"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password)

        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, hashed_pw)
            )
            mysql.connection.commit()
        except:
            return render_template("register.html", error="Username already exists")
        finally:
            cur.close()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/dictionary")
@login_required
def dictionary_page():
    return render_template("dictionary.html", username=session["username"])

@app.route("/learn")
@login_required
def learn_page():
    return render_template("learn.html", username=session["username"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ============================================================
# ===================== PREDICT ==============================
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

        current_word = "None"
        sentence = ""
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
                raw_word = str(labels[idx])
                current_word = get_stable_gesture(raw_word)
                sentence = update_sentence(current_word)
                finalized_sentence = check_auto_pause()
        _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
        frame_b64 = base64.b64encode(buffer).decode()
        spoken_sentence = None

        if finalized_sentence:
            spoken_sentence = apply_basic_grammar(finalized_sentence)

        return jsonify({
        "success": True,
        "gesture": current_word,
        "sentence": sentence,
        "final_sentence": spoken_sentence,
        "confidence": round(confidence, 3),
        "frame": f"data:image/jpeg;base64,{frame_b64}"
        })


    except Exception as e:
        print("Prediction error:", e)
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# ================= CLEAR SENTENCE ===========================
# ============================================================
@app.route("/api/clear-sentence", methods=["POST"])
def clear_sentence_api():
    clear_sentence()
    return jsonify({"success": True})

# ============================================================
# ===================== TRANSLATE ============================
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

# ============================================================
# ======================= SPEAK ==============================
# ============================================================
@app.route("/api/speak", methods=["POST"])
def speak():
    data = request.json
    text = data.get("text", "").strip()
    lang = data.get("lang", "en")

    if not text or text == "None":
        return jsonify({"success": False})

    try:
        if lang != "en":
            text = GoogleTranslator(source="en", target=lang).translate(text)

        speak_text(text, lang)

    except Exception as e:
        print("Speak error:", e)

    return jsonify({"success": True})

# @app.route("/dictionary")
# def dictionary_page():
#     return render_template("dictionary.html")

@app.route("/api/dictionary")
def get_dictionary():
    with open("dictionary/signs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)
# ============================================================
# ======================== MAIN ==============================
# ============================================================
if __name__ == "__main__":
    def open_browser():
        time.sleep(2)
        import webbrowser
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser, daemon=True).start()

    print("\n🚀 Phase-1 Sign Language Translator Running")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
