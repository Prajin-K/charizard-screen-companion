"""Main Entry Point for Charizard Screen Companion.

Launches the floating desktop pet, configures Windows High-DPI Pass-Through scaling,
loads environment variables, and manages the application lifecycle.
"""

import os
import sys

# 1. Windows High-DPI Scaling Configuration (must be set before QApplication initialization)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

from ui.companion_widget import CompanionWidget


def main():
    """Configure environment and execute Qt application event loop."""
    # 2. Load environment variables from .env
    load_dotenv()

    # 3. Create Qt Application instance
    app = QApplication(sys.argv)

    # 4. Windows High-DPI Pass-Through Rounding Policy
    # Prevents Windows OS display scaling (125%/150%) from stretching and blurring the canvas
    if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, "PassThrough"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app.setApplicationName("Charizard Screen Companion")
    app.setApplicationDisplayName("Charizard Screen Companion")
    app.setOrganizationName("CharizardAI")

    # 5. Resolve high-quality animated WebP asset path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    webp_path = os.path.join(base_dir, "charizard_idle.webp")

    # 6. Instantiate Floating Companion (with automatic fallback to GIF / emoji)
    companion = CompanionWidget(asset_path=webp_path)

    # 7. Position initial widget near upper-right desktop area (similar to prototype reference)
    primary_screen = QGuiApplication.primaryScreen()
    if primary_screen:
        screen_geo = primary_screen.availableGeometry()
        # Default offset: 240px from right, 80px from top
        initial_x = screen_geo.right() - 240
        initial_y = screen_geo.top() + 80
        companion.move(initial_x, initial_y)

    companion.show()

    # 8. Start application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
