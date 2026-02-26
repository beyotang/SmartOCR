import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QTabWidget, QLabel, QComboBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView, QApplication,
    QLineEdit, QAbstractItemView, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from ui.settings_dialog import SettingsDialog
from services.i18n import i18n
from app_config import config


# Model-specific export formats
MODEL_FORMATS = {
    "PP-OCRv5": ["TXT", "JSON", "可搜索PDF", "带标注图片", "CSV"],
    "PP-StructureV3": ["DOCX (Word)", "XLSX (Excel)", "Markdown", "HTML", "JSON", "PDF"],
    "PaddleOCR-VL": ["Markdown", "LaTeX公式", "JSON", "TXT", "代码"]
}

# Model-specific accepted file extensions
MODEL_FILE_EXTS = {
    "PP-OCRv5": ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf'],
    "PP-StructureV3": ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf'],
    "PaddleOCR-VL": ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
}


class DropTableWidget(QTableWidget):
    """Table widget that accepts drag-drop files"""
    files_dropped = Signal(list)
    
    def __init__(self, accepted_extensions):
        super().__init__()
        self.accepted_extensions = accepted_extensions
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
    
    def update_accepted_extensions(self, exts):
        self.accepted_extensions = exts
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in self.accepted_extensions:
                files.append(path)
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
        else:
            QMessageBox.warning(self, "格式不支持", f"当前模型不支持此文件格式。\n支持的格式: {', '.join(self.accepted_extensions)}")

    def contextMenuEvent(self, event):
        """Override context menu to show Chinese options"""
        menu = QMenu(self)
        action_copy = menu.addAction("复制内容")
        action_delete = menu.addAction("删除")
        action_clear = menu.addAction("清空全部")
        
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == action_copy:
            items = self.selectedItems()
            if items:
                text = "\n".join([item.text() for item in items])
                QApplication.clipboard().setText(text)
        elif action == action_delete:
            rows = set(item.row() for item in self.selectedItems())
            for row in sorted(rows, reverse=True):
                self.removeRow(row)
        elif action == action_clear:
            self.setRowCount(0)


class MainWindow(QMainWindow):
    open_result_requested = Signal()

    def __init__(self):
        super().__init__()
        self.update_ui_text()
        # Default window size: filename column (600) + progress column (150) + result column (200) + borders (50)
        self.resize(1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_images = QWidget()
        self.init_images_tab(self.tab_images)
        self.tabs.addTab(self.tab_images, i18n.get("tab_images"))

        self.tab_docs = QWidget()
        self.init_docs_tab(self.tab_docs)
        self.tabs.addTab(self.tab_docs, i18n.get("tab_docs"))

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        self.btn_screenshot = QPushButton(i18n.get("btn_screenshot"))
        bottom_layout.addWidget(self.btn_screenshot)
        
        self.btn_open_res = QPushButton(i18n.get("btn_open_result"))
        self.btn_open_res.clicked.connect(lambda: self.open_result_requested.emit())
        bottom_layout.addWidget(self.btn_open_res)

        self.btn_settings = QPushButton(i18n.get("btn_settings"))
        self.btn_settings.clicked.connect(self.open_settings)
        bottom_layout.addWidget(self.btn_settings)

        self.btn_exit = QPushButton(i18n.get("btn_exit"))
        self.btn_exit.clicked.connect(self.exit_app)
        bottom_layout.addWidget(self.btn_exit)

        bottom_layout.addStretch()

        self.btn_start = QPushButton(i18n.get("btn_start"))
        self.btn_start.clicked.connect(self.start_batch_processing)
        bottom_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton(i18n.get("btn_stop"))
        self.btn_stop.clicked.connect(self.stop_batch_processing)
        self.btn_stop.setEnabled(False)
        bottom_layout.addWidget(self.btn_stop)

        layout.addLayout(bottom_layout)

    def exit_app(self):
        # Check if there are any running tasks by looking at the table
        has_running_tasks = self._has_processing_items()
        
        if has_running_tasks:
            # Task is running, ask for confirmation
            reply = QMessageBox.question(
                self,
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
        
        # Force exit the entire process to ensure no threads remain
        import os
        QApplication.quit()
        os._exit(0)  # Force exit to kill all threads
    
    def _has_processing_items(self):
        """Check if any items in the tables are currently being processed."""
        processing_texts = ["处理中...", "Processing..."]
        
        # Check images table
        for row in range(self.table_images.rowCount()):
            result_item = self.table_images.item(row, 2)  # Result column
            if result_item and result_item.text() in processing_texts:
                return True
        
        # Check docs table
        for row in range(self.table_docs.rowCount()):
            result_item = self.table_docs.item(row, 2)  # Result column
            if result_item and result_item.text() in processing_texts:
                return True
        
        return False

    def update_ui_text(self):
        self.setWindowTitle(i18n.get("app_title"))

    def get_default_output_path(self, sub_folder):
        """Get absolute path for default output folder"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
        
        return os.path.join(base_dir, "output", sub_folder)

    def init_images_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Top bar
        top_bar = QHBoxLayout()
        
        top_bar.addWidget(QLabel(i18n.get("label_model")))
        self.combo_model_img = QComboBox()
        self.combo_model_img.addItems(["PP-OCRv5", "PP-StructureV3", "PaddleOCR-VL"])
        self.combo_model_img.setCurrentText("PP-OCRv5")  # Default for images
        self.combo_model_img.currentTextChanged.connect(self.on_img_model_changed)
        top_bar.addWidget(self.combo_model_img)
        
        top_bar.addWidget(QLabel("导出格式:"))
        self.combo_format_img = QComboBox()
        self.update_format_combo(self.combo_format_img, "PP-OCRv5")
        top_bar.addWidget(self.combo_format_img)
        
        top_bar.addWidget(QLabel("同时处理:"))
        self.combo_workers_img = QComboBox()
        self.combo_workers_img.addItems([str(i) for i in range(1, 21)])  # 1-20
        self.combo_workers_img.setCurrentText("5")  # Default to 5
        self.combo_workers_img.setMaximumWidth(50)
        top_bar.addWidget(self.combo_workers_img)
        
        top_bar.addWidget(QLabel("输出路径:"))
        self.path_img = QLineEdit()
        self.path_img.setText(self.get_default_output_path("images"))
        self.path_img.setMinimumWidth(200)
        top_bar.addWidget(self.path_img)
        
        btn_browse_img = QPushButton("...")
        btn_browse_img.setMaximumWidth(30)
        btn_browse_img.clicked.connect(lambda: self.browse_folder(self.path_img))
        top_bar.addWidget(btn_browse_img)
        
        btn_open_folder_img = QPushButton("打开文件夹")
        btn_open_folder_img.clicked.connect(lambda: self.open_folder(self.path_img.text()))
        top_bar.addWidget(btn_open_folder_img)
        
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Drag-drop table with model-specific extensions
        self.table_images = DropTableWidget(MODEL_FILE_EXTS["PP-OCRv5"])
        self.table_images.setColumnCount(3)
        self.table_images.setHorizontalHeaderLabels([
            i18n.get("col_filename"), i18n.get("col_progress"), i18n.get("col_result")
        ])
        # Make all columns resizable
        self.table_images.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_images.setColumnWidth(0, 600)  # Filename column
        self.table_images.setColumnWidth(1, 150)  # Progress column
        self.table_images.setColumnWidth(2, 200)  # Result column
        self.table_images.files_dropped.connect(lambda files: self.add_files_to_table(files, self.table_images))

        btn_layout = QHBoxLayout()
        btn_add = QPushButton(i18n.get("btn_add_images"))
        btn_add.clicked.connect(lambda: self.add_files_for_model(self.combo_model_img.currentText(), self.table_images))
        btn_clear = QPushButton(i18n.get("btn_clear"))
        btn_clear.clicked.connect(lambda: self.table_images.setRowCount(0))
        btn_clear_done = QPushButton("清空已完成")
        btn_clear_done.clicked.connect(lambda: self.clear_completed_rows(self.table_images))
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_clear_done)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addWidget(self.table_images)

    def on_img_model_changed(self, model_name):
        self.update_format_combo(self.combo_format_img, model_name)
        self.table_images.update_accepted_extensions(MODEL_FILE_EXTS.get(model_name, []))

    def on_doc_model_changed(self, model_name):
        self.update_format_combo(self.combo_format_doc, model_name)
        self.table_docs.update_accepted_extensions(MODEL_FILE_EXTS.get(model_name, []))

    def update_format_combo(self, combo, model_name):
        combo.clear()
        formats = MODEL_FORMATS.get(model_name, ["TXT"])
        combo.addItems(formats)
        # Default selection
        if "TXT" in formats:
            combo.setCurrentText("TXT")
        elif formats:
            combo.setCurrentIndex(0)

    def init_docs_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Top bar
        top_bar = QHBoxLayout()
        
        top_bar.addWidget(QLabel(i18n.get("label_model")))
        self.combo_model_doc = QComboBox()
        self.combo_model_doc.addItems(["PP-OCRv5", "PP-StructureV3", "PaddleOCR-VL"])
        self.combo_model_doc.setCurrentText("PP-StructureV3")  # Default for docs
        self.combo_model_doc.currentTextChanged.connect(self.on_doc_model_changed)
        top_bar.addWidget(self.combo_model_doc)
        
        top_bar.addWidget(QLabel("导出格式:"))
        self.combo_format_doc = QComboBox()
        self.update_format_combo(self.combo_format_doc, "PP-StructureV3")
        top_bar.addWidget(self.combo_format_doc)
        
        top_bar.addWidget(QLabel("同时处理:"))
        self.combo_workers_doc = QComboBox()
        self.combo_workers_doc.addItems([str(i) for i in range(1, 21)])  # 1-20
        self.combo_workers_doc.setCurrentText("5")  # Default to 5
        self.combo_workers_doc.setMaximumWidth(50)
        top_bar.addWidget(self.combo_workers_doc)
        
        top_bar.addWidget(QLabel("输出路径:"))
        self.path_doc = QLineEdit()
        self.path_doc.setText(self.get_default_output_path("docs"))
        self.path_doc.setMinimumWidth(200)
        top_bar.addWidget(self.path_doc)
        
        btn_browse_doc = QPushButton("...")
        btn_browse_doc.setMaximumWidth(30)
        btn_browse_doc.clicked.connect(lambda: self.browse_folder(self.path_doc))
        top_bar.addWidget(btn_browse_doc)
        
        btn_open_folder_doc = QPushButton("打开文件夹")
        btn_open_folder_doc.clicked.connect(lambda: self.open_folder(self.path_doc.text()))
        top_bar.addWidget(btn_open_folder_doc)
        
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Drag-drop table with model-specific extensions
        self.table_docs = DropTableWidget(MODEL_FILE_EXTS["PP-StructureV3"])
        self.table_docs.setColumnCount(3)
        self.table_docs.setHorizontalHeaderLabels([
            i18n.get("col_filename"), i18n.get("col_progress"), i18n.get("col_result")
        ])
        # Make all columns resizable
        self.table_docs.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_docs.setColumnWidth(0, 600)  # Filename column
        self.table_docs.setColumnWidth(1, 150)  # Progress column
        self.table_docs.setColumnWidth(2, 200)  # Result column
        self.table_docs.files_dropped.connect(lambda files: self.add_files_to_table(files, self.table_docs))

        btn_layout = QHBoxLayout()
        btn_add = QPushButton(i18n.get("btn_add_docs"))
        btn_add.clicked.connect(lambda: self.add_files_for_model(self.combo_model_doc.currentText(), self.table_docs))
        btn_clear = QPushButton(i18n.get("btn_clear"))
        btn_clear.clicked.connect(lambda: self.table_docs.setRowCount(0))
        btn_clear_done = QPushButton("清空已完成")
        btn_clear_done.clicked.connect(lambda: self.clear_completed_rows(self.table_docs))
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_clear_done)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addWidget(self.table_docs)

    def add_files_for_model(self, model_name, table_widget):
        exts = MODEL_FILE_EXTS.get(model_name, ['.jpg', '.png'])
        ext_list = ' '.join([f'*{e}' for e in exts])
        filter_str = f"支持的文件 ({ext_list})"
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", filter_str)
        if files:
            self.add_files_to_table(files, table_widget)

    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            line_edit.setText(folder)

    def open_folder(self, path):
        if not path:
            path = self.get_default_output_path("images")
        if not os.path.exists(path):
            os.makedirs(path)
        os.startfile(path)

    def clear_completed_rows(self, table_widget):
        """Remove rows where result column shows completion status"""
        completed_statuses = ["成功", "完成", "已导出", "无内容"]
        rows_to_remove = []
        
        for row in range(table_widget.rowCount()):
            result_item = table_widget.item(row, 2)
            if result_item:
                text = result_item.text()
                if any(status in text for status in completed_statuses):
                    rows_to_remove.append(row)
        
        # Remove from bottom to top
        for row in reversed(rows_to_remove):
            table_widget.removeRow(row)

    def add_files_to_table(self, files, table_widget):
        for f in files:
            row = table_widget.rowCount()
            table_widget.insertRow(row)

            # File path - editable
            name_item = QTableWidgetItem(f)
            name_item.setData(Qt.UserRole, f)
            table_widget.setItem(row, 0, name_item)

            # Progress bar
            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(0)
            table_widget.setCellWidget(row, 1, pbar)

            # Result - EDITABLE for copying error info
            result_item = QTableWidgetItem(i18n.get("status_pending"))
            table_widget.setItem(row, 2, result_item)

    def add_files(self, filter_str, table_widget):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", filter_str)
        if files:
            self.add_files_to_table(files, table_widget)

    def open_settings(self):
        try:
            dialog = SettingsDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, i18n.get("msg_error"), str(e))

    def start_batch_processing(self):
        idx = self.tabs.currentIndex()

        if idx == 0:
            target_table = self.table_images
            mode = "images"
            model_override = self.combo_model_img.currentText()
            output_dir = self.path_img.text()
            export_fmt = self.combo_format_img.currentText()
            max_workers = int(self.combo_workers_img.currentText())
        else:
            target_table = self.table_docs
            mode = "docs"
            model_override = self.combo_model_doc.currentText()
            output_dir = self.path_doc.text()
            export_fmt = self.combo_format_doc.currentText()
            max_workers = int(self.combo_workers_doc.currentText())

        row_count = target_table.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, i18n.get("msg_error"), i18n.get("msg_no_files"))
            return

        # Collect files and their row indices, skipping already successful tasks
        files = []
        row_indices = []  # Track original row indices for status updates
        
        # Status patterns that indicate successful completion (skip these)
        success_patterns = ["成功", "已导出", "Success", "Exported"]
        
        for r in range(row_count):
            result_item = target_table.item(r, 2)
            result_text = result_item.text() if result_item else ""
            
            # Check if this task was already successfully completed
            is_already_done = any(pattern in result_text for pattern in success_patterns)
            
            if is_already_done:
                # Skip this task, it's already done
                continue
            
            # Add this task to the processing list
            item = target_table.item(r, 0)
            files.append(item.data(Qt.UserRole) or item.text())
            row_indices.append(r)
            
            # Reset progress and status for this task
            target_table.cellWidget(r, 1).setValue(0)
            target_table.setItem(r, 2, QTableWidgetItem(i18n.get("status_pending")))

        # Check if there are any tasks to process
        if not files:
            QMessageBox.information(self, "SmartOCR", "所有任务已完成，无需重新执行。")
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_start.setText(i18n.get("status_processing"))

        self.current_table = target_table
        self.current_row_indices = row_indices  # Store for status updates

        from services.batch_processor import batch_processor

        worker = batch_processor.process(mode, files, model_override, output_dir, export_fmt, max_workers, row_indices)

        worker.signals.progress_update.connect(self.on_item_progress)
        worker.signals.status_update.connect(self.on_item_status)
        worker.signals.result_update.connect(self.on_item_result)
        worker.signals.finished.connect(self.on_batch_finished)
        worker.signals.stopped.connect(self.on_batch_stopped)

        batch_processor.start(worker)

    def stop_batch_processing(self):
        from services.batch_processor import batch_processor
        batch_processor.stop()
        self.btn_stop.setEnabled(False)
        # Show "restart" button text while waiting for task to actually stop
        self.btn_start.setText(i18n.get("btn_restart"))

    def on_item_progress(self, row, current, total):
        pbar = self.current_table.cellWidget(row, 1)
        if pbar:
            pbar.setValue(current)

    def on_item_status(self, row, status_text):
        self.current_table.setItem(row, 2, QTableWidgetItem(status_text))

    def on_item_result(self, row, text):
        self.current_table.setItem(row, 2, QTableWidgetItem(text))

    def on_batch_finished(self):
        self.reset_buttons()
        QMessageBox.information(self, "SmartOCR", i18n.get("msg_done"))

    def on_batch_stopped(self):
        """Handle user-initiated stop - show restart button and update stuck items"""
        # Force update any items still showing "处理中..." to "用户已终止任务"
        if hasattr(self, 'current_table') and self.current_table:
            for row in range(self.current_table.rowCount()):
                result_item = self.current_table.item(row, 2)
                if result_item:
                    current_text = result_item.text()
                    # Update items that are still showing processing status
                    if current_text in ["处理中...", "待处理", "Processing...", "Pending"]:
                        self.current_table.setItem(row, 2, QTableWidgetItem("用户已终止任务"))
        
        self.btn_start.setText(i18n.get("btn_restart"))
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def reset_buttons(self):
        self.btn_start.setText(i18n.get("btn_start"))
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
