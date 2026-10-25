import os
import re
import httpx
from fastapi import FastAPI, Request, Response, Query, status
from dotenv import load_dotenv
from ai_agent import generate_ai_reply
from telegram_agent import process_telegram_command, send_telegram_message

load_dotenv()

app = FastAPI(title="Honu Pie AI Messenger & Telegram Commander")

PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "honupie_secret_verify_token_2026")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "1454811705")

GRAPH_API_URL = "https://graph.facebook.com/v19.0/me/messages"

@app.get("/")
def home():
    return {"status": "ok", "message": "Honu Pie AI Agent Server is Running 24/7!"}

# ==========================================
# 1. HỆ THỐNG TELEGRAM CHỈ HUY TỪ XA (CHO SẾP)
# ==========================================

recent_logs = []

# Kiểm tra trực tiếp xem Bot có gửi được tin nhắn về Telegram cho Sếp không
@app.get("/test-telegram")
async def test_telegram(msg: str = "🫡 Chào Sếp Hoàng! Đây là tin nhắn kiểm tra trực tiếp từ máy chủ Honu Pie!"):
    admin_id = os.getenv("TELEGRAM_ADMIN_ID", "1454811705").strip()
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "Chưa có TELEGRAM_BOT_TOKEN"}
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": admin_id, "text": msg}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=10.0)
            return {
                "status_code": res.status_code,
                "telegram_api_response": res.json(),
                "target_chat_id": admin_id,
                "note": "Nếu ok=true nghĩa là bot đã gửi tin nhắn vào máy sếp thành công!"
            }
        except Exception as e:
            return {"error": str(e)}

# Xem nhật ký tin nhắn gửi tới máy chủ trong thời gian thực
@app.get("/view-logs")
def view_logs():
    return {"total_logs": len(recent_logs), "logs": recent_logs[-20:]}

# Cài đặt Webhook Telegram tự động 1-Click
@app.get("/setup-telegram")
async def setup_telegram():
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "Chưa có TELEGRAM_BOT_TOKEN trong Environment Variables của Render!"}
    
    webhook_url = "https://honupie-bot.onrender.com/telegram-webhook"
    tg_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(tg_api, timeout=10.0)
            return {
                "status": "success",
                "telegram_response": res.json(),
                "message": "Đã kết nối Telegram thành công! Sếp có thể bắt đầu nhắn tin ra lệnh cho Bot trên Telegram rồi!"
            }
        except Exception as e:
            return {"error": str(e)}

# Tiếp nhận tin nhắn chỉ đạo của Sếp từ Telegram
@app.post("/telegram-webhook")
async def handle_telegram_webhook(request: Request):
    try:
        data = await request.json()
        message = data.get("message") or data.get("edited_message") or {}
        chat = message.get("chat", {})
        sender_id = str(chat.get("id") or message.get("from", {}).get("id", "")).strip()
        command_text = message.get("text", "").strip()

        recent_logs.append({
            "sender_id": sender_id,
            "text": command_text,
            "from_user": message.get("from", {}).get("username", "")
        })

        if sender_id and command_text:
            await process_telegram_command(sender_id, command_text, TELEGRAM_BOT_TOKEN)
        elif sender_id and not command_text:
            await send_telegram_message(TELEGRAM_BOT_TOKEN, sender_id, "Dạ Sếp, em đã nhận được tín hiệu nhưng chưa thấy nội dung. Sếp gửi mệnh lệnh cho em nhé!")
    except Exception as e:
        recent_logs.append({"error": str(e)})
        print(f"[ERROR Telegram Webhook] {e}")

    return {"status": "ok"}

# ==========================================
# 2. HỆ THỐNG MESSENGER CHĂM SÓC KHÁCH HÀNG
# ==========================================

@app.get("/subscribe")
async def subscribe_page():
    if not PAGE_ACCESS_TOKEN:
        return {"error": "Chưa có FB_PAGE_ACCESS_TOKEN"}
    
    url = "https://graph.facebook.com/v19.0/me/subscribed_apps"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {"subscribed_fields": ["messages", "messaging_postbacks"]}
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, params=params, json=payload, timeout=10.0)
            return {
                "status_code": res.status_code,
                "facebook_response": res.json()
            }
        except Exception as e:
            return {"error": str(e)}

@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain", status_code=status.HTTP_200_OK)
    return Response(content="Verification token mismatch", status_code=status.HTTP_403_FORBIDDEN)

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                message = messaging_event.get("message", {})
                
                if not sender_id or message.get("is_echo") or not message.get("text"):
                    continue
                
                user_text = message.get("text").strip()
                await send_sender_action(sender_id, "typing_on")
                
                raw_ai_reply = generate_ai_reply(sender_id, user_text)
                
                image_url = None
                img_match = re.search(r"\[IMAGE:(https?://[^\]]+)\]", raw_ai_reply)
                if img_match:
                    image_url = img_match.group(1).strip()
                
                clean_reply = re.sub(r"\[IMAGE:[^\]]+\]", "", raw_ai_reply).strip()
                
                await send_facebook_message(sender_id, clean_reply)
                if image_url:
                    await send_facebook_image(sender_id, image_url)
                
                await send_sender_action(sender_id, "typing_off")
                
        return Response(content="EVENT_RECEIVED", status_code=status.HTTP_200_OK)
    return Response(content="Not Found", status_code=status.HTTP_404_NOT_FOUND)

async def send_facebook_message(recipient_id: str, text: str):
    if not PAGE_ACCESS_TOKEN or not text:
        return
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(GRAPH_API_URL, params=params, json=payload, timeout=10.0)
        except Exception:
            pass

async def send_facebook_image(recipient_id: str, image_url: str):
    if not PAGE_ACCESS_TOKEN or not image_url:
        return
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"attachment": {"type": "image", "payload": {"url": image_url, "is_reusable": True}}}
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(GRAPH_API_URL, params=params, json=payload, timeout=10.0)
        except Exception:
            pass

async def send_sender_action(recipient_id: str, action: str):
    if not PAGE_ACCESS_TOKEN:
        return
    payload = {"recipient": {"id": recipient_id}, "sender_action": action}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(GRAPH_API_URL, params=params, json=payload, timeout=5.0)
        except Exception:
            pass
