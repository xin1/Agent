FROM python:3.9-slim

# 安装 LibreOffice 及中文字体等依赖
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-noto-cjk \
    python3-pip \
    poppler-utils \
    && apt-get clean

# 设置 LibreOffice 为 headless 模式
ENV HOME=/tmp

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY ./app /app
COPY ./static /static

WORKDIR /app

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]


下面是一个完整的部署流程和 Python 项目代码，可以**批量将 `.doc` 和 `.docx` 文件转换为 `.pdf` 文件**，适用于 Windows 和 Linux 环境。我们将使用 `python-docx`（仅限读取 `.docx`），`mammoth`（可选美化 HTML），以及 `LibreOffice`（跨平台 doc 转 pdf）或 `win32com.client`（仅限 Windows 上的 Word COM 接口）。

---

## ✅ 1. 依赖环境安装

### ✅ Windows 环境推荐依赖：

```bash
pip install python-docx
pip install comtypes
```

确保你的电脑安装了 Microsoft Word，并配置了 Word 的 COM 接口。

### ✅ Linux 或跨平台依赖：

```bash
sudo apt update
sudo apt install libreoffice
```

---

## ✅ 2. 项目结构示例

```
doc_to_pdf_converter/
├── convert.py          # 主脚本
├── docs/               # 输入的 .doc/.docx 文件
└── output_pdfs/        # 输出的 PDF 文件
```

---

## ✅ 3. 主程序 `convert.py`

我们提供两个方案：**Windows COM 接口方案（支持 `.doc` 和 `.docx`）** 和 **跨平台 LibreOffice 方案**。

---

### ✅ 方案一：Windows Word COM 批量转换（推荐 Windows 用户）

```python
import os
import comtypes.client

def convert_to_pdf_windows(input_path, output_path):
    word = comtypes.client.CreateObject('Word.Application')
    word.Visible = False

    for filename in os.listdir(input_path):
        if filename.endswith(".doc") or filename.endswith(".docx"):
            doc_path = os.path.join(input_path, filename)
            pdf_filename = os.path.splitext(filename)[0] + ".pdf"
            pdf_path = os.path.join(output_path, pdf_filename)
            try:
                doc = word.Documents.Open(doc_path)
                doc.SaveAs(pdf_path, FileFormat=17)
                doc.Close()
                print(f"Converted: {filename} -> {pdf_filename}")
            except Exception as e:
                print(f"Failed to convert {filename}: {e}")
    word.Quit()

if __name__ == "__main__":
    input_dir = "docs"
    output_dir = "output_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    convert_to_pdf_windows(input_dir, output_dir)
```

---

### ✅ 方案二：Linux/macOS/跨平台 LibreOffice 转换（推荐服务器/容器部署）

```python
import os
import subprocess

def convert_to_pdf_libreoffice(input_path, output_path):
    for filename in os.listdir(input_path):
        if filename.endswith(".doc") or filename.endswith(".docx"):
            doc_path = os.path.join(input_path, filename)
            try:
                subprocess.run([
                    'libreoffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', output_path,
                    doc_path
                ], check=True)
                print(f"Converted: {filename}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to convert {filename}: {e}")

if __name__ == "__main__":
    input_dir = "docs"
    output_dir = "output_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    convert_to_pdf_libreoffice(input_dir, output_dir)
```

---

## ✅ 4. 使用方法

将你的 `.doc` 和 `.docx` 文件放到 `docs/` 目录下，然后运行：

* **Windows 用户：**

```bash
python convert.py
```

* **Linux/macOS 用户（需安装 libreoffice）：**

```bash
python convert.py
```

---

## ✅ 5. Docker 方式部署（可选）

如你希望部署到服务器并使用 Docker，提供一个简单的 Dockerfile 示例（基于 LibreOffice）：

```Dockerfile
FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y libreoffice python3 python3-pip && \
    pip3 install --no-cache-dir python-docx

WORKDIR /app
COPY . /app

CMD ["python3", "convert.py"]
```

---

如你希望我打包一个压缩好的示例项目（ZIP）或者加上 Flask/FastAPI 接口用于上传并转换，我也可以继续补充。是否需要？


明白了，我将构建一个完整的 Docker 容器版 PDF 结构提取工具，支持上传 `.doc` 和 `.docx` 文件，使用纯 Python 工具（不依赖 LibreOffice）转换为 PDF，并无缝集成到你现有的裁剪 + CSV 提取流程中。稍后我会提供完整的项目结构和代码，便于你直接部署。


# PDF Cropping and Structure Extraction Tool

This project provides a web-based tool for uploading `.pdf`, `.doc`, and `.docx` files and processing them in a Docker container. It converts Word files to PDF using Microsoft Word automation, applies top/bottom cropping, extracts structured text, and returns CSV output. The backend is implemented with FastAPI, and a simple HTML/JavaScript frontend handles file upload, cropping parameters, progress display, and download links.

## Features

* **Multi-file Upload:** Supports uploading multiple `.pdf`, `.doc`, and `.docx` files simultaneously.
* **Word→PDF Conversion:** Converts `.doc` and `.docx` to PDF using pure Python (comtypes + MS Word).
* **PDF Cropping:** Crops the top and bottom margins of PDF pages by specified distances (in points).
* **Structured Extraction:** Extracts text from the cropped PDF and saves it as CSV (page number + text lines).
* **User Interface:** Frontend with multi-file upload form, crop settings, progress indicator, and download links.
* **FastAPI Backend:** All logic is integrated into FastAPI, serving endpoints for upload, status, and download.
* **Containerized Deployment:** Includes `Dockerfile` and `requirements.txt` for easy container build and deployment.

## Project Structure

The repository is organized as follows:

```
pdf_tool/
├── main.py           # FastAPI application and endpoints
├── word2pdf.py       # Word→PDF conversion (comtypes + MS Word)
├── crop.py           # PDF cropping (PyMuPDF)
├── extract.py        # Text extraction to CSV (pdfplumber)
├── static/
│   └── index.html    # Frontend HTML/JS page
├── requirements.txt  # Python dependencies
└── Dockerfile        # Docker container setup
```

* **main.py** – FastAPI application defining the HTTP endpoints (`/upload`, `/status`, `/download`) and background processing.
* **word2pdf.py** – Module using `comtypes` to automate MS Word and save `.doc/.docx` as PDF.
* **crop.py** – Uses PyMuPDF to crop each PDF page by setting its `cropbox`.
* **extract.py** – Uses `pdfplumber` to extract text from each page of the (cropped) PDF and write to CSV.
* **static/index.html** – Frontend page with a form for file upload and crop settings, plus embedded JavaScript for processing.
* **Dockerfile** & **requirements.txt** – For building a Docker image (Windows container with Python and Word).

## Backend Code

Below are the backend Python modules. The main FastAPI app (`main.py`) integrates file upload, conversion, cropping, extraction, and result serving:

```python
# main.py
import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from word2pdf import convert_doc_to_pdf
from crop import crop_pdf
from extract import extract_pdf_to_csv

app = FastAPI()
# Serve static files (HTML/JS) from the "static" directory
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# In-memory store for job status
jobs = {}

@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    top: int = Form(...),
    bottom: int = Form(...)
):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join("jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)
    file_paths = []

    # Save uploaded files to the job directory
    for uploaded_file in files:
        file_path = os.path.join(job_dir, uploaded_file.filename)
        contents = await uploaded_file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        file_paths.append(file_path)

    # Initialize job status
    jobs[job_id] = {"status": "processing", "done": 0, "total": len(file_paths), "files": []}
    # Launch background processing
    background_tasks.add_task(process_job, job_id, file_paths, top, bottom)
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return {
        "status": job["status"],
        "done": job["done"],
        "total": job["total"],
        "files": job["files"]
    }

@app.get("/download/{job_id}/{filename}")
async def download_result(job_id: str, filename: str):
    result_path = os.path.join("jobs", job_id, "results", filename)
    if os.path.exists(result_path):
        return FileResponse(path=result_path, media_type='text/csv', filename=filename)
    else:
        return JSONResponse({"error": "File not found"}, status_code=404)

def process_job(job_id: str, file_paths: list, top: int, bottom: int):
    job = jobs[job_id]
    results_dir = os.path.join("jobs", job_id, "results")
    os.makedirs(results_dir, exist_ok=True)
    result_files = []

    for file_path in file_paths:
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)

        # 1. Convert .doc/.docx to PDF if necessary
        if ext.lower() in [".doc", ".docx"]:
            pdf_path = os.path.join(os.path.dirname(file_path), f"{name}.pdf")
            convert_doc_to_pdf(file_path, pdf_path)
        else:
            pdf_path = file_path

        # 2. Crop the PDF (top/bottom)
        cropped_path = os.path.join(os.path.dirname(file_path), f"{name}_cropped.pdf")
        crop_pdf(pdf_path, cropped_path, top, bottom)

        # 3. Extract structured text to CSV
        csv_filename = f"{name}.csv"
        csv_path = os.path.join(results_dir, csv_filename)
        extract_pdf_to_csv(cropped_path, csv_path)

        result_files.append(csv_filename)
        job["done"] += 1

    job["files"] = result_files
    job["status"] = "completed"
```

**Modules for conversion and processing:**

```python
# word2pdf.py
from comtypes import CoInitialize, CoUninitialize
import comtypes.client

def convert_doc_to_pdf(input_path: str, output_path: str):
    """
    Convert a Word .doc/.docx file to PDF using MS Word automation.
    This uses comtypes to automate Word (FileFormat=17 for PDF).
    """
    CoInitialize()
    word = comtypes.client.CreateObject('Word.Application')
    word.Visible = False
    word.DisplayAlerts = False
    doc = word.Documents.Open(input_path)
    doc.SaveAs(output_path, FileFormat=17)
    doc.Close()
    word.Quit()
    CoUninitialize()
```

```python
# crop.py
import fitz  # PyMuPDF

def crop_pdf(input_path: str, output_path: str, top: int, bottom: int):
    """
    Crop the top and bottom margins of each page in a PDF.
    Uses PyMuPDF: set_cropbox(Rect) defines the visible area.
    """
    doc = fitz.open(input_path)
    for page in doc:
        rect = page.rect
        # Define new rectangle, cropping 'top' points from the top and 'bottom' points from the bottom
        new_rect = fitz.Rect(rect.x0, rect.y0 + bottom, rect.x1, rect.y1 - top)
        page.set_cropbox(new_rect)
    doc.save(output_path)
```

```python
# extract.py
import pdfplumber
import csv

def extract_pdf_to_csv(input_pdf: str, output_csv: str):
    """
    Extract text from each page of the PDF and write to a CSV file.
    Each row contains (page number, text line).
    """
    with pdfplumber.open(input_pdf) as pdf:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["page", "text"])
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    for line in text.splitlines():
                        writer.writerow([i, line])
```

## Frontend (HTML/JS)

The frontend is a single HTML page (`static/index.html`) with embedded JavaScript. It provides a form for uploading files and setting crop margins. Upon submission, it sends the files and parameters to the `/upload` endpoint, then polls `/status` for progress. When processing is complete, it displays download links for the resulting CSV files.

```html
<!-- static/index.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PDF Cropping and Extraction Tool</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        #progress { margin-top: 10px; }
        #links a { display: block; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>PDF Cropping and Structure Extraction Tool</h1>
    <form id="upload-form">
        <label>Top crop (points): <input type="number" id="top" value="0"></label><br>
        <label>Bottom crop (points): <input type="number" id="bottom" value="0"></label><br>
        <input type="file" id="files" multiple><br><br>
        <button type="button" onclick="startProcessing()">Start</button>
    </form>
    <div id="progress"></div>
    <div id="links"></div>

    <script>
    async function startProcessing() {
        const filesInput = document.getElementById('files');
        const files = filesInput.files;
        const top = document.getElementById('top').value || 0;
        const bottom = document.getElementById('bottom').value || 0;
        const formData = new FormData();
        formData.append('top', top);
        formData.append('bottom', bottom);
        for (let file of files) {
            formData.append('files', file);
        }
        // Upload files to backend
        let res = await fetch('/upload', { method: 'POST', body: formData });
        let data = await res.json();
        let jobId = data.job_id;
        document.getElementById('progress').innerText = 'Job ID: ' + jobId;

        // Poll status endpoint
        let progressDiv = document.getElementById('progress');
        let linksDiv = document.getElementById('links');
        let interval = setInterval(async () => {
            let statusRes = await fetch(`/status/${jobId}`);
            let status = await statusRes.json();
            progressDiv.innerText = `Processed: ${status.done} / ${status.total}`;
            if (status.status === 'completed') {
                clearInterval(interval);
                // Display download links for each CSV
                status.files.forEach(filename => {
                    let a = document.createElement('a');
                    a.href = `/download/${jobId}/${encodeURIComponent(filename)}`;
                    a.innerText = `Download ${filename}`;
                    linksDiv.appendChild(a);
                });
            }
        }, 1000);
    }
    </script>
</body>
</html>
```

## Dockerfile and Deployment

Below is a `Dockerfile` and `requirements.txt` suitable for building the application in a container. We use a Windows Server Core image with Python. **Note:** Microsoft Word must be installed in the container for the `.doc/.docx`→PDF conversion to work.

```dockerfile
# Dockerfile (Windows container with Python and MS Word)
FROM python:3.9-windowsservercore-ltsc2022

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . /app

# Note: Ensure Microsoft Word is installed in this container for DOCX->PDF conversion
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```text
# requirements.txt
fastapi
uvicorn
python-multipart
PyMuPDF
pdfplumber
comtypes
pdfminer.six
```

To build and run the Docker container:

1. **Build the image:**

   ```bash
   docker build -t pdf_tool .
   ```
2. **Run the container (port 8000):**

   ```bash
   docker run -p 8000:8000 pdf_tool
   ```

After deployment, visit `http://localhost:8000/` in a browser to use the upload interface.

This solution uses `comtypes` to automate MS Word for PDF conversion, PyMuPDF’s `set_cropbox` for cropping, and FastAPI’s static file mounting for the frontend, all integrated into a seamless application.

**References:** The conversion and processing steps follow examples from the `comtypes` Word automation guide, PyMuPDF documentation on cropping, and FastAPI’s static files tutorial.
