"""
Text-to-Speech using gTTS (Optional for MVP)
Simple and free - works well for both English and Urdu
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SimpleTTS:
    """Simple TTS using gTTS (Google Text-to-Speech)"""
    
    def __init__(self):
        self.enabled = False
        
        try:
            from gtts import gTTS
            self.gTTS = gTTS
            self.enabled = True
            logger.info("gTTS available for text-to-speech")
        except ImportError:
            logger.warning("gTTS not installed. TTS disabled. Install with: pip install gtts")
    
    def synthesize(self, text: str, output_path: str, language: str = "en") -> bool:
        """
        Convert text to speech and save to file
        
        Args:
            text: Text to convert
            output_path: Where to save audio file
            language: Language code ('en' for English, 'ur' for Urdu)
            
        Returns:
            True if successful
        """
        if not self.enabled:
            logger.warning("TTS not available")
            return False
        
        try:
            # Create TTS object
            tts = self.gTTS(text=text, lang=language, slow=False)
            
            # Save to file
            tts.save(output_path)
            
            logger.info(f"TTS generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return False
    
    def synthesize_to_bytes(self, text: str, language: str = "en") -> Optional[bytes]:
        """
        Convert text to speech and return as bytes
        Useful for streaming
        """
        if not self.enabled:
            return None
        
        try:
            import io
            
            tts = self.gTTS(text=text, lang=language, slow=False)
            
            # Save to bytes buffer
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            return fp.read()
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None


# Global instance
_tts = None


def get_tts() -> SimpleTTS:
    """Get or create TTS instance"""
    global _tts
    if _tts is None:
        _tts = SimpleTTS()
    return _tts
