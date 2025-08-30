from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

# 查詢擴展的提示模板
# 指示 LLM 根據原始問題生成多個不同角度的查詢
QUERY_EXPANSION_PROMPT = ChatPromptTemplate.from_template(
    """
You are an AI assistant specializing in query expansion for retrieval systems.
Your task is to rewrite a given user query into 3 different versions, aiming to improve document retrieval.
The expanded queries should cover different angles, use synonyms, or rephrase the original intent.
Return ONLY the expanded queries, separated by newlines.

Original Query:
{question}

Expanded Queries:
"""
)

def create_query_expansion_chain(model) -> Runnable:
    """
    建立一個用於查詢擴展的 LangChain 鏈。

    Args:
        model: 用於生成擴展查詢的語言模型。

    Returns:
        一個接收問題並返回擴展查詢字串的 Runnable 鏈。
    """
    return QUERY_EXPANSION_PROMPT | model | StrOutputParser()
