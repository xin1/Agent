# pip install gradio pymupdf pdfplumber

import gradio as gr
import fitz  # PyMuPDF
import pdfplumber
import re
import csv
import tempfile
import os

def process_pdf(file, top_crop, bottom_crop):
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        cropped_path = os.path.join(tmpdir, "cropped.pdf")
        csv_path = os.path.join(tmpdir, "output.csv")

        # 保存上传的文件
        with open(input_path, "wb") as f:
            f.write(file.read())

        # Step 1: 裁剪 PDF 页眉页脚
        crop_pdf(input_path, cropped_path, top_crop, bottom_crop)

        # Step 2: 提取结构化内容
        extract_pdf_sections(cropped_path, csv_path)

        return cropped_path, csv_path

def crop_pdf(input_pdf, output_pdf, top_crop, bottom_crop):
    doc = fitz.open(input_pdf)
    for page in doc:
        rect = page.rect
        crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
        page.set_cropbox(crop_rect)
    doc.save(output_pdf)
    doc.close()

def extract_pdf_sections(input_pdf, output_csv):
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['标题', '内容'])

        current_title = None
        current_content = []

        with pdfplumber.open(input_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    header = get_smart_header(line)
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

def get_smart_header(line):
    line = line.strip()
    if len(line) > 50:
        return None
    if re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line):
        return line
    return None

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

# ===== Gradio 界面部分 =====
gr_interface = gr.Interface(
    fn=process_pdf,
    inputs=[
        gr.File(label="上传 PDF", type="binary"),
        gr.Slider(0, 150, value=50, step=1, label="裁剪上边距 (px)"),
        gr.Slider(0, 150, value=50, step=1, label="裁剪下边距 (px)")
    ],
    outputs=[
        gr.File(label="裁剪后的 PDF"),
        gr.File(label="提取内容 CSV")
    ],
    title="📄 PDF 页眉页脚裁剪 + 标题内容提取工具",
    description="上传 PDF，设置裁剪高度后，自动生成裁剪后的 PDF 和结构化 CSV 文件"
)

if __name__ == "__main__":
    gr_interface.launch()
