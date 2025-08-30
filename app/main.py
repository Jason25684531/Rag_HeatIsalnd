import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, Response

# 載入環境變數
load_dotenv()

# 添加 src 目錄到系統路徑
import sys
sys.path.append(str(Path(__file__).parent.parent))

# 導入 RAG 核心模組
from src.llm.gemini import get_gemini_model
from src.data_processing.document_loader import load_documents
from src.data_processing.text_splitter import split_documents
from src.vector_store.chroma_manager import ChromaManager
from src.rag.chain import create_conversational_rag_chain

# --- 【修改處】---
# 導入我們新建的 LineBotManager 類別
from app.line_handler import LineBotManager

# --- 1. 初始化 Flask App ---
app = Flask(__name__)

# --- 【修改處】---
# 建立並初始化 LineBotManager 實例，將其與 app 綁定
line_bot_manager = LineBotManager(app)

# --- 2. 初始化 RAG 引擎 ---
print("正在初始化 RAG 引擎...")
llm = get_gemini_model()
DOCUMENTS_DIR = str(Path(__file__).parent.parent / "data" / "documents")
CHROMA_DB_DIR = str(Path(__file__).parent.parent / "data" / "db")
CHROMA_COLLECTION_NAME = "rag_collection"
chroma_manager = ChromaManager(CHROMA_DB_DIR, CHROMA_COLLECTION_NAME)

raw_docs = load_documents(DOCUMENTS_DIR)
retriever = None
if raw_docs:
    split_docs = split_documents(raw_docs)
    chroma_manager.add_documents(split_docs)
    retriever = chroma_manager.create_hybrid_retriever(split_docs)
else:
    retriever = chroma_manager.get_vector_retriever()

# 建立 RAG 鏈實例
conversational_rag_chain = create_conversational_rag_chain(llm, retriever)

# --- 3. 【修改處】將 RAG 鏈注入到 LineBotManager 實例中 ---
line_bot_manager.set_rag_chain(conversational_rag_chain)

print("✅ RAG 引擎初始化完成，並已注入 LINE Manager 實例！")

# --- 4. API 路由定義 ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    session_id = data.get('session_id', str(uuid.uuid4()))
    if not message: return jsonify({"error": "Message is required"}), 400
    def generate():
        stream = conversational_rag_chain.stream({"input": message}, config={"configurable": {"session_id": session_id}})
        for chunk in stream:
            if "answer" in chunk:
                yield chunk['answer']
    return Response(generate(), mimetype='text/plain')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    global retriever, conversational_rag_chain, llm
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    
    filename = file.filename
    file_path = os.path.join(DOCUMENTS_DIR, filename)
    file.save(file_path)

    print(f"偵測到新文件 '{filename}'，正在重新索引...")
    raw_docs = load_documents(DOCUMENTS_DIR)
    split_docs = split_documents(raw_docs)
    chroma_manager.add_documents(split_docs)
    
    retriever = chroma_manager.create_hybrid_retriever(split_docs)
    conversational_rag_chain = create_conversational_rag_chain(llm, retriever)
    
    # 【修改處】將更新後的 RAG 鏈也設定到 LINE manager 實例中
    app.line_bot_manager.set_rag_chain(conversational_rag_chain)
    
    print("✅ 文件索引與 RAG 鏈更新完成！")
    return jsonify({"message": f"File '{filename}' uploaded and indexed successfully."})

# --- 【修改處】Webhook 路由現在呼叫 manager 的方法 ---
@app.route("/webhook", methods=['POST'])
def webhook():
    return app.line_bot_manager.handle_webhook_request(request)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)