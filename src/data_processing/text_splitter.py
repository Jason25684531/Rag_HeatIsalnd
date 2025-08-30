# src/data_processing/text_splitter.py
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_documents(documents: List[Document]) -> List[Document]:
    """
    使用 RecursiveCharacterTextSplitter 將文檔分割成更小的片段。

    Args:
        documents: 從 loader 載入的 Document 對象列表。

    Returns:
        分割後的 Document 對象列表。
    """
    # 初始化文本分割器
    # chunk_size: 每個文本片段的最大長度（字元數）。
    # chunk_overlap: 相鄰片段之間的重疊字元數。這有助於保持上下文的連續性。
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )
    
    print(f"準備將 {len(documents)} 份文件進行分割...")
    split_docs = text_splitter.split_documents(documents)
    print(f"文件已成功分割成 {len(split_docs)} 個片段。")
    
    return split_docs