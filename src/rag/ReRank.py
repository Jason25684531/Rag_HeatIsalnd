from typing import List
from langchain_core.documents import Document
from langchain_community.document_transformers import LongContextReorder

def reorder_documents(documents: List[Document]) -> List[Document]:
    """
    對檢索到的文件列表進行重新排序，以優化 LLM 的處理效果。

    這個函式會將最相關的文件放在列表的開頭和結尾，
    避免 LLM 的 "Lost in the Middle" 問題。

    Args:
        documents: 從 retriever 檢索到的文件列表。

    Returns:
        經過重新排序的文件列表。
    """
    if not documents:
        return []

    # LongContextReorder 是一個簡單的實作，它會改變文件的順序
    # 這樣最重要的資訊就分佈在上下文的兩端
    print(f"--- 正在對 {len(documents)} 份文件進行重新排序 (Re-ranking)... ---")
    reorderer = LongContextReorder()
    reordered_docs = reorderer.transform_documents(documents)
    
    print("✅ 文件重新排序完成。")
    return reordered_docs
