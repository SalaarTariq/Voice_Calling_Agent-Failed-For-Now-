"""
LLM Provider - Single LLM selection (Gemini OR Groq)
No fallbacks for MVP simplicity
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_llm():
    """
    Get LLM instance based on environment configuration
    Returns either Gemini or Groq - NO fallback
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider == "gemini":
        return get_gemini_llm()
    elif provider == "groq":
        return get_groq_llm()
    else:
        raise ValueError(f"Invalid LLM_PROVIDER: {provider}. Must be 'gemini' or 'groq'")


def get_gemini_llm():
    """Initialize Gemini LLM"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=2048,
        )
        
        logger.info("Gemini LLM initialized successfully")
        return llm
        
    except ImportError:
        raise ImportError("langchain-google-genai not installed. Run: pip install langchain-google-genai")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        raise


def get_groq_llm():
    """Initialize Groq LLM"""
    try:
        from langchain_groq import ChatGroq
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        llm = ChatGroq(
            model="mixtral-8x7b-32768",  # Fast and good for conversations
            groq_api_key=api_key,
            temperature=0.7,
            max_tokens=2048,
        )
        
        logger.info("Groq LLM initialized successfully")
        return llm
        
    except ImportError:
        raise ImportError("langchain-groq not installed. Run: pip install langchain-groq")
    except Exception as e:
        logger.error(f"Failed to initialize Groq: {e}")
        raise
