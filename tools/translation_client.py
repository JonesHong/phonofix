import json
import urllib.request
import urllib.error

def translate_text(text, target_lang="zh-tw"):
    """
    Call the local translation API.
    Endpoint: POST http://localhost:8000/api/v1/translate
    
    Args:
        text (str): The text to translate.
        target_lang (str): The target language code (default: "zh-tw").
        
    Returns:
        str: The translated text, or an error message if translation fails.
    """
    url = "http://localhost:8000/api/v1/translate"
    payload = {
        "text": text,
        "target_lang": target_lang,
        "preferred_provider": "auto",
        "is_refined": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("success"):
                    return result["data"]["text"]
    except Exception:
        return "[Translation Skipped]"
    return "[Translation Failed]"
