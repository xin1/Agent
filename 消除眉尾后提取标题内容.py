import fitz  # PyMuPDF
import re
import csv

def extract_multilevel_from_cropped_pdf(input_pdf, output_csv, top_crop=55, bottom_crop=55):
    doc = fitz.open(input_pdf)

    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['标题', '内容'])

        current_title = None
        current_content = []

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

                header = get_smart_header(line)
                if header:
                    # 写入上一节
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

def get_smart_header(line):
    """
    更智能的标题识别：
    - 以 1 / 1.1 / 1.1.1 开头
    - 总长度不超过50字符（防止正文误判为标题）
    """
    line = line.strip()
    if len(line) > 50:
        return None
    if re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line):
        return line
    return None

def clean_content(content_lines):
    """
    合并断开的句子行：如果前一行没有标点，和下一行合并
    """
    cleaned = []
    for line in content_lines:
        if not line:
            continue
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

# ======== 主程序入口 =========
if __name__ == "__main__":
    input_pdf = r"D:\Files\xFusion\Tu.pdf"
    output_csv = r"D:\Files\xFusion\Tu_structured_output_2.csv"

    try:
        extract_multilevel_from_cropped_pdf(input_pdf, output_csv)
        print(f"✅ 成功提取并导出至 CSV：{output_csv}")
    except Exception as e:
        print(f"❌ 出错：{str(e)}")
