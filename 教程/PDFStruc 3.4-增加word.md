```
# 替换 APT 源
RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y libreoffice --fix-missing && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

```
```
FROM python:3.9-slim

# 安装 LibreOffice 和依赖
RUN apt-get update && apt-get install -y libreoffice && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 拷贝项目代码
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置 LibreOffice 命令别名
ENV PATH="/usr/bin/libreoffice:${PATH}"

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

```
好的，以下是完整的 **支持 `.doc`、`.docx` 和 `.pdf`** 的结构化提取工具（PDFStruc），包括：

* ✅ Docker 容器（Windows Server Core）；
* ✅ 安装 LibreOffice（用于将 Word 转为 PDF）；
* ✅ FastAPI 后端处理上传、转换、提取与 CSV 导出；
* ✅ 前端页面支持上传、预览与下载结构化 CSV。

---

## ✅ 一、项目结构

```
pdfstruc/
├── app/
│   ├── main.py                # FastAPI 主入口
│   ├── convert_doc.py         # Word 转 PDF
│   ├── extract_pdf.py         # PDF 内容结构提取为 CSV
│   └── utils.py               # 工具函数
├── static/
│   └── index.html             # 前端页面
├── requirements.txt           # Python 依赖
└── Dockerfile                 # Docker 配置
```

---

## 📄 `requirements.txt`

```txt
fastapi
uvicorn
python-docx
pdfplumber
pypdf
python-multipart
jinja2
```

---

## 🐳 `Dockerfile`（基于 Windows Server Core）

```Dockerfile
# 使用 Windows 容器基础镜像
FROM python:3.9-windowsservercore-ltsc2022

WORKDIR /app

# 安装 LibreOffice（静默模式）
ADD https://download.documentfoundation.org/libreoffice/stable/7.6.4/win/x86_64/LibreOffice_7.6.4_Win_x64.msi libreoffice.msi
RUN msiexec /i libreoffice.msi /quiet /norestart && del libreoffice.msi

# 环境变量配置
ENV PATH="C:\\Program Files\\LibreOffice\\program;${PATH}"

# 拷贝文件
COPY ./app /app
COPY ./static /app/static
COPY requirements.txt .

# 安装依赖
RUN pip install -r requirements.txt

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧠 `app/convert_doc.py`：Word 转 PDF

```python
import os
import subprocess

def convert_to_pdf(input_path: str, output_dir: str) -> str:
    """
    使用 LibreOffice 将 Word 文档转换为 PDF
    """
    output_path = os.path.join(output_dir, os.path.splitext(os.path.basename(input_path))[0] + ".pdf")
    command = [
        "soffice", "--headless", "--convert-to", "pdf",
        "--outdir", output_dir, input_path
    ]
    subprocess.run(command, check=True)
    return output_path
```

---

## 📄 `app/extract_pdf.py`：提取结构化内容为 CSV

```python
import pdfplumber
import csv
import os

def extract_pdf_structure(pdf_path: str, csv_path: str):
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                for line in text.split("\n"):
                    rows.append([f"Page {page_num}", line.strip()])

    with open(csv_path, "w", newline='', encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Page", "Content"])
        writer.writerows(rows)
```

---

## ⚙️ `app/utils.py`：文件保存工具

```python
import os
import uuid

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_upload_file(upload_file) -> str:
    file_ext = os.path.splitext(upload_file.filename)[-1]
    file_id = str(uuid.uuid4()) + file_ext
    file_path = os.path.join(UPLOAD_DIR, file_id)
    with open(file_path, "wb") as f:
        f.write(upload_file.file.read())
    return file_path
```

---

## 🚀 `app/main.py`：FastAPI 主接口

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from convert_doc import convert_to_pdf
from extract_pdf import extract_pdf_structure
from utils import save_upload_file, OUTPUT_DIR
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    uploaded_path = save_upload_file(file)

    ext = os.path.splitext(uploaded_path)[-1].lower()
    if ext in [".doc", ".docx"]:
        pdf_path = convert_to_pdf(uploaded_path, OUTPUT_DIR)
    elif ext == ".pdf":
        pdf_path = uploaded_path
    else:
        return {"error": "Unsupported file type."}

    csv_path = os.path.join(OUTPUT_DIR, os.path.splitext(os.path.basename(pdf_path))[0] + ".csv")
    extract_pdf_structure(pdf_path, csv_path)

    return {"csv_url": f"/download/{os.path.basename(csv_path)}"}

@app.get("/download/{filename}")
def download_csv(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    return FileResponse(path, media_type="text/csv", filename=filename)
```

---

## 🌐 `static/index.html`：前端页面

```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>PDFStruc 上传工具</title>
</head>
<body>
    <h2>上传 .doc / .docx / .pdf 文件</h2>
    <form id="upload-form" enctype="multipart/form-data">
        <input type="file" name="file" accept=".pdf,.doc,.docx" required>
        <button type="submit">上传并提取</button>
    </form>
    <div id="result"></div>

    <script>
        document.getElementById("upload-form").addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const res = await fetch("/upload/", {
                method: "POST",
                body: formData
            });
            const json = await res.json();
            if (json.csv_url) {
                document.getElementById("result").innerHTML =
                    `<p>提取完成！<a href="${json.csv_url}" target="_blank">点击下载 CSV</a></p>`;
            } else {
                document.getElementById("result").innerText = "处理失败：" + JSON.stringify(json);
            }
        });
    </script>
</body>
</html>
```

---

## 🧪 使用方式

1. 将上述结构保存到文件夹 `pdfstruc/`
2. 在该目录中打开命令行，构建镜像：

```bash
docker build -t pdfstruc .
```

3. 运行容器：

```bash
docker run -p 8000:8000 pdfstruc
```

4. 访问：`http://localhost:8000` 上传 `.doc` / `.docx` / `.pdf` 文件，提取结构化内容并下载 CSV。

---

如你需要打包多个文档、增加剪裁或更复杂的结构提取（比如基于标题层级生成知识图谱），我可以继续扩展这套框架。需要我加上压缩下载、多文件上传、结构化智能提取等功能吗？
