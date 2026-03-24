let mediaStream = null;
let isRunning = false;
let frameHistory = [];
let lastSpoken = null;
let sentence = "";
let processingFrame = false;

// ===== CRITICAL SETTINGS FOR SPEED =====
const HISTORY_SIZE = 5;
const STABILITY_RATIO = 0.70;
const FRAME_INTERVAL = 33;
const CONFIDENCE_THRESHOLD = 0.70;
// ======================================

async function initWebcam() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            },
            audio: false
        });
        
        const video = document.getElementById("webcam");
        video.srcObject = mediaStream;
        
        return new Promise((resolve) => {
            video.onloadedmetadata = () => {
                video.play();
                resolve();
            };
        });
    } catch (err) {
        alert("Camera access denied: " + err.message);
    }
}

if (document.getElementById("startBtn")) {
    document.getElementById("startBtn").addEventListener("click", async () => {
        await initWebcam();
        isRunning = true;
        document.getElementById("startBtn").disabled = true;
        document.getElementById("stopBtn").disabled = false;
        processFrames();
    });

    document.getElementById("stopBtn").addEventListener("click", () => {
        isRunning = false;
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
        }
        document.getElementById("startBtn").disabled = false;
        document.getElementById("stopBtn").disabled = true;
    });

    document.getElementById("clearBtn").addEventListener("click", () => {
        sentence = "";
        frameHistory = [];
        lastSpoken = null;
        updateDisplay();
    });

    document.getElementById("speakBtn").addEventListener("click", () => {
        const lang = document.getElementById("languageSelect").value || "en";
        if (sentence.trim()) {
            translateAndSpeak(sentence.trim(), lang);
        }
    });

    document.getElementById("copyBtn").addEventListener("click", () => {
        navigator.clipboard.writeText(sentence);
        alert("Copied to clipboard!");
    });

    document.getElementById("languageSelect").addEventListener("change", () => {
        const lang = document.getElementById("languageSelect").value;
        const translatedBox = document.getElementById("translatedBox");
        
        if (lang === "en") {
            translatedBox.style.display = "none";
        } else {
            translatedBox.style.display = "block";
            updateDisplay();
        }
    });
}

async function processFrames() {
    if (!isRunning) return;

    if (processingFrame) {
        setTimeout(processFrames, FRAME_INTERVAL);
        return;
    }

    processingFrame = true;

    const video = document.getElementById("webcam");
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d", { alpha: false });

    try {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);

        const imgData = canvas.toDataURL("image/jpeg", 0.65);

        const response = await fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ frame: imgData })
        });

        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                handlePrediction(result.gesture, result.confidence);
            }
        }
    } catch (err) {
        console.error("Prediction error:", err);
    } finally {
        processingFrame = false;
    }

    setTimeout(processFrames, FRAME_INTERVAL);
}

function handlePrediction(gesture, confidence) {
    if (confidence < CONFIDENCE_THRESHOLD || gesture === "None") {
        document.getElementById("gesture").textContent = gesture;
        document.getElementById("confidence").textContent = `Confidence: ${(confidence * 100).toFixed(0)}%`;
        return;
    }

    frameHistory.push(gesture);
    if (frameHistory.length > HISTORY_SIZE) {
        frameHistory.shift();
    }

    if (frameHistory.length === HISTORY_SIZE) {
        const mostCommon = getMostCommon(frameHistory);
        const freq = frameHistory.filter(g => g === mostCommon).length;
        const stability = freq / HISTORY_SIZE;

        if (stability >= STABILITY_RATIO && mostCommon !== lastSpoken) {
            addWord(mostCommon);
            lastSpoken = mostCommon;
            frameHistory = [];
        }
    }

    document.getElementById("gesture").textContent = gesture;
    document.getElementById("confidence").textContent = `Confidence: ${(confidence * 100).toFixed(0)}%`;
    updateDisplay();
}

function getMostCommon(arr) {
    const counts = {};
    let maxCount = 0;
    let mostCommon = arr[0];

    for (let item of arr) {
        counts[item] = (counts[item] || 0) + 1;
        if (counts[item] > maxCount) {
            maxCount = counts[item];
            mostCommon = item;
        }
    }

    return mostCommon;
}

function addWord(word) {
    const lang = document.getElementById("languageSelect").value || "en";
    
    if (word === "space") {
        sentence += " ";
    } else if (word === "del") {
        sentence = sentence.slice(0, -1);
    } else if (word !== "None") {
        sentence += word + " ";
        // Translate and speak immediately
        translateAndSpeak(word, lang);
    }
    updateDisplay();
}

function updateDisplay() {
    const display = document.getElementById("sentence");
    display.textContent = sentence || "[Waiting for gestures...]";
    display.scrollTop = display.scrollHeight;
    updateTranslation();
}

async function updateTranslation() {
    const lang = document.getElementById("languageSelect").value;
    
    if (lang === "en" || !sentence.trim()) {
        return;
    }

    try {
        const response = await fetch("/api/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: sentence.trim(), lang: lang })
        });

        if (response.ok) {
            const result = await response.json();
            document.getElementById("translatedText").textContent = result.translated || sentence;
        }
    } catch (err) {
        console.error("Translation error:", err);
    }
}

async function translateAndSpeak(word, lang) {
    if (lang === "en") {
        // English - speak directly
        speakWord(word, lang);
        return;
    }

    // Translate to target language
    try {
        const response = await fetch("/api/translate-word", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ word: word, lang: lang })
        });

        if (response.ok) {
            const result = await response.json();
            const translatedWord = result.translated;
            
            // Speak the TRANSLATED word in target language
            speakWord(translatedWord, lang);
        } else {
            // Fallback to English
            speakWord(word, lang);
        }
    } catch (err) {
        console.error("Translation error:", err);
        speakWord(word, lang);
    }
}

function speakWord(text, lang) {
    // Speak text in specified language
    fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text, lang: lang })
    }).catch(err => console.error("TTS error:", err));
}

function renderDictionary(data) {
  const container = document.getElementById("dictionaryContainer");
  container.innerHTML = "";

  for (const category in data) {
    container.innerHTML += `<div class="category-title">${category.toUpperCase()}</div>`;
    container.innerHTML += `<div class="cards" id="cat-${category}"></div>`;

    const catDiv = document.getElementById(`cat-${category}`);

    data[category].forEach(sign => {
      catDiv.innerHTML += `
        <div class="sign-card">
          <h4>${sign.word}</h4>
          <img src="/static/signs/${sign.file}" alt="${sign.word}">
          <p>${sign.description}</p>
          <small>Difficulty: ${sign.difficulty}</small>
        </div>
      `;
    });
  }
}

if (data.sentence !== undefined) {
    document.getElementById("sentenceText").innerText = data.sentence;
}
if (data.final_sentence) {
    document.getElementById("finalSentence").innerText =
        data.final_sentence;
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        console.log("🚀 Sign Translator Ready - Multi-Language TTS Mode!");
    });
} else {
    console.log("🚀 Sign Translator Ready - Multi-Language TTS Mode!");
}