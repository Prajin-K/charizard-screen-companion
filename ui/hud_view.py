"""Glassmorphic HUD Card View for Charizard Screen Companion.

Implements the sleek dark translucent speech card styled after the AI Companion prototype:
- Charcoal backdrop with subtle ember/orange borders.
- Header with status indicators ('Idle', 'Scanning Screen...', 'Flamethrower Analyzing...', 'Done').
- Markdown output panel for AI responses.
- Quick action buttons ('Summarize Screen', 'Debug & Fix Errors', 'Explain Concept/Diagram').
- Custom query QLineEdit with Send button.
- Minimize/collapse toggle.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextBrowser,
    QGraphicsDropShadowEffect,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPointF
from PyQt6.QtGui import QColor, QFont, QPainter, QPolygonF, QBrush, QPen


class HUDCard(QFrame):
    """Custom QFrame that draws a glassmorphic background with a subtle speech arrow pointing left."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Drop shadow effect for floating depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(255, 85, 0, 75))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        """Paint dark glassmorphic rounded rect with a speech pointer toward Charizard."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Drawing dimensions (offset from left for pointer arrow)
        pointer_width = 12
        card_rect = self.rect().adjusted(pointer_width, 1, -2, -2)

        # 1. Fill card background: dark charcoal translucent
        bg_brush = QBrush(QColor(22, 18, 16, 240))  # rgba(22, 18, 16, 0.94)
        border_pen = QPen(QColor(255, 85, 0, 110), 1.2)  # subtle ember border

        painter.setBrush(bg_brush)
        painter.setPen(border_pen)
        painter.drawRoundedRect(card_rect, 16, 16)

        # 2. Draw speech bubble pointer triangle pointing to Charizard
        pointer = QPolygonF([
            QPointF(pointer_width, 42),
            QPointF(2, 54),
            QPointF(pointer_width, 66),
        ])
        painter.setPen(border_pen)
        painter.drawPolygon(pointer)

        # Mask inside the pointer seam
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(pointer)

        painter.end()


class HUDView(QWidget):
    """Full HUD view widget containing all interactive controls, outputs, and inputs."""

    # Signals
    query_submitted = pyqtSignal(str, str)     # action_type, custom_prompt
    close_requested = pyqtSignal()             # retract card
    crop_mode_changed = pyqtSignal(bool)       # True = active window, False = full screen

    def __init__(self, parent=None):
        super().__init__(parent)
        self.crop_active_window = True
        self.init_ui()

    def init_ui(self):
        """Initialize layout and widgets."""
        self.setFixedWidth(390)
        self.setMinimumHeight(480)
        self.setMaximumHeight(640)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Background card frame
        self.card = HUDCard(self)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 14, 14, 14)
        card_layout.setSpacing(10)

        # --- 1. Header Bar ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.title_label = QLabel("✨ AI Companion ✨", self)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffb366;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
                background: transparent;
            }
        """)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Crop Mode Toggle Pill
        self.crop_btn = QPushButton("🪟 App", self)
        self.crop_btn.setToolTip("Toggle between Active App crop and Full Screen capture")
        self.crop_btn.setCheckable(True)
        self.crop_btn.setChecked(True)
        self.crop_btn.setStyleSheet("""
            QPushButton {
                background: rgba(45, 36, 30, 0.85);
                color: #d8c2b0;
                border: 1px solid rgba(255, 85, 0, 0.35);
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:checked {
                background: rgba(255, 85, 0, 0.25);
                color: #ffaa55;
                border: 1px solid #ff5500;
            }
            QPushButton:hover {
                background: rgba(255, 85, 0, 0.35);
            }
        """)
        self.crop_btn.clicked.connect(self._toggle_crop_mode)
        header_layout.addWidget(self.crop_btn)

        # Minimize / Close Button
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setToolTip("Collapse HUD (Click Charizard anytime to reopen)")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(60, 48, 42, 0.6);
                color: #c9b0a0;
                border: none;
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 70, 0, 0.85);
                color: white;
            }
        """)
        self.close_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(self.close_btn)

        card_layout.addLayout(header_layout)

        # --- 2. Status Badge ---
        status_bar = QHBoxLayout()
        self.status_dot = QLabel("●", self)
        self.status_dot.setStyleSheet("color: #00e676; font-size: 10px; background: transparent;")
        self.status_text = QLabel("Idle - Ready to observe", self)
        self.status_text.setStyleSheet("color: #a8988b; font-size: 11px; font-weight: 500; background: transparent;")
        status_bar.addWidget(self.status_dot)
        status_bar.addWidget(self.status_text)
        status_bar.addStretch()

        # Copy response button
        self.copy_btn = QPushButton("📋 Copy", self)
        self.copy_btn.setToolTip("Copy response markdown to clipboard")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8c7e73;
                border: none;
                font-size: 10px;
                padding: 1px 4px;
            }
            QPushButton:hover {
                color: #ff9944;
            }
        """)
        self.copy_btn.clicked.connect(self._copy_response)
        status_bar.addWidget(self.copy_btn)

        card_layout.addLayout(status_bar)

        # --- 3. Output Panel (QTextBrowser with Markdown) ---
        self.output_browser = QTextBrowser(self)
        self.output_browser.setOpenExternalLinks(True)
        self.output_browser.setPlaceholderText(
            "Charizard is ready! ✨\n\n"
            "• Click a quick question below to inspect your screen.\n"
            "• Or type your question in the box below."
        )
        self.output_browser.setStyleSheet("""
            QTextBrowser {
                background: rgba(14, 11, 10, 0.85);
                color: #f2eee8;
                border: 1px solid rgba(255, 85, 0, 0.25);
                border-radius: 10px;
                padding: 10px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 12px;
                line-height: 1.45;
                selection-background-color: #ff5500;
                selection-color: #ffffff;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(20, 16, 14, 0.5);
                width: 6px;
                margin: 2px 0 2px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 85, 0, 0.45);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 85, 0, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        card_layout.addWidget(self.output_browser, stretch=1)

        # --- 4. Quick Action Buttons Header ---
        quick_header = QLabel("Ask me anything:\n<span style='font-size:10px; color:#8c7e73;'>Quick Doubt-Solving Questions</span>", self)
        quick_header.setTextFormat(Qt.TextFormat.RichText)
        quick_header.setStyleSheet("color: #e6ded6; font-size: 12px; font-weight: 600; background: transparent;")
        card_layout.addWidget(quick_header)

        # --- Quick Action Buttons (matching reference image style) ---
        quick_btn_style = """
            QPushButton {
                background: rgba(35, 28, 24, 0.8);
                color: #e8d9cc;
                border: 1px solid rgba(255, 85, 0, 0.3);
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(255, 85, 0, 0.22);
                border: 1px solid rgba(255, 85, 0, 0.7);
                color: #ffffff;
            }
            QPushButton:pressed {
                background: rgba(255, 85, 0, 0.4);
            }
        """

        self.btn_summarize = QPushButton("📄  Summarize this open page", self)
        self.btn_summarize.setStyleSheet(quick_btn_style)
        self.btn_summarize.clicked.connect(lambda: self.query_submitted.emit("summarize", ""))
        card_layout.addWidget(self.btn_summarize)

        self.btn_debug = QPushButton("🐛  Debug visible code & errors", self)
        self.btn_debug.setStyleSheet(quick_btn_style)
        self.btn_debug.clicked.connect(lambda: self.query_submitted.emit("debug", ""))
        card_layout.addWidget(self.btn_debug)

        self.btn_explain = QPushButton("💡  Explain diagram / concept", self)
        self.btn_explain.setStyleSheet(quick_btn_style)
        self.btn_explain.clicked.connect(lambda: self.query_submitted.emit("explain", ""))
        card_layout.addWidget(self.btn_explain)

        # --- 5. Custom Query Input & Send Button ---
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self.input_edit = QLineEdit(self)
        self.input_edit.setPlaceholderText("Ask Charizard about your screen...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background: rgba(18, 14, 12, 0.9);
                color: #f7f3ee;
                border: 1px solid rgba(255, 85, 0, 0.35);
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #ff5500;
                background: rgba(24, 18, 16, 0.95);
            }
        """)
        self.input_edit.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self.input_edit, stretch=1)

        self.send_btn = QPushButton("🔥 Ask", self)
        self.send_btn.setFixedSize(56, 28)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4500, stop:1 #ff7700);
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5500, stop:1 #ff8800);
            }
            QPushButton:pressed {
                background: #cc3700;
            }
        """)
        self.send_btn.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_btn)

        card_layout.addLayout(input_layout)
        main_layout.addWidget(self.card)

    def _toggle_crop_mode(self):
        """Toggle between active window crop and full screen capture."""
        self.crop_active_window = self.crop_btn.isChecked()
        if self.crop_active_window:
            self.crop_btn.setText("🪟 App")
            self.crop_btn.setToolTip("Currently cropping active app")
        else:
            self.crop_btn.setText("🖥️ Full")
            self.crop_btn.setToolTip("Currently capturing full screen")
        self.crop_mode_changed.emit(self.crop_active_window)

    def _on_send_clicked(self):
        """Triggered when the user submits a custom question."""
        text = self.input_edit.text().strip()
        if text:
            self.input_edit.clear()
            self.query_submitted.emit("custom", text)

    def _copy_response(self):
        """Copy response text to system clipboard."""
        text = self.output_browser.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            prev_status = self.status_text.text()
            self.set_status("Copied to clipboard!", color="#00e676")
            # Restore status after 1.5s
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.set_status(prev_status))

    def set_status(self, text: str, color: str = "#ff9933"):
        """Update status text and indicator dot color."""
        self.status_text.setText(text)
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")

    def set_busy(self, is_busy: bool, message: str = ""):
        """Toggle UI busy state during AI reasoning."""
        self.btn_summarize.setEnabled(not is_busy)
        self.btn_debug.setEnabled(not is_busy)
        self.btn_explain.setEnabled(not is_busy)
        self.send_btn.setEnabled(not is_busy)
        self.input_edit.setEnabled(not is_busy)

        if is_busy:
            self.set_status(message or "Flamethrower Analyzing...", color="#ff5500")
        else:
            self.set_status("Done", color="#00e676")

    def display_markdown(self, markdown_text: str):
        """Render markdown text in the output browser."""
        self.output_browser.setMarkdown(markdown_text)

    def display_error(self, error_message: str):
        """Render error message in the output browser."""
        self.output_browser.setMarkdown(error_message)
        self.set_status("Error", color="#ff1744")
