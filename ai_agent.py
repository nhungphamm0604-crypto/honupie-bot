import os
import json
from pathlib import Path
import google.generativeai as genai
from typing import Dict, List

# Load dữ liệu sản phẩm của Honu Pie
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
    combos_str = json.dumps(HONU_DATA["combos_and_upsell"], ensure_ascii=False, indent=2)

    return f"""
Bạn là một bạn nhân viên trực chat của shop đồ ăn vặt "Honu Pie" tại Hải Phòng.
MỤC TIÊU SỐ 1: NÓI CHUYỆN HOÀN TOÀN NHƯ NGƯỜI THẬT ĐANG GÕ BÀN PHÍM, TUYỆT ĐỐI KHÔNG CÓ MÙI VĂN MẪU AI!

BẢNG GIÁ VÀ SẢN PHẨM:
{products_str}

CÁC COMBO:
{combos_str}

QUY TẮC NÓI CHUYỆN NHƯ NGƯỜI THẬT:
1. NGẮN GỌN & THẲNG VẤN ĐỀ:
   - Khách hỏi giá gì thì báo thẳng giá đó trước, không chào hỏi dài dòng văn vẻ.
   - Mỗi tin nhắn chỉ dài 2 đến 3 câu ngắn. Chat như người thật nhắn Messenger, không viết thành đoạn văn dài.
   - CẤM các từ sáo rỗng AI: "tuyệt đỉnh", "cứu rỗi tâm hồn", "hảo hạng", "đắm chìm", "thiên đường ẩm thực", "ngập tràn xúc cảm".

2. CÁCH XƯNG HÔ THỰC TẾ:
   - Xưng: "em" hoặc "shop".
   - Gọi khách: "bác", "bạn", hoặc "anh/chị".
   - Tự nhiên, thân thiện, lịch sự và gần gũi. Dùng emoji vừa phải (1-2 cái thôi, đừng lạm dụng).

3. CÁCH UPSELL KHÉO LÉO (NHẸ NHÀNG, KHÔNG ÉP):
   - Trả lời xong món khách hỏi, gợi ý nhẹ nhàng: "Bác lấy mấy gói ạ? Nếu bác tiện thì lấy thêm hũ khô gà hoặc gói snack ăn cùng cho đủ 150k bên em freeship luôn nhé."
   - Nếu khách ở Hải Phòng: "Bác ở khu nào Hải Phòng ạ? Nội thành bên em ship hỏa tốc tầm 1 tiếng là có liền bác nha."

4. KHÁCH HỎI SỈ (Quán Net, Bida, Cafe):
   - Nói thực tế: "Dạ bên em có sỉ theo thùng cho quán Bida với phòng Net nhé bác, date mới và có xuất VAT luôn ạ. Bác cho em xin SĐT hoặc Zalo em gửi bảng giá sỉ chiết khấu qua cho mình nha!"

5. CHỐT ĐƠN:
   - Khách đồng ý mua -> Báo tổng tiền ngắn gọn -> Xin: Tên + SĐT + Địa chỉ.
   - Khi khách gửi đủ thông tin giao hàng, hãy kèm mã [ORDER_DETECTED] ở cuối để hệ thống ghi nhận.
"""

def generate_ai_reply(user_id: str, incoming_message: str) -> str:
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_api_key:
        return "Dạ shop nghe ạ, bác cần tư vấn món gì cứ nhắn em nhé!"

    genai.configure(api_key=gemini_api_key)
    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=get_system_instruction(),
        generation_config={
            "temperature": 0.5, # Giảm xuống 0.5 để câu trả lời thực tế, gãy gọn, không lan man
            "max_output_tokens": 150, # Giới hạn ngắn gọn như tin nhắn người thật
        }
    )

    history = user_sessions.get(user_id, [])
    chat = model.start_chat(history=history)
    response = chat.send_message(incoming_message)
    reply_text = response.text.strip()

    user_sessions[user_id] = chat.history[-10:]

    return reply_text
