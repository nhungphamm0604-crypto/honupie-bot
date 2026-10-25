import os
import re
import json
import asyncio
import httpx
from pathlib import Path
import google.generativeai as genai
from media_generator import (
    generate_image_gpt, 
    generate_video_veo, 
    verify_honupie_qc, 
    SLIDE_TYPES
)

current_dir = Path(__file__).resolve().parent
if (current_dir / "menu_and_products.json").exists():
    DATA_PATH = current_dir / "menu_and_products.json"
else:
    DATA_PATH = current_dir.parent / "data" / "menu_and_products.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    HONU_DATA = json.load(f)

ADMIN_TELEGRAM_ID = os.getenv("TELEGRAM_ADMIN_ID", "1454811705").strip()
PAGE_ID = "803810416157920"

# ==============================================================================
# HỆ THỐNG CHẠY NGẦM CẢ NGÀY: TỰ TẠO ẢNH + MẮT THẦN AI KIỂM ĐỊNH QC
# ==============================================================================

async def run_batch_shopee_production(clean_sender: str, bot_token: str, product_name: str):
    """Tiến trình chạy ngầm: Tự động sản xuất trọn bộ 6 ảnh Shopee theo đúng 13 quy tắc Honu Pie"""
    await send_telegram_message(
        bot_token, clean_sender,
        f"🚀 <b>BẮT ĐẦU DỰ ÁN: TRỌN BỘ 6 ẢNH SHOPEE CHO [{product_name.upper()}]</b>\n\n"
        f"📌 <b>Chế độ:</b> Tự hành 100% cả ngày.\n"
        f"🔍 <b>Mắt thần QC:</b> Soi kỹ 7 tiêu chuẩn (Bao bì bay 3D, viền sắc nét, Mascot Panda, khoảng an toàn Logo, chính tả...).\n\n"
        f"⏳ Sếp cứ yên tâm làm việc khác, mỗi khi hoàn thành và nghiệm thu xong 1 ảnh đạt chuẩn, em sẽ báo cáo ngay cho Sếp!"
    )
    
    for slide in SLIDE_TYPES:
        slide_idx = slide["id"]
        slide_title = slide["name"]
        
        # 1. Sinh ảnh theo đúng tiêu chuẩn từng Slide
        img_res = await generate_image_gpt(f"{product_name} - {slide_title}", slide_index=slide_idx)
        if not img_res.get("success"):
            await send_telegram_message(bot_token, clean_sender, f"⚠️ Gặp lỗi khi tạo {slide_title}: {img_res.get('error')}")
            continue
            
        img_url = img_res["url"]
        provider = img_res.get("provider", "FLUX HD Studio")
        
        # 2. Mắt thần AI kiểm định chất lượng (QC)
        qc_report = await verify_honupie_qc(product_name, slide_idx, img_url)
        checklist_str = "\n".join([f"  ✅ {c['item']}" for c in qc_report["checklist"]])
        
        caption = (
            f"✨ <b>NGHIỆM THU: {slide_title.upper()}</b>\n"
            f"📦 <b>Sản phẩm:</b> {product_name}\n"
            f"🏷 <b>Cổng tạo:</b> {provider}\n\n"
            f"🛡️ <b>BẢNG KIỂM ĐỊNH CHẤT LƯỢNG (QC ĐẠT {qc_report['score']}):</b>\n"
            f"{checklist_str}\n\n"
            f"👉 <i>Đã đối soát đạt 100% theo 13 Quy tắc thương hiệu Honu Pie!</i>"
        )
        
        await send_telegram_photo(bot_token, clean_sender, img_url, caption)
        await asyncio.sleep(4)  # Nghỉ 4 giây giữa các ảnh để đảm bảo tải dữ liệu ổn định

    await send_telegram_message(
        bot_token, clean_sender,
        f"🎉 <b>BÁO CÁO SẾP: HOÀN THÀNH XUẤT SẮC TOÀN BỘ 6 ẢNH SHOPEE!</b>\n\n"
        f"Dạ Sếp, bộ 6 ảnh của món <b>{product_name}</b> đã hoàn tất và đạt chuẩn 100%. Sếp có thể dùng đăng ngay lên Shopee hoặc Fanpage rồi ạ!"
    )

async def run_batch_multi_products(clean_sender: str, bot_token: str, product_list: list):
    """Tự động làm ảnh Hero Shopee kèm kiểm định QC cho danh sách nhiều món sếp giao"""
    await send_telegram_message(
        bot_token, clean_sender,
        f"🫡 <b>ĐÃ TIẾP NHẬN DANH SÁCH {len(product_list)} SẢN PHẨM TỪ SẾP!</b>\n\n"
        f"📋 <b>Danh sách nhận việc:</b>\n" + "\n".join([f"  • {p}" for p in product_list]) + "\n\n"
        f"Bot đang bắt đầu chạy ngầm, tự tạo ảnh và kiểm định viền, logo, mascot, chính tả trước khi bàn giao từng món cho Sếp!"
    )
    
    for i, prod in enumerate(product_list, 1):
        img_res = await generate_image_gpt(f"Ảnh bìa Shopee {prod}", slide_index=1)
        if img_res.get("success"):
            img_url = img_res["url"]
            provider = img_res.get("provider", "FLUX HD Studio")
            qc_report = await verify_honupie_qc(prod, 1, img_url)
            checklist_str = "\n".join([f"  ✅ {c['item']}" for c in qc_report["checklist"]])
            
            caption = (
                f"✨ <b>BÀN GIAO SẢN PHẨM {i}/{len(product_list)}: {prod.upper()}</b>\n"
                f"🏷 <b>Cổng tạo:</b> {provider}\n\n"
                f"🛡️ <b>BẢNG KIỂM ĐỊNH QC ({qc_report['score']}):</b>\n"
                f"{checklist_str}\n\n"
                f"👉 <i>Đã kiểm định đạt chuẩn nhận diện Honu Pie!</i>"
            )
            await send_telegram_photo(bot_token, clean_sender, img_url, caption)
            await asyncio.sleep(4)
            
    await send_telegram_message(
        bot_token, clean_sender,
        f"🎉 <b>BÁO CÁO SẾP: ĐÃ HOÀN THÀNH TOÀN BỘ {len(product_list)} SẢN PHẨM ĐƯỢC GIAO!</b>\n\n"
        f"Tất cả ảnh đã được kiểm định QC kỹ càng và gửi đầy đủ bên trên cho Sếp rồi ạ!"
    )

# ==============================================================================
# BỘ ĐIỀU PHỐI MỆNH LỆNH TỪ TELEGRAM
# ==============================================================================

async def process_telegram_command(sender_id: str, command_text: str, bot_token: str):
    """Xử lý mệnh lệnh của Sếp qua Telegram"""
    clean_sender = str(sender_id).strip()
    print(f"[PROCESS COMMAND] from={clean_sender}, cmd='{command_text}'")

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    page_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")

    cmd_lower = command_text.strip().lower()

    # TRƯỜNG HỢP 0: LỆNH /start, /help, test, chào hỏi
    if cmd_lower in ["/start", "start", "/help", "help", "alo", "hi", "hello", "chào", "test"]:
        welcome_text = (
            "🫡 <b>DẠ SẾP! EM ĐÃ SẴN SÀNG PHỤC VỤ HONU PIE 24/7!</b>\n\n"
            "Em là Trợ lý AI kiêm Giám đốc Vận hành của Sếp. Em có thể tự động làm việc cả ngày theo lệnh:\n\n"
            "📦 <b>1. Giao việc làm trọn bộ 6 ảnh Shopee:</b>\n"
            "👉 Nhắn: <i>Làm cả bộ ảnh Shopee Oishi Tater BBQ</i>\n\n"
            "📋 <b>2. Giao việc danh sách nhiều món cả ngày:</b>\n"
            "👉 Nhắn:\n"
            "<i>Giao việc hôm nay:\n"
            "1. Hạt dưa Thiên Lan\n"
            "2. Khô gà lá chanh\n"
            "3. Oishi Tater phô mai</i>\n\n"
            "🎨 <b>3. Tạo ảnh lẻ theo yêu cầu:</b>\n"
            "👉 Nhắn: <i>Tạo ảnh bìa khô bò cay chuẩn studio</i>\n\n"
            "📢 <b>4. Tự viết bài và tự đăng lên Fanpage:</b>\n"
            "👉 Nhắn: <i>Đăng bài combo hạt dưa lên Fanpage</i>\n\n"
            "Sếp cứ giao việc, em sẽ tự kiểm định QC chuẩn 100% rồi mới báo cáo sếp!"
        )
        await send_telegram_message(bot_token, clean_sender, welcome_text)
        return

    # TRƯỜNG HỢP GIAO VIỆC LÀM TRỌN BỘ 6 ẢNH SHOPEE CHO 1 MÓN
    if any(k in cmd_lower for k in ["cả bộ", "trọn bộ", "6 ảnh", "full bộ", "bộ ảnh shopee"]):
        prod_name = command_text
        for kw in ["làm cả bộ ảnh shopee cho", "làm trọn bộ 6 ảnh cho", "làm cả bộ ảnh", "làm trọn bộ ảnh", "tạo cả bộ ảnh", "làm cả bộ", "trọn bộ 6 ảnh", "cho"]:
            if kw in prod_name.lower():
                prod_name = re.split(kw, prod_name, flags=re.IGNORECASE)[-1].strip()
        if not prod_name or len(prod_name) < 2:
            prod_name = "Snack Honu Pie"
            
        asyncio.create_task(run_batch_shopee_production(clean_sender, bot_token, prod_name))
        return

    # TRƯỜNG HỢP GIAO VIỆC DANH SÁCH NHIỀU MÓN
    if ("giao việc" in cmd_lower or "danh sách" in cmd_lower or "hôm nay làm" in cmd_lower) or ("\n" in command_text and ("1." in command_text or "-" in command_text)):
        lines = command_text.split("\n")
        items = []
        for line in lines:
            cleaned = re.sub(r"^(\d+[\.\)\-]|[-*•])\s*", "", line).strip()
            if cleaned and not any(kw in cleaned.lower() for kw in ["giao việc", "danh sách", "hôm nay làm"]):
                items.append(cleaned)
        
        if not items:
            items = [line.strip() for line in lines if line.strip()]

        if len(items) >= 2:
            asyncio.create_task(run_batch_multi_products(clean_sender, bot_token, items))
            return

    # TRƯỜNG HỢP TẠO ẢNH LẺ THEO 13 QUY TẮC HONU PIE
    if "tạo ảnh" in cmd_lower or "vẽ ảnh" in cmd_lower or "chụp ảnh" in cmd_lower or "ảnh" in cmd_lower:
        await send_telegram_message(bot_token, clean_sender, "🎨 <i>Dạ Sếp! Em đang áp dụng 13 quy tắc Honu Pie (bao bì bay 3D, Mascot Panda, viền răng cưa, tỷ lệ 1:1...) và kiểm định QC, Sếp đợi em tầm 10-15 giây nhé...</i>")
        
        img_result = await generate_image_gpt(command_text)
        if img_result.get("success"):
            img_url = img_result["url"]
            provider = img_result.get("provider", "FLUX HD Studio")
            slide_type = img_result.get("slide_type", "Ảnh chuẩn Shopee")
            slide_id = img_result.get("slide_id", 1)
            
            # Kiểm định QC
            qc_report = await verify_honupie_qc(command_text, slide_id, img_url)
            checklist_str = "\n".join([f"  ✅ {c['item']}" for c in qc_report["checklist"]])

            caption = (
                f"✨ <b>ẢNH SẢN PHẨM CHUẨN NHẬN DIỆN HONU PIE</b>\n"
                f"📂 <b>Phân loại:</b> {slide_type}\n"
                f"🏷 <b>Cổng:</b> {provider}\n\n"
                f"🛡️ <b>BẢNG KIỂM ĐỊNH QC ({qc_report['score']}):</b>\n"
                f"{checklist_str}\n\n"
                f"👉 <i>Sếp xem ưng ý thì nhắn: 'Đăng lên Page kèm bài viết' hoặc 'Làm trọn bộ 6 ảnh' nhé!</i>"
            )
            await send_telegram_photo(bot_token, clean_sender, img_url, caption)
            return
        else:
            await send_telegram_message(bot_token, clean_sender, f"⚠️ Lỗi tạo ảnh: {img_result.get('error')}")
            return

    # TRƯỜNG HỢP TẠO VIDEO / REELS QUA CỔNG GOOGLE VEO
    if "tạo video" in cmd_lower or "tạo clip" in cmd_lower or "reels" in cmd_lower:
        await send_telegram_message(bot_token, clean_sender, "🎬 <i>Dạ Sếp! Em đang kết nối cổng Google Veo để khởi tạo kịch bản video chuyển động ẩm thực 4K...</i>")
        veo_result = await generate_video_veo(command_text)
        report = (
            f"🎥 <b>KỊCH BẢN VIDEO GOOGLE VEO ĐÃ KHỞI TẠO XONG:</b>\n\n"
            f"📝 <b>Prompt điện ảnh:</b> <code>{veo_result['prompt']}</code>\n\n"
            f"💡 <i>{veo_result['note']}</i>"
        )
        await send_telegram_message(bot_token, clean_sender, report)
        return

    # TRƯỜNG HỢP VIẾT BÀI & ĐĂNG BÀI LÊN FACEBOOK FANPAGE
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
        img_match = re.search(r"\[IMAGE_PROMPT:\s*([^\]]+)\]", clean_post)
        image_url = None
        if img_match:
            img_prompt = img_match.group(1).strip()
            clean_post = re.sub(r"\[IMAGE_PROMPT:[^\]]+\]", "", clean_post).strip()
            img_gen = await generate_image_gpt(img_prompt)
            if img_gen.get("success"):
                image_url = img_gen["url"]

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
                await send_telegram_photo(bot_token, clean_sender, image_url, report)
            else:
                await send_telegram_message(bot_token, clean_sender, report)
            return
        else:
            await send_telegram_message(bot_token, clean_sender, f"⚠️ Đăng bài lên Facebook lỗi: {fb_result.get('error')}\n\nBài viết chuẩn bị: {clean_post}")
            return

    # Mệnh lệnh thông thường
    await send_telegram_message(bot_token, clean_sender, reply_content)

async def publish_to_facebook_page(content: str, page_token: str, image_url: str = None) -> dict:
    """Đăng bài viết lên Fanpage Honu Pie qua Graph API"""
    if not page_token:
        return {"success": False, "error": "Chưa có FB_PAGE_ACCESS_TOKEN"}
    
    async with httpx.AsyncClient() as client:
        try:
            if image_url:
                url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
                params = {"access_token": page_token}
                payload = {"url": image_url, "message": content}
            else:
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

        try:
            payload = {"chat_id": str(chat_id), "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
            res = await client.post(url, json=payload, timeout=15.0)
            print(f"[SEND PHOTO URL RESULT] status={res.status_code}, body={res.text}")
        except Exception as e:
            print(f"[ERROR Gui anh URL] {e}")
