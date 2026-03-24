# Sign Language Translator

Real-time sign language translator built with **Flask**, TensorFlow, MediaPipe, and OpenCV for the browser, with multilingual translation and text‑to‑speech (TTS) support.[file:2]

The app detects hand gestures from a webcam feed, classifies them into sign vocabulary using a trained ML model, translates the recognized word/sentence into Indian languages, and plays audio output.[file:2][file:4]

---

## Key Features

- Real-time hand gesture recognition using MediaPipe Hands (up to 2 hands).[file:2][file:4]  
- TensorFlow/Keras model for sign classification (trained on 126‑feature hand landmark vectors).![file:4]  
- Multilingual translation for 10 languages: English, Tamil, Hindi, Telugu, Malayalam, Kannada, Marathi, Gujarati, Bengali, Punjabi.[file:2][file:4]  
- Text-to-speech using gTTS, with background queue for smooth non-blocking playback.[file:2][file:4]  
- Web-based UI via Flask (HTML templates + JS) with live camera preview and overlayed detections.[file:2][file:4]  
- Packaged Windows `.exe` build using PyInstaller for easy non-Python distribution (optional).[file:2]

---

## Tech Stack

- Backend: Flask, Flask-CORS.[file:2][file:4]  
- Computer Vision: OpenCV, MediaPipe Hands.[file:2][file:4]  
- Machine Learning: TensorFlow/Keras, scikit-learn, NumPy, pandas.[file:3][file:4]  
- Translation: `deep-translator` (Google Translate backend).[file:2][file:4]  
- Text-to-Speech: `gTTS` (Google Text-to-Speech).[file:2][file:4]  
- Platform: Tested on Windows 10/11, Python 3.10.x.[file:3][file:4]  

---

## Directory Structure

```text
project-root/
├─ app.py                  # Flask backend with MediaPipe & ML
├─ trainmodel.py           # Training script for gesture model
├─ requirements.txt        # Python dependencies
├─ models/
│  ├─ twohandmlp.h5        # Trained Keras model
│  └─ twohandlabelclasses.npy  # Gesture labels
├─ templates/
│  ├─ index.html           # Home page
│  ├─ translator.html      # Main translator UI
│  └─ about.html           # About page
├─ static/
│  ├─ css/
│  │  └─ style.css
│  └─ js/
│     ├─ app.js
│     └─ camera.js
└─ .venv/                  # (optional) Virtual environment
```

[file:2][file:4]

---

## Installation

### 1. Create and Activate Virtual Environment

```bash
# Windows (PowerShell)
cd path\to\project
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Windows (cmd)
.\.venv\Scripts\activate.bat

# macOS / Linux
cd /path/to/project
python -m venv .venv
source .venv/bin/activate
```

[file:3][file:4]

### 2. Install Dependencies

Recommended `requirements.txt` (no pinned versions for easier install):[file:3]

```txt
Flask
Flask-CORS
opencv-python
mediapipe
tensorflow
numpy
Pillow
deep-translator
gtts
```

Install:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

[file:3][file:4]

If you hit version issues on Windows, a known working stack is:[file:4]

- Python 3.10.x  
- TensorFlow 2.10.0  
- NumPy 1.26.4  
- MediaPipe 0.10.11  
- Protobuf 3.19.6  

```bash
pip install "numpy==1.26.4" "tensorflow==2.10.0" "mediapipe==0.10.11" "protobuf==3.19.6"
```

[file:4]

---

## Training the Model (Optional)

If you want to retrain the gesture model:[file:4]

1. Prepare a CSV dataset `twohandsigns.csv` (features + `label` column).  
2. Update the CSV path in `trainmodel.py`.  
3. Run:[file:4]

```bash
python trainmodel.py
```

This generates `models/twohandmlp.h5` and `models/twohandlabelclasses.npy`.[file:4]

---

## Running the Application

From the project root with the virtual environment activated:[file:3][file:4]

```bash
python app.py
```

What happens:[file:2][file:4]

- Backend starts at `http://127.0.0.1:5000`.  
- A browser window automatically opens at `/translator` (if enabled).[file:2][file:4]  
- Allow camera access in the browser.

Then:[file:4]

1. Show sign gestures to the camera.  
2. Recognized gesture and confidence appear on screen.  
3. Choose target language from the dropdown.  
4. Click “Translate” to see translated text.  
5. Click “Speak” to hear the translated audio.[file:2][file:4]

---

## Building a Windows Executable (Optional)

You can bundle the app as a standalone `.exe` using PyInstaller:[file:2]

1. Install PyInstaller inside the venv:

```bash
pip install pyinstaller
```

[file:2]

2. Run from project root:[file:2]

```bash
pyinstaller -w -F ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "models;models" ^
  app.py
```

3. Find the built executable in `dist/` and run it.[file:2]

The app opens the browser automatically and runs without requiring Python on the target machine.[file:2]

---

## API Endpoints

| Endpoint          | Method | Description                                |
|-------------------|--------|--------------------------------------------|
| `/`               | GET    | Home page.[file:4]                         |
| `/translator`     | GET    | Main translator UI.[file:4]                |
| `/about`          | GET    | About page.[file:4]                        |
| `/api/languages`  | GET    | List of supported languages.[file:2][file:4] |
| `/api/predict`    | POST   | Predict gesture from webcam frame.[file:2][file:4] |
| `/api/translate-word` | POST | Translate a single detected word.[file:2][file:4] |
| `/api/translate`  | POST   | Translate a full sentence.[file:2][file:4] |
| `/api/speak`      | POST   | Queue text for TTS playback.[file:2][file:4] |

---

## Troubleshooting (Quick Notes)

- **No matching distribution for `opencv-python==4.8.0`**  
  Use `opencv-python==4.8.0.74` or a newer version.[file:3]

- **TensorFlow / MediaPipe DLL errors on Windows**  
  Install Microsoft Visual C++ Redistributable (x64) and restart, then re‑activate the venv.[file:3][file:4]

- **NumPy 2.x compatibility error**  
  Force reinstall NumPy 1.26.4.[file:4]

```bash
pip install "numpy==1.26.4" --force-reinstall
```

- **Protobuf builder error with MediaPipe**  

```bash
pip uninstall -y protobuf
pip install "protobuf==3.19.6"
```

[file:4]

---

## Future Work / Roadmap

- Android native app using MediaPipe Tasks + TensorFlow Lite for on-device inference.[file:2]  
- Improved gesture vocabulary and continuous sentence mode.  
- Offline translation and TTS on mobile devices.[file:2]
