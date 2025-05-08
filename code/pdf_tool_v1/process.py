import os
import fitz  # PyMuPDF
import csv
import re
from uuid import uuid4

os.makedirs("outputs", exist_ok=True)

def process_pdf_and_extract(file, top_cm, bottom_cm):
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
    filename = file.filename.rsplit('.', 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{filename}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')  # 1 总则、1.1 标题
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)

        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))  # 从上到下排序

        for block in sorted_blocks:
            text = block[4].strip()
            if not text:
                continue

            match = heading_pattern.match(text)
            if match:
                current_heading = f"{match.group(1)} {match.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    # ✅ 写入 CSV：使用 utf-8-sig 编码防止乱码
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # writer.writerow(["标题", "内容"])
        for heading, content in content_dict.items():
            writer.writerow([heading, content.strip()])

    return csv_path

