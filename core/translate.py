from deep_translator import GoogleTranslator
import os

def translate_text(text):
    """Traduz um texto para o idioma especificado."""
    raw_lang = os.getenv("LANG", "pt")
    clean_lang = raw_lang.split(".")[0].split("_")[0].lower()
    try:
        return GoogleTranslator(source='auto', target=clean_lang).translate(text)
    except Exception:
        return GoogleTranslator(source='auto', target="en").translate(text)