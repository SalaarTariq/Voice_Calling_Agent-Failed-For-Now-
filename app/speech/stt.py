"""
Speech-to-Text using Whisper (Optional for MVP)
Can be used for voice calls in future
"""

import logging
import os

logger = logging.getLogger(__name__)


class WhisperSTT:
    """Whisper Speech-to-Text handler"""
    
    def __init__(self):
        self.model = None
        self.enabled = False
        
        try:
            import whisper
            self.whisper = whisper
            self.enabled = True
            logger.info("Whisper STT available (not loaded yet)")
        except ImportError:
            logger.warning("Whisper not installed. STT disabled. Install with: pip install openai-whisper")
    
    def load_model(self, model_size="base"):
        """Load Whisper model (lazy loading)"""
        if not self.enabled:
            raise RuntimeError("Whisper not installed")
        
        if self.model is None:
            logger.info(f"Loading Whisper model: {model_size}")
            self.model = self.whisper.load_model(model_size)
            logger.info("Whisper model loaded")
    
    def transcribe(self, audio_path: str, language: str = None) -> str:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file
            language: Optional language code ('en' or 'ur')
            
        Returns:
            Transcribed text
        """
        if not self.enabled:
            return "[STT not available - Whisper not installed]"
        
        try:
            # Lazy load model
            if self.model is None:
                self.load_model()
            
            # Transcribe
            result = self.model.transcribe(
                audio_path,
                language=language,
                fp16=False  # Use fp32 for CPU compatibility
            )
            
            text = result["text"].strip()
            logger.info(f"Transcribed: {text[:50]}...")
            
            return text
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return f"[Transcription error: {e}]"


# Global instance
_stt = None


def get_stt() -> WhisperSTT:
    """Get or create STT instance"""
    global _stt
    if _stt is None:
        _stt = WhisperSTT()
    return _stt
