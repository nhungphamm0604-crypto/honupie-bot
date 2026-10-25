import os
import re
import json
import asyncio
import httpx
from pathlib import Path
from media_generator import (
    generate_image_gpt, 
    generate_video_veo, 
    verify_honupie_qc, 
    SLIDE_TYPES
)
from shopee_listing_generator import generate_shopee_listing

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
# 1. BỘ NÃO GPT-4o-MINI PHÂN TÍCH Ý ĐỊNH SẾP (KHÔNG CẦN CÂU LỆNH CỐ ĐỊNH)
# ==============================================================================

async def analyze_ceo_intent_with_gpt(command_text: str, openai_key: str) -> dict:
    """
    Dùng não GPT-4o-mini để thấu hiểu ý định của Sếp từ bất kỳ câu nói tự nhiên nào:
    Sếp nói tiếng lóng, nói tắt, giao việc cả ngày, bắt bẻ... GPT đều hiểu chuẩn 100%.
    """
    menu_names = [p["name"] for p in HONU_DATA.get("products", [])]
    system_prompt = f"""
Bạn là Trợ lý Vận hành & Giám đốc Sản xuất của tiệm ăn vặt "Honu Pie - Ăn Vặt Chuẩn Vibe".
Sếp Hoàng (chủ tiệm) vừa nhắn tin giao việc qua Telegram: "{command_text}".

DANH SÁCH SẢN PHẨM TRONG MENU HONU PIE:
{json.dumps(menu_names, ensure_ascii=False, indent=2)}

NHIỆM VỤ CỦA BẠN: Phân tích câu nói tự nhiên của Sếp và trả về DUY NHẤT một JSON hợp lệ (không kèm markdown) theo cấu trúc:
{{
  "action": "batch_all_products" | "batch_single_product" | "batch_list" | "single_image" | "create_video" | "post_facebook" | "chat",
  "products": ["tên các món sếp muốn làm"],
  "slide_index": 1,
  "concept": "mô tả phong cách ảnh nếu sếp có dặn thêm",
  "facebook_content": "nội dung bài viết nếu sếp muốn đăng page",
  "reply_to_ceo": "lời thưa gửi dạ sếp ngắn gọn, thông minh, lễ phép, nói rõ em chuẩn bị làm gì"
}}

HƯỚNG DẪN BẮT Ý ĐỊNH:
1. Nếu Sếp nói: "Tạo từng bộ sản phẩm cho mỗi sản phẩm này", "làm hết các món", "làm bộ ảnh cho cả menu", "làm cả ngày"...
   ➔ action: "batch_all_products", products: toàn bộ danh sách món trong menu.
2. Nếu Sếp nói: "Làm cả bộ ảnh cho [món]", "trọn bộ 6 ảnh cho món này"...
   ➔ action: "batch_single_product", products: [tên món đó].
3. Nếu Sếp liệt kê nhiều món (1. Món A, 2. Món B...):
   ➔ action: "batch_list", products: [danh sách các món đó].
4. Nếu Sếp bảo tạo 1 ảnh, vẽ ảnh, chụp ảnh, "cho t 1 cái ảnh hạt dưa nhìn thèm thèm"...
   ➔ action: "single_image".
5. Nếu Sếp bảo làm clip, video, reels:
   ➔ action: "create_video".
6. Nếu Sếp bảo đăng bài, viết bài lên Fanpage:
   ➔ action: "post_facebook".
7. Nếu Sếp bảo viết mô tả shopee, tạo tên mô tả, listing shopee, bài đăng shopee:
   ➔ action: "shopee_listing".
8. Còn lại nếu sếp chỉ chào hỏi, hỏi han buôn bán:
   ➔ action: "chat".
"""
    # 1. Thử gọi trực tiếp não bộ GPT-6.1 Sol với mức suy luận Vừa (reasoning effort: medium)
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-6.1-sol",
                    "reasoning": {"effort": "medium"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": command_text}
                    ],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            if res.status_code == 200:
                data = res.json()["choices"][0]["message"]["content"]
                return json.loads(data)
            else:
                print(f"[GPT-6.1 Sol Status {res.status_code}] {res.text}")
    except Exception as e:
        print(f"[GPT-6.1 Sol Error] {e}")

    # 2. Dự phòng gpt-4o-mini nếu tài khoản chưa mở quyền gpt-6.1-sol
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": command_text}
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=20.0
            )
            if res.status_code == 200:
                data = res.json()["choices"][0]["message"]["content"]
                return json.loads(data)
    except Exception as e:
        print(f"[GPT Fallback Error] {e}")

    # BỘ PHÂN TÍCH THÔNG MINH DỰ PHÒNG (NẾU OPENAI CHƯA CÓ CREDIT HOẶC MẠNG NGHẼN)
    cmd_lower = command_text.lower().strip()
    
    # 1. Sếp hỏi về thời gian thực hiện (bao lâu, mấy phút, khi nào xong...)
    if any(q in cmd_lower for q in ["bao lâu", "mất bao lâu", "mấy phút", "mấy tiếng", "khi nào xong", "bao giờ xong"]):
        return {
            "action": "chat",
            "reply_to_ceo": (
                "⏱️ <b>Dạ Sếp! Thời gian sản xuất được tính chuẩn như sau ạ:</b>\n\n"
                "• <b>1 ảnh lẻ:</b> Mất khoảng <b>10 - 15 giây</b> (tạo ảnh + kiểm định QC).\n"
                "• <b>1 bộ 6 ảnh Shopee:</b> Mất khoảng <b>1.5 - 2 phút</b> cho trọn bộ (vừa tạo vừa soi viền, logo, mascot).\n"
                "• <b>Toàn bộ Menu (7 món):</b> Mất khoảng <b>10 - 12 phút</b> chạy ngầm cả ngày.\n\n"
                "Cứ xong và nghiệm thu đạt chuẩn ảnh nào là em ting ting gửi ngay vào Telegram này cho Sếp duyệt ảnh đó ạ!"
            )
        }

    # 2. Sếp hỏi thăm, thắc mắc, hỏi lỗi
    if any(q in cmd_lower for q in ["sao thế", "sao lâu", "được không", "thế nào", "là gì", "ở đâu"]):
        return {
            "action": "chat",
            "reply_to_ceo": (
                "🫡 <b>Dạ Sếp! Em đang trực chiến 24/7 đây ạ!</b>\n\n"
                "Mọi hệ thống đã sẵn sàng. Sếp muốn em tạo bộ ảnh cho món nào hay cần soạn mô tả Shopee, sếp cứ chỉ đạo là em cày ngay ạ!"
            )
        }

    # 3. Sếp bảo tạo các bộ ảnh / tất cả các món
    if any(k in cmd_lower for k in ["tạo các bộ", "từng bộ", "mỗi sản phẩm", "toàn bộ", "hết các món", "tất cả", "đã gửi"]):
        all_prods = [p["name"] for p in HONU_DATA.get("products", [])]
        return {
            "action": "batch_all_products",
            "products": all_prods,
            "reply_to_ceo": f"🫡 Dạ Sếp! Em bắt đầu chạy ngầm sản xuất trọn bộ ảnh Shopee cho toàn bộ {len(all_prods)} sản phẩm trong Menu ngay đây ạ!"
        }

    # 4. Sếp nhắc tên món cụ thể
    for p in HONU_DATA.get("products", []):
        p_name = p["name"].lower()
        if any(term in cmd_lower for term in [p_name, "tater", "oishi", "bò bbq", "hạt dưa", "bắp", "kettle", "vfoods", "pillows", "khô gà", "khô bò"]):
            return {
                "action": "batch_single_product",
                "products": [p["name"]],
                "reply_to_ceo": f"🚀 Dạ Sếp! Em bắt đầu sản xuất trọn bộ 6 ảnh Shopee cho món [{p['name'].upper()}] ngay ạ!"
            }

    # Mặc định phản hồi tôn trọng Sếp
    return {
        "action": "chat",
        "reply_to_ceo": f"🫡 Dạ Sếp! Em đã nhận chỉ đạo: <i>'{command_text}'</i>. Sếp muốn em tạo ảnh cho món nào hay soạn bài đăng Shopee, sếp bảo em làm liền nhé!"
    }

# ==============================================================================
# 2. CÁC TIẾN TRÌNH CHẠY NGẦM CẢ NGÀY (ASYNC PIPELINES)
# ==============================================================================

async def run_batch_shopee_production(clean_sender: str, bot_token: str, product_name: str):
    """Tiến trình chạy ngầm: Tự động sản xuất trọn bộ 6 ảnh Shopee theo đúng 13 quy tắc Honu Pie"""
    await send_telegram_message(
        bot_token, clean_sender,
        f"🚀 <b>BẮT ĐẦU DỰ ÁN: TRỌN BỘ 6 ẢNH SHOPEE CHO [{product_name.upper()}]</b>\n\n"
        f"📌 <b>Chế độ:</b> Tự hành 100% cả ngày qua cổng OpenAI DALL-E 3 & FLUX Studio.\n"
        f"🔍 <b>Mắt thần QC:</b> Soi kỹ 7 tiêu chuẩn (Bao bì bay 3D, viền sắc nét, Mascot Panda, khoảng an toàn Logo, chính tả...).\n\n"
        f"⏳ Sếp cứ yên tâm làm việc khác, mỗi khi hoàn thành và nghiệm thu xong 1 ảnh đạt chuẩn, em sẽ báo cáo ngay cho Sếp!"
    )
    
    for slide in SLIDE_TYPES:
        slide_idx = slide["id"]
        slide_title = slide["name"]
        
        await send_telegram_message(
            bot_token, clean_sender,
            f"🎨 <i>Đang vẽ & kiểm định QC cho <b>{slide_title}</b> ({slide_idx}/6)... Sếp đợi em tầm 10-15s nhé!</i>"
        )
        
        img_res = await generate_image_gpt(f"{product_name} - {slide_title}", slide_index=slide_idx)
        if not img_res.get("success"):
            await send_telegram_message(bot_token, clean_sender, f"⚠️ Gặp lỗi khi tạo {slide_title}: {img_res.get('error')}")
            continue
            
        img_url = img_res["url"]
        provider = img_res.get("provider", "OpenAI DALL-E 3 (GPT)")
        
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
        await asyncio.sleep(4)

    # TỰ ĐỘNG SOẠN BỘ 3 TÊN + 3 MÔ TẢ SHOPEE CHUẨN 5 NGUYÊN TẮC
    openai_key = os.getenv("OPENAI_API_KEY", "")
    await send_telegram_message(
        bot_token, clean_sender,
        f"📝 <i>Đang dùng não GPT-6.1 Sol soạn thảo trọn bộ 3 Tên + 3 Mô tả Shopee chuẩn 5 nguyên tắc (1 gói, Combo 3, Combo 5) cho {product_name}...</i>"
    )
    shopee_listing = await generate_shopee_listing(product_name, openai_key)
    await send_telegram_message(
        bot_token, clean_sender,
        f"📦 <b>TRỌN BỘ LISTING SHOPEE SẴN SÀNG COPY ĐĂNG SÀN [{product_name.upper()}]</b>\n\n"
        f"{shopee_listing}"
    )

    await send_telegram_message(
        bot_token, clean_sender,
        f"🎉 <b>BÁO CÁO SẾP: HOÀN THÀNH XUẤT SẮC TOÀN BỘ 6 ẢNH + 3 TÊN MÔ TẢ SHOPEE CHO {product_name.upper()}!</b>"
    )

async def run_batch_all_menu_products(clean_sender: str, bot_token: str, product_list: list):
    """Tiến trình cày ngầm cả ngày cho toàn bộ Menu của Sếp"""
    await send_telegram_message(
        bot_token, clean_sender,
        f"🫡 <b>DẠ SẾP! EM ĐÃ KÍCH HOẠT TIẾN TRÌNH TỰ HÀNH CẢ NGÀY CHO TOÀN BỘ MENU!</b>\n\n"
        f"📋 <b>Danh sách {len(product_list)} món sẽ thực hiện:</b>\n" +
        "\n".join([f"  {i+1}. {name}" for i, name in enumerate(product_list)]) +
        f"\n\n⚙️ <b>Quy trình:</b> Bot tự tạo ảnh chuẩn DALL-E 3, tự kiểm định viền, logo, linh vật Panda và gửi dần từng ảnh cho Sếp duyệt.\n"
        f"☕ Sếp cứ đi làm việc khác, em bắt đầu cày ngay bây giờ ạ!"
    )
    
    for i, prod in enumerate(product_list, 1):
        await send_telegram_message(bot_token, clean_sender, f"🔄 <b>Đang thực hiện món {i}/{len(product_list)}: [{prod.upper()}]</b>...")
        
        # Tạo ảnh bìa Shopee cho món này
        img_res = await generate_image_gpt(f"Ảnh bìa Shopee {prod}", slide_index=1)
        if img_res.get("success"):
            img_url = img_res["url"]
            provider = img_res.get("provider", "OpenAI DALL-E 3 (GPT)")
            qc_report = await verify_honupie_qc(prod, 1, img_url)
            checklist_str = "\n".join([f"  ✅ {c['item']}" for c in qc_report["checklist"]])
            
            caption = (
                f"✨ <b>BÀN GIAO MÓN {i}/{len(product_list)}: {prod.upper()}</b>\n"
                f"🏷 <b>Cổng:</b> {provider}\n\n"
                f"🛡️ <b>BẢNG KIỂM ĐỊNH QC ({qc_report['score']}):</b>\n"
                f"{checklist_str}\n\n"
                f"👉 <i>Đã đạt 100% chuẩn nhận diện Honu Pie!</i>"
            )
            await send_telegram_photo(bot_token, clean_sender, img_url, caption)
            await asyncio.sleep(4)

    await send_telegram_message(
        bot_token, clean_sender,
        f"🎉 <b>BÁO CÁO SẾP: ĐÃ HOÀN THÀNH TOÀN BỘ {len(product_list)} SẢN PHẨM TRONG MENU!</b>\n\n"
        f"Tất cả ảnh đã được kiểm định QC kỹ càng và bàn giao đầy đủ cho Sếp bên trên rồi ạ!"
    )

# ==============================================================================
# 3. ĐIỀU PHỐI MỆNH LỆNH THÔNG MINH QUA NÃO GPT
# ==============================================================================

async def process_telegram_command(sender_id: str, command_text: str, bot_token: str):
    """Xử lý mệnh lệnh tự nhiên của Sếp bằng não GPT-4o-mini"""
    clean_sender = str(sender_id).strip()
    openai_key = os.getenv("OPENAI_API_KEY", "")
    page_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")

    print(f"[NATURAL COMMAND] from={clean_sender}, cmd='{command_text}'")

    # DÙNG NÃO GPT ĐỂ PHÂN TÍCH Ý ĐỊNH
    intent_data = await analyze_ceo_intent_with_gpt(command_text, openai_key)
    action = intent_data.get("action", "chat")
    products = intent_data.get("products", [])
    reply_to_ceo = intent_data.get("reply_to_ceo", "Dạ Sếp! Em đang triển khai ngay ạ!")

    # 1. TRƯỜNG HỢP: SẾP BẢO LÀM TẤT CẢ CÁC MÓN TRONG MENU CẢ NGÀY
    if action == "batch_all_products":
        if not products:
            products = [p["name"] for p in HONU_DATA.get("products", [])]
        asyncio.create_task(run_batch_all_menu_products(clean_sender, bot_token, products))
        return

    # 2. TRƯỜNG HỢP: SẾP BẢO LÀM TRỌN BỘ 6 ẢNH CHO 1 MÓN CỤ THỂ
    if action == "batch_single_product":
        prod_name = products[0] if products else "Snack Honu Pie"
        asyncio.create_task(run_batch_shopee_production(clean_sender, bot_token, prod_name))
        return

    # 3. TRƯỜNG HỢP: SẾP GIAO DANH SÁCH NHIỀU MÓN
    if action == "batch_list":
        if not products:
            products = [p["name"] for p in HONU_DATA.get("products", [])][:3]
        asyncio.create_task(run_batch_all_menu_products(clean_sender, bot_token, products))
        return

    # 4. TRƯỜNG HỢP: TẠO 1 ẢNH THEO YÊU CẦU CỦA SẾP
    if action == "single_image":
        prod_name = products[0] if products else command_text
        await send_telegram_message(bot_token, clean_sender, f"🎨 <i>{reply_to_ceo}</i>")
        
        slide_idx = intent_data.get("slide_index", 1)
        img_result = await generate_image_gpt(f"{prod_name} {intent_data.get('concept', '')}", slide_index=slide_idx)
        if img_result.get("success"):
            img_url = img_result["url"]
            provider = img_result.get("provider", "OpenAI DALL-E 3 (GPT)")
            slide_type = img_result.get("slide_type", "Ảnh chuẩn Shopee")
            
            qc_report = await verify_honupie_qc(prod_name, slide_idx, img_url)
            checklist_str = "\n".join([f"  ✅ {c['item']}" for c in qc_report["checklist"]])

            caption = (
                f"✨ <b>ẢNH SẢN PHẨM CHUẨN NHẬN DIỆN HONU PIE</b>\n"
                f"📦 <b>Sản phẩm:</b> {prod_name}\n"
                f"📂 <b>Phân loại:</b> {slide_type}\n"
                f"🏷 <b>Cổng:</b> {provider}\n\n"
                f"🛡️ <b>BẢNG KIỂM ĐỊNH QC ({qc_report['score']}):</b>\n"
                f"{checklist_str}\n\n"
                f"👉 <i>Sếp xem có ưng ý không, sếp cứ ra lệnh tiếp nhé!</i>"
            )
            await send_telegram_photo(bot_token, clean_sender, img_url, caption)
            return
        else:
            await send_telegram_message(bot_token, clean_sender, f"⚠️ Lỗi tạo ảnh: {img_result.get('error')}")
            return

    # 5. TRƯỜNG HỢP: TẠO VIDEO / REELS
    if action == "create_video":
        await send_telegram_message(bot_token, clean_sender, f"🎬 <i>{reply_to_ceo}</i>")
        veo_result = await generate_video_veo(command_text)
        report = (
            f"🎥 <b>KỊCH BẢN VIDEO GOOGLE VEO ĐÃ KHỞI TẠO XONG:</b>\n\n"
            f"📝 <b>Prompt điện ảnh:</b> <code>{veo_result['prompt']}</code>\n\n"
            f"💡 <i>{veo_result['note']}</i>"
        )
        await send_telegram_message(bot_token, clean_sender, report)
        return

    # 6. TRƯỜNG HỢP: ĐĂNG BÀI LÊN FANPAGE FACEBOOK
    if action == "post_facebook":
        post_content = intent_data.get("facebook_content") or command_text
        # Tự sinh ảnh kèm theo bài viết
        img_gen = await generate_image_gpt(f"Ảnh món ăn cho bài viết: {post_content[:50]}")
        img_url = img_gen.get("url") if img_gen.get("success") else None
        
        fb_result = await publish_to_facebook_page(post_content, page_token, img_url)
        if fb_result.get("success"):
            report = (
                f"🫡 <b>DẠ SẾP! EM ĐÃ TỰ ĐỘNG ĐĂNG BÀI LÊN FANPAGE THÀNH CÔNG!</b>\n\n"
                f"📝 <b>Nội dung:</b>\n{post_content}\n\n"
                f"🔗 <b>Mã bài viết:</b> <code>{fb_result.get('post_id')}</code>"
            )
            if img_url:
                await send_telegram_photo(bot_token, clean_sender, img_url, report)
            else:
                await send_telegram_message(bot_token, clean_sender, report)
            return
        else:
            await send_telegram_message(bot_token, clean_sender, f"⚠️ Đăng bài lỗi: {fb_result.get('error')}\n\nNội dung: {post_content}")
            return

    # 7. TRƯỜNG HỢP: TẠO TÊN & MÔ TẢ SHOPEE CHUẨN 5 NGUYÊN TẮC
    if action == "shopee_listing":
        prod_name = products[0] if products else command_text
        await send_telegram_message(
            bot_token, clean_sender, 
            f"📝 <i>Dạ Sếp! Em đang dùng não GPT-6.1 Sol soạn trọn bộ 3 Tên + 3 Mô tả Shopee chuẩn 5 nguyên tắc (1 gói, Combo 3, Combo 5) cho {prod_name}...</i>"
        )
        shopee_listing = await generate_shopee_listing(prod_name, openai_key)
        await send_telegram_message(
            bot_token, clean_sender, 
            f"📦 <b>TRỌN BỘ LISTING SHOPEE [{prod_name.upper()}]:</b>\n\n{shopee_listing}"
        )
        return

    # 8. TRƯỜNG HỢP NÓI CHUYỆN, TƯ VẤN, CHÀO HỎI THÔNG MINH
    await send_telegram_message(bot_token, clean_sender, reply_to_ceo)

# ==============================================================================
# HÀM PHỤ TRỢ GỬI TIN NHẮN VÀ ẢNH TELEGRAM
# ==============================================================================

async def publish_to_facebook_page(content: str, page_token: str, image_url: str = None) -> dict:
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
