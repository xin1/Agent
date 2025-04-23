from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
import fitz  # PyMuPDF
import re, csv, io, zipfile
from tempfile import NamedTemporaryFile

app = FastAPI()

@app.post("/api/process-pdf")
def process_pdf(
    file: UploadFile = File(...),
    top_cm: float = Form(...),
    bottom_cm: float = Form(...)
):
    # 将 cm 转换为 px（近似）
    top_px = int(float(top_cm) * 28.35)
    bottom_px = int(float(bottom_cm) * 28.35)

    # 保存上传的 PDF
    temp_input = NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_input.write(file.file.read())
    temp_input.close()

    # 创建输出 PDF 路径
    cropped_path = temp_input.name.replace('.pdf', '_cropped.pdf')
    csv_path = temp_input.name.replace('.pdf', '_output.csv')

    # 剪裁 PDF
    crop_pdf(temp_input.name, cropped_path, top_px, bottom_px)

    # 提取结构化内容
    extract_to_csv(cropped_path, csv_path, top_px, bottom_px)

    # 打包为 zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        zipf.write(cropped_path, arcname="output_cropped.pdf")
        zipf.write(csv_path, arcname="output.csv")
    zip_buffer.seek(0)

    return StreamingResponse(zip_buffer, media_type="application/zip", headers={
        "Content-Disposition": "attachment; filename=processed_output.zip"
    })


def crop_pdf(input_path, output_path, top_crop, bottom_crop):
    doc = fitz.open(input_path)
    for page in doc:
        rect = page.rect
        page.set_cropbox(fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop))
    doc.save(output_path)
    doc.close()


def extract_to_csv(input_pdf, output_csv, top_crop, bottom_crop):
    doc = fitz.open(input_pdf)
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['标题', '内容'])
        current_title = None
        current_content = []

        def flush():
            if current_title:
                writer.writerow([
                    current_title,
                    '\n'.join(clean_content(current_content))
                ])

        for page in doc:
            rect = page.rect
            crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
            text = page.get_text(clip=crop_rect)
            for line in text.split('\n'):
                line = line.strip()
                if not line: continue
                if is_smart_header(line):
                    flush()
                    current_title = line
                    current_content = []
                elif current_title:
                    current_content.append(line)
        flush()
    doc.close()


def is_smart_header(line):
    if len(line) > 50: return False
    return bool(re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line))

def clean_content(lines):
    result = []
    for line in lines:
        if not line: continue
        if result and not result[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            result[-1] += ' ' + line
        else:
            result.append(line)
    return result
