import sys
import os
import keyboard
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QMenu, QSystemTrayIcon
from PySide6.QtCore import QTimer, QByteArray, QBuffer, QIODevice, Signal, QObject
from PySide6.QtGui import QIcon, QAction
from ui.main_window import MainWindow
from ui.snipping_tool import SnippingTool
from ui.result_window import ResultWindow
from ui.progress_overlay import ProgressOverlay
from services.ocr_engine import ocr_client
from app_config import config
import threading


class OCRResultHolder:
    def __init__(self):
        self.result = None
        self.ready = False


def run_app():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    main_window = MainWindow()
    main_window.show()

    snipping_tool = SnippingTool()
    result_window = ResultWindow()
    progress_overlay = ProgressOverlay()

    # Wire up "Open Result" button
    main_window.open_result_requested.connect(result_window.force_show)

    result_holder = OCRResultHolder()

    def check_result():
        if result_holder.ready:
            result_holder.ready = False
            on_ocr_finished(result_holder.result)

    result_timer = QTimer()
    result_timer.timeout.connect(check_result)
    result_timer.start(100)

    # Track windows to restore after screenshot
    hidden_windows = []
    
    def hide_all_windows():
        """Hide all application windows including dialogs."""
        hidden_windows.clear()
        for widget in QApplication.topLevelWidgets():
            # Skip snipping tool and progress overlay - they need special handling
            if widget is snipping_tool or widget is progress_overlay:
                continue
            # Hide visible windows and track them for restoration
            if widget.isVisible():
                hidden_windows.append(widget)
                widget.hide()
    
    def restore_windows():
        """Restore previously hidden windows."""
        for widget in hidden_windows:
            if widget and not widget.isVisible():
                widget.show()
        hidden_windows.clear()

    def do_screenshot_ocr():
        """Trigger screenshot capture with hide/show logic"""
        hide_all_windows()
        QTimer.singleShot(200, snipping_tool.start_capture)

    # Connect main window screenshot button
    main_window.btn_screenshot.clicked.connect(do_screenshot_ocr)

    def on_capture_done(pixmap):
        restore_windows()

        if pixmap:
            print("Capture taken, processing...")
            progress_overlay.show_progress()

            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            pixmap.save(buffer, "PNG")
            img_bytes = bytes(byte_array.data())

            # Get screenshot model from config
            screenshot_model = config.get("screenshot_model", "PP-OCRv5")

            def do_ocr():
                try:
                    res = ocr_client.ocr_image(img_bytes, model_override=screenshot_model)
                    result_holder.result = res
                    result_holder.ready = True
                except Exception as e:
                    result_holder.result = {"error": str(e)}
                    result_holder.ready = True

            t = threading.Thread(target=do_ocr)
            t.daemon = True
            t.start()
        else:
            print("Capture cancelled")

    def on_ocr_finished(res):
        progress_overlay.hide()

        if "error" in res:
            error_info = f"API Error: {res['error']}\n\nRaw Response:\n{res.get('raw_response', '')}"
            result_window.set_text(error_info)
        elif "words_result" in res:
            text_lines = [item["words"] for item in res["words_result"]]
            full_text = "\n".join(text_lines)
            if not full_text:
                full_text = f"(No text found)\n\nDebug: {res.get('debug_info', '')}"

            result_window.set_text(full_text)

            if getattr(snipping_tool, "auto_translate", False):
                snipping_tool.auto_translate = False
                result_window.on_translate()
        else:
            result_window.set_text(f"Unknown Result Format:\n{res}")

    snipping_tool.capture_done.connect(on_capture_done)

    # ========== HOTKEY MANAGEMENT ==========
    from services.hotkey_manager import hotkey_manager
    
    def trigger_trans_snip():
        hide_all_windows()
        snipping_tool.auto_translate = True
        QTimer.singleShot(200, snipping_tool.start_capture)
    
    # Connect hotkey manager signals
    hotkey_manager.screenshot_triggered.connect(do_screenshot_ocr)
    hotkey_manager.translate_triggered.connect(trigger_trans_snip)
    
    # Register initial hotkeys from config
    screenshot_hk = config.get("hotkey_cature") or "F4"
    translate_hk = config.get("hotkey_trans_capture") or "F6"
    show_main_hk = config.get("hotkey_show_main") or "F9"
    hotkey_manager.register_screenshot_hotkey(screenshot_hk)
    hotkey_manager.register_translate_hotkey(translate_hk)
    hotkey_manager.register_show_main_hotkey(show_main_hk)

    # Translation Logic
    from services.translator import translator

    def on_translate_request(text, mode, target_lang):
        result_window.trans_editor.setPlaceholderText(f"Translating to {target_lang}...")
        res = translator.translate(text, mode, target_lang)
        result_window.trans_editor.setPlainText(res)

    result_window.translate_requested.connect(on_translate_request)

    # ========== SYSTEM TRAY ==========
    tray_icon = QSystemTrayIcon()
    tray_icon.setIcon(QIcon.fromTheme("camera-photo"))  # Fallback icon
    tray_icon.setToolTip("SmartOCR")

    tray_menu = QMenu()

    # 显示主窗口（同时关闭设置窗口，防止卡在后台）
    action_show_main = QAction("🏠 显示主窗口", None)
    def show_main_window():
        # Close any open settings dialogs to prevent them from getting stuck
        from ui.settings_dialog import SettingsDialog
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, SettingsDialog):
                widget.close()
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()
    action_show_main.triggered.connect(show_main_window)
    tray_menu.addAction(action_show_main)
    
    # Connect show main hotkey signal
    hotkey_manager.show_main_triggered.connect(show_main_window)

    tray_menu.addSeparator()

    action_screenshot = QAction("📷 截图识别", None)
    action_screenshot.triggered.connect(do_screenshot_ocr)
    tray_menu.addAction(action_screenshot)

    action_trans_screenshot = QAction("🔤 截图翻译", None)
    action_trans_screenshot.triggered.connect(trigger_trans_snip)
    tray_menu.addAction(action_trans_screenshot)

    tray_menu.addSeparator()

    action_show_result = QAction("📄 显示识别窗口", None)
    action_show_result.triggered.connect(result_window.force_show)
    tray_menu.addAction(action_show_result)

    tray_menu.addSeparator()

    action_settings = QAction("⚙️ 设置", None)
    action_settings.triggered.connect(lambda: main_window.open_settings())
    tray_menu.addAction(action_settings)

    action_exit = QAction("❌ 退出", None)
    def exit_app():
        # Check if there are any running tasks by looking at the table
        has_running_tasks = main_window._has_processing_items()
        
        if has_running_tasks:
            # Task is running, ask for confirmation
            reply = QMessageBox.question(
                main_window,
                "确认退出",
                "有任务正在执行中，强制退出将会终止任务。\n是否确认退出？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            # User confirmed, stop the task first
            from services.batch_processor import batch_processor
            batch_processor.stop()
        
        tray_icon.hide()
        QApplication.quit()
        os._exit(0)  # Force exit to kill all threads
    action_exit.triggered.connect(exit_app)
    tray_menu.addAction(action_exit)

    tray_icon.setContextMenu(tray_menu)
    
    # 双击托盘图标显示主窗口
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.DoubleClick:
            show_main_window()
    tray_icon.activated.connect(on_tray_activated)
    
    tray_icon.show()

    # Handle minimize to tray
    def on_main_close(event):
        if config.get("minimize_to_tray", False):
            event.ignore()
            main_window.hide()
        else:
            event.accept()
            exit_app()

    main_window.closeEvent = on_main_close

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
