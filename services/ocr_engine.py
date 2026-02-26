import requests
import base64
import time
from app_config import config


class PaddleOCRClient:
    def __init__(self):
        # Use a session for connection reuse
        self._session = requests.Session()
        # Set default headers
        self._session.headers.update({
            "Content-Type": "application/json"
        })
    
    def ocr_image(self, image_data: bytes, model_override=None, stop_event=None, optimize_for_small=True):
        """OCR for images (fileType=1). Default optimizes for small text (screenshot mode)."""
        return self.ocr_file(image_data, file_type=1, model_override=model_override, 
                            stop_event=stop_event, optimize_for_small=optimize_for_small)

    def ocr_file(self, file_data: bytes, file_type=1, model_override=None, stop_event=None, optimize_for_small=False):
        """
        OCR for any file.
        file_type: 0 = PDF/document, 1 = image
        stop_event: threading.Event to signal cancellation
        optimize_for_small: If True, use optimized parameters for small text (slower but more accurate)
        """
        # Check if already stopped before starting
        if stop_event and stop_event.is_set():
            return {"error": "任务已被用户终止"}
        
        current_model = model_override if model_override else config.get("current_model")
        model_config = config.get_model_config(current_model)

        api_url = model_config.get("url")
        token = model_config.get("token")

        if not api_url or not token:
            return {"error": f"缺少 {current_model} 的 URL 或 Token，请在设置中配置。"}

        file_b64 = base64.b64encode(file_data).decode("ascii")

        headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }

        # Base payload - only required parameters for faster processing
        payload = {"file": file_b64, "fileType": file_type}
        
        # Only add optimization parameters for screenshot mode (small text detection)
        # For batch processing, use default API parameters for speed
        if optimize_for_small:
            if current_model == "PP-OCRv5":
                # Optimize for small text detection (screenshot mode)
                payload["textDetThresh"] = 0.15
                payload["textDetBoxThresh"] = 0.3
                payload["textDetUnclipRatio"] = 2.0
                payload["textRecScoreThresh"] = 0.0
                
            elif current_model == "PP-StructureV3":
                payload["textDetThresh"] = 0.15
                payload["textDetBoxThresh"] = 0.3
                payload["textDetUnclipRatio"] = 2.0
                
            elif current_model == "PaddleOCR-VL":
                payload["temperature"] = 0.1

        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Check stop_event before making the request
                if stop_event and stop_event.is_set():
                    return {"error": "任务已被用户终止"}
                
                # Use reasonable timeout - 10s for connect, 90s for read
                response = self._session.post(
                    api_url, 
                    json=payload, 
                    headers=headers, 
                    timeout=(10, 90)
                )

                # Check stop after request
                if stop_event and stop_event.is_set():
                    return {"error": "任务已被用户终止"}

                if response.status_code != 200:
                    return {"error": f"HTTP {response.status_code}", "raw_response": response.text[:500]}

                result_json = response.json()

                if "errorCode" in result_json and result_json["errorCode"] != 0:
                    return {"error": f"API错误: {result_json.get('errorMsg')}", "raw_response": str(result_json)[:500]}

                return self._parse_result(result_json, current_model)

            except requests.exceptions.Timeout as e:
                last_error = "请求超时，请检查网络或稍后重试"
                if attempt < max_retries:
                    time.sleep(1)  # Wait 1 second before retry
                    continue
            except requests.exceptions.ConnectionError as e:
                if stop_event and stop_event.is_set():
                    return {"error": "任务已被用户终止"}
                last_error = f"连接错误: {str(e)[:80]}"
                if attempt < max_retries:
                    time.sleep(1)  # Wait 1 second before retry
                    continue
            except Exception as e:
                if stop_event and stop_event.is_set():
                    return {"error": "任务已被用户终止"}
                return {"error": f"异常: {str(e)}"}
        
        return {"error": last_error or "请求失败"}

    def _parse_result(self, json_data, model_name=None):
        """Parse API response for all model types."""
        res = json_data.get("result", {})
        all_lines = []
        markdown_text = ""
        tables_html = []  # List of HTML tables from PP-StructureV3
        layout_data = []

        # ========== PP-StructureV3 Format ==========
        # Returns layoutParsingResults with markdown.text and table_res_list
        if "layoutParsingResults" in res and isinstance(res["layoutParsingResults"], list):
            for item in res["layoutParsingResults"]:
                # Get markdown text (primary output for PP-StructureV3)
                if "markdown" in item and isinstance(item["markdown"], dict):
                    md_text = item["markdown"].get("text", "")
                    if md_text:
                        markdown_text += md_text + "\n\n"
                
                # Get table HTML from table_res_list (key for Excel export)
                if "table_res_list" in item and isinstance(item["table_res_list"], list):
                    for table in item["table_res_list"]:
                        if "pred_html" in table:
                            tables_html.append(table["pred_html"])
                
                # Get prunedResult text
                if "prunedResult" in item:
                    pr = item["prunedResult"]
                    if isinstance(pr, str):
                        all_lines.append(pr)
                    elif isinstance(pr, dict):
                        if "text" in pr:
                            all_lines.append(pr["text"])
                        if "rec_texts" in pr:
                            all_lines.extend([t for t in pr["rec_texts"] if isinstance(t, str)])
                
                # Get parsing_res_list for layout data
                if "parsing_res_list" in item:
                    for block in item["parsing_res_list"]:
                        block_content = block.get("block_content", "")
                        block_label = block.get("block_label", "text")
                        if block_content:
                            layout_data.append({
                                "label": block_label,
                                "content": block_content,
                                "bbox": block.get("block_bbox"),
                                "order": block.get("block_order")
                            })
                            if block_label != "table":  # Avoid duplicating table content
                                all_lines.append(block_content)

        # ========== PP-OCRv5 Format ==========
        if "ocrResults" in res and isinstance(res["ocrResults"], list):
            for ocr_item in res["ocrResults"]:
                if "prunedResult" in ocr_item:
                    pr = ocr_item["prunedResult"]
                    if isinstance(pr, str):
                        all_lines.append(pr)
                    elif isinstance(pr, dict) and "rec_texts" in pr:
                        all_lines.extend([t for t in pr["rec_texts"] if isinstance(t, str)])
                
                if "rec_texts" in ocr_item and isinstance(ocr_item["rec_texts"], list):
                    for text in ocr_item["rec_texts"]:
                        if isinstance(text, str) and text.strip():
                            all_lines.append(text)

        # ========== Fallback: rec_texts at result level ==========
        if not all_lines and "rec_texts" in res:
            if isinstance(res["rec_texts"], list):
                for text in res["rec_texts"]:
                    if isinstance(text, str) and text.strip():
                        all_lines.append(text)

        # ========== PaddleOCR-VL Format ==========
        if not all_lines and "structureResults" in res:
            for item in res["structureResults"]:
                if "rec_texts" in item and isinstance(item["rec_texts"], list):
                    all_lines.extend([t for t in item["rec_texts"] if isinstance(t, str)])

        # Build result
        if not all_lines and not markdown_text and not tables_html:
            return {
                "words_result": [], 
                "markdown": "",
                "tables_html": [],
                "layout_data": [],
                "debug_info": f"未找到文字。结果键: {list(res.keys())}", 
                "raw_response": str(json_data)[:500]
            }

        # Use markdown_text if available (PP-StructureV3), otherwise join lines
        if markdown_text:
            final_text = markdown_text.strip()
        else:
            final_text = "\n".join(all_lines)

        return {
            "words_result": [{"words": line} for line in all_lines] if all_lines else [{"words": final_text}],
            "markdown": markdown_text,
            "tables_html": tables_html,  # HTML tables for Excel export
            "layout_data": layout_data,
            "raw_result": res
        }


ocr_client = PaddleOCRClient()
