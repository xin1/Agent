import fitz  # PyMuPDF
import re
import csv
import os
import tempfile
import gradio as gr

def extract_pdf(input_pdf, top_cm, bottom_cm):
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(temp_dir, "input.pdf")
        input_pdf.save(pdf_path)

        output_csv = os.path.join(temp_dir, "output.csv")
        cropped_pdf_path = os.path.join(temp_dir, "cropped.pdf")

        doc = fitz.open(pdf_path)
        cropped_doc = fitz.open()

        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['标题', '内容'])

            current_title = None
            current_content = []

            for i, page in enumerate(doc):
                h = page.rect.height
                top_px = top_cm * 28.35
                bottom_px = bottom_cm * 28.35
                crop_rect = fitz.Rect(page.rect.x0, page.rect.y0 + top_px, page.rect.x1, page.rect.y1 - bottom_px)

                text = page.get_text(clip=crop_rect)

                # 添加裁剪后的页到新PDF
                new_page = cropped_doc.new_page(width=page.rect.width, height=crop_rect.height)
                new_page.show_pdf_page(fitz.Rect(0, 0, page.rect.width, crop_rect.height), doc, i, clip=crop_rect)

                if not text:
                    continue

                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    header = get_smart_header(line)
                    if header:
                        if current_title:
                            writer.writerow([current_title, '\n'.join(clean_content(current_content))])
                        current_title = line
                        current_content = []
                    elif current_title:
                        current_content.append(line)

            if current_title:
                writer.writerow([current_title, '\n'.join(clean_content(current_content))])

        doc.close()
        cropped_doc.save(cropped_pdf_path)
        cropped_doc.close()

        return output_csv, cropped_pdf_path

    except Exception as e:
        return f"❌ 出错：{str(e)}", None


def get_smart_header(line):
    if len(line.strip()) > 50:
        return None
    return line if re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line) else None


def clean_content(lines):
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if cleaned and cleaned[-1][-1] not in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned


with gr.Blocks() as demo:
    gr.Markdown("### 📄 PDF页眉/页尾剪裁 + 标题内容提取工具")

    with gr.Row():
        pdf_input = gr.File(label="上传PDF", file_types=[".pdf"])
        top_cm = gr.Number(value=2, label="页眉裁剪（cm）")
        bottom_cm = gr.Number(value=2, label="页脚裁剪（cm）")

    run_btn = gr.Button("🔍 开始处理")

    csv_output = gr.File(label="提取内容 CSV")
    pdf_output = gr.File(label="裁剪后 PDF")

    run_btn.click(fn=extract_pdf,
                  inputs=[pdf_input, top_cm, bottom_cm],
                  outputs=[csv_output, pdf_output])

demo.queue(concurrency_count=1).launch()
