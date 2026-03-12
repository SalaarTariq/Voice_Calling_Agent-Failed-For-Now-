"""
LLM Provider - Gemini or Groq via LangChain
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_llm():
    """
    Get LLM instance based on LLM_PROVIDER env var.
    Returns a LangChain chat model (Gemini or Groq).
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        return _get_gemini()
    elif provider == "groq":
        return _get_groq()
    else:
        raise ValueError(f"Invalid LLM_PROVIDER: {provider}. Must be 'gemini' or 'groq'")


def _get_gemini():
    """Initialize Gemini LLM"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=2048,
        )

        logger.info("Gemini LLM initialized")
        return llm

    except ImportError:
        raise ImportError("langchain-google-genai not installed. Run: pip install langchain-google-genai")


def _get_groq():
    """Initialize Groq LLM"""
    try:
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=api_key,
            temperature=0.7,
            max_tokens=2048,
        )

        logger.info("Groq LLM initialized")
        return llm

    except ImportError:
        raise ImportError("langchain-groq not installed. Run: pip install langchain-groq")
