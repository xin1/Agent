from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, shutil
from pdf_processor import process_pdf

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process/")
async def process_pdf_endpoint(
    request: Request,
    file: UploadFile,
    top_cm: float = Form(2.5),
    bottom_cm: float = Form(2.5)
):
    filename = file.filename
    temp_path = f"output/{filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    cropped_pdf, csv_file = process_pdf(temp_path, top_cm, bottom_cm)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "pdf_path": cropped_pdf,
        "csv_path": csv_file
    })

@app.get("/download/")
def download_file(path: str):
    return FileResponse(path, filename=os.path.basename(path), media_type='application/octet-stream')
