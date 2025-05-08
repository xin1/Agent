from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from process import process_pdf_and_extract
from preview import generate_preview_image
from zip_util import zip_csvs

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
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
    return {"preview_path": preview_path}

@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        csv_path = process_pdf_and_extract(file, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}

@app.get("/download/")
async def download(path: str):
    return FileResponse(path, filename=os.path.basename(path))
