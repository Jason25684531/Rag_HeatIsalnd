from app.main import app

if __name__ == "__main__":
    # 將主機設置為 '0.0.0.0' 可以讓同一個區域網路下的其他設備
    # debug=True 會在程式碼變更時自動重啟伺服器，方便開發。
    # 生產環境中應設置為 False。
    app.run(host='0.0.0.0', port=5000, debug=True)