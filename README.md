#  Charizard Screen Companion

> An interactive, floating, animated desktop pet that visually understands your screen on-demand and answers questions, debugs errors, or summarizes content using Google Gemini Multimodal Vision without manual screenshots.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green?logo=qt)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini%20Vision-orange?logo=google)
![Privacy](https://img.shields.io/badge/Privacy-First%20Design-brightgreen)
![License](https://img.shields.io/badge/License-MIT-purple)

---

##  Key Features

- **Draggable Animated Desktop Pet**: Seamlessly looping 240-frame Chibi Charizard (`charizard_idle.webp` with `charizard_idle.gif` fallback) floating on your desktop with smooth bilinear filtering, transparent background, and border snapping.
- **Glassmorphic HUD Card**: Dark translucent speech bubble (`rgba(22, 18, 16, 0.94)`) with ember accents (`#ff5500`), clean typography, and embedded markdown browser.
- **Privacy-First In-Memory Capture**:
  - Never streams continuous video.
  - Takes on-demand captures only when triggered.
  - Automatically zero-opacities companion during screenshot to prevent self-capture.
  - Keeps all images strictly in volatile RAM (`io.BytesIO`)—no unencrypted screenshot files written to disk.
  - **Safety Guard**: Blocks capture if sensitive window titles (e.g., Bitwarden, 1Password, Banking, `.env`, Incognito) are active.
  - **Active Window Cropping**: Option to crop directly to the focused application instead of multi-monitor desktops.
- **Asynchronous Multimodal Vision**: Powered by `google-genai` with an automatic model fallback cascade (`gemini-3-flash-preview`, `gemini-3.8-flash`, `gemini-flash-latest`, `gemini-3.1-flash-lite`) running on a background `QThread` to maintain a silky 60 FPS GUI.
- **Memory Optimized**: Employs on-demand frame streaming (`QMovie.CacheMode.CacheNone`), keeping the entire application's footprint under ~45 MB of RAM.
- **Quick Action Buttons**:
  -  **Summarize Screen**: Extracts the key visual and textual takeaways in 3 concise bullet points.
  -  **Debug & Fix Errors**: Detects visible code bugs, syntax errors, and stack traces with instant fixes.
  -  **Explain Concept/Diagram**: Explains flowcharts, architectures, papers, or dense documents.
  -  **Ask Charizard**: Custom question input field with Enter/Send support.

---

## 📂 Project Structure

```text
orb-desktop-agent/
├── charizard_idle.webp       # High-res animated mascot asset (smooth 240-frame WebP)
├── charizard_idle.gif        # Animated mascot asset fallback
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── main.py                   # Application entry point & High-DPI Pass-Through setup
├── core/
│   ├── __init__.py
│   ├── screen_capture.py     # Privacy filter, active window crop, in-memory mss/Qt capture
│   └── vision_worker.py      # QThread worker calling Gemini API with model cascade
├── ui/
│   ├── __init__.py
│   ├── companion_widget.py   # Floating mascot, WebP animation, drag, context menu, & snapping
│   └── hud_view.py           # Glassmorphism speech bubble, controls, and markdown output
└── README.md                 # Project documentation
```

---

##  Quick Start Guide

### 1. Clone the Repository & Install Dependencies

```bash
git clone https://github.com/Prajin-K/charizard-screen-companion.git
cd charizard-screen-companion

pip install -r requirements.txt
```

*(Requirements: `PyQt6`, `mss`, `Pillow`, `pygetwindow`, `google-genai`, `python-dotenv`)*

### 2. Configure Your Gemini API Key

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *(On Windows Command Prompt: `copy .env.example .env`)*

2. Open `.env` and add your API key:
   ```ini
   GEMINI_API_KEY=AIzaSyYourActualKeyHere
   ```
   >  You can get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/).

### 3. Launch the Companion

```bash
python main.py
```

---

##  Controls & Interactions

| Action | Control |
|---|---|
| **Drag Mascot** | Click and hold Charizard with the **Left Mouse Button** to move him across your desktop. |
| **Snap to Edge** | Release Charizard within 30px of any screen boundary to automatically snap to the edge. |
| **Toggle HUD** | Left-click Charizard to expand or collapse the attached glassmorphic AI card. |
| **Context Menu** | **Right-click Charizard** to access `🔄 Restart Companion` or `❌ Quit`. |
| **Crop Active App** | Toggle the `🪟 App` / `🖥️ Full` pill in the HUD header to switch between capturing only the focused app or your entire display. |
| **Copy Response** | Click the `📋 Copy` button to copy the AI's markdown response to your clipboard. |
| **Close / Retract** | Click the `✕` button on the top-right of the HUD to collapse it back into the pet. |

---

##  Privacy & Security Architecture

1. **Zero Disk Storage**: Screen captures are processed entirely inside volatile RAM (`io.BytesIO`) using `PIL.Image` and streamed directly to Gemini as in-memory byte parts.
2. **Foreground Safety Guard**: Before any capture occurs, the active foreground window title is checked against a blacklist:
   ```python
   ["bitwarden", "1password", "bank", ".env", "incognito", "vault", "password", ...]
   ```
   If a match is found, the capture is blocked, and a privacy notification is displayed on the HUD.
3. **Ghost Capture**: The companion window drops opacity to 0% before screen grabbing, ensuring it never captures or occludes itself.

---

##  Fallback Protection

- If `charizard_idle.webp` is absent or fails decoding, the app automatically falls back to `charizard_idle.gif`.
- If both animation assets are missing, the companion falls back to an amber-glowing emoji mascot (`🔥🦎`) with drop-shadow effects, guaranteeing that the application never crashes on launch.

---

## 📜 License

MIT License. Feel free to use, modify, and build upon this project.
