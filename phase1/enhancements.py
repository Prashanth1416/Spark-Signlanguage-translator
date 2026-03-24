from collections import deque
import time

# ===============================
# Gesture Stabilization
# ===============================
PREDICTION_WINDOW = 10
STABLE_THRESHOLD = 6

gesture_buffer = deque(maxlen=PREDICTION_WINDOW)

def get_stable_gesture(new_gesture):
    gesture_buffer.append(new_gesture)

    if len(gesture_buffer) < PREDICTION_WINDOW:
        return "None"

    counts = {}
    for g in gesture_buffer:
        if g != "None":
            counts[g] = counts.get(g, 0) + 1

    for gesture, count in counts.items():
        if count >= STABLE_THRESHOLD:
            return gesture

    return "None"

# ===============================
# Sentence Builder + Auto Pause
# ===============================
sentence_buffer = []
last_added_word = None
last_gesture_time = time.time()

PAUSE_THRESHOLD = 1.8  # seconds

def update_sentence(word):
    global last_added_word, last_gesture_time

    now = time.time()

    if word != "None":
        last_gesture_time = now

        if word != last_added_word:
            sentence_buffer.append(word)
            last_added_word = word

    if len(sentence_buffer) > 15:
        sentence_buffer.pop(0)

    return " ".join(sentence_buffer)

def check_auto_pause():
    """
    Returns finalized sentence if pause detected,
    otherwise returns None
    """
    global last_gesture_time, last_added_word

    if not sentence_buffer:
        return None

    if time.time() - last_gesture_time >= PAUSE_THRESHOLD:
        final_sentence = " ".join(sentence_buffer)
        sentence_buffer.clear()
        last_added_word = None
        return final_sentence

    return None

def clear_sentence():
    global last_added_word
    sentence_buffer.clear()
    last_added_word = None
