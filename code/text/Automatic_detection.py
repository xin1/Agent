import fitz  # PyMuPDF
import re
import csv
from collections import Counter

def detect_header_footer_heights(doc, sample_pages=5):
    header_y_vals, footer_y_vals = [], []
    for page in doc[:sample_pages]:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b['type'] != 0 or not b.get("lines"): continue
            y0, y1 = b['bbox'][1], b['bbox'][3]
            if y0 < 150: header_y_vals.append(y1)
            elif y1 > page.rect.height - 150: footer_y_vals.append(y0)
    top_crop = int(max(Counter(header_y_vals), key=Counter(header_y_vals).get)) if header_y_vals else 50
    bottom_crop = int(page.rect.height - min(Counter(footer_y_vals), key=Counter(footer_y_vals).get)) if footer_y_vals else 50
    return top_crop, bottom_crop

def crop_pdf(input_path, output_path, top_crop, bottom_crop):
    doc = fitz.open(input_path)
    for page in doc:
        rect = page.rect
        page.set_cropbox(fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop))
    doc.save(output_path)
    doc.close()

def extract_multilevel_to_csv(input_pdf, output_csv, top_crop, bottom_crop):
    doc = fitz.open(input_pdf)
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['一级标题', '二级标题', '三级标题', '内容'])
        level1 = level2 = level3 = None
        current_content = []

        def flush():
            if level1 or level2 or level3:
                writer.writerow([
                    level1 or '', level2 or '', level3 or '',
                    '\n'.join(clean_content(current_content))
                ])

        for page in doc:
            rect = page.rect
            crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
            text = page.get_text(clip=crop_rect)
            for line in text.split('\n'):
                line = line.strip()
                if not line: continue
                level = get_header_level(line)
                if level == 1:
                    flush(); level1, level2, level3 = clean_header_text(line), None, None; current_content = []
                elif level == 2:
                    flush(); level2, level3 = clean_header_text(line), None; current_content = []
                elif level == 3:
                    flush(); level3 = clean_header_text(line); current_content = []
                else:
                    current_content.append(line)
        flush()
    doc.close()

def get_header_level(line):
    if len(line) > 50: return None
    if re.match(r'^\d+\s', line): return 1
    elif re.match(r'^\d+\.\d+\s', line): return 2
    elif re.match(r'^\d+\.\d+\.\d+\s', line): return 3
    return None

def clean_header_text(line):
    return re.sub(r'^\d+(\.\d+){0,2}\s*', '', line).strip()

def clean_content(lines):
    result = []
    for line in lines:
        if not line: continue
        if result and not result[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            result[-1] += ' ' + line
        else:
            result.append(line)
    return result

# ========= 路径设置 =========
input_pdf = r"F:\Fusion\.py\input.pdf"
cropped_pdf = r"F:\Fusion\.py\input_cropped.pdf"
output_csv = r"F:\Fusion\.py\input_output.csv"

doc = fitz.open(input_pdf)
top_crop, bottom_crop = detect_header_footer_heights(doc)
doc.close()

crop_pdf(input_pdf, cropped_pdf, top_crop, bottom_crop)
extract_multilevel_to_csv(cropped_pdf, output_csv, top_crop, bottom_crop)

print("✅ 剪裁完成: ", cropped_pdf)
print("✅ CSV生成: ", output_csv)
