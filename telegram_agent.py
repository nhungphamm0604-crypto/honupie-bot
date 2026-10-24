import os
import re
import json
import httpx
from pathlib import Path
import google.generativeai as genai

# Load dữ liệu sản phẩm của Honu Pie
current_dir = Path(__file__).resolve().parent
if (current_dir / "menu_and_products.json").exists():
    DATA_PATH = current_dir / "menu_and_products.json"
else:
    DATA_PATH = current_dir.parent / "data" / "menu_and_products.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    HONU_DATA = json.load(f)

ADMIN_TELEGRAM_ID = "1454811705"
PAGE_ID = "803810416157920"

async def process_telegram_command(sender_id: str, command_text: str, bot_token: str) -> str:
    """Xử lý mọi chỉ đạo của Sếp từ Telegram và tự động thực thi"""
    if str(sender_id) != ADMIN_TELEGRAM_ID:
        return "Xin lỗi, tôi là trợ lý riêng của Sếp Honu Pie và chỉ nhận lệnh từ Sếp!"

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    page_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")

    # 1. Dùng Gemini để hiểu yêu cầu của Sếp và tự sáng tạo bài viết
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=f"""
Bạn là Trợ lý Marketing & Vận hành cấp cao của thương hiệu đồ ăn vặt "Honu Pie - Ăn Vặt Chuẩn Vibe" tại Hải Phòng.
Sếp của bạn (Telegram ID: {ADMIN_TELEGRAM_ID}) vừa giao việc qua Telegram: "{command_text}".

DỮ LIỆU SẢN PHẨM:
{json.dumps(HONU_DATA['products'], ensure_ascii=False, indent=2)}

NHIỆM VỤ CỦA BẠN:
1. Nếu Sếp bảo "viết bài", "đăng bài", "post bài", "tạo bài":
   - Tự động viết 1 bài viết hoàn chỉnh đăng Facebook Fanpage:
     * Hook giật gân, cuốn hút, thèm ăn.
     * Thân bài: Chi tiết món ăn, vị giòn rụm, chính sách giảm 2k trên Page so với Shopee.
     * Kèm link Shopee: https://shopee.vn/honupie và chính sách hỏa tốc Hải Phòng.
     * Danh sách 5-8 hashtag chuẩn (#honupie #anvatchuanvibe #anvathaiphong...).
   - Ở đầu bài viết, hãy ghi mã: [ACTION_POST_FB] để hệ thống tự động đăng thẳng lên Facebook!
2. Nếu Sếp hỏi thông tin hoặc giao việc khác:
   - Trả lời ngắn gọn, lễ phép, dạ vâng báo cáo Sếp rõ ràng!
"""
    )

    response = model.generate_content(command_text)
    reply_content = response.text.strip()

    # 2. Nếu có lệnh đăng bài lên Facebook Fanpage
    if "[ACTION_POST_FB]" in reply_content:
        clean_post = reply_content.replace("[ACTION_POST_FB]", "").strip()
        
        # Đăng bài lên Facebook Fanpage qua Graph API
        fb_result = await publish_to_facebook_page(clean_post, page_token)
        
        if fb_result.get("success"):
            post_id = fb_result.get("post_id")
            return (
                f"🫡 <b>DẠ SẾP! EM ĐÃ VIẾT VÀ TỰ ĐỘNG ĐĂNG BÀI LÊN FANPAGE XONG RỒI Ạ!</b>\n\n"
                f"📝 <b>Nội dung đã đăng:</b>\n\n{clean_post}\n\n"
                f"🔗 <b>Mã bài viết:</b> <code>{post_id}</code>\n"
                f"👉 <i>Sếp có thể vào Fanpage Honu Pie kiểm tra ngay nhé!</i>"
            )
        else:
            return (
                f"⚠️ <b>Dạ Sếp, em đã viết xong bài nhưng đăng lên Facebook bị vướng lỗi:</b>\n"
                f"<code>{fb_result.get('error')}</code>\n\n"
                f"📝 <b>Bài viết em đã chuẩn bị sẵn đây ạ:</b>\n\n{clean_post}"
            )
    
    return reply_content

async def publish_to_facebook_page(content: str, page_token: str) -> dict:
    """Gọi Meta Graph API để tự động đăng bài lên Fanpage Honu Pie"""
    if not page_token:
        return {"success": False, "error": "Chưa có FB_PAGE_ACCESS_TOKEN"}
    
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    params = {"access_token": page_token}
    payload = {"message": content}

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, params=params, json=payload, timeout=15.0)
            data = res.json()
            if res.status_code == 200 and "id" in data:
                return {"success": True, "post_id": data["id"]}
            return {"success": False, "error": data.get("error", {}).get("message", res.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

async def send_telegram_message(bot_token: str, chat_id: str, text: str):
    """Gửi tin nhắn phản hồi báo cáo lại cho Sếp trên Telegram"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=10.0)
        except Exception as e:
            print(f"[ERROR] Gui Telegram that bai: {e}")
