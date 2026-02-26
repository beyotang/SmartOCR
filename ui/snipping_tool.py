from PySide6.QtWidgets import QWidget, QApplication, QRubberBand
from PySide6.QtCore import Qt, QRect, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QFont, QBrush
import sys

class SnippingTool(QWidget):
    capture_done = Signal(object) # Emits QPixmap or None

    def __init__(self):
        super().__init__()
        # Use Tool | Frameless | StayOnTop
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        # Translucent background is key to not just be a black block if opacity fails
        self.setAttribute(Qt.WA_TranslucentBackground, False) 
        self.setCursor(Qt.CrossCursor)
        
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_snipping = False
        self.original_pixmap = None

    def start_capture(self):
        # 1. Grab screen BEFORE showing this window
        screen = QApplication.primaryScreen()
        if screen:
             # Grab the whole virtual desktop if possible, but for now primary screen
            self.original_pixmap = screen.grabWindow(0)
        
        # 2. Set geometry to match screen
        self.setGeometry(screen.geometry())
        
        # 3. Show full screen
        self.show()
        self.activateWindow()

    def paintEvent(self, event):
        if self.original_pixmap:
            painter = QPainter(self)
            # Draw the real screen background
            painter.drawPixmap(0, 0, self.original_pixmap)
            
            # Draw dimming overlay (black with alpha)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            
            # If snipping, clear the dimming rect to show original screen "brightly"
            if self.start_point != self.end_point:
                rect = QRect(self.start_point, self.end_point).normalized()
                
                # Draw the original pixmap inside the rect again (to "undim" it)
                painter.drawPixmap(rect, self.original_pixmap, rect)
                
                # Draw border
                pen = QPen(QColor(0, 120, 215), 2)
                painter.setPen(pen)
                painter.drawRect(rect)
                
                # Draw ESC hint ABOVE selection box with highlight background
                hint_text = "按 ESC 键取消截图"
                font = QFont("Microsoft YaHei", 16)
                font.setBold(True)
                painter.setFont(font)
                
                # Calculate text position (above selection)
                text_width = painter.fontMetrics().horizontalAdvance(hint_text)
                text_height = painter.fontMetrics().height()
                
                # Center above the selection box
                text_x = rect.left() + (rect.width() - text_width) // 2
                text_y = rect.top() - 10  # 10px above selection
                
                # Make sure it's on screen
                if text_y < text_height + 10:
                    text_y = rect.bottom() + text_height + 10  # Below if no room above
                if text_x < 10:
                    text_x = 10
                if text_x + text_width > self.width() - 10:
                    text_x = self.width() - text_width - 10
                
                # Draw background for hint
                bg_rect = QRect(text_x - 8, text_y - text_height - 2, text_width + 16, text_height + 8)
                painter.fillRect(bg_rect, QColor(0, 120, 215, 200))
                
                # Draw text in white on blue background
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(text_x, text_y, hint_text)
                
                # Draw selection size hint
                width = rect.width()
                height = rect.height()
                size_text = f"{width} × {height}"
                font = QFont("Microsoft YaHei", 10)
                painter.setFont(font)
                painter.setPen(QPen(QColor(255, 255, 255)))
                
                size_x = rect.left() + 5
                size_y = rect.bottom() + 20 if rect.bottom() + 25 < self.height() else rect.top() - 5
                
                # Background for size hint
                size_width = painter.fontMetrics().horizontalAdvance(size_text)
                size_bg = QRect(size_x - 4, size_y - 14, size_width + 8, 18)
                painter.fillRect(size_bg, QColor(0, 0, 0, 150))
                painter.drawText(size_x, size_y, size_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_snipping = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_snipping:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_snipping = False
            rect = QRect(self.start_point, self.end_point).normalized()
            
            self.close() # Close immediately
            
            if rect.width() > 10 and rect.height() > 10:
                captured_pixmap = self.original_pixmap.copy(rect)
                self.capture_done.emit(captured_pixmap)
            else:
                self.capture_done.emit(None)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.capture_done.emit(None)
            self.close()
