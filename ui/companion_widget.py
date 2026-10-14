"""Floating Animated Mascot and Companion Widget for Charizard Screen Companion.

Manages:
1. Frameless, translucent, always-on-top floating canvas with High-DPI Pass-Through support.
2. Animated WebP / GIF playback with smooth bilinear filtering (no pixelation or blurriness).
3. Continuous looping and smooth scaling to 130x130 px companion dimensions.
4. Robust fallback chain: charizard_idle.webp -> charizard_idle.gif -> glowing emoji mascot.
5. Drag-and-drop movement across desktop and snapping near borders.
6. Click-to-toggle attached glassmorphic HUD speech card.
7. Pre-capture zero-opacity screen hiding and background vision worker dispatch.
"""

import os
import time
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QApplication,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtGui import (
    QMovie,
    QColor,
    QFont,
    QCursor,
    QGuiApplication,
    QPainter,
    QPaintEvent,
)

from ui.hud_view import HUDView
from core.screen_capture import capture_screen_to_bytes, PrivacyFilterBlockedError
from core.vision_worker import VisionWorker


class MascotLabel(QLabel):
    """Interactive QLabel hosting the animated QMovie with smooth bilinear filtering and drag handling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMouseTracking(True)

        self._movie: QMovie = None
        self._drag_start_pos = None
        self._window_start_pos = None
        self._is_dragging = False
        self._press_time = 0

    def setMovie(self, movie: QMovie):
        """Bind QMovie and connect frame update for smooth repainting."""
        super().setMovie(movie)
        self._movie = movie
        if movie:
            movie.frameChanged.connect(lambda: self.update())

    def paintEvent(self, event: QPaintEvent):
        """Paint movie frames with smooth bilinear filtering, anti-aliasing, and watermark masking."""
        if self._movie and self._movie.isValid():
            pixmap = self._movie.currentPixmap()
            if not pixmap.isNull():
                pw = pixmap.width()
                ph = pixmap.height()

                # Dynamic Watermark Safeguard:
                # If frame is uncropped or wide (> 1.37 ratio), crop out the right 16% and bottom 8%
                # where the watermark/diamond icon resides, preserving only the centered Charizard.
                if pw > int(ph * 1.37):
                    clean_w = int(pw * 0.84)
                    clean_h = int(ph * 0.95)
                    pixmap = pixmap.copy(0, 0, clean_w, clean_h)

                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

                # Scale proportionally with smooth transformation
                target_rect = self.rect()
                scaled_pix = pixmap.scaled(
                    target_rect.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                # Center the rendered mascot within the label
                x = (target_rect.width() - scaled_pix.width()) // 2
                y = (target_rect.height() - scaled_pix.height()) // 2
                painter.drawPixmap(x, y, scaled_pix)
                painter.end()
                return

        super().paintEvent(event)

    def mousePressEvent(self, event):
        """Track click origin and initial window position."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            window = self.window()
            if window:
                self._window_start_pos = window.pos()
            self._is_dragging = False
            self._press_time = time.time()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Perform smooth window dragging when mouse moves beyond threshold."""
        if self._drag_start_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self._drag_start_pos

            # If moved more than 4 pixels, consider it a drag
            if delta.manhattanLength() > 4 or self._is_dragging:
                self._is_dragging = True
                window = self.window()
                if window and self._window_start_pos is not None:
                    window.move(self._window_start_pos + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Toggle HUD if clicked, or snap window if dragged near borders."""
        if event.button() == Qt.MouseButton.LeftButton:
            elapsed = time.time() - self._press_time
            window = self.window()

            if not self._is_dragging and elapsed < 0.4:
                # User clicked Charizard -> toggle HUD
                if hasattr(window, "toggle_hud"):
                    window.toggle_hud()
            else:
                # User finished dragging -> apply snap-to-border logic
                if hasattr(window, "snap_to_screen_borders"):
                    window.snap_to_screen_borders()

            self._drag_start_pos = None
            self._window_start_pos = None
            self._is_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """Show sleek right-click context menu with Restart and Quit options."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(26, 20, 18, 0.96);
                color: #f5eee6;
                border: 1px solid rgba(255, 85, 0, 0.5);
                border-radius: 8px;
                padding: 4px;
                font-size: 11px;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QMenu::item {
                padding: 6px 18px 6px 10px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 85, 0, 0.35);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 85, 0, 0.2);
                margin: 4px 6px;
            }
        """)

        restart_action = menu.addAction("🔄  Restart Companion")
        menu.addSeparator()
        quit_action = menu.addAction("❌  Quit")

        selected = menu.exec(event.globalPos())
        window = self.window()

        if selected == restart_action:
            if hasattr(window, "restart_app"):
                window.restart_app()
        elif selected == quit_action:
            QApplication.quit()


class CompanionWidget(QWidget):
    """Floating Desktop Mascot and Attached HUD Controller."""

    def __init__(self, asset_path: str = "charizard_idle.webp", parent=None):
        super().__init__(parent)
        self.asset_path = asset_path
        self.hud_visible = False
        self.vision_worker: VisionWorker = None
        self.movie: QMovie = None

        # Fixed companion sizing (130x130 px for razor-sharp high-DPI scaling)
        self.mascot_size = QSize(130, 130)

        self.init_window_properties()
        self.init_ui()
        self.init_movie()

    def init_window_properties(self):
        """Configure frameless, translucent, always-on-top window attributes."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def init_ui(self):
        """Build layout with Mascot on the left and attached HUD on the right."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Mascot container
        self.mascot_container = QWidget(self)
        self.mascot_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.mascot_container.setFixedSize(self.mascot_size)

        mascot_layout = QVBoxLayout(self.mascot_container)
        mascot_layout.setContentsMargins(0, 0, 0, 0)
        mascot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot label
        self.mascot_label = MascotLabel(self.mascot_container)
        self.mascot_label.setFixedSize(self.mascot_size)
        self.mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mascot_layout.addWidget(self.mascot_label)

        # Subtle warm ember aura behind Charizard
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(20)
        glow.setColor(QColor(255, 120, 0, 100))
        glow.setOffset(0, 0)
        self.mascot_label.setGraphicsEffect(glow)

        self.main_layout.addWidget(self.mascot_container)

        # Glassmorphic HUD Card
        self.hud = HUDView(self)
        self.hud.close_requested.connect(self.hide_hud)
        self.hud.query_submitted.connect(self.handle_query)
        self.main_layout.addWidget(self.hud)

        # Default state: HUD collapsed, mascot only
        self.hud.hide()
        self.hud_visible = False
        self.adjustSize()

    def init_movie(self):
        """Initialize continuous animated WebP playback with fallback chain."""
        # Candidate 1: Preferred animated WebP asset
        base_dir = os.path.dirname(os.path.abspath(self.asset_path)) if os.path.isabs(self.asset_path) else os.getcwd()
        candidate_files = [
            os.path.abspath(self.asset_path),
            os.path.join(base_dir, "charizard_idle.webp"),
            os.path.join(base_dir, "charizard_idle.gif"),
        ]

        for candidate in candidate_files:
            if os.path.exists(candidate):
                movie = QMovie(candidate)
                if movie.isValid():
                    # Low-Memory Streaming Mode: avoids caching 240 uncompressed frames in RAM (~45MB footprint)
                    self.movie.setCacheMode(QMovie.CacheMode.CacheNone)
                    # Smooth display scaling
                    self.movie.setScaledSize(self.mascot_size)

                    # Continuous seamless looping
                    try:
                        self.movie.setLoopCount(-1)
                    except Exception:
                        pass
                    self.movie.finished.connect(self.movie.start)

                    self.mascot_label.setMovie(self.movie)
                    self.movie.start()
                    return

        # Candidate 2: Graceful Fallback to Animated Amber Glowing Emoji Mascot
        self.render_fallback_mascot()

    def render_fallback_mascot(self):
        """Render emoji fallback with amber glow if animation assets are absent or corrupt."""
        self.mascot_label.setText("🔥🦎")
        self.mascot_label.setFont(QFont("Segoe UI Emoji", 38))
        self.mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mascot_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #ff6600;
            }
        """)

    def toggle_hud(self):
        """Toggle HUD card visibility with boundary clamping."""
        if self.hud_visible:
            self.hide_hud()
        else:
            self.show_hud()

    def show_hud(self):
        """Expand window and display HUD card."""
        self.hud_visible = True
        self.hud.show()
        self.adjustSize()

        # Ensure window doesn't overflow right or bottom screen boundary
        self.clamp_to_screen()

    def hide_hud(self):
        """Collapse HUD card and shrink window back to mascot only."""
        self.hud_visible = False
        self.hud.hide()
        self.adjustSize()

    def clamp_to_screen(self):
        """Keep the companion window comfortably within screen bounds."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        screen_geo = screen.availableGeometry()
        x = self.x()
        y = self.y()
        w = self.width()
        h = self.height()

        # If extending past right edge, shift left
        if x + w > screen_geo.right():
            x = max(screen_geo.left(), screen_geo.right() - w - 10)
        # If extending past bottom edge, shift up
        if y + h > screen_geo.bottom():
            y = max(screen_geo.top(), screen_geo.bottom() - h - 10)

        self.move(x, y)

    def snap_to_screen_borders(self, snap_distance: int = 30):
        """Snap mascot near screen borders if dropped close to edges."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        geo = screen.availableGeometry()
        curr_x = self.x()
        curr_y = self.y()
        target_x = curr_x
        target_y = curr_y

        # Snap to Left or Right
        if abs(curr_x - geo.left()) < snap_distance:
            target_x = geo.left() + 10
        elif abs((curr_x + self.width()) - geo.right()) < snap_distance:
            target_x = geo.right() - self.width() - 10

        # Snap to Top or Bottom
        if abs(curr_y - geo.top()) < snap_distance:
            target_y = geo.top() + 10
        elif abs((curr_y + self.height()) - geo.bottom()) < snap_distance:
            target_y = geo.bottom() - self.height() - 10

        if target_x != curr_x or target_y != curr_y:
            self.move(target_x, target_y)

    def handle_query(self, action_type: str, custom_prompt: str):
        """Perform on-demand capture and run vision reasoning worker."""
        # 1. Update UI status to scanning
        self.hud.set_status("Scanning Screen...", color="#3399ff")
        self.hud.set_busy(True, message="Scanning Screen...")

        # 2. Privacy-first Pre-capture Hiding:
        # Hide companion so it doesn't photograph itself
        self.setWindowOpacity(0.0)
        QApplication.processEvents()

        image_bytes = None
        window_title = ""

        try:
            # Short event flush for compositor repainting
            time.sleep(0.06)
            QApplication.processEvents()

            # Execute capture pipeline
            crop_mode = self.hud.crop_active_window
            image_bytes, window_title, _ = capture_screen_to_bytes(
                crop_to_active_window=crop_mode,
                target_format="PNG",
            )

        except PrivacyFilterBlockedError as blocked_err:
            # Restore visibility and alert user
            self.setWindowOpacity(1.0)
            self.hud.set_busy(False)
            self.hud.display_error(f"🛡️ **Privacy Guard Triggered**\n\n{str(blocked_err)}")
            return

        except Exception as cap_err:
            self.setWindowOpacity(1.0)
            self.hud.set_busy(False)
            self.hud.display_error(f"⚠️ **Capture Error:** {str(cap_err)}")
            return

        finally:
            # Always restore mascot visibility
            self.setWindowOpacity(1.0)
            QApplication.processEvents()

        # 3. Launch background QThread worker
        self.hud.set_status(f"Flamethrower Analyzing ({window_title[:20]})...", color="#ff5500")

        self.vision_worker = VisionWorker(
            image_bytes=image_bytes,
            prompt=custom_prompt,
            action_type=action_type,
            mime_type="image/png",
            parent=self,
        )

        self.vision_worker.status_changed.connect(
            lambda msg: self.hud.set_status(msg, color="#ff5500")
        )
        self.vision_worker.response_ready.connect(self._on_worker_response)
        self.vision_worker.error_occurred.connect(self._on_worker_error)
        self.vision_worker.finished.connect(self._on_worker_finished)

        self.vision_worker.start()

    def _on_worker_response(self, response_text: str):
        """Display successful Gemini vision analysis in HUD."""
        self.hud.display_markdown(response_text)
        self.hud.set_status("Done - Flames settled", color="#00e676")

    def _on_worker_error(self, error_message: str):
        """Display error response in HUD."""
        self.hud.display_error(error_message)

    def _on_worker_finished(self):
        """Reset busy state once background processing terminates."""
        self.hud.set_busy(False)
        self.vision_worker = None

    def restart_app(self):
        """Relaunch the companion process and exit current instance."""
        import sys
        import subprocess

        # Launch fresh instance
        subprocess.Popen([sys.executable] + sys.argv)
        # Terminate current instance
        QApplication.quit()
