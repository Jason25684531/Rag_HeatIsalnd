import os
import threading
from flask import current_app
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

class LineBotManager:
    def __init__(self, app=None):
        self.app = app
        self.rag_chain = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """將管理器綁定到指定的 Flask app 實例。"""
        self.app = app
        app.line_bot_manager = self  # 將此實例附加到 app 物件上

        channel_secret = os.getenv('LINE_CHANNEL_SECRET')
        channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        
        if not channel_secret or not channel_access_token:
            print("警告：LINE Channel Secret 或 Access Token 未設定。LINE Bot 功能將無法使用。")
            self.handler = None
            self.configuration = None
            return

        self.configuration = Configuration(access_token=channel_access_token)
        self.handler = WebhookHandler(channel_secret)

        self.handler.add(
            MessageEvent,
            message=TextMessageContent
        )(lambda event, destination: self.handle_message(event))

    def set_rag_chain(self, chain):
        self.rag_chain = chain
        print("✅ RAG chain has been set in the LineBotManager instance.")

    def handle_webhook_request(self, request):
        if not self.handler:
            print("錯誤：LineBotManager 未成功初始化。")
            return 'Configuration error', 500
            
        signature = request.headers['X-Line-Signature']
        body = request.get_data(as_text=True)

        try:
            self.handler.handle(body, signature)
        except InvalidSignatureError:
            return 'Invalid signature.', 400
        except Exception as e:
            print(f"Webhook handling error: {e}")
            return 'Internal Server Error', 500
        return 'OK'

    def handle_message(self, event):
        if self.rag_chain is None:
            print("錯誤：RAG 鏈尚未在 LineBotManager 實例中初始化。")
            return

        thread = threading.Thread(target=self._process_in_background, args=(event, current_app._get_current_object()))
        thread.start()

    def _process_in_background(self, event, app):
        """在背景執行緒中處理所有耗時的 RAG 處理和訊息推送。"""
        # 使用傳入的 app 物件來建立應用程式上下文
        with app.app_context():
            user_id = event.source.user_id
            user_message = event.message.text
            
            print(f"背景執行緒：為 {user_id} 處理訊息: {user_message}")

            response_content = ""
            try:
                for chunk in self.rag_chain.stream(
                    {"input": user_message},
                    config={"configurable": {"session_id": user_id}}
                ):
                    if "answer" in chunk:
                        response_content += chunk['answer']
            except Exception as e:
                print(f"RAG 鏈處理時發生錯誤: {e}")
                response_content = "抱歉，處理您的請求時發生了內部錯誤。"

            print(f"背景執行緒：準備推送訊息給 {user_id}: {response_content}")

            with ApiClient(self.configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=response_content)]
                    )
                )