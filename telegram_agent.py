import os
import re
import json
import httpx
from pathlib import Path
import google.generativeai as genai
from media_generator import generate_image_gpt, generate_video_veo

current_dir = Path(__file__).resolve().parent
if (current_dir / "menu_and_products.json").exists():
    DATA_PATH = current_dir / "menu_and_products.json"
else:
    DATA_PATH = current_dir.parent / "data" / "menu_and_products.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    HONU_DATA = json.load(f)

ADMIN_TELEGRAM_ID = os.getenv("TELEGRAM_ADMIN_ID", "1454811705").strip()
PAGE_ID = "803810416157920"

async def process_telegram_command(sender_id: str, command_text: str, bot_token: str):
    """Xử lý mệnh lệnh của Sếp qua Telegram: Tự tạo ảnh GPT, tạo video Veo, đăng bài Facebook"""
    clean_sender = str(sender_id).strip()
    print(f"[PROCESS COMMAND] from={clean_sender}, cmd='{command_text}'")

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    page_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")

    # Phân tích ý định của Sếp:
    cmd_lower = command_text.strip().lower()

    # TRƯỜNG HỢP 0: LỆNH /start, /help, test, chào hỏi
    if cmd_lower in ["/start", "start", "/help", "help", "alo", "hi", "hello", "chào", "test"]:
        welcome_text = (
            "🫡 <b>DẠ SẾP! EM ĐÃ SẴN SÀNG PHỤC VỤ HONU PIE 24/7!</b>\n\n"
            "Em là Trợ lý AI kiêm Giám đốc Marketing của Sếp. Em có thể tự động làm mọi việc theo lệnh của Sếp:\n\n"
            "🎨 <b>1. Tạo ảnh sản phẩm AI:</b>\n"
            "👉 Nhắn: <i>Tạo ảnh Hạt dưa rang bơ chuẩn studio ánh sáng ấm</i>\n\n"
            "🎬 <b>2. Tạo video / Reels bằng AI (Google Veo):</b>\n"
            "👉 Nhắn: <i>Tạo video reels bim bim Oishi chuyển động chậm</i>\n\n"
            "📢 <b>3. Tự viết bài và tự đăng lên Fanpage:</b>\n"
            "👉 Nhắn: <i>Đăng bài combo khô gà cay lên Fanpage</i> (Em sẽ tự viết bài, tự sinh ảnh và tự đăng)\n\n"
            "Sếp cứ nhắn mệnh lệnh bất kỳ cho em nhé!"
        )
        await send_telegram_message(bot_token, clean_sender, welcome_text)
        return

    # TRƯỜNG HỢP 1: SẾP YÊU CẦU TẠO ẢNH QUA CỔNG GPT (DALL-E 3)
    if "tạo ảnh" in cmd_lower or "vẽ ảnh" in cmd_lower or "chụp ảnh" in cmd_lower:
        await send_telegram_message(bot_token, sender_id, "🎨 <i>Dạ Sếp! Em đang kết nối cổng GPT (DALL-E 3) để tạo ảnh sản phẩm theo yêu cầu, Sếp đợi em tầm 10-15 giây nhé...</i>")
        
        img_result = await generate_image_gpt(command_text)
        if img_result.get("success"):
            img_url = img_result["url"]
            provider = img_result.get("provider", "GPT DALL-E 3")
            caption = (
                f"✨ <b>ẢNH SẢN PHẨM TẠO TỰ ĐỘNG QUA {provider} ĐÂY Ạ SẾP!</b>\n\n"
                f"📌 <b>Yêu cầu:</b> {command_text}\n\n"
                f"👉 <i>Sếp xem có ưng ý không, nếu muốn đăng lên Fanpage kèm bài viết thì chỉ cần nhắn: 'Đăng ảnh này lên Page nhé' là em đăng liền!</i>"
            )
            await send_telegram_photo(bot_token, sender_id, img_url, caption)
            return
        else:
            await send_telegram_message(bot_token, sender_id, f"⚠️ Lỗi tạo ảnh: {img_result.get('error')}")
            return

    # TRƯỜNG HỢP 2: SẾP YÊU CẦU TẠO VIDEO / REELS QUA CỔNG GOOGLE VEO
    if "tạo video" in cmd_lower or "tạo clip" in cmd_lower or "reels" in cmd_lower:
        await send_telegram_message(bot_token, sender_id, "🎬 <i>Dạ Sếp! Em đang kết nối cổng Google Veo để khởi tạo kịch bản video chuyển động ẩm thực 4K...</i>")
        veo_result = await generate_video_veo(command_text)
        report = (
            f"🎥 <b>KỊCH BẢN VIDEO GOOGLE VEO ĐÃ KHỞI TẠO XONG:</b>\n\n"
            f"📝 <b>Prompt điện ảnh:</b> <code>{veo_result['prompt']}</code>\n\n"
            f"💡 <i>{veo_result['note']}</i>"
        )
        await send_telegram_message(bot_token, sender_id, report)
        return

    # TRƯỜNG HỢP 3: SẾP RA LỆNH VIẾT BÀI & ĐĂNG BÀI LÊN FACEBOOK (TỰ TẠO CẢ ẢNH + CAPTION)
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=f"""
Bạn là Trợ lý Vận hành & Marketing cấp cao của tiệm đồ ăn vặt "Honu Pie - Ăn Vặt Chuẩn Vibe" tại Hải Phòng.
Sếp vừa ra lệnh: "{command_text}".
DỮ LIỆU MÓN ĂN:
{json.dumps(HONU_DATA['products'], ensure_ascii=False, indent=2)}

Nếu Sếp bảo đăng bài / viết bài:
- Tự viết bài chuẩn viral, hài hước, kích thích vị giác, báo giá giảm 2k trên Page so với Shopee, kèm link https://shopee.vn/honupie.
- Chèn mã [POST_FB] ở đầu.
- Chèn mã [IMAGE_PROMPT: mô tả ngắn món ăn bằng tiếng Anh] để hệ thống tự động gọi GPT tạo ảnh kèm theo bài viết!
"""
        )

        response = model.generate_content(command_text)
        reply_content = response.text.strip()
    except Exception as e:
        reply_content = f"Dạ Sếp! Em đã nhận lệnh '{command_text}', nhưng cổng AI đang báo lỗi: {e}. Sếp kiểm tra lại biến GEMINI_API_KEY trên Render nhé ạ!"

    if "[POST_FB]" in reply_content:
        clean_post = reply_content.replace("[POST_FB]", "").strip()
        
        # Kiểm tra xem có yêu cầu tạo ảnh tự động không
        img_match = re.search(r"\[IMAGE_PROMPT:\s*([^\]]+)\]", clean_post)
        image_url = None
        if img_match:
            img_prompt = img_match.group(1).strip()
            clean_post = re.sub(r"\[IMAGE_PROMPT:[^\]]+\]", "", clean_post).strip()
            img_gen = await generate_image_gpt(img_prompt)
            if img_gen.get("success"):
                image_url = img_gen["url"]

        # Gọi API đăng bài kèm ảnh lên Fanpage
        fb_result = await publish_to_facebook_page(clean_post, page_token, image_url)
        
        if fb_result.get("success"):
            post_id = fb_result.get("post_id")
            report = (
                f"🫡 <b>DẠ SẾP! EM ĐÃ TỰ ĐỘNG TẠO NỘI DUNG VÀ ĐĂNG THÀNH CÔNG LÊN FANPAGE!</b>\n\n"
                f"📝 <b>Bài viết:</b>\n{clean_post}\n\n"
                f"🔗 <b>ID Bài viết:</b> <code>{post_id}</code>\n"
                f"👉 <i>Đã đăng kèm ảnh sản phẩm chuẩn studio rồi ạ!</i>"
            )
            if image_url:
                await send_telegram_photo(bot_token, sender_id, image_url, report)
            else:
                await send_telegram_message(bot_token, sender_id, report)
            return
        else:
            await send_telegram_message(bot_token, sender_id, f"⚠️ Đăng bài lên Facebook lỗi: {fb_result.get('error')}\n\nBài viết chuẩn bị: {clean_post}")
            return

    # Mệnh lệnh thông thường
    await send_telegram_message(bot_token, sender_id, reply_content)

async def publish_to_facebook_page(content: str, page_token: str, image_url: str = None) -> dict:
    """Đăng bài viết (kèm ảnh nếu có) lên Fanpage Honu Pie qua Graph API"""
    if not page_token:
        return {"success": False, "error": "Chưa có FB_PAGE_ACCESS_TOKEN"}
    
    async with httpx.AsyncClient() as client:
        try:
            if image_url:
                # Đăng bài dạng Photo kèm Caption
                url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
                params = {"access_token": page_token}
                payload = {"url": image_url, "message": content}
            else:
                # Đăng bài viết thường dạng Status
                url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
                params = {"access_token": page_token}
                payload = {"message": content}

            res = await client.post(url, params=params, json=payload, timeout=20.0)
            data = res.json()
            if res.status_code == 200 and ("id" in data or "post_id" in data):
                return {"success": True, "post_id": data.get("id") or data.get("post_id")}
            return {"success": False, "error": data.get("error", {}).get("message", res.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

async def send_telegram_message(bot_token: str, chat_id: str, text: str):
    if not text:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, timeout=10.0)
            print(f"[SEND MSG RESULT] status={res.status_code}, body={res.text}")
        except Exception as e:
            print(f"[ERROR Gui Telegram that bai] {e}")

async def send_telegram_photo(bot_token: str, chat_id: str, photo_url: str, caption: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    async with httpx.AsyncClient() as client:
        # Tải ảnh về rồi gửi dạng file trực tiếp lên Telegram (chắc chắn 100% thành công)
        try:
            img_res = await client.get(photo_url, timeout=25.0)
            if img_res.status_code == 200:
                files = {"photo": ("honupie_dish.jpg", img_res.content, "image/jpeg")}
                data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}
                res = await client.post(url, data=data, files=files, timeout=20.0)
                print(f"[SEND PHOTO RESULT] status={res.status_code}, body={res.text}")
                return
        except Exception as e:
            print(f"[ERROR Tai anh fallback] {e}")

        # Phương án 2: Gửi link ảnh trực tiếp
        try:
            payload = {"chat_id": str(chat_id), "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
            res = await client.post(url, json=payload, timeout=15.0)
            print(f"[SEND PHOTO URL RESULT] status={res.status_code}, body={res.text}")
        except Exception as e:
            print(f"[ERROR Gui anh URL] {e}")
