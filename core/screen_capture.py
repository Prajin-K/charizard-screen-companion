"""Screen Capture Pipeline for Charizard Screen Companion.

Provides privacy-first, on-demand screen capture with:
1. In-memory processing (io.BytesIO) - zero disk writes.
2. Active window bounding box detection & cropping (pygetwindow / win32).
3. Safety blacklist check against sensitive window titles (passwords, banks, .env).
4. Dual-engine capture (mss with fallback to Qt QScreen).
"""

import io
import sys
from typing import Optional, Tuple, Dict, Any
from PIL import Image

# Privacy safety blacklist terms (case-insensitive)
SENSITIVE_KEYWORDS = [
    "bitwarden",
    "1password",
    "lastpass",
    "keeper",
    "keepass",
    "dashlane",
    "bank",
    ".env",
    "incognito",
    "inprivate",
    "private browsing",
    "password",
    "credential",
    "secret_key",
    "id_rsa",
    "vault",
]


class PrivacyFilterBlockedError(Exception):
    """Raised when an active window title matches sensitive blacklist terms."""
    pass


def check_privacy_safety(window_title: str) -> Tuple[bool, str]:
    """Inspect active window title against sensitive keywords.

    Args:
        window_title: Title string of the active foreground window.

    Returns:
        Tuple of (is_safe: bool, matched_reason: str).
    """
    if not window_title:
        return True, ""

    title_lower = window_title.lower()
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in title_lower:
            return False, f"Privacy Guard: Active window contains sensitive term '{keyword}'."

    return True, ""


def get_active_window_info() -> Dict[str, Any]:
    """Retrieve title and geometry of the current foreground application.

    Returns:
        Dict with keys:
            - 'title': str
            - 'rect': Tuple[int, int, int, int] (left, top, width, height) or None
    """
    # 1. Try pygetwindow first
    try:
        import pygetwindow as gw
        active_win = gw.getActiveWindow()
        if active_win and active_win.title:
            rect = (active_win.left, active_win.top, active_win.width, active_win.height)
            if active_win.width > 30 and active_win.height > 30:
                return {
                    "title": active_win.title.strip(),
                    "rect": rect,
                }
    except Exception:
        pass

    # 2. Try Windows ctypes Win32 API fallback
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.strip()

                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 30 and h > 30:
                    return {
                        "title": title or "Active Window",
                        "rect": (rect.left, rect.top, w, h),
                    }
        except Exception:
            pass

    return {
        "title": "Full Desktop",
        "rect": None,
    }


def capture_screen_raw() -> Image.Image:
    """Capture the full screen using mss, with fallback to PyQt6 QScreen.

    Returns:
        A PIL.Image.Image object in RGB mode.
    """
    # 1. Primary Engine: mss
    try:
        import mss
        with mss.MSS() as sct:
            # Use monitor 0 (all monitors combined) or primary monitor 1
            monitor = sct.monitors[0] if len(sct.monitors) > 0 else sct.monitors[1]
            sct_img = sct.grab(monitor)
            pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return pil_img
    except Exception as mss_err:
        pass

    # 2. Resilient Fallback Engine: PyQt6 QGuiApplication
    try:
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import QBuffer, QIODevice

        screen = QGuiApplication.primaryScreen()
        if screen:
            pix = screen.grabWindow(0)
            qbuf = QBuffer()
            qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
            pix.save(qbuf, "PNG")
            img_bytes = bytes(qbuf.data())
            return Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as qt_err:
        pass

    # 3. Third Fallback: PIL ImageGrab
    try:
        from PIL import ImageGrab
        return ImageGrab.grab().convert("RGB")
    except Exception as e:
        raise RuntimeError(f"All screen capture engines failed: {e}")


def capture_screen_to_bytes(
    crop_to_active_window: bool = True,
    target_format: str = "PNG"
) -> Tuple[bytes, str, Image.Image]:
    """Perform on-demand, privacy-filtered screen capture entirely in memory.

    Args:
        crop_to_active_window: If True and foreground window is detected,
                              crops the capture to that app's bounding box.
        target_format: 'PNG' or 'JPEG' (default 'PNG').

    Returns:
        Tuple of (image_bytes, window_title, pil_image).

    Raises:
        PrivacyFilterBlockedError: If foreground window contains sensitive keywords.
    """
    # Step 1: Detect active window and inspect privacy filter
    win_info = get_active_window_info()
    win_title = win_info.get("title", "Desktop Screen")
    win_rect = win_info.get("rect")

    is_safe, reason = check_privacy_safety(win_title)
    if not is_safe:
        raise PrivacyFilterBlockedError(
            f"Capture blocked by Privacy Guard!\n"
            f"Active window: '{win_title}'\n"
            f"Reason: {reason}"
        )

    # Step 2: Grab full screen in-memory
    full_image = capture_screen_raw()

    # Step 3: Crop to active window if requested and valid
    captured_image = full_image
    if crop_to_active_window and win_rect:
        left, top, width, height = win_rect
        # Bound coordinates to image dimensions
        img_w, img_h = full_image.size
        crop_x1 = max(0, left)
        crop_y1 = max(0, top)
        crop_x2 = min(img_w, left + width)
        crop_y2 = min(img_h, top + height)

        if (crop_x2 - crop_x1) >= 50 and (crop_y2 - crop_y1) >= 50:
            captured_image = full_image.crop((crop_x1, crop_y1, crop_x2, crop_y2))

    # Step 4: Encode to in-memory bytes (never saved to disk)
    buffer = io.BytesIO()
    if target_format.upper() == "JPEG":
        captured_image.save(buffer, format="JPEG", quality=90, optimize=True)
    else:
        captured_image.save(buffer, format="PNG", optimize=True)

    buffer.seek(0)
    image_bytes = buffer.getvalue()

    return image_bytes, win_title, captured_image
