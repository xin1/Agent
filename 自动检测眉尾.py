import fitz  # PyMuPDF
import re
import csv
from collections import Counter

def detect_header_footer_heights(doc, sample_pages=5):
    header_y_vals = []
    footer_y_vals = []

    for page in doc[:sample_pages]:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b['type'] != 0 or not b.get("lines"):
                continue
            y0 = b['bbox'][1]
            y1 = b['bbox'][3]

            if y0 < 150:
                header_y_vals.append(y1)
            elif y1 > page.rect.height - 150:
                footer_y_vals.append(y0)

    top_crop = int(max(Counter(header_y_vals), key=Counter(header_y_vals).get)) if header_y_vals else 50
    bottom_crop = int(page.rect.height - min(Counter(footer_y_vals), key=Counter(footer_y_vals).get)) if footer_y_vals else 50

    return top_crop, bottom_crop

def extract_multilevel_to_csv(input_pdf, output_csv):
    doc = fitz.open(input_pdf)
    top_crop, bottom_crop = detect_header_footer_heights(doc)
    print(f"🔍 自动裁剪页眉页脚：上 {top_crop}px，下 {bottom_crop}px")

    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['一级标题', '二级标题', '三级标题', '内容'])

        level1 = level2 = level3 = None
        current_content = []

        def flush():
            if level1 or level2 or level3:
                writer.writerow([
                    level1 or '',
                    level2 or '',
                    level3 or '',
                    '\n'.join(clean_content(current_content))
                ])

        for page in doc:
            rect = page.rect
            crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
            text = page.get_text(clip=crop_rect)

            if not text:
                continue

            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                level = get_header_level(line)
                if level == 1:
                    flush()
                    level1, level2, level3 = clean_header_text(line), None, None
                    current_content = []
                elif level == 2:
                    flush()
                    level2, level3 = clean_header_text(line), None
                    current_content = []
                elif level == 3:
                    flush()
                    level3 = clean_header_text(line)
                    current_content = []
                else:
                    current_content.append(line)

        flush()
    doc.close()

def get_header_level(line):
    """返回标题层级（1/2/3），不是标题则返回None"""
    if len(line) > 50:
        return None
    if re.match(r'^\d+\s', line):        # 1 标题
        return 1
    elif re.match(r'^\d+\.\d+\s', line):  # 1.1 标题
        return 2
    elif re.match(r'^\d+\.\d+\.\d+\s', line):  # 1.1.1 标题
        return 3
    return None

def clean_header_text(line):
    """去掉编号部分，只保留标题文本"""
    return re.sub(r'^\d+(\.\d+){0,2}\s*', '', line).strip()

def clean_content(content_lines):
    cleaned = []
    for line in content_lines:
        if not line:
            continue
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

# ============ 主程序 ============
if __name__ == "__main__":
    input_pdf = r"F:\Fusion\.py\input.pdf"
    output_csv = r"F:\Fusion\.py\structured_output.csv"

    try:
        extract_multilevel_to_csv(input_pdf, output_csv)
        print(f"✅ 提取完成，输出文件：{output_csv}")
    except Exception as e:
        print(f"❌ 出错：{str(e)}")
