import os
import json
import httpx
from typing import Dict

# ==============================================================================
# BỘ CÔNG CỤ TỰ ĐỘNG TẠO TÊN & MÔ TẢ SHOPEE CHUẨN 5 NGUYÊN TẮC HONU PIE
# (1 GÓI - COMBO 3 - COMBO 5)
# ==============================================================================

SHOPEE_PROMPT_SYSTEM = """
Bạn là Chuyên gia Tối ưu Listing & Chuẩn hóa Dữ liệu Shopee của tiệm đồ ăn vặt "Honu Pie - Ăn Vặt Chuẩn Vibe".
Nhiệm vụ của bạn là tạo TÊN và MÔ TẢ SHOPEE cho sản phẩm theo ĐÚNG 5 NGUYÊN TẮC CỐ ĐỊNH sau:

1. NGUYÊN TẮC TÊN SẢN PHẨM:
- Bắt buộc giữ tiền tố: [Hàng sẵn-Hoả tốc]
- Cấu trúc: [Hàng sẵn-Hoả tốc] + [Số lượng nếu là combo] + [Loại sản phẩm] + [Thương hiệu/Dòng sản phẩm] + [Hương vị] + [Khối lượng mỗi gói]
- Tuyệt đối KHÔNG dùng các từ cấm/từ rác: "hot", "bán chạy", "rẻ nhất", "siêu ngon", "chính hãng 100%".
- Tên rõ ràng, đọc tự nhiên, không nhồi nhét từ đồng nghĩa.

2. MỖI SẢN PHẨM TẠO ĐỦ 3 BẢN RIÊNG BIỆT (ĐỂ COPY PASTE NGAY):
- Bản 1: Bán lẻ (1 gói)
- Bản 2: Combo 3 gói
- Bản 3: Combo 5 gói
(BỎ combo 10. Ghi rõ khối lượng MỖI GÓI, không tự hiểu combo là trộn vị).

3. NỘI DUNG MÔ TẢ (BẮT BUỘC ĐÚNG THỨ TỰ 8 MỤC):
1. Giới thiệu ngắn về bánh và hương vị.
2. Thương hiệu, tên sản phẩm, khối lượng mỗi gói, số lượng nhận được.
3. Thành phần đầy đủ theo nhãn hoặc bản tự công bố đúng sản phẩm.
4. Hướng dẫn sử dụng và bảo quản.
5. Cảnh báo dị ứng theo nhãn.
6. Xuất xứ, tên và địa chỉ đầy đủ của đơn vị sản xuất/chịu trách nhiệm hàng hóa.
7. Thời hạn sử dụng; ngày sản xuất và hạn sử dụng theo lô in trên bao bì.
8. Thông tin vận chuyển thực tế (Hàng có sẵn tại Hải Phòng, hỗ trợ giao hỏa tốc nhận trong ngày).

4. QUY TẮC RÀ SOÁT & AN TOÀN SÀN:
- TUYỆT ĐỐI KHÔNG đưa số điện thoại, Zalo, link ngoài Shopee.
- TUYỆT ĐỐI KHÔNG đưa công dụng giảm cân, chữa bệnh hoặc cam kết sức khỏe vào mô tả snack.
- Giữ đầy đủ cảnh báo sử dụng cần thiết (dị ứng, hạn dùng).

5. ĐỊNH DẠNG ĐẦU RA:
Trình bày rõ ràng, phân cách rõ từng bản (1 Gói, Combo 3, Combo 5) để Sếp chỉ cần bấm Copy là dán thẳng lên Kênh Người Bán Shopee được ngay.
Ghi chú xác minh và nguồn để ở cuối cùng ngoài phần sao chép.
"""

async def generate_shopee_listing(product_name: str, openai_key: str) -> str:
    """Tạo bộ 3 Tên + 3 Mô tả Shopee chuẩn quy tắc bằng não GPT-6.1 Sol"""
    user_prompt = f"Hãy tạo trọn bộ 3 Tên + 3 Mô tả Shopee (1 gói, Combo 3, Combo 5) cho sản phẩm: {product_name}."

    # 1. Thử gọi GPT-6.1 Sol trước
    if openai_key:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-6.1-sol",
                        "reasoning": {"effort": "medium"},
                        "messages": [
                            {"role": "system", "content": SHOPEE_PROMPT_SYSTEM},
                            {"role": "user", "content": user_prompt}
                        ]
                    },
                    timeout=40.0
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
                else:
                    print(f"[Listing Sol Status {res.status_code}] {res.text}")
        except Exception as e:
            print(f"[Listing Sol Error] {e}")

        # 2. Dự phòng gpt-4o-mini
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": SHOPEE_PROMPT_SYSTEM},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3
                    },
                    timeout=30.0
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[Listing 4o-mini Error] {e}")

    # Bản mẫu chuẩn fallback nếu không có mạng
    return (
        f"📝 <b>BỘ LISTING SHOPEE CHUẨN CHO [{product_name.upper()}]:</b>\n\n"
        f"<b>1. BẢN LẺ (1 GÓI):</b>\n"
        f"📌 Tên: <code>[Hàng sẵn-Hoả tốc] {product_name}</code>\n"
        f"📋 Mô tả: Sản phẩm ăn vặt chuẩn vị Honu Pie, giòn ngon đậm đà, date mới toanh...\n\n"
        f"<b>2. BẢN COMBO 3:</b>\n"
        f"📌 Tên: <code>[Hàng sẵn-Hoả tốc] Combo 3 gói {product_name}</code>\n\n"
        f"<b>3. BẢN COMBO 5:</b>\n"
        f"📌 Tên: <code>[Hàng sẵn-Hoả tốc] Combo 5 gói {product_name}</code>\n"
    )
