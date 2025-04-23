import fitz  # PyMuPDF
import re
import csv

def extract_multilevel_from_cropped_pdf(input_pdf, output_csv, top_crop=50, bottom_crop=50):
    doc = fitz.open(input_pdf)

    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['标题', '内容'])

        current_title = None
        current_content = []

        for page in doc:
            rect = page.rect
            crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
            text = page.get_text(clip=crop_rect)  # 只提取裁剪区域文本

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

        # 写入最后一节
        if current_title:
            writer.writerow([
                current_title,
                '\n'.join(clean_content(current_content))
            ])

    doc.close()

def get_header_level(line):
    if re.match(r'^\d+\b', line): return line          # 1
    if re.match(r'^\d+\.\d+\b', line): return line     # 1.1
    if re.match(r'^\d+\.\d+\.\d+\b', line): return line  # 1.1.1
    return None

def clean_content(content_lines):
    cleaned = []
    for line in content_lines:
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

# === 示例使用 ===
if __name__ == "__main__":
    input_pdf = r"F:\Fusion\.py\input.pdf"
    output_csv = r"F:\Fusion\.py\structured_output.csv"

    try:
        extract_multilevel_from_cropped_pdf(input_pdf, output_csv)
        print(f"✅ 成功提取裁剪后内容到: {output_csv}")
    except Exception as e:
        print(f"❌ 出错: {str(e)}")
