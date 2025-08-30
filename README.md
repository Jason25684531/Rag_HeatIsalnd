# RAG 系統完整流程說明

本文件詳細描述了這套進階 RAG (Retrieval-Augmented Generation) 系統從服務啟動到使用者互動的完整處理流程。

---

## 一、服務啟動階段 (Initialization)

當執行 `python run.py` 時，應用程式在接受任何請求前，會先完成以下初始化步驟：

### 1. 載入設定
- 讀取 `.env` 檔案中的環境變數（如 `GOOGLE_API_KEY`）。

### 2. 初始化核心元件
- **LLM**：初始化 Google Gemini 模型。  
- **ChromaDB**：初始化本地的 ChromaDB 客戶端，並載入指定的集合 (collection)。

### 3. 建立知識庫索引 (Indexing)
- **載入文件 (`document_loader.py`)**：掃描 `data/documents/` 目錄，載入所有 `.txt` 檔案。  
- **文本分割 (`text_splitter.py`)**：將載入的文件分割成大小適中且有重疊的文本片段 (chunks)。

### 4. Embedding 與儲存 (`chroma_manager.py`)
- 使用 `BAAI/bge-large-zh-v1.5` Embedding 模型將每個文本片段轉換為向量。  
- 將向量與其對應的原始文本存入 ChromaDB。

### 5. 建立 RAG 鏈 (`chain.py`)
- **建立混合式檢索器 (Hybrid Retriever)**：
  - 初始化 `BM25Retriever`（關鍵字檢索）。  
  - 初始化 Chroma 向量檢索器，並設定為 MMR 模式（最大邊際相關性）。  
  - 將兩者結合成一個 `EnsembleRetriever`，設定權重為 `[0.5, 0.5]`。

- **組裝完整對話鏈**：將所有 Pre-Retrieval、Retrieval、Post-Retrieval 和 Generation 步驟用 LCEL 串接起來，並與對話歷史功能綁定。

### 6. 啟動 Flask 伺服器
- 等待前端的請求。

---

## 二、使用者互動流程 (User Interaction)

當使用者在前端介面輸入問題並按下「傳送」後，後端會觸發以下處理：

### 第 1 站：檢索前處理 (Pre-Retrieval)

**目標**：將使用者的原始問題轉化成最適合進行文件檢索的「黃金查詢」。

1. **結合歷史紀錄重寫問題 (History-Aware Rewrite)**  
   - **輸入**：使用者最新問題 + 完整對話歷史  
   - **處理**：RAG 鏈呼叫 LLM，使用 `CONTEXTUALIZE_Q_SYSTEM_PROMPT` 將問題改寫成一個無需上下文即可理解的完整問題  
   - **輸出**：一個獨立、清晰的問題字串

2. **查詢擴展 (Query Expansion)**  
   - **輸入**：上一步產出的獨立問題  
   - **處理**：RAG 鏈再次呼叫 LLM，生成 3 個不同措辭或角度的相似問題  
   - **輸出**：包含原始問題與擴展問題的長字串

---

### 第 2 站：檢索 (Retrieval)

**目標**：使用「黃金查詢」從知識庫找出最相關的文件片段。

- **處理**：`EnsembleRetriever` 開始工作  
  - **並行檢索**：
    - `BM25Retriever` 根據關鍵字找出 Top 5 文件  
    - Chroma 向量儲存使用 MMR 演算法，找出 Top 5 文件（兼具相關性與多樣性）
  - **結果融合 (Reciprocal Rank Fusion)**：  
    - 收集兩組結果（最多 10 份文件）  
    - 使用 RRF 演算法計算新綜合分數  
    - 產生最終、已排序列表

- **輸出**：已按綜合相關性排序的文件列表

---

### 第 3 站：檢索後處理 (Post-Retrieval)

**目標**：優化檢索到的文件列表，使 LLM 高效利用。

- **處理**：`reorder_documents` 使用 `LongContextReorder` 演算法  
  - 將最重要的文件（列表開頭）和次重要文件（列表結尾）交錯排列  
  - 對抗 LLM 的「中間遺忘 (Lost in the Middle)」問題

- **輸出**：順序經過優化的文件列表

---

### 第 4 站：生成 (Generation)

**目標**：生成最終回答。

- **處理**：
  - **建構最終提示 (Prompt)**：將優化後的文件內容作為 `{context}`，使用者原始問題 `{input}` 與對話歷史填入 `QA_SYSTEM_PROMPT` 模板  
  - **呼叫 LLM**：將提示發送給 Gemini 模型

- **輸出**：  
  - Gemini 根據設定角色（如「熱島效應專家」）生成專業、簡潔且在 100 字以內的答案  
  - 以串流 (Stream) 形式即時回傳給前端
