from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QDialogButtonBox, QLabel, QGroupBox, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, 
    QHeaderView, QFileDialog, QCheckBox, QAbstractItemView, QTextEdit
)
from PySide6.QtCore import Qt
from app_config import config
from ui.widgets import HotkeyRecorder
from services.i18n import i18n


MODEL_DESCRIPTION = """
1. PP-OCRv5 (通用文字识别模型)
该模型专注于"图转文"，主要输出基础格式和用于检索的文档。
• TXT：纯文本文件。
• JSON：包含文本内容、检测框坐标（Polygons）及置信度的结构化数据。
• Searchable PDF：可搜索 PDF（在原图层下方叠加透明文字层，支持复制和搜索）。
• JPG / PNG / BMP：带文字检测框和识别结果标注的可视化图像。
• CSV：简单的识别结果列表（每行一个识别出的结果）。

2. PP-StructureV3 (文档结构化分析模型)
这是功能最全的文档转换工具，旨在"还原排版"和"解析复杂结构"。
• DOCX (Microsoft Word)：支持版面还原，包括段落、标题、嵌入图像和表格的完整排版。
• XLSX (Microsoft Excel)：专门用于表格识别，将图片中的表格精准还原为可编辑的 Excel 表格。
• Markdown (.md)：将整页文档转换为带有标题级数、正文、表格和公式链接的 Markdown 格式。
• HTML：常用于表格导出，生成符合 Web 标准的表格代码或单页预览。
• JSON (Layout Tree)：输出版面树结构，详细记录哪些区域是 Header、Footer、Figure、Table 或 Text。
• PDF：基于版面分析后的重排版 PDF。

3. PaddleOCR-VL (多模态视觉语言大模型)
该模型基于语义理解，侧重于"智能生成"和"公式/代码提取"。
• Markdown：这是其最核心的输出方式，能够处理复杂的图文混排、多列排版。
• LaTeX：专门用于高精度导出数学公式、物理符号和化学方程式。
• JSON (Semantic KVP)：语义化的键值对提取（例如：自动从发票图片中提取 { "金额": "100.00", "日期": "2023-10-01" }）。
• TXT (Narrative)：叙述性文本，不仅是文字识别，还可以对文档内容进行描述、摘要或问答输出。
• Code (Py/C++/etc.)：如果图像中包含代码截图，可直接转换为对应的程序源码格式。

核心区别总结：
PP-OCRv5：主要给您文字内容。
PP-StructureV3：主要给您可编辑的办公文档 (Word/Excel)。
PaddleOCR-VL：主要给您格式化的语义信息 (Markdown/LaTeX/JSON)。
""".strip()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.get("settings_title"))
        # Match main window size (filename column 600 + progress 150 + result 200 + borders 50)
        self.resize(1000, 700) 
        
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.tab_ocr = QWidget()
        self.init_ocr_tab()
        self.tabs.addTab(self.tab_ocr, i18n.get("tab_ocr_models"))
        
        self.tab_trans = QWidget()
        self.init_trans_tab()
        self.tabs.addTab(self.tab_trans, i18n.get("tab_ai_trans"))
        
        self.tab_gen = QWidget()
        self.init_gen_tab()
        self.tabs.addTab(self.tab_gen, i18n.get("tab_general"))
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        main_layout.addWidget(buttons)

    def init_ocr_tab(self):
        layout = QVBoxLayout(self.tab_ocr)
        layout.setSpacing(6)  # Reduce spacing
        layout.setContentsMargins(10, 10, 10, 10)
        
        lbl = QLabel(i18n.get("lbl_ocr_config"))
        layout.addWidget(lbl)
        
        form = QFormLayout()
        form.setSpacing(6)  # Reduce form spacing
        form.setVerticalSpacing(6)
        
        self.combo_ocr_model = QComboBox()
        self.combo_ocr_model.addItems(["PP-OCRv5", "PP-StructureV3", "PaddleOCR-VL"])
        self.combo_ocr_model.setCurrentText(config.get("current_model"))
        self.combo_ocr_model.currentTextChanged.connect(self.on_ocr_model_changed)
        
        self.input_ocr_url = QLineEdit()
        self.input_ocr_url.textChanged.connect(self.save_ocr_config)
        
        self.input_ocr_token = QLineEdit()
        self.input_ocr_token.setEchoMode(QLineEdit.Password)
        self.input_ocr_token.textChanged.connect(self.save_ocr_config)
        
        # Screenshot Model Selector
        self.combo_screenshot_model = QComboBox()
        self.combo_screenshot_model.addItems(["PP-OCRv5", "PP-StructureV3", "PaddleOCR-VL"])
        self.combo_screenshot_model.setCurrentText(config.get("screenshot_model", "PP-OCRv5"))
        self.combo_screenshot_model.currentTextChanged.connect(lambda t: config.set("screenshot_model", t))
        
        form.addRow(i18n.get("lbl_select_model"), self.combo_ocr_model)
        form.addRow(i18n.get("lbl_api_url"), self.input_ocr_url)
        form.addRow(i18n.get("lbl_token"), self.input_ocr_token)
        form.addRow(i18n.get("lbl_screenshot_model"), self.combo_screenshot_model)
        layout.addLayout(form)
        
        self.load_ocr_fields(self.combo_ocr_model.currentText())
        
        # Model description text
        layout.addWidget(QLabel("模型介绍:"))
        desc_text = QTextEdit()
        desc_text.setPlainText(MODEL_DESCRIPTION)
        desc_text.setReadOnly(True)
        # Set fixed height to display all content (approximately 30 lines at 15px each)
        desc_text.setMinimumHeight(450)
        layout.addWidget(desc_text)

    def on_ocr_model_changed(self, model_name):
        config.set("current_model", model_name)
        self.load_ocr_fields(model_name)

    def load_ocr_fields(self, model_name):
        self.input_ocr_url.blockSignals(True)
        self.input_ocr_token.blockSignals(True)
        
        data = config.get_model_config(model_name)
        self.input_ocr_url.setText(data.get("url", ""))
        self.input_ocr_token.setText(data.get("token", ""))
        
        self.input_ocr_url.blockSignals(False)
        self.input_ocr_token.blockSignals(False)

    def save_ocr_config(self):
        model = self.combo_ocr_model.currentText()
        url = self.input_ocr_url.text()
        token = self.input_ocr_token.text()
        config.set_model_config(model, url, token)

    def init_trans_tab(self):
        layout = QVBoxLayout(self.tab_trans)
        
        group_con = QGroupBox(i18n.get("grp_llm_con"))
        form = QFormLayout()
        
        trans_cfg = config.get("translation")
        
        self.input_trans_url = QLineEdit(trans_cfg.get("api_url", ""))
        self.input_trans_url.textChanged.connect(self.save_trans_config)
        
        self.input_trans_key = QLineEdit(trans_cfg.get("api_key", ""))
        self.input_trans_key.setEchoMode(QLineEdit.Password)
        self.input_trans_key.textChanged.connect(self.save_trans_config)
        
        self.input_trans_model = QLineEdit(trans_cfg.get("model", "gpt-3.5-turbo"))
        self.input_trans_model.textChanged.connect(self.save_trans_config)
        
        form.addRow(i18n.get("lbl_api_base"), self.input_trans_url)
        form.addRow(i18n.get("lbl_api_key"), self.input_trans_key)
        form.addRow(i18n.get("lbl_model_name"), self.input_trans_model)
        group_con.setLayout(form)
        layout.addWidget(group_con)
        
        lbl = QLabel(i18n.get("lbl_trans_modes"))
        layout.addWidget(lbl)
        
        btn_add_prompt = QPushButton(i18n.get("btn_add_mode"))
        btn_add_prompt.clicked.connect(self.add_empty_prompt_row)
        layout.addWidget(btn_add_prompt)
        
        cols = ["模式", "描述", "系统提示词", "用户提示词", "思考", "流式"]
        self.table_prompts = QTableWidget()
        self.table_prompts.setColumnCount(len(cols))
        self.table_prompts.setHorizontalHeaderLabels(cols)
        self.table_prompts.setWordWrap(True)
        self.table_prompts.setColumnWidth(2, 450)
        self.table_prompts.setColumnWidth(3, 160)
        
        prompts = trans_cfg.get("custom_prompts", [])
        self.table_prompts.setRowCount(len(prompts))
        
        for r, p in enumerate(prompts):
            self.fill_prompt_row(r, p)
            
        self.table_prompts.cellChanged.connect(self.save_trans_config)
        layout.addWidget(self.table_prompts)

    def fill_prompt_row(self, r, p):
        self.table_prompts.setItem(r, 0, QTableWidgetItem(p.get("mode", "")))
        self.table_prompts.setItem(r, 1, QTableWidgetItem(p.get("description", "")))
        self.table_prompts.setItem(r, 2, QTableWidgetItem(p.get("system_prompt", "")))
        self.table_prompts.setItem(r, 3, QTableWidgetItem(p.get("prompt", "")))
        
        self.set_combo_cell(r, 4, p.get("enable_thinking", False))
        self.set_combo_cell(r, 5, p.get("stream", False))

    def set_combo_cell(self, row, col, current_val):
        combo = QComboBox()
        combo.addItems(["否", "是"])
        combo.setCurrentText("是" if current_val else "否")
        combo.currentTextChanged.connect(self.save_trans_config)
        self.table_prompts.setCellWidget(row, col, combo)

    def add_empty_prompt_row(self):
        r = self.table_prompts.rowCount()
        self.table_prompts.insertRow(r)
        self.fill_prompt_row(r, {})

    def save_trans_config(self):
        prompts = []
        for r in range(self.table_prompts.rowCount()):
            mode = self.table_prompts.item(r, 0).text() if self.table_prompts.item(r, 0) else ""
            desc = self.table_prompts.item(r, 1).text() if self.table_prompts.item(r, 1) else ""
            sys_p = self.table_prompts.item(r, 2).text() if self.table_prompts.item(r, 2) else ""
            usr_p = self.table_prompts.item(r, 3).text() if self.table_prompts.item(r, 3) else ""
            
            combo_think = self.table_prompts.cellWidget(r, 4)
            think_val = combo_think.currentText() == "是" if combo_think else False
            
            combo_stream = self.table_prompts.cellWidget(r, 5)
            stream_val = combo_stream.currentText() == "是" if combo_stream else False
            
            if mode:
                prompts.append({
                    "mode": mode,
                    "description": desc,
                    "system_prompt": sys_p,
                    "prompt": usr_p,
                    "enable_thinking": think_val,
                    "stream": stream_val
                })
        
        trans_config = {
            "api_url": self.input_trans_url.text(),
            "api_key": self.input_trans_key.text(),
            "model": self.input_trans_model.text(),
            "custom_prompts": prompts
        }
        config.set("translation", trans_config)

    def init_gen_tab(self):
        layout = QVBoxLayout(self.tab_gen)
        form = QFormLayout()
        
        # Language
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["简体中文 (zh_CN)", "English (en_US)"])
        self.lang_map = {"简体中文 (zh_CN)": "zh_CN", "English (en_US)": "en_US"}
        
        current_lang = config.get("language", "zh_CN")
        for k, v in self.lang_map.items():
            if v == current_lang:
                self.combo_lang.setCurrentText(k)
        
        self.combo_lang.currentTextChanged.connect(self.save_lang_config)

        # Minimize to Tray
        self.chk_tray = QCheckBox()
        self.chk_tray.setChecked(config.get("minimize_to_tray", False))
        self.chk_tray.toggled.connect(lambda v: config.set("minimize_to_tray", v))

        # Hotkeys - set type so they know which hotkey to update
        self.hk_capture = HotkeyRecorder()
        self.hk_capture.hotkey_type = "screenshot"
        self.hk_capture.setText(config.get("hotkey_cature") or "F4")
        
        self.hk_trans = HotkeyRecorder()
        self.hk_trans.hotkey_type = "translate"
        self.hk_trans.setText(config.get("hotkey_trans_capture") or "F6")
        
        self.hk_show_main = HotkeyRecorder()
        self.hk_show_main.hotkey_type = "show_main"
        self.hk_show_main.setText(config.get("hotkey_show_main") or "F9")
        
        form.addRow(i18n.get("lbl_lang"), self.combo_lang)
        form.addRow(i18n.get("lbl_minimize_tray"), self.chk_tray)
        form.addRow(i18n.get("lbl_hk_capture"), self.hk_capture)
        form.addRow(i18n.get("lbl_hk_trans"), self.hk_trans)
        form.addRow(i18n.get("lbl_hk_show_main"), self.hk_show_main)
        
        layout.addLayout(form)
        layout.addStretch()

    def save_lang_config(self, text):
        val = self.lang_map.get(text, "zh_CN")
        config.set("language", val)

    def accept(self):
        super().accept()
