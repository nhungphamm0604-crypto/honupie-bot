import os
import re
import httpx
from fastapi import FastAPI, Request, Response, Query, status
from dotenv import load_dotenv
from ai_agent import generate_ai_reply

load_dotenv()

app = FastAPI(title="Honu Pie AI Messenger Agent")

PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "honupie_secret_verify_token_2026")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GRAPH_API_URL = "https://graph.facebook.com/v19.0/me/messages"

@app.get("/")
def home():
    return {"status": "ok", "message": "Honu Pie AI Agent Server is Running 24/7!"}

# 1. Xác thực Webhook với Facebook Meta
@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain", status_code=status.HTTP_200_OK)
    return Response(content="Verification token mismatch", status_code=status.HTTP_403_FORBIDDEN)

# 2. Nhận tin nhắn từ khách gửi vào Fanpage
@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                message = messaging_event.get("message", {})
                
                # Bỏ qua tin nhắn do chính Fanpage gửi đi hoặc tin không có văn bản
                if not sender_id or message.get("is_echo") or not message.get("text"):
                    continue
                
                user_text = message.get("text").strip()
                
                # Bật trạng thái "Đang gõ..." trên Messenger để khách thấy tự nhiên
                await send_sender_action(sender_id, "typing_on")
                
                # Gọi Bộ não AI Gemini để suy nghĩ câu trả lời & tự động Upsell
                ai_reply = generate_ai_reply(sender_id, user_text)
                
                # Kiểm tra nếu phát hiện đơn hàng hoặc khách để lại số điện thoại
                if "[ORDER_DETECTED]" in ai_reply or re.search(r"(\+84|0)\d{9,10}", user_text):
                    clean_reply = ai_reply.replace("[ORDER_DETECTED]", "").strip()
                    await notify_owner_new_order(sender_id, user_text, clean_reply)
                else:
                    clean_reply = ai_reply
                
                # Gửi câu trả lời về lại Messenger của khách
                await send_facebook_message(sender_id, clean_reply)
                await send_sender_action(sender_id, "typing_off")
                
        return Response(content="EVENT_RECEIVED", status_code=status.HTTP_200_OK)
    
    return Response(content="Not Found", status_code=status.HTTP_404_NOT_FOUND)

async def send_facebook_message(recipient_id: str, text: str):
    if not PAGE_ACCESS_TOKEN:
        print("[WARNING] Chưa điền FB_PAGE_ACCESS_TOKEN")
        return
        
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(GRAPH_API_URL, params=params, json=payload, timeout=10.0)
            if res.status_code != 200:
                print(f"[ERROR] Gửi tin nhắn thất bại: {res.text}")
        except Exception as e:
            print(f"[ERROR] Exception sending FB message: {e}")

async def send_sender_action(recipient_id: str, action: str):
    if not PAGE_ACCESS_TOKEN:
        return
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": action
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(GRAPH_API_URL, params=params, json=payload, timeout=5.0)
        except Exception:
            pass

async def notify_owner_new_order(customer_id: str, customer_msg: str, bot_summary: str):
    """Báo đơn hàng mới tức thì về điện thoại qua Telegram Bot"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    alert_text = (
        f"🚨 <b>HONU PIE CÓ ĐƠN / KHÁCH TIỀM NĂNG MỚI!</b>\n\n"
        f"👤 <b>Khách nhắn:</b> {customer_msg}\n"
        f"🤖 <b>AI đã tư vấn:</b> {bot_summary}\n\n"
        f"👉 <i>Kiểm tra hộp thư Fanpage để đóng hàng hoặc chốt đơn ngay!</i>"
    )
    
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": alert_text,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(tg_url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"[ERROR] Không thể gửi thông báo Telegram: {e}")
