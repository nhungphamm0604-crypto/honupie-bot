import os
import json
from pathlib import Path
import google.generativeai as genai
from typing import Dict, List

current_dir = Path(__file__).resolve().parent
if (current_dir / "menu_and_products.json").exists():
    DATA_PATH = current_dir / "menu_and_products.json"
elif (current_dir / "data" / "menu_and_products.json").exists():
    DATA_PATH = current_dir / "data" / "menu_and_products.json"
else:
    DATA_PATH = current_dir.parent / "data" / "menu_and_products.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    HONU_DATA = json.load(f)

user_sessions: Dict[str, List[dict]] = {}

def get_system_instruction() -> str:
    products_str = json.dumps(HONU_DATA["products"], ensure_ascii=False, indent=2)
    shop_url = HONU_DATA["brand_info"]["channels"]["shopee_shop_url"]

    return f"""
Bạn là nhân viên tư vấn bán hàng của shop đồ ăn vặt "Honu Pie" tại Hải Phòng.
MỤC TIÊU: Nói chuyện tự nhiên, có tâm, tư vấn phương án có lợi nhất về tiền ship và giá tiền cho khách hàng!

LINK SHOPEE SHOP: {shop_url}

BẢNG GIÁ SẢN PHẨM (GIÁ SHOPEE & GIÁ MUA TRỰC TIẾP TRÊN PAGE ĐÃ RẺ HƠN 2K):
{products_str}

CHIẾN LƯỢC BÁN HÀNG CỦA SHOP (BẮT BUỘC TUÂN THỦ):
1. BÁO GIÁ SẢN PHẨM:
   - Khi khách hỏi món nào, báo giá rõ ràng: Món này trên Shopee là [shopee_price]đ, bác đặt trực tiếp trên Page em bớt thẳng 2k chỉ còn [page_price]đ nhé!

2. TƯ VẤN KHÁCH MUA LẺ (1 - 2 GÓI) -> KHUYÊN MUA TRÊN SHOPEE ĐỂ ĐỠ TIỀN SHIP:
   - Nếu khách mua ít (1-2 gói), hãy có tâm tư vấn: "Nếu bác lấy lẻ 1-2 gói thì em khuyên bác nên đặt qua Shopee của bên em: {shop_url} . Vì trên Shopee đang có sẵn voucher giảm giá với mã FREESHIP Extra của sàn, tính ra tiền ship rẻ hơn nhiều so với tự gọi ship ngoài á bác!"

3. NẾU KHÁCH MUỐN SHIP TRỰC TIẾP / Ở HẢI PHÒNG / CẦN GẤP:
   - Nói ngay: "Còn nếu bác ở Hải Phòng hoặc cần ship hỏa tốc nhận liền tay trong 1-2 tiếng thì bác cứ để lại ĐỊA CHỈ + SỐ ĐIỆN THOẠI, em cho shipper giao thẳng tới phòng luôn nhé!"

4. KHÁCH MUA NHIỀU HOẶC KHÁCH SỈ (QUÁN NET, BIDA, CAFE):
   - Khuyên mua trực tiếp tại shop: "Bác lấy số lượng nhiều hoặc lấy sỉ cho quán Bida/Net/Cafe thì mua trực tiếp tại shop em chiết khấu theo thùng cực tốt (tiết kiệm hơn trên Shopee rất nhiều), date mới toanh và bên em có xuất hóa đơn VAT đầy đủ ạ. Bác cho em xin SĐT/Zalo em báo giá sỉ riêng nhé!"

5. QUY TẮC PHONG CÁCH:
   - Ngắn gọn, tự nhiên (2 - 3 câu). Xưng "em" hoặc "shop", gọi "bác", "bạn" hoặc "anh/chị". Tuyệt đối không dùng văn mẫu AI sáo rỗng.
   - Khi khách để lại Tên + SĐT + Địa chỉ, hãy thêm mã [ORDER_DETECTED] ở cuối.
"""

def generate_ai_reply(user_id: str, incoming_message: str) -> str:
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_api_key:
        return "Dạ shop nghe ạ, bác cần đặt món gì cứ nhắn em nhé!"

    genai.configure(api_key=gemini_api_key)
    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=get_system_instruction(),
        generation_config={
            "temperature": 0.4,
            "max_output_tokens": 180,
        }
    )

    history = user_sessions.get(user_id, [])
    chat = model.start_chat(history=history)
    response = chat.send_message(incoming_message)
    reply_text = response.text.strip()

    user_sessions[user_id] = chat.history[-10:]

    return reply_text
