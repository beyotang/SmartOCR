from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt

class ProgressOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(300, 100)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("Processing OCR...\nPlease Wait")
        self.label.setAlignment(Qt.AlignCenter)
        # Style it to look like a floating HUD
        self.label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            border-radius: 10px;
            font-size: 16px;
            padding: 20px;
        """)
        layout.addWidget(self.label)
        
    def show_progress(self):
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        self.show()
