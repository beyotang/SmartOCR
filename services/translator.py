import requests
from app_config import config

class TranslatorService:
    def translate(self, text, mode_name="文本翻译", target_lang="中文"):
        """
        Translates text using a custom AI Model, specific Prompt Mode, and Target Language.
        """
        trans_cfg = config.get("translation", {})
        api_url = trans_cfg.get("api_url")
        api_key = trans_cfg.get("api_key")
        model = trans_cfg.get("model")
        
        if not api_url:
            return f"[Error]: Translation API URL not configured in Settings."

        # Find the prompt template
        prompts = trans_cfg.get("custom_prompts", [])
        template = next((p for p in prompts if p["mode"] == mode_name), None)
        
        if not template:
            return f"[Error]: Mode '{mode_name}' not found."

        # Replace placeholders
        # We replace `${tolang}` AND `target_lang` to be safe/compatible with user prompt style
        sys_prompt = template.get("system_prompt", "")
        sys_prompt = sys_prompt.replace("${tolang}", target_lang).replace("target_lang", target_lang)
        
        user_prompt_prefix = template.get("prompt", "")
        user_prompt_prefix = user_prompt_prefix.replace("${tolang}", target_lang).replace("target_lang", target_lang)
        
        final_user_content = f"{user_prompt_prefix}\n{text}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": final_user_content}
            ],
            "stream": False
        }
        
        try:
            req_url = api_url
            # Auto-append endpoint if missing (simple heuristic)
            if "chat/completions" not in req_url:
                if req_url.endswith("/"):
                    req_url += "v1/chat/completions"
                else:
                    req_url += "/v1/chat/completions"
                
            resp = requests.post(req_url, json=payload, headers=headers, timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    return f"API returned no choices: {data}"
            else:
                return f"Error: {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"Translation Error: {e}"

translator = TranslatorService()
