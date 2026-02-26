import json
import os
import sys

# Default configuration
DEFAULT_CONFIG = {
    "models": {
        "PP-OCRv5": {
            "url": "",
            "token": ""
        },
        "PP-StructureV3": {
            "url": "",
            "token": ""
        },
        "PaddleOCR-VL": {
            "url": "",
            "token": ""
        }
    },
    "current_model": "PP-StructureV3",
    "translation": {
        "api_url": "",
        "api_key": "",
        "model": "",
        "custom_prompts": [
            {
                "mode": "文本翻译",
                "description": "标准翻译",
                "system_prompt": "你是一个精通 ${tolang} 的专业翻译人员。请直接输出翻译结果，不要包含任何解释。",
                "prompt": "请将以下内容翻译为 ${tolang}：",
                "enable_thinking": False,
                "stream": False
            },
            {
                "mode": "学术翻译",
                "description": "专业学术风格，准确且正式",
                "system_prompt": "你是一个精通 ${tolang} 的专业学术翻译家。请直接输出翻译结果，不要包含任何解释。保持术语准确，行文正式。",
                "prompt": "请将以下内容翻译为 ${tolang}：",
                "enable_thinking": False,
                "stream": False
            },
            {
                "mode": "文章润色",
                "description": "优化文笔，提升流畅度",
                "system_prompt": "你是一个资深文学编辑。任务是润色用户提供的文本，使其更自然、流畅、优美。请直接输出润色后的正文，严禁输出\"这是润色后的版本\"等废话。",
                "prompt": "请润色以下内容，使其更加地道：",
                "enable_thinking": False,
                "stream": False
            },
            {
                "mode": "内容总结",
                "description": "提炼核心要点，生成摘要",
                "system_prompt": "你是一个高效的信息分析师。请阅读文本并输出简短精炼的总结。要求：1. 只输出总结内容。2. 只要结果，不要过程。",
                "prompt": "请总结以下内容的要点：",
                "enable_thinking": False,
                "stream": False
            }
        ]
    },
    "batch": {
        "images": {
            "output_dir": "output/images",
            "formats": ["md"]
        },
        "docs": {
            "output_dir": "output/docs",
            "formats": ["TXT Standard (.txt)"]
        }
    },
    "hotkey_cature": "F4",
    "hotkey_trans_capture": "F6",
    "save_dir": "output",
    "language": "zh_CN",
    "screenshot_model": "PP-OCRv5",
    "minimize_to_tray": True,
    "hotkey_batch": "Ctrl+F4",
    "export_format": ["md", "txt"]
}


class ConfigManager:
    def __init__(self):
        # Determine config file path (next to exe or script)
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            self.base_path = os.path.dirname(sys.executable)
        else:
            # Running as script
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.config_path = os.path.join(self.base_path, "config.json")
        self.data = {}
        self._load()

    def _load(self):
        # Check if config file exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.data = DEFAULT_CONFIG.copy()
                self._save()
        else:
            # First launch: create default config
            self.data = DEFAULT_CONFIG.copy()
            self._save()

    def _save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self._save()

    def get_model_config(self, model_name):
        return self.data.get("models", {}).get(model_name, {})

    def set_model_config(self, model_name, url, token):
        if "models" not in self.data:
            self.data["models"] = {}
        self.data["models"][model_name] = {"url": url, "token": token}
        self._save()

    def get_batch_config(self, mode):
        return self.data.get("batch", {}).get(mode, {})


# Global config instance
config = ConfigManager()
