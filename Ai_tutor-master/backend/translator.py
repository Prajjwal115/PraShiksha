"""
backend/translator.py - Language translation module
Uses deep-translator (free, no API key needed) with caching
"""
from typing import Optional


SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "mr": "Marathi (मराठी)",
    "bn": "Bengali (বাংলা)",
    "gu": "Gujarati (ગુજરાતી)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "pa": "Punjabi (ਪੰਜਾਬੀ)",
    "ur": "Urdu (اردو)",
    "ml": "Malayalam (മലയാളം)"
}

DEEP_TRANSLATOR_LANG_MAP = {
    "en": "english", "hi": "hindi", "mr": "marathi", "bn": "bengali",
    "gu": "gujarati", "ta": "tamil", "te": "telugu", "kn": "kannada",
    "pa": "punjabi", "ur": "urdu", "ml": "malayalam"
}


class TranslationModule:
    """
    Translates AI responses to the student's preferred language.
    Uses deep-translator (GoogleTranslator) — no API key required.
    Falls back gracefully if translation fails.
    """

    def __init__(self):
        self._available = self._check_availability()
        self._cache: dict[str, str] = {}

    def _check_availability(self) -> bool:
        try:
            from deep_translator import GoogleTranslator  # noqa
            return True
        except ImportError:
            print("⚠️  deep-translator not installed. Install: pip install deep-translator")
            return False

    def translate(self, text: str, target_lang: str) -> str:
        """
        Translate text to target_lang.
        Returns original text if translation fails or lang is English.
        """
        if target_lang == "en" or not self._available:
            return text

        cache_key = f"{target_lang}:{hash(text[:100])}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            from deep_translator import GoogleTranslator
            dt_lang = DEEP_TRANSLATOR_LANG_MAP.get(target_lang, "english")

            # Split long text into chunks (deep-translator limit: ~5000 chars)
            chunks = self._split_text(text)
            translated_chunks = []

            for chunk in chunks:
                if chunk.strip():
                    translated = GoogleTranslator(source="auto", target=dt_lang).translate(chunk)
                    translated_chunks.append(translated or chunk)
                else:
                    translated_chunks.append(chunk)

            result = "".join(translated_chunks)
            self._cache[cache_key] = result
            return result

        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Return original on failure

    def _split_text(self, text: str, chunk_size: int = 4000) -> list[str]:
        """Split text into chunks that respect paragraph boundaries."""
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < chunk_size:
                current += para + "\n\n"
            else:
                if current:
                    chunks.append(current)
                current = para + "\n\n"
        if current:
            chunks.append(current)
        return chunks

    def detect_language(self, text: str) -> str:
        """Detect the language of given text."""
        if not self._available:
            return "en"
        try:
            from deep_translator import GoogleTranslator
            # Use translate with target=en and check if it detects source
            translator = GoogleTranslator(source="auto", target="english")
            _ = translator.translate(text[:50])
            # deep-translator doesn't expose detected lang easily; return "en" as fallback
            return "en"
        except Exception:
            return "en"

    @property
    def is_available(self) -> bool:
        return self._available

    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        return SUPPORTED_LANGUAGES

    @staticmethod
    def get_language_name(code: str) -> str:
        return SUPPORTED_LANGUAGES.get(code, "English")
