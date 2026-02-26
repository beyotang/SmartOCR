from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QToolBar, QLabel, QComboBox, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from app_config import config

from services.i18n import i18n

class ResultWindow(QMainWindow):
    # Updated signal: text, mode, target_lang
    translate_requested = Signal(str, str, str) 

    def __init__(self):
        super().__init__()
        self.setWindowTitle(i18n.get("win_result_title"))
        self.resize(800, 600)
        # Ensure it's a top-level window that stays on top
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        # Store original text for split function
        self.original_text = ""
        self.is_merged = False
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        
        self.action_copy = QAction(i18n.get("action_copy"), self)
        self.action_copy.triggered.connect(self.copy_text)
        self.toolbar.addAction(self.action_copy)

        self.action_merge = QAction("合并", self)
        self.action_merge.triggered.connect(self.toggle_merge)
        self.toolbar.addAction(self.action_merge)
        
        self.toolbar.addSeparator()

        # Translation Controls
        self.combo_trans_mode = QComboBox()
        self.refresh_trans_modes()
        self.toolbar.addWidget(QLabel(i18n.get("lbl_mode")))
        self.toolbar.addWidget(self.combo_trans_mode)
        
        # Target Lang Selector
        self.toolbar.addWidget(QLabel(i18n.get("lbl_target")))
        self.combo_target_lang = QComboBox()
        self.combo_target_lang.addItems(["Chinese", "English", "French", "Russian", "German", "Japanese", "Korean"])
        # Map nice names to what we pass to prompt
        self.lang_map = {
            "Chinese": "中文", "English": "English", "French": "Francais", 
            "Russian": "Russian", "German": "Deutsch", "Japanese": "Japanese", "Korean": "Korean"
        }
        self.toolbar.addWidget(self.combo_target_lang)

        self.action_translate = QAction(i18n.get("action_translate"), self)
        self.action_translate.triggered.connect(self.on_translate)
        self.toolbar.addAction(self.action_translate)
        
        # Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("OCR Result...")
        self.splitter.addWidget(self.text_editor)
        
        self.trans_editor = QTextEdit()
        self.trans_editor.setPlaceholderText("Translation Result...")
        self.trans_editor.hide()
        self.splitter.addWidget(self.trans_editor)
        
        main_layout.addWidget(self.splitter)
        
    def refresh_trans_modes(self):
        self.combo_trans_mode.clear()
        prompts = config.get("translation", {}).get("custom_prompts", [])
        for p in prompts:
            self.combo_trans_mode.addItem(p.get("mode", "Unknown"))

    def force_show(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def set_text(self, text):
        self.original_text = text
        self.is_merged = False
        self.action_merge.setText("合并")
        self.text_editor.setPlainText(text)
        self.force_show()
        self.refresh_trans_modes()

    def append_debug_info(self, text):
        # Helper to append error info if needed, or just set text
        current = self.text_editor.toPlainText()
        if current:
            self.text_editor.setPlainText(current + "\n\n" + text)
        else:
            self.text_editor.setPlainText(text)

    def copy_text(self):
        self.text_editor.selectAll()
        self.text_editor.copy()

    def toggle_merge(self):
        if self.is_merged:
            # Split: restore original text
            self.text_editor.setPlainText(self.original_text)
            self.action_merge.setText("合并")
            self.is_merged = False
        else:
            # Merge: combine all lines
            text = self.text_editor.toPlainText()
            self.original_text = text  # Store for split
            merged = text.replace("\n", "")
            self.text_editor.setPlainText(merged)
            self.action_merge.setText("拆分")
            self.is_merged = True

    def on_translate(self):
        text = self.text_editor.toPlainText()
        mode = self.combo_trans_mode.currentText()
        target_display = self.combo_target_lang.currentText()
        target_val = self.lang_map.get(target_display, target_display)
        
        if text:
            self.trans_editor.show()
            self.translate_requested.emit(text, mode, target_val)
