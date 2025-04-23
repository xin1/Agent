import fitz  # PyMuPDF
import pdfplumber
import re
import csv

def crop_pdf(input_pdf, cropped_pdf, top_crop=50, bottom_crop=50):
    """裁剪 PDF 去除页眉页脚"""
    doc = fitz.open(input_pdf)
    for page in doc:
        rect = page.rect
        crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
        page.set_cropbox(crop_rect)
    doc.save(cropped_pdf)
    doc.close()

def extract_multilevel_sections(pdf_path, output_csv):
    """从 PDF 中提取1级/2级/3级标题及其内容"""
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['标题', '内容'])

        with pdfplumber.open(pdf_path) as pdf:
            current_title = None
            current_content = []
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    header = get_header_level(line)
                    if header:
                        if current_title:
                            writer.writerow([
                                current_title,
                                '\n'.join(clean_content(current_content))
                            ])
                        current_title = line
                        current_content = []
                    elif current_title:
                        current_content.append(line)

            if current_title:
                writer.writerow([
                    current_title,
                    '\n'.join(clean_content(current_content))
                ])

def get_header_level(line):
    """识别1级/2级/3级标题"""
    if re.match(r'^\d+\b', line):             # 1
        return line
    if re.match(r'^\d+\.\d+\b', line):        # 1.1
        return line
    if re.match(r'^\d+\.\d+\.\d+\b', line):   # 1.1.1
        return line
    return None

def clean_content(content_lines):
    """合并被断开的行"""
    cleaned = []
    for line in content_lines:
        if not line:
            continue
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

# ======== 主程序 =========
if __name__ == "__main__":
    input_pdf = r"F:\Fusion\.py\input.pdf"
    cropped_pdf = r"F:\Fusion\.py\output_no_header_footer.pdf"
    output_csv = r"F:\Fusion\.py\structured_output.csv"

    try:
        crop_pdf(input_pdf, cropped_pdf)  # 第一步：裁剪页眉页脚
        extract_multilevel_sections(cropped_pdf, output_csv)  # 第二步：提取结构
        print(f"✅ 成功：已生成裁剪后PDF并提取内容至CSV: {output_csv}")
    except Exception as e:
        print(f"❌ 错误：{str(e)}")
