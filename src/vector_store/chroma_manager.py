from typing import List
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_chroma import Chroma
import chromadb # <-- 導入 chromadb 以使用其設定

# --- 【修正處 1】---
# 根據 LangChain 的更新，從新的套件導入 HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

class ChromaManager:
    def __init__(self, db_path: str, collection_name: str):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_function = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3"
        )

        # --- 【修正處 2】---
        # 明確地建立一個 ChromaDB 客戶端，並指定設定。
        # 這有助於解決在開發伺服器重啟時的 SQLite 鎖定問題。
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=chromadb.Settings(
                # 這裡可以加入更多 ChromaDB 的微調設定
                anonymized_telemetry=False # 建議關閉遙測
            ),
        )

        self.vector_store = Chroma(
            client=self.client, # <-- 使用我們剛剛建立的客戶端
            collection_name=collection_name,
            embedding_function=self.embedding_function,
        )

    def add_documents(self, documents: List[Document]):
        """將文檔添加到 ChromaDB"""
        self.vector_store.add_documents(documents)
        print(f"成功將 {len(documents)} 個文檔片段添加到 ChromaDB。")

    def create_hybrid_retriever(self, documents: List[Document]) -> EnsembleRetriever:
        """
        建立一個結合了 BM25 關鍵字搜尋和 Chroma 向量搜尋的混合式檢索器。
        """
        if not documents:
            print("警告：沒有提供文件給 BM25，僅使用向量檢索。")
            return self.get_vector_retriever()

        print("正在建立混合式檢索器 (Hybrid Retriever)...")
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = 5

        vector_retriever = self.get_vector_retriever()

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever], weights=[0.5, 0.5]
        )
        
        print("✅ 混合式檢索器建立完成！")
        return ensemble_retriever

    def get_vector_retriever(self) -> VectorStoreRetriever:
        """
        獲取向量檢索器，並啟用 MMR (Maximal Marginal Relevance) 模式。
        """
        print("啟用 MMR 模式來優化檢索結果的多樣性。")
        return self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                'k': 5,          # 最終要返回的文檔數量
                'fetch_k': 20,   # 初始獲取的候選文檔數量
                'lambda_mult': 0.7 # 控制多樣性。1為最大多樣性，0為最大相關性。
            }
        )

