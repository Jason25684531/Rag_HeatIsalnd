RAG 熱島效應專家
系統完整流程報告
一份從使用者互動到 AI 生成的深度解析

階段一：服務啟動 (Initialization)
當執行 python run.py 時，應用程式在接受任何請求前，會先完成以下初始化步驟：

載入設定：讀取 .env 中的 API 金鑰與 LINE Bot 設定。

知識庫索引：載入、切割 .txt 文件，並將其轉換為向量存入 ChromaDB。

建立檢索器：初始化 BM25 與 MMR 向量檢索器，並組合成混合式檢索器。

組裝 RAG 鏈：將所有處理步驟串接成一個完整的對話鏈。

階段二：使用者互動流程
使用者輸入
使用者透過網頁或 LINE Bot 提出問題。

> 熱島效應是什麼？

➡️ 檢索前處理 (Pre-Retrieval)
1a. 結合歷史紀錄重寫問題
將模糊問題（如 "那是什麼？"）轉化為無需上下文即可理解的獨立問題。

// Input: (History: "什麼是熱島效應？"), "那有何影響？"
// Output: "熱島效應有何影響？"

➡️ 檢索 (Retrieval)
混合式檢索 (EnsembleRetriever)
稀疏檢索 (Sparse)：BM25 演算法，精準匹配關鍵字。

bm25_retriever.k = 3

密集檢索 (Dense)：向量搜尋，理解語義並透過 MMR 增加多樣性。

search_type="mmr", k=3

使用 Reciprocal Rank Fusion (RRF) 演算法融合兩者結果並排序，最多產出 6 份文件。

➡️ 檢索後處理 (Post-Retrieval)
文件重新排序與精選
使用 LongContextReorder 將重要文件置於頭尾，對抗「中間遺忘」，並只選取最精華的前 3 份文件。

// Input: [Doc1, Doc2, Doc3, Doc4, Doc5]
// Output: [Doc1, Doc5, Doc2] (示例)

➡️ 生成 (Generation)
建構最終提示並呼叫 LLM
將精選後的文件、問題、歷史和「熱島效應專家」人設 (System Prompt) 一併發送給 Gemini 模型。

➡️ AI 回應
以專家身份，生成專業、簡潔的答案，並以串流形式回傳至網頁或推送至 LINE。