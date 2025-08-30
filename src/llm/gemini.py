# Initialization of the Gemini language model
# src/llm/gemini.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI

def get_gemini_model() -> ChatGoogleGenerativeAI:
    """獲取並配置 Gemini 模型"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7,
        convert_system_message_to_human=True
    )