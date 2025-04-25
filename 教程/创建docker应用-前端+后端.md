基于 **FastAPI 后端 + HTML 静态前端 + Docker 部署** 的 PDF 剪裁与结构提取工具
--
支持上传 PDF、输入页眉页尾裁剪距离，并下载裁剪后的 PDF 和结构化的 CSV 文件。

### 📁 项目结构

```bash
pdf_tool/
├── app.py                  # FastAPI 应用主程序
├── pdf_processor.py        # PDF 剪裁+结构提取逻辑
├── templates/
│   └── index.html          # 静态网页（上传文件和下载结果）
├── static/                 # 静态资源（可留空）
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像构建配置
└── output/                 # 生成文件保存目录（Docker 会挂载）
```

---

### ✅ 1. `requirements.txt`

```txt
fastapi
uvicorn
python-multipart
jinja2
pdfplumber
PyMuPDF
```

---

### ✅ 2. `pdf_processor.py`

```python
import fitz  # PyMuPDF
import pdfplumber
import re
import csv
import os

def process_pdf(pdf_path: str, top_cm: float, bottom_cm: float):
    # 单位换算
    top_px = int(top_cm * 28.35)
    bottom_px = int(bottom_cm * 28.35)

    cropped_path = pdf_path.replace(".pdf", "_cropped.pdf")
    csv_path = pdf_path.replace(".pdf", ".csv")

    # 裁剪 PDF
    doc = fitz.open(pdf_path)
    for page in doc:
        rect = page.rect
        crop_rect = fitz.Rect(rect.x0, rect.y0 + top_px, rect.x1, rect.y1 - bottom_px)
        page.set_cropbox(crop_rect)
    doc.save(cropped_path)
    doc.close()

    # 提取结构化信息
    with open(csv_path, "w", newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["标题", "内容"])

        current_title = None
        current_content = []

        with pdfplumber.open(cropped_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if is_heading(line):
                        if current_title:
                            writer.writerow([current_title, '\n'.join(current_content)])
                        current_title = line
                        current_content = []
                    elif current_title:
                        current_content.append(line)
        if current_title:
            writer.writerow([current_title, '\n'.join(current_content)])

    return cropped_path, csv_path

def is_heading(line):
    if len(line) > 50:
        return False
    return bool(re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line.strip()))
```

---

### ✅ 3. `app.py`

```python
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
```

---

### ✅ 4. `templates/index.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PDF 剪裁工具</title>
</head>
<body>
    <h2>上传 PDF 文件并设置裁剪距离</h2>
    <form action="/process/" enctype="multipart/form-data" method="post">
        <label>PDF 文件：</label>
        <input type="file" name="file" required><br><br>
        <label>页眉剪裁（cm）：</label>
        <input type="number" name="top_cm" step="0.1" value="2.5"><br><br>
        <label>页尾剪裁（cm）：</label>
        <input type="number" name="bottom_cm" step="0.1" value="2.5"><br><br>
        <button type="submit">处理</button>
    </form>

    {% if pdf_path %}
        <h3>处理完成：</h3>
        <a href="/download/?path={{ pdf_path }}">下载裁剪后 PDF</a><br>
        <a href="/download/?path={{ csv_path }}">下载结构化 CSV</a>
    {% endif %}
</body>
</html>
```

---

### ✅ 5. `Dockerfile`

```Dockerfile
FROM python:3.10
WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install pdfplumber jinja2 fastapi uvicorn python-multipart fitz PyMuPDF --trust...(公司源）

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### ✅ 6. 构建并运行 Docker 容器

```bash
# 进入项目目录
cd pdf_tool

# 构建镜像
docker build -t pdf-tool-app .

# 启动容器（指定端口映射）
docker run -d -p 8090:8000 --name pdf_tool_app pdf-tool-app
```

然后访问：
```
http://<你的云服务器IP>:8090/
```

---

### 🧠 提示

- 如需支持大文件上传，可以在 FastAPI 配置中加上传大小限制。
- 你可以设置 `output/` 为挂载卷，方便文件下载。
- 如果后续需要身份验证、用户上传记录等功能可以继续扩展。
