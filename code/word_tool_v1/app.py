from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
from typing import List
from io import BytesIO
from convert_doc import convert_doc_to_pdf
from process import process_pdf_and_extract
from preview import generate_preview_image
from zip_util import zip_csvs
from uuid import uuid4
import shutil
import os
from fastapi.responses import JSONResponse
from fastapi import Request
import traceback


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

@app.get("/")
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/preview/")
async def preview(
    file: UploadFile = File(...),
    top_cm: float = Form(...),
    bottom_cm: float = Form(...)
):
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext in ("doc", "docx"):
        # Word 先转换为 PDF，得到文件路径
        pdf_path = convert_doc_to_pdf(file)
        # 直接传路径给 generate_preview_image
        preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
    else:
        # 对 PDF 上传文件
        file_bytes = await file.read()
        preview_path = generate_preview_image((file_bytes), top_cm, bottom_cm)

    return {"preview_path": preview_path}

from io import BytesIO

@app.post("/process_batch/")
async def process_batch(
    files: List[UploadFile] = File(...),
    top_cm: float = Form(...),
    bottom_cm: float = Form(...)
):
    try:
        csv_paths = []

        for file in files:
            ext = file.filename.rsplit(".", 1)[-1].lower()

            if ext in ("doc", "docx"):
                pdf_path = convert_doc_to_pdf(file)
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                csv_path = process_pdf_and_extract(BytesIO(pdf_bytes), top_cm, bottom_cm, filename=file.filename)
            else:
                file_bytes = await file.read()
                csv_path = process_pdf_and_extract(BytesIO(file_bytes), top_cm, bottom_cm, filename=file.filename)

            csv_paths.append(csv_path)

        if len(csv_paths) == 1:
            return JSONResponse(content={"path": csv_paths[0], "is_zip": False})
        else:
            zip_path = zip_csvs(csv_paths)
            return JSONResponse(content={"path": zip_path, "is_zip": True})

    except Exception as e:
        # 打印错误日志方便调试
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "文档处理失败", "detail": str(e)}
        )


@app.get("/download/")
async def download(path: str = Query(..., alias="path")):
    return FileResponse(path, filename=os.path.basename(path))
