# Module for loading and processing various document types
# src/data_processing/document_loader.py
from pathlib import Path
from typing import List
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document

def load_documents(directory_path: str) -> List[Document]:
    """
    從指定目錄載入 .txt 文件。
    未來可在此擴展以支持更多文件類型 (pdf, docx, etc.)。
    """
    # 目前只載入 .txt 文件
    loader = DirectoryLoader(
        directory_path,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
        use_multithreading=True
    )
    return loader.load()