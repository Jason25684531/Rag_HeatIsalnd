from app.main import app

if __name__ == "__main__":
    # 將主機設置為 '0.0.0.0' 可以讓同一個區域網路下的其他設備
    # (例如您的手機) 透過您電腦的 IP 位址來訪問這個應用程式。
    # 如果您只想讓本機訪問，可以改回 '12-7.0.0.1'。
    # debug=True 會在程式碼變更時自動重啟伺服器，方便開發。
    # 生產環境中應設置為 False。
    app.run(host='0.0.0.0', port=5000, debug=True)