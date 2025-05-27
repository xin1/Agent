import fitz
from uuid import uuid4
import os
from fastapi import UploadFile

def generate_preview_image(source, top_cm: float, bottom_cm: float) -> str:
    """
    source: 
      - UploadFile      （file.file.read() 可用）
      - str             （PDF 文件路径）
      - 文件二进制流对象（.read() 可用，如 open(..., "rb")）
    返回：生成的预览 PNG 相对路径
    """
    os.makedirs("outputs", exist_ok=True)

    # 打开 PDF
    if isinstance(source, str):
        pdf = fitz.open(source)
    elif isinstance(source, UploadFile):
        data = source.file
        pdf = fitz.open(stream=data, filetype="pdf")
    else:
        # 任何有 .read() 方法的流
        data = source
        pdf = fitz.open(stream=data, filetype="pdf")

    # 取第11页，不足11页取第二页
    page_num = 10 if pdf.page_count > 10 else 1
    page = pdf.load_page(page_num)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_filename = f"{uuid4().hex}_preview.png"
    preview_path = os.path.join("outputs", preview_filename)
    pix.save(preview_path)

    return preview_path
