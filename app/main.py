# app/main.py
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS

# 載入環境變數
load_dotenv()

# 添加 src 目錄到系統路徑，這樣才能正確導入我們的模組
import sys
sys.path.append(str(Path(__file__).parent.parent))

# 從我們創建的模組中導入所有需要的元件
from src.llm.gemini import get_gemini_model
from src.data_processing.document_loader import load_documents
from src.data_processing.text_splitter import split_documents
from src.vector_store.chroma_manager import ChromaManager
from src.rag.chain import create_conversational_rag_chain

# --- 1. 初始化 Flask 應用 ---
app = Flask(__name__)
CORS(app)  # 允許跨域請求，方便前後端分離開發

# --- 2. 設定常數與路徑 ---
DOCUMENTS_DIR = str(Path(__file__).parent.parent / "data" / "documents")
CHROMA_DB_DIR = str(Path(__file__).parent.parent / "data" / "db")
CHROMA_COLLECTION_NAME = "rag_collection"

# --- 3. 初始化 RAG 引擎 (應用程式啟動時執行一次) ---
print("正在初始化 RAG 引擎...")
llm = get_gemini_model()
chroma_manager = ChromaManager(CHROMA_DB_DIR, CHROMA_COLLECTION_NAME)

# 應用程式啟動時，自動載入並索引 /data/documents/ 中的現有文件
print(f"從 {DOCUMENTS_DIR} 載入文件...")
raw_docs = load_documents(DOCUMENTS_DIR)
# 先宣告 retriever 變數，它將在下面被賦值
retriever = None

if raw_docs:
    print("文件載入成功，正在進行文本分割、索引與檢索器建立...")
    split_docs = split_documents(raw_docs)
    chroma_manager.add_documents(split_docs)
    
    # =============================================================
    # ==建立混合式檢索器 ==
    # =============================================================
    retriever = chroma_manager.create_hybrid_retriever(split_docs)
    # =============================================================

else:
    print("在 data/documents/ 中未找到任何文件，僅初始化純向量檢索器。")
    # 如果沒有文件，則使用純向量檢索器作為備用
    retriever = chroma_manager.get_vector_retriever()

# 使用建立好的檢索器（可能是混合式或純向量式）來建立 RAG 鏈
conversational_rag_chain = create_conversational_rag_chain(llm, retriever)
print("✅ RAG 引擎初始化完成！")


# --- 4. API 路由定義 ---

@app.route('/')
def index():
    """提供前端主頁面"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """處理聊天請求"""
    data = request.json
    message = data.get('message')
    session_id = data.get('session_id', str(uuid.uuid4()))

    if not message:
        return jsonify({"error": "Message is required"}), 400

    def generate_stream_response():
        """使用 stream 模式，實現打字機效果的回應"""
        try:
            stream = conversational_rag_chain.stream(
                {"input": message},
                config={"configurable": {"session_id": session_id}}
            )
            for chunk in stream:
                if "answer" in chunk:
                    yield chunk['answer']
        except Exception as e:
            print(f"Error during stream generation: {e}")
            yield "抱歉，處理您的請求時發生錯誤。"

    return Response(generate_stream_response(), mimetype='text/plain')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """處理文件上傳並更新整個 RAG 系統"""
    # =============================================================
    # == 修改處：宣告我們要修改的是全局變數 ==
    # == 這樣才能在函式內部更新整個應用的 retriever 和 RAG 鏈 ==
    # =============================================================
    global retriever, conversational_rag_chain
    # =============================================================

    if 'file' not in request.files:
        return jsonify({"error": "請求中找不到檔案"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未選擇任何檔案"}), 400
    
    if file:
        filename = file.filename
        file_path = os.path.join(DOCUMENTS_DIR, filename)
        file.save(file_path)

        print(f"偵測到新文件 '{filename}'，正在重新索引並更新 RAG 系統...")
        raw_docs = load_documents(DOCUMENTS_DIR)
        split_docs = split_documents(raw_docs)
        chroma_manager.add_documents(split_docs)
        
        # =============================================================
        # == 修改處：重新建立混合式檢索器，並用它來更新全局的 RAG 鏈 ==
        # =============================================================
        retriever = chroma_manager.create_hybrid_retriever(split_docs)
        conversational_rag_chain = create_conversational_rag_chain(llm, retriever)
        # =============================================================
        
        print("✅ 文件索引與 RAG 鏈更新完成！")
        return jsonify({"message": f"檔案 '{filename}' 已成功上傳並索引。"}), 200

# --- 5. 啟動應用程式 ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

