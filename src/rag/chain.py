from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser

# 導入我們自定義的模組
from .query_expansion import create_query_expansion_chain
from .ReRank import reorder_documents
from src.config import QA_SYSTEM_PROMPT, CONTEXTUALIZE_Q_SYSTEM_PROMPT


# 儲存每個 session 的歷史記錄 (In-memory)
store = {}

def get_session_history(session_id: str):
    """根據 session_id 獲取或創建一個對話歷史記錄"""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def create_conversational_rag_chain(model, retriever):
    """
    建立一個整合了 Pre-Retrieval 和 Post-Retrieval 的完整 RAG 鏈。
    此版本修正了 RunnableWithMessageHistory 的輸入類型錯誤。
    """
    # 【修改處】：直接使用從 config 導入的 CONTEXTUALIZE_Q_SYSTEM_PROMPT
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", CONTEXTUALIZE_Q_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    rewrite_question_chain = contextualize_q_prompt | model | StrOutputParser()

    # --- 步驟 2: 建立「文件檢索與後處理」鏈 ---
    query_expansion_chain = create_query_expansion_chain(model)

    def retrieval_and_postprocessing_chain(rewritten_question: str):
        expanded_queries = query_expansion_chain.invoke({"question": rewritten_question})
        full_query = rewritten_question + "\n" + expanded_queries
        print(f"--- 執行檢索的完整查詢 ---\n{full_query}\n--------------------------")
        retrieved_docs = retriever.invoke(full_query)
        reranked_docs = reorder_documents(retrieved_docs)
        return reranked_docs

    # --- 步驟 3: 建立最終問答鏈 ---
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", QA_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    question_answer_chain = create_stuff_documents_chain(model, qa_prompt)

    # --- 步驟 4: 使用 LCEL 串起所有流程 ---
    rag_chain = (
        RunnablePassthrough.assign(
            rewritten_question=rewrite_question_chain
        ).assign(
            context=lambda x: retrieval_and_postprocessing_chain(x["rewritten_question"])
        )
        | question_answer_chain
    )

    # --- 【關鍵修正處】 ---
    # 我們建立一個新的鏈，其唯一的目的就是將 rag_chain 的字串輸出
    # 打包成一個符合規範的字典。
    def format_output(answer_string):
        """將純文字答案包裝成字典"""
        return {"answer": answer_string}

    # 建立一個最終的可執行鏈，它包含了格式化輸出的步驟
    final_chain = rag_chain | RunnableLambda(format_output)

    # --- 步驟 5: 綁定對話歷史管理功能 ---
    conversational_rag_chain_with_summary = RunnableWithMessageHistory(
        final_chain, # <-- 現在傳遞的是一個 Runnable 物件，而不是字典
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer", # 這個 key 能成功匹配到 final_chain 輸出的字典
    )

    return conversational_rag_chain_with_summary

