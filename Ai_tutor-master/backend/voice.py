"""
backend/voice.py - Text-to-Speech module
Supports: gTTS (online, multilingual), pyttsx3 (offline fallback)
"""
import os
import io
import tempfile
import threading
from typing import Optional


LANGUAGE_CODES = {
    "en": "en", "hi": "hi", "mr": "mr", "bn": "bn",
    "gu": "gu", "ta": "ta", "te": "te", "kn": "kn", "pa": "pa"
}


class VoiceModule:
    """
    Text-to-Speech module.
    Primary: gTTS (Google TTS) - requires internet
    Fallback: pyttsx3 - offline
    In Streamlit: returns audio bytes for st.audio()
    """

    def __init__(self, language: str = "en"):
        self.language = language
        self._gtts_available = self._check_gtts()
        self._pyttsx3_available = self._check_pyttsx3()

    def _check_gtts(self) -> bool:
        try:
            import gtts  # noqa
            return True
        except ImportError:
            return False

    def _check_pyttsx3(self) -> bool:
        try:
            import pyttsx3  # noqa
            return True
        except ImportError:
            return False

    def set_language(self, language: str):
        self.language = language

    def text_to_audio_bytes(self, text: str) -> Optional[bytes]:
        """
        Convert text to audio bytes (MP3 via gTTS, WAV via pyttsx3).
        Returns bytes for st.audio() in Streamlit, or None if unavailable.
        """
        # Clean text: remove markdown symbols
        clean = self._clean_text(text)

        if self._gtts_available:
            return self._gtts_bytes(clean)
        elif self._pyttsx3_available:
            return self._pyttsx3_bytes(clean)
        return None

    def _clean_text(self, text: str) -> str:
        import re
        # Remove markdown formatting
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)       # italic
        text = re.sub(r'#+\s', '', text)                # headings
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # code blocks
        text = re.sub(r'`(.+?)`', r'\1', text)          # inline code
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text) # links
        text = re.sub(r'^\s*[-*]\s', '', text, flags=re.MULTILINE)  # bullets
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _gtts_bytes(self, text: str) -> Optional[bytes]:
        try:
            from gtts import gTTS
            lang_code = LANGUAGE_CODES.get(self.language, "en")
            # gTTS has a character limit per call; split long texts
            if len(text) > 500:
                text = text[:500] + "..."  # truncate for speed in demo

            tts = gTTS(text=text, lang=lang_code, slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return buf.read()
        except Exception as e:
            print(f"gTTS error: {e}")
            return None

    def _pyttsx3_bytes(self, text: str) -> Optional[bytes]:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                tmp_path = f.name

            engine.save_to_file(text[:300], tmp_path)
            engine.runAndWait()
            engine.stop()

            with open(tmp_path, 'rb') as f:
                audio_bytes = f.read()
            os.unlink(tmp_path)
            return audio_bytes
        except Exception as e:
            print(f"pyttsx3 error: {e}")
            return None

    @property
    def is_available(self) -> bool:
        return self._gtts_available or self._pyttsx3_available

    @property
    def audio_format(self) -> str:
        return "mp3" if self._gtts_available else "wav"
