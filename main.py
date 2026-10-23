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

# Endpoint kích hoạt đăng ký Fanpage với Webhook 1-Click
@app.get("/subscribe")
async def subscribe_page():
    if not PAGE_ACCESS_TOKEN:
        return {"error": "Chưa có FB_PAGE_ACCESS_TOKEN"}
    
    url = "https://graph.facebook.com/v19.0/me/subscribed_apps"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "subscribed_fields": ["messages", "messaging_postbacks"]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, params=params, json=payload, timeout=10.0)
            return {
                "status_code": res.status_code,
                "facebook_response": res.json(),
                "message": "Nếu success = true nghĩa là Fanpage đã kết nối nhận tin nhắn 100%!"
            }
        except Exception as e:
            return {"error": str(e)}

# 1. Xác thực Webhook với Facebook
@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain", status_code=status.HTTP_200_OK)
    return Response(content="Verification token mismatch", status_code=status.HTTP_403_FORBIDDEN)

# 2. Xử lý tin nhắn khách gửi vào
@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    print(f"[LOG] Nhan event tu Facebook: {data}")
    
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                message = messaging_event.get("message", {})
                
                if not sender_id or message.get("is_echo") or not message.get("text"):
                    continue
                
                user_text = message.get("text").strip()
                print(f"[LOG] Khach {sender_id} nhan: {user_text}")
                
                # Bật trạng thái "Đang gõ..."
                await send_sender_action(sender_id, "typing_on")
                
                # AI suy nghĩ câu trả lời
                raw_ai_reply = generate_ai_reply(sender_id, user_text)
                
                # Tách link ảnh nếu có tag [IMAGE:url]
                image_url = None
                img_match = re.search(r"\[IMAGE:(https?://[^\]]+)\]", raw_ai_reply)
                if img_match:
                    image_url = img_match.group(1).strip()
                
                clean_reply = re.sub(r"\[IMAGE:[^\]]+\]", "", raw_ai_reply)
                
                # Kiểm tra thông báo đơn hàng
                if "[ORDER_DETECTED]" in clean_reply or re.search(r"(\+84|0)\d{9,10}", user_text):
                    clean_reply = clean_reply.replace("[ORDER_DETECTED]", "").strip()
                    await notify_owner_new_order(sender_id, user_text, clean_reply)
                else:
                    clean_reply = clean_reply.strip()
                
                # 1. Gửi tin nhắn văn bản
                print(f"[LOG] Bot tra loi: {clean_reply}")
                await send_facebook_message(sender_id, clean_reply)
                
                # 2. Tự động gửi ảnh nếu có
                if image_url:
                    await send_facebook_image(sender_id, image_url)
                
                await send_sender_action(sender_id, "typing_off")
                
        return Response(content="EVENT_RECEIVED", status_code=status.HTTP_200_OK)
    
    return Response(content="Not Found", status_code=status.HTTP_404_NOT_FOUND)

async def send_facebook_message(recipient_id: str, text: str):
    if not PAGE_ACCESS_TOKEN or not text:
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
                print(f"[ERROR] Gui tin nhan that bai: {res.text}")
            else:
                print(f"[SUCCESS] Da gui tin nhan thanh cong toi {recipient_id}")
        except Exception as e:
            print(f"[ERROR] Exception sending FB message: {e}")

async def send_facebook_image(recipient_id: str, image_url: str):
    if not PAGE_ACCESS_TOKEN or not image_url:
        return
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True}
            }
        }
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(GRAPH_API_URL, params=params, json=payload, timeout=10.0)
        except Exception as e:
            print(f"[ERROR] Gui anh that bai: {e}")

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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    alert_text = (
        f"🚨 <b>HONU PIE CÓ ĐƠN / KHÁCH MỚI!</b>\n\n"
        f"👤 <b>Khách nhắn:</b> {customer_msg}\n"
        f"🤖 <b>AI đã tư vấn:</b> {bot_summary}\n"
    )
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": alert_text, "parse_mode": "HTML"}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(tg_url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"[ERROR] Bao Telegram loi: {e}")
