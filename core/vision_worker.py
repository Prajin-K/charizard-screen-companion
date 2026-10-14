"""Asynchronous Multimodal Vision Worker for Charizard Screen Companion.

Executes Google GenAI API calls on a dedicated QThread to ensure 60 FPS GUI responsiveness.
Loads GEMINI_API_KEY from .env, prepares in-memory image parts, and generates markdown insights.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

# Standard Charizard Persona System Instruction
CHARIZARD_SYSTEM_PROMPT = """You are 'Charizard', an expert AI screen companion and fiery pair-programming dragon assistant.
You possess razor-sharp vision and deep technical knowledge across software development, system design, debugging, UI/UX, and mathematics.

Guidelines:
1. Speak in a confident, friendly, helpful, and energetic tone (with occasional subtle fiery/dragon charm, e.g., 'Eyes blazing', 'Spotted with dragon vision!').
2. When answering, be clear, structured, and direct.
3. Use Github-flavored Markdown:
   - Use bold headers (##, ###)
   - Use code blocks with language identifiers (e.g. ```python, ```bash, ```javascript)
   - Highlight key terms, file names, or terminal commands
4. Focus strictly on what is visible in the provided screenshot.
"""

# Quick Action Prompt Presets
PROMPT_PRESETS = {
    "summarize": (
        "Analyze the provided screen capture. Provide a high-level visual and textual summary "
        "in exactly 3 concise, impactful bullet points. Mention the active app/context, the main "
        "task or content displayed, and any immediate notable takeaways."
    ),
    "debug": (
        "Inspect the visible code, terminal output, stack trace, IDE red underlines, or console errors "
        "on this screen. Identify any bugs, syntax mistakes, or runtime exceptions. "
        "Explain exactly what is wrong and provide the corrected code snippet or command to fix it."
    ),
    "explain": (
        "Analyze the flowchart, diagram, architecture diagram, UI layout, algorithm, or document visible "
        "on this screen. Break down the core concepts into simple, structured explanations with "
        "intuitive analogies and step-by-step logic."
    ),
}


class VisionWorker(QThread):
    """Worker thread that executes multimodal vision inference without blocking the UI."""

    # Qt Signals for GUI communication
    status_changed = pyqtSignal(str)       # e.g., "Flamethrower Analyzing..."
    response_ready = pyqtSignal(str)       # Full generated markdown response
    error_occurred = pyqtSignal(str)       # Friendly error description
    finished = pyqtSignal()                # Thread lifecycle completion

    def __init__(
        self,
        image_bytes: bytes,
        prompt: str,
        action_type: str = "custom",
        mime_type: str = "image/png",
        parent=None,
    ):
        """Initialize the vision worker.

        Args:
            image_bytes: In-memory bytes of the captured screen.
            prompt: User-provided query or preset prompt text.
            action_type: One of 'summarize', 'debug', 'explain', or 'custom'.
            mime_type: MIME type of the image bytes ('image/png' or 'image/jpeg').
            parent: Optional QObject parent.
        """
        super().__init__(parent)
        self.image_bytes = image_bytes
        self.prompt = prompt
        self.action_type = action_type
        self.mime_type = mime_type

    def run(self):
        """Thread execution entry point."""
        try:
            # Step 1: Securely load .env and check API key
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key or api_key.strip() == "" or "your_gemini_api_key_here" in api_key:
                self.error_occurred.emit(
                    "⚠️ **Error: GEMINI_API_KEY not found in .env**\n\n"
                    "Please create a `.env` file in the project folder with your key:\n"
                    "```ini\n"
                    "GEMINI_API_KEY=AIzaSy...\n"
                    "```\n"
                    "Get a key for free at [Google AI Studio](https://aistudio.google.com/)."
                )
                self.finished.emit()
                return

            self.status_changed.emit("Flamethrower Analyzing...")

            # Step 2: Initialize Google GenAI client
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key.strip())

            # Step 3: Determine the effective prompt
            effective_prompt = self.prompt
            if self.action_type in PROMPT_PRESETS and not self.prompt.strip():
                effective_prompt = PROMPT_PRESETS[self.action_type]
            elif self.action_type in PROMPT_PRESETS and self.prompt.strip():
                effective_prompt = f"{PROMPT_PRESETS[self.action_type]}\n\nAdditional User Request: {self.prompt.strip()}"

            # Step 4: Package in-memory image part and prompt contents
            image_part = types.Part.from_bytes(
                data=self.image_bytes,
                mime_type=self.mime_type,
            )

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        image_part,
                        types.Part.from_text(text=effective_prompt),
                    ],
                )
            ]

            # Step 5: Configure generation with Charizard system instructions
            config = types.GenerateContentConfig(
                system_instruction=CHARIZARD_SYSTEM_PROMPT,
                temperature=0.4,
            )

            # Step 6: Generate response with automatic resilient model fallback
            CANDIDATE_MODELS = [
                "gemini-3-flash-preview",
                "gemini-3.8-flash",
                "gemini-flash-latest",
                "gemini-3.1-flash-lite",
            ]

            response = None
            last_err = None

            for model_name in CANDIDATE_MODELS:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                    if response and response.text:
                        break
                except Exception as model_err:
                    last_err = model_err
                    continue

            if response and response.text:
                self.response_ready.emit(response.text)
            elif last_err:
                raise last_err
            else:
                self.error_occurred.emit("⚠️ Charizard did not receive any text response from Gemini.")

        except Exception as exc:
            err_msg = str(exc)
            # Provide actionable error context
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                user_msg = "🔥 **Rate Limit or Quota Exceeded (429)**\nPlease wait a moment before asking again or check your Gemini API quota."
            elif "API_KEY_INVALID" in err_msg or "400" in err_msg and "API key" in err_msg:
                user_msg = "🔑 **Invalid API Key**\nPlease verify that your `GEMINI_API_KEY` in `.env` is correct."
            elif "timed out" in err_msg.lower() or "connection" in err_msg.lower():
                user_msg = "🌐 **Network Timeout**\nCharizard could not reach Google servers. Please check your internet connection."
            else:
                user_msg = f"🔥 **Analysis Error:**\n```\n{err_msg}\n```"

            self.error_occurred.emit(user_msg)

        finally:
            self.finished.emit()
