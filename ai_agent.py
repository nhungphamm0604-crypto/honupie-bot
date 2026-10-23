import os
import json
from pathlib import Path
import google.generativeai as genai
from typing import Dict, List

# Load dữ liệu sản phẩm của Honu Pie (linh hoạt tìm file dù đặt ở đâu)
current_dir = Path(__file__).resolve().parent
if (current_dir / "menu_and_products.json").exists():
    DATA_PATH = current_dir / "menu_and_products.json"
elif (current_dir / "data" / "menu_and_products.json").exists():
    DATA_PATH = current_dir / "data" / "menu_and_products.json"
else:
    DATA_PATH = current_dir.parent / "data" / "menu_and_products.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    HONU_DATA = json.load(f)

# Lưu trữ lịch sử hội thoại cho từng khách (theo sender_id trên Facebook)
user_sessions: Dict[str, List[dict]] = {}

def get_system_instruction() -> str:
    brand = HONU_DATA["brand_info"]
    products_str = json.dumps(HONU_DATA["products"], ensure_ascii=False, indent=2)
    combos_str = json.dumps(HONU_DATA["combos_and_upsell"], ensure_ascii=False, indent=2)

    return f"""
Bạn là AI chuyên gia bán hàng và chốt đơn xuất sắc của thương hiệu: "{brand['name']}".
Slogan: "{brand['slogan']}"
Trụ sở: {brand['location']}
Shopee: {brand['channels']['shopee']}
Phong cách trò chuyện: {brand['voice_tone']}

DANH SÁCH SẢN PHẨM:
{products_str}

CÁC COMBO VÀ GÓI SỈ:
{combos_str}

ĐẶC BIỆT - CHIẾN THUẬT UPSELL & CHỐT ĐƠN TỰ ĐỘNG:
1. KHÁCH HỎI 1 MÓN LẺ:
   - Khen món đó ngon (tả ngắn gọn độ giòn/béo/chua cay).
   - Ngay lập tức gợi ý thêm 1 món đi kèm để tạo thành combo hoàn hảo (Ví dụ: khách hỏi Hạt dưa -> rủ rê thêm Khô gà lá chanh để vừa cắn vừa nhai).
   - Nếu đơn hàng sắp chạm mốc 150k -> Nhắc khách lấy thêm món nhỏ để được FREESHIP!
2. NẾU KHÁCH Ở HẢI PHÒNG:
   - Nhắc ngay: "Bên em có SHIP HỎA TỐC 1-2 tiếng là tới tận cửa, thèm là có liền!".
3. NẾU KHÁCH HỎI SỈ (Cho quán Net, Cyber Game, Quán Bida, Quán Cafe):
   - Chuyển sang phong cách đối tác chuyên nghiệp: "Dạ Honu Pie chuyên đổ sỉ theo thùng chiết khấu cực sâu cho Cyber Game và Quán Bida toàn quốc, date mới toanh, đầy đủ giấy VSATTP và XUẤT HÓA ĐƠN VAT".
   - Xin ngay Tên Quán + Số Điện Thoại/Zalo để chủ shop gửi bảng báo giá sỉ riêng.
4. CHỐT ĐƠN:
   - Khi khách đồng ý mua, hãy tổng kết đơn hàng: Tên món x Số lượng -> Tổng tiền.
   - Xin đầy đủ: Họ tên người nhận + Số điện thoại + Địa chỉ cụ thể.
   - Khi đã nhận đủ Họ tên, SĐT, Địa chỉ, hãy thêm cụm từ đặc biệt [ORDER_DETECTED] vào cuối câu trả lời để hệ thống tự động báo đơn về điện thoại của chủ shop.

LƯU Ý QUAN TRỌNG:
- Trả lời ngắn gọn, súc tích (tầm 2-4 câu), không viết dài dòng như văn mẫu.
- Luôn thân thiện, tạo cảm giác thèm ăn, dùng emoji sinh động.
"""

def generate_ai_reply(user_id: str, incoming_message: str) -> str:
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_api_key:
        return "Dạ Honu Pie nghe nè bồ ơi! Shop đang nâng cấp hệ thống một xíu, bồ để lại tin nhắn món muốn đặt và SĐT, shop phản hồi ngay nhé!"

    genai.configure(api_key=gemini_api_key)
    
    # Khởi tạo mô hình Gemini 1.5 Flash / 2.0 Flash
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=get_system_instruction(),
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 350,
        }
    )

    history = user_sessions.get(user_id, [])
    
    chat = model.start_chat(history=history)
    response = chat.send_message(incoming_message)
    reply_text = response.text.strip()

    user_sessions[user_id] = chat.history[-10:]

    return reply_text
