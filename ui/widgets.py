from PySide6.QtWidgets import QLineEdit, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence

class HotkeyRecorder(QLineEdit):
    key_sequence_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("点击后按键设置快捷键...")
        self.setReadOnly(True) # Prevent typing text manually
        self.current_sequence = ""
        self.hotkey_type = None  # "screenshot" or "translate"

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()
        
        # Block ESC key - it's reserved for cancel
        if key == Qt.Key_Escape:
            QMessageBox.warning(self, "提示", "ESC 键已保留用于取消截图，请选择其他按键。")
            return
        
        # Ignore modifier-only presses
        if key in [Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta]:
            return

        parts = []
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.MetaModifier:
            parts.append("Win")
            
        # Get key text
        key_text = QKeySequence(key).toString()
        if not key_text:
             key_text = str(key)
        
        parts.append(key_text)
        
        sequence = "+".join(parts)
        self.setText(sequence)
        self.current_sequence = sequence
        self.key_sequence_changed.emit(sequence)
        
        # Apply hotkey immediately using hotkey manager
        self._apply_hotkey_immediately(sequence)

    def _apply_hotkey_immediately(self, sequence):
        """Apply the new hotkey immediately without restart."""
        try:
            from services.hotkey_manager import hotkey_manager
            from app_config import config
            
            if self.hotkey_type == "screenshot":
                if hotkey_manager.register_screenshot_hotkey(sequence):
                    config.set("hotkey_cature", sequence)
                    print(f"Screenshot hotkey updated to: {sequence}")
            elif self.hotkey_type == "translate":
                if hotkey_manager.register_translate_hotkey(sequence):
                    config.set("hotkey_trans_capture", sequence)
                    print(f"Translate hotkey updated to: {sequence}")
            elif self.hotkey_type == "show_main":
                if hotkey_manager.register_show_main_hotkey(sequence):
                    config.set("hotkey_show_main", sequence)
                    print(f"Show main window hotkey updated to: {sequence}")
        except Exception as e:
            print(f"Failed to update hotkey: {e}")

    def mousePressEvent(self, e):
        self.setFocus()
        super().mousePressEvent(e)

    def focusInEvent(self, e):
        if not self.text():
            self.setPlaceholderText("请按下快捷键...")
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        self.setPlaceholderText("点击后按键设置快捷键...")
        super().focusOutEvent(e)
