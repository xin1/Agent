import fitz  # PyMuPDF
import pdfplumber
import re
import csv
import os

def process_pdf(pdf_path: str, top_cm: float, bottom_cm: float):
    # 单位换算
    top_px = int(top_cm * 28.35)
    bottom_px = int(bottom_cm * 28.35)

    cropped_path = pdf_path.replace(".pdf", "_cropped.pdf")
    csv_path = pdf_path.replace(".pdf", ".csv")

    # 裁剪 PDF
    doc = fitz.open(pdf_path)
    for page in doc:
        rect = page.rect
        crop_rect = fitz.Rect(rect.x0, rect.y0 + top_px, rect.x1, rect.y1 - bottom_px)
        page.set_cropbox(crop_rect)
    doc.save(cropped_path)
    doc.close()

    # 提取结构化信息
    with open(csv_path, "w", newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["标题", "内容"])

        current_title = None
        current_content = []

        with pdfplumber.open(cropped_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if is_heading(line):
                        if current_title:
                            writer.writerow([current_title, '\n'.join(current_content)])
                        current_title = line
                        current_content = []
                    elif current_title:
                        current_content.append(line)
        if current_title:
            writer.writerow([current_title, '\n'.join(current_content)])

    return cropped_path, csv_path

def is_heading(line):
    if len(line) > 50:
        return False
    return bool(re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line.strip()))
