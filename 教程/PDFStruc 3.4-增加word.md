以下是完整的基于 Docker 构建的 PDF 和 Word 文件结构化提取工具，支持 `.doc`、`.docx` 和 `.pdf`，使用 LibreOffice 进行 Word → PDF 转换，具备 CSV 输出、预览图生成、静态前端等功能。

---

### 📁 项目结构

```
pdf_tool_app/
├── app.py              # FastAPI 主应用入口
├── process.py          # 核心处理逻辑（PDF/Word→结构提取→CSV）
├── preview.py          # 页面预览图生成模块
├── zip_util.py         # 多文件打包下载支持
├── static/
│   ├── index.html      # 简洁前端页面
│   └── style.css
├── outputs/            # 生成的 CSV 与预览图自动存放
├── Dockerfile          # 构建 Docker 镜像
└── requirements.txt    # Python 依赖列表
```

---

## ✅ 1. `app.py`

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from process import handle_file
from zip_util import zip_outputs

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    output_path = handle_file(file)
    return {"message": "Processed", "csv": f"/outputs/{output_path}"}

@app.get("/download-zip/")
async def download_zip():
    zip_path = zip_outputs()
    return FileResponse(zip_path, filename="outputs.zip", media_type="application/zip")
```

---

## ✅ 2. `process.py`

```python
import os
import uuid
import fitz  # PyMuPDF
from PyPDF2 import PdfReader
import csv
import subprocess

def convert_word_to_pdf(input_path, output_path):
    subprocess.run([
        "libreoffice", "--headless", "--convert-to", "pdf", "--outdir",
        os.path.dirname(output_path), input_path
    ])

def extract_pdf_structure(pdf_path, csv_path):
    reader = PdfReader(pdf_path)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Page", "Content"])
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            writer.writerow([i+1, text.strip()])

def generate_preview(pdf_path, preview_path):
    doc = fitz.open(pdf_path)
    if doc.page_count > 0:
        pix = doc[0].get_pixmap()
        pix.save(preview_path)

def handle_file(file):
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    file_ext = file.filename.split(".")[-1].lower()
    file_id = str(uuid.uuid4())
    input_path = f"outputs/{file_id}.{file_ext}"
    with open(input_path, "wb") as f:
        f.write(file.file.read())

    # Word 转 PDF
    if file_ext in ["doc", "docx"]:
        pdf_path = input_path.replace(f".{file_ext}", ".pdf")
        convert_word_to_pdf(input_path, pdf_path)
    elif file_ext == "pdf":
        pdf_path = input_path
    else:
        return "Unsupported file"

    # 提取结构并生成 CSV 和预览
    csv_path = pdf_path.replace(".pdf", ".csv")
    preview_path = pdf_path.replace(".pdf", ".png")
    extract_pdf_structure(pdf_path, csv_path)
    generate_preview(pdf_path, preview_path)
    return os.path.basename(csv_path)
```

---

## ✅ 3. `preview.py`（可选，已整合入 process.py）

如需拆出单独模块可保留。

---

## ✅ 4. `zip_util.py`

```python
import os
import zipfile

def zip_outputs():
    zip_path = "outputs/outputs.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for filename in os.listdir("outputs"):
            if filename.endswith(".csv") or filename.endswith(".png"):
                zf.write(os.path.join("outputs", filename), filename)
    return zip_path
```

---

## ✅ 5. `static/index.html`

```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>PDF & Word 结构提取</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h2>上传 Word / PDF 文档</h2>
    <input type="file" id="fileInput">
    <button onclick="upload()">上传并处理</button>
    <div id="result"></div>

    <script>
        async function upload() {
            const file = document.getElementById("fileInput").files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch("/upload/", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            document.getElementById("result").innerHTML = `
                <p>处理完成！</p>
                <a href="${data.csv}" target="_blank">下载 CSV</a><br>
                <img src="${data.csv.replace('.csv', '.png')}" width="300">
                <br><a href="/download-zip/">下载全部输出</a>
            `;
        }
    </script>
</body>
</html>
```

---

## ✅ 6. `static/style.css`

```css
body {
    font-family: sans-serif;
    padding: 2em;
    background-color: #f8f8f8;
}
button {
    margin-top: 10px;
}
img {
    margin-top: 15px;
    border: 1px solid #ccc;
}
```

---

## ✅ 7. `requirements.txt`

```
fastapi
uvicorn
python-multipart
PyPDF2
PyMuPDF
```

---

## ✅ 8. `Dockerfile`

```dockerfile
FROM python:3.10-slim

# 安装 LibreOffice 和依赖
RUN apt-get update && \
    apt-get install -y libreoffice && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 拷贝代码
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建输出目录
RUN mkdir -p outputs

# 启动服务
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

## 🚀 启动容器构建与运行

```bash
docker build -t pdfstruc .
docker run -p 7860:7860 -v $(pwd)/outputs:/app/outputs pdfstruc
```

然后访问：

```
http://localhost:7860
```

---

如需支持中文字体识别更好，推荐在 `Dockerfile` 中额外加：

```dockerfile
RUN apt-get install -y fonts-noto-cjk
```

---

如需我为你生成 GitHub 项目、压缩包或提供 Docker Hub 镜像发布建议，也可以继续告诉我。
