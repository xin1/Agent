下面是一个完整的项目目录和关键代码结构，用于构建支持 `.pdf`, `.doc`, `.docx` 文件上传、Word 转 PDF、裁剪正文、结构化提取并导出 CSV 的系统。功能包括：

* 上传支持 PDF / Word 文件；
* Word 自动转换为 PDF（使用 LibreOffice）；
* 可配置裁剪顶部/底部；
* 输出结构化 CSV；
* 使用 UUID 处理临时文件但最终下载名保留原始文件名；
* 可部署于 Docker 容器中。

---

### 🗂️ 项目目录结构（假设项目名为 `pdf_tool_app/`）

```
pdf_tool_app/
├── app.py                     # FastAPI 启动入口
├── process.py                 # 主处理逻辑（裁剪+结构化提取）
├── convert_doc.py            # Word → PDF 转换逻辑
├── preview.py                # 裁剪预览图生成（可选）
├── zip_util.py               # 打包多个 CSV 文件的工具
├── file_utils.py             # 处理文件名、保存上传、生成UUID等
├── outputs/                  # 输出目录（CSV、PDF）
├── uploads/                  # 上传文件暂存目录
├── static/                   # 前端 HTML/CSS/JS
│   └── index.html
├── Dockerfile
└── requirements.txt
```

---

### 📄 `app.py`（FastAPI 接口示例）

```python
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
from process import process_pdf_and_extract
from file_utils import save_upload_file, get_original_name
import os

app = FastAPI()

@app.post("/process/")
async def process_file(file: UploadFile, top_cm: float = Form(1), bottom_cm: float = Form(1)):
    uuid_name, original_name, local_path = await save_upload_file(file)

    # 结构化提取
    csv_path = process_pdf_and_extract(local_path, top_cm, bottom_cm)

    # 还原原始文件名（加 .csv）
    download_name = get_original_name(original_name) + ".csv"
    return FileResponse(csv_path, filename=download_name, media_type='text/csv')
```

---

### 📄 `file_utils.py`（保存文件、生成 UUID、记录原名）

```python
import os
import shutil
import uuid

UPLOAD_DIR = "uploads/"
OUTPUT_DIR = "outputs/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in " ._-()" else "_" for c in name)

async def save_upload_file(file):
    original_name = os.path.splitext(file.filename)[0]
    safe_name = sanitize_filename(original_name)
    ext = os.path.splitext(file.filename)[-1].lower()
    uid = uuid.uuid4().hex

    filename = f"{uid}_{safe_name}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 统一转为 PDF
    if ext in (".doc", ".docx"):
        from convert_doc import convert_doc_to_pdf
        pdf_path = convert_doc_to_pdf(file_path)
        return uid, safe_name, pdf_path
    else:
        return uid, safe_name, file_path

def get_original_name(safe_name):
    return safe_name.strip().replace(" ", "_")
```

---

### 📄 `convert_doc.py`（调用 LibreOffice 转 PDF）

```python
import subprocess
import os

def convert_doc_to_pdf(input_path):
    output_dir = os.path.dirname(input_path)
    subprocess.run([
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        input_path
    ], check=True)

    base = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(output_dir, base + ".pdf")
```

---

### 📄 `process.py`（PDF 裁剪与结构提取）

```python
import fitz  # PyMuPDF
import csv
import re
import os
from uuid import uuid4

def process_pdf_and_extract(pdf_path, top_cm, bottom_cm):
    pdf = fitz.open(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    csv_path = os.path.join("outputs", f"{uuid4().hex}_{base_name}.csv")

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)

        for b in sorted(blocks, key=lambda b: (b[1], b[0])):
            text = b[4].strip()
            if not text:
                continue
            m = heading_pattern.match(text)
            if m:
                current_heading = f"{m.group(1)} {m.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for h, c in content_dict.items():
            writer.writerow([h, c.strip()])

    return csv_path
```

---

### 📄 `Dockerfile` 示例

```dockerfile
FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y libreoffice poppler-utils && \
    pip install fastapi uvicorn python-multipart PyMuPDF

WORKDIR /app
COPY . /app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 📄 `static/index.html`（可选：用于上传文件的简单页面）

```html
<!DOCTYPE html>
<html>
<head><title>PDF/Word 结构化提取</title></head>
<body>
  <h2>上传 PDF 或 Word 文件</h2>
  <form action="/process/" method="post" enctype="multipart/form-data">
    文件: <input type="file" name="file"><br>
    裁剪上边距（cm）: <input type="number" name="top_cm" value="1"><br>
    裁剪下边距（cm）: <input type="number" name="bottom_cm" value="1"><br>
    <input type="submit" value="上传并提取">
  </form>
</body>
</html>
```

---

### ✅ 注意事项

1. LibreOffice 必须已安装，确保 `libreoffice` 命令在容器或主机中可用；
2. 所有路径中均保留 UUID 前缀确保唯一性，但下载名用原始文件名；
3. 对中文、空格、特殊字符已进行转义和清洗，避免路径/下载出错；
4. 你也可以添加 `/preview/` 接口，生成图片预览。

---

如需我将此结构打包为完整项目或 Docker 镜像配置进一步完善，欢迎继续告诉我！

为支持“记录原始文件名并在 CSV 下载时恢复”，同时避免中文、空格或特殊字符造成的处理和下载异常，推荐采用以下完整方案：

---

## ✅ 总体设计目标

1. 上传文件时保存其原始名称（含中文、空格等）。
2. 中间处理过程使用 `uuid` 命名，避免文件名冲突。
3. 下载 CSV 时将原始名称还原为下载名，自动加 `.csv` 后缀。
4. 所有文件路径采用安全编码（避免系统路径错误）。

---

## ✅ 1. 路由入口（FastAPI 示例：`app.py`）

```python
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
from uuid import uuid4
import os
import shutil
import urllib.parse

from process import process_pdf_and_extract

app = FastAPI()

# 保存上传文件并处理
@app.post("/process/")
async def process(file: UploadFile, top_cm: float = Form(0), bottom_cm: float = Form(0)):
    # 保存上传原始名
    original_name = file.filename
    base_name = os.path.splitext(original_name)[0]
    ext = os.path.splitext(original_name)[-1].lower()

    # 安全处理文件路径（避免特殊字符）
    safe_id = uuid4().hex
    safe_dir = f"/tmp/{safe_id}"
    os.makedirs(safe_dir, exist_ok=True)

    safe_file_path = os.path.join(safe_dir, "input" + ext)
    with open(safe_file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 处理逻辑
    csv_path = process_pdf_and_extract(safe_file_path, top_cm, bottom_cm)

    # 将 CSV 暂存位置与原始名关联（保存在 dict 或数据库中）
    final_name = f"{base_name}.csv"
    return {"download_path": f"/download/?path={urllib.parse.quote(csv_path)}&name={urllib.parse.quote(final_name)}"}
```

---

## ✅ 2. 下载接口（统一原始名）

```python
@app.get("/download/")
def download_csv(path: str, name: str):
    safe_path = urllib.parse.unquote(path)
    safe_name = urllib.parse.unquote(name)

    if not os.path.exists(safe_path):
        return {"error": "文件不存在"}

    # 返回带原始文件名的响应
    return FileResponse(
        path=safe_path,
        filename=safe_name,
        media_type="text/csv"
    )
```

---

## ✅ 3. `process_pdf_and_extract.py`（关键处理逻辑）

```python
import fitz
import re
import csv
import os
from uuid import uuid4
from convert_doc import convert_doc_to_pdf

def process_pdf_and_extract(input_path, top_cm, bottom_cm):
    ext = os.path.splitext(input_path)[-1].lower()

    if ext in (".doc", ".docx"):
        input_path = convert_doc_to_pdf(input_path)  # 返回 PDF 路径

    pdf = fitz.open(input_path)

    # 用 uuid 命名处理后的 CSV 文件
    csv_path = f"/tmp/{uuid4().hex}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)

        for b in sorted(blocks, key=lambda b: (b[1], b[0])):
            text = b[4].strip()
            if not text: continue
            m = heading_pattern.match(text)
            if m:
                current_heading = f"{m.group(1)} {m.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for h, c in content_dict.items():
            writer.writerow([h, c.strip()])

    return csv_path
```

---

## ✅ 4. `convert_doc_to_pdf.py`（Word转PDF）

```python
import subprocess
import os

def convert_doc_to_pdf(input_path):
    output_dir = os.path.dirname(input_path)
    subprocess.run([
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", output_dir, input_path
    ], check=True)
    
    base = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(output_dir, base + ".pdf")
```

---

## ✅ 5. Dockerfile 补充（LibreOffice）

确保 LibreOffice 安装：

```dockerfile
RUN apt-get update && apt-get install -y libreoffice
```

---

## ✅ 推荐优化（可选）

* 上传后立即清洗特殊字符（如 `/ \ ? : *`）或统一用 URL 编码处理。
* 加入 Redis 或 SQLite 映射 `uuid -> 原始文件名`，支持持久下载名恢复。
* 自动清理 `/tmp` 中的临时文件。

---

如需我帮助你直接生成完整目录和文件结构，我也可以一键输出部署版本。是否需要？

可以，我们可以完全不用 `file.file.read()` 或 `_io.BufferedReader` 的 `.file` 属性，**也不用传 `file` 对象**。直接通过保存为本地 `.pdf` 或 `.docx` 文件路径来处理，非常清晰可靠。

---

## ✅ 方法：全部转本地文件处理流程（推荐）

### 🌟目标：

* 不再从内存 `UploadFile.file.read()` 读取。
* 上传后立即保存为 `.pdf`（若是 Word 先转换），然后传本地路径给 `generate_preview_image(path: str, ...)`。
* `preview.py` 使用 `fitz.open(path)` 读取路径。

---

## ✅ 修改方案一览

### 1. ✅ `preview.py`：只接受 PDF 路径

```python
# preview.py
import fitz
from uuid import uuid4
import os

def generate_preview_image(pdf_path: str, top_cm: float, bottom_cm: float) -> str:
    os.makedirs("outputs", exist_ok=True)
    pdf = fitz.open(pdf_path)  # ← 打开路径
    page = pdf.load_page(0)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_filename = f"{uuid4().hex}_preview.png"
    preview_path = os.path.join("outputs", preview_filename)
    pix.save(preview_path)

    return preview_path
```

---

### 2. ✅ `app.py`：预览端点使用保存路径

```python
from fastapi import FastAPI, File, UploadFile, Form
from convert_doc import convert_doc_to_pdf
from preview import generate_preview_image
import os
import shutil
from uuid import uuid4

app = FastAPI()

@app.post("/preview/")
async def preview(file: UploadFile = File(...),
                  top_cm: float = Form(...),
                  bottom_cm: float = Form(...)):
    os.makedirs("uploads", exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename_base = uuid4().hex
    save_path = os.path.join("uploads", f"{filename_base}.{ext}")

    # 保存上传文件到本地
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 如果是 Word 文件，转换为 PDF
    if ext in ("doc", "docx"):
        pdf_path = convert_doc_to_pdf(save_path)
    else:
        pdf_path = save_path  # 已是 PDF

    # 用路径生成预览
    preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
    return {"preview_path": preview_path}
```

---

### 3. ✅ `convert_doc.py`：接受文件路径并返回 `.pdf` 路径

```python
# convert_doc.py
import subprocess
import os

def convert_doc_to_pdf(doc_path: str) -> str:
    output_dir = os.path.dirname(doc_path)
    subprocess.run([
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        doc_path
    ], check=True)

    base = os.path.splitext(doc_path)[0]
    return base + ".pdf"
```

---

## 🔁 说明

* 上传 `.doc/.docx/.pdf` → 保存在 `uploads/`；
* Word 转 PDF 后直接读取路径，不使用 `file.read()`；
* 预览使用 `fitz.open(pdf_path)`，避免 `_io.BufferedReader` 错误；
* 逻辑清晰、易调试、兼容本地部署与 Docker 容器。

---

## ✅ 总结

**完全不用 `file.file` 或 `file.read()`，只操作本地路径文件。**
这也是服务器或容器部署中最稳定、最不出错的做法。

是否需要我为你整理完整目录结构和文件？或者直接提供 Dockerfile 一起运行测试？

为了实现上传时用 `uuid` 命名中间文件、但最终下载的 CSV 保留原始 Word 或 PDF 文件名的逻辑，这里是完整整合方案：

---

### ✅ 核心改动目标

1. **上传时文件重命名为 UUID**：避免特殊字符、空格干扰；
2. **内部处理统一使用 UUID 文件名**；
3. **结果 CSV 使用原始文件名输出**；
4. **支持 PDF、Word（.doc/.docx）**，中间自动转 PDF。

---

### ✅ 示例整合代码（`app.py` 伪完整形式）

```python
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
import os, shutil, uuid, fitz, csv, re
from convert_doc import convert_doc_to_pdf  # 你已有的转换逻辑

app = FastAPI()

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def sanitize_filename(name):
    # 仅保留中文、英文、数字、点和下划线
    return re.sub(r'[^\u4e00-\u9fa5\w.-]', '_', name)


def extract_pdf_to_csv(pdf_path, original_filename, top_cm, bottom_cm):
    pdf = fitz.open(pdf_path)
    heading_pattern = re.compile(r'^(\\d+(\\.\\d+)*)(\\s+)(.+)')
    content_dict = {}
    current_heading = None

    for page in pdf:
        rect = page.rect
        clip = fitz.Rect(rect.x0, rect.y0 + top_cm * 28.35, rect.x1, rect.y1 - bottom_cm * 28.35)
        blocks = page.get_text("blocks", clip=clip)
        for b in sorted(blocks, key=lambda b: (b[1], b[0])):
            text = b[4].strip()
            if not text:
                continue
            m = heading_pattern.match(text)
            if m:
                current_heading = f"{m.group(1)} {m.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    safe_filename = sanitize_filename(original_filename.rsplit(".", 1)[0]) + ".csv"
    output_csv_path = os.path.join(OUTPUT_DIR, safe_filename)

    with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for k, v in content_dict.items():
            writer.writerow([k, v.strip()])

    return output_csv_path


@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower()
    uuid_filename = uuid.uuid4().hex + "." + ext
    temp_path = os.path.join(UPLOAD_DIR, uuid_filename)

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    if ext in ["doc", "docx"]:
        pdf_path = convert_doc_to_pdf(temp_path)
    elif ext == "pdf":
        pdf_path = temp_path
    else:
        return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

    try:
        csv_path = extract_pdf_to_csv(pdf_path, file.filename, top_cm, bottom_cm)
        return {"csv_filename": os.path.basename(csv_path)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/download/")
def download(path: str):
    full_path = os.path.join(OUTPUT_DIR, path)
    if not os.path.exists(full_path):
        return JSONResponse(status_code=404, content={"error": "File not found."})
    return FileResponse(full_path, filename=path, media_type="text/csv")
```

---

### ✅ 你需要准备的：

* `convert_doc_to_pdf(path)`：Word ➜ PDF 转换函数（使用 `LibreOffice` CLI 或 `docx2pdf` + `comtypes`）；
* `uploads/` 与 `outputs/`：自动创建；
* 可在 `Docker` 中加入 LibreOffice。

---

需要我补充 `convert_doc_to_pdf` 的实现，或帮你自动构建 Dockerfile 也可以。是否继续？

好的，我们换一种更“流式”的办法：**统一把 PDF 数据读成 bytes，再用 `io.BytesIO` 包装**，这样就不依赖 `UploadFile.file`，也不再传递 `BufferedReader`。下面是最小化的改法。

---

## 1. 修改 `preview.py`：接收 `BytesIO`

```python
# preview.py
import fitz
from uuid import uuid4
import os
import io

def generate_preview_image(data: bytes, top_cm: float, bottom_cm: float) -> str:
    """
    data: PDF 的原始 bytes
    """
    os.makedirs("outputs", exist_ok=True)

    pdf = fitz.open(stream=data, filetype="pdf")
    page = pdf.load_page(0)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_filename = f"{uuid4().hex}_preview.png"
    preview_path = os.path.join("outputs", preview_filename)
    pix.save(preview_path)

    return preview_path
```

> **要点**：删掉对 `UploadFile` 和文件路径的判断，统一用 bytes。

---

## 2. 修改 `/preview/` 路由：用 BytesIO

在 `app.py` 中，改 `/preview/` 处理逻辑，先把上传的（PDF 或转换后的 Word→PDF）都读成 bytes，再传给 `generate_preview_image`：

```python
# app.py
from fastapi import FastAPI, File, UploadFile, Form
from convert_doc import convert_doc_to_pdf
from preview import generate_preview_image
import os

@app.post("/preview/")
async def preview(file: UploadFile = File(...),
                  top_cm: float = Form(...),
                  bottom_cm: float = Form(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext in ("doc", "docx"):
        # 1. 将 Word 转为 PDF，得到临时路径
        pdf_path = convert_doc_to_pdf(file)
        # 2. 读取 PDF 文件 bytes
        with open(pdf_path, "rb") as f:
            data = f.read()
    else:
        # 直接从 UploadFile 读取所有 bytes
        data = await file.read()

    # 3. 调用统一的 bytes 版预览
    preview_path = generate_preview_image(data, top_cm, bottom_cm)
    return {"preview_path": preview_path}
```

> **说明**：
>
> * Word 走转换后读文件 bytes；
> * PDF 直接从 `UploadFile` 里 `await file.read()` 取 bytes；
> * 都不再传 `file` 对象本身，避免 `_io.BufferedReader` 问题。

---

### 3. 重建并测试

```bash
docker build -t pdfstruc-preview-fixed .
docker run -p 8000:8000 pdfstruc-preview-fixed
```

1. 打开页面，上传 `.docx`，点击“预览剪裁”
2. 查看后台日志无错误，右侧应显示生成的 PNG

这样就用 bytes+BytesIO 的方式完全绕过了属性不匹配的问题。


看起来你在 `/preview/` 路由里还在对 Word 转 PDF 后用 `open(..., "rb")` 得到一个 `BufferedReader`，然后把它传给 `generate_preview_image`，所以才进了 `elif isinstance(source, UploadFile)` 之外，落到最后一分支拿 `source.read()`，但 `source` 此时是 `BufferedReader`，没有 `.file`。

最干净的方案就是：**在路由里，永远只给 `generate_preview_image` 传两种类型之一**：

1. 原始的 `UploadFile`（用于 PDF）
2. 字符串路径（用于 Word → PDF）

绝对不要传已经 `open(...)` 的文件流。下面把最小改动展示给你。

---

## 1. 覆盖 `preview.py`

```python
# preview.py
import fitz
from uuid import uuid4
import os
from fastapi import UploadFile

def generate_preview_image(source, top_cm: float, bottom_cm: float) -> str:
    """
    source: UploadFile 或 PDF 文件路径（str）
    """
    os.makedirs("outputs", exist_ok=True)

    if isinstance(source, str):
        pdf = fitz.open(source)
    elif isinstance(source, UploadFile):
        data = source.file.read()
        pdf = fitz.open(stream=data, filetype="pdf")
    else:
        # 不应该到这儿，抛个异常帮你警告
        raise ValueError(f"Unsupported preview source type: {type(source)}")

    page = pdf.load_page(0)
    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    name = f"{uuid4().hex}_preview.png"
    path = os.path.join("outputs", name)
    pix.save(path)
    return path
```

---

## 2. 更新 `app.py` 中的 `/preview/` 路由

```python
# app.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
# … 其他 imports …
from convert_doc import convert_doc_to_pdf
from preview import generate_preview_image

@app.post("/preview/")
async def preview(
    file: UploadFile = File(...),
    top_cm: float = Form(...),
    bottom_cm: float = Form(...)
):
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext in ("doc", "docx"):
        # 不要用 open()，直接拿路径
        pdf_path = convert_doc_to_pdf(file)
        source = pdf_path
    else:
        # 直接传 UploadFile，generate_preview_image 会自己读 .file.read()
        source = file

    preview_path = generate_preview_image(source, top_cm, bottom_cm)
    return {"preview_path": preview_path}
```

---

### 为什么这样能解决

* **不传 `BufferedReader`**：完全去掉 `with open(..., "rb")` 那一行，不再给 `generate_preview_image` 传已经打开的文件流。
* **只传字符串或 UploadFile**：`generate_preview_image` 只处理这两种类型，避免进入错误分支。

完成后，重建容器并测试：

```bash
docker build -t pdfstruc:v3.6 .
docker run -p 8000:8000 pdfstruc:v3.6
```

这时上传 Word 和 PDF 调用“预览剪裁”，都应该能正确生成并显示预览图了。

请用下面的完整版 `preview.py`（覆盖原文件），它能够兼容三种输入类型：

* 字符串路径（转换后的 PDF 文件）
* FastAPI 的 `UploadFile`
* 任何带 `.read()` 方法的二进制流（例如 `open(..., "rb")`）

并确保在 `app.py` 的 `/preview/` 路由中直接传入路径或 `UploadFile`，而 **不再** 对文件做 `open()`，这样就不会出现 `BufferedReader` 没有 `.file` 的问题。

---

### 完整替换：`preview.py`

```python
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
        data = source.file.read()
        pdf = fitz.open(stream=data, filetype="pdf")
    else:
        # 任何有 .read() 方法的流
        data = source.read()
        pdf = fitz.open(stream=data, filetype="pdf")

    # 取第一页
    page = pdf.load_page(0)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_filename = f"{uuid4().hex}_preview.png"
    preview_path = os.path.join("outputs", preview_filename)
    pix.save(preview_path)

    return preview_path
```

---

### 修改 `/preview/` 路由：`app.py`

找到 `app.py` 中的 `/preview/`，改成这样——注意 **不使用** `open()`, 直接传路径或 `UploadFile`:

```python
from convert_doc import convert_doc_to_pdf
from preview import generate_preview_image

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
        # 对 PDF 上传文件，直接传 UploadFile
        preview_path = generate_preview_image(file, top_cm, bottom_cm)

    return {"preview_path": preview_path}
```

---

完成上述两处：

1. **覆盖 `preview.py`**
2. **更新 `app.py` 中的 `/preview/` 处理**

然后重建并运行容器，你就能对 `.doc/.docx` 和 `.pdf` 文件正常生成预览了。



```
INFO:     192.168.65.1:18770 - "GET / HTTP/1.1" 200 OK
convert /tmp/tmpuhxmh7bp/imm领料指导书.docx -> /tmp/tmpuhxmh7bp/imm领料指导书.pdf using filter : writer_pdf_Export
INFO:     192.168.65.1:22621 - "POST /preview/ HTTP/1.1" 500 Internal Server Error
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/uvicorn/protocols/http/h11_impl.py", line 403, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
  File "/usr/local/lib/python3.9/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/fastapi/applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/errors.py", line 187, in __call__
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 73, in app
    response = await f(request)
  File "/usr/local/lib/python3.9/site-packages/fastapi/routing.py", line 301, in app
    raw_response = await run_endpoint_function(
  File "/usr/local/lib/python3.9/site-packages/fastapi/routing.py", line 212, in run_endpoint_function
    return await dependant.call(**values)
  File "/app/app.py", line 35, in preview
    preview_path = generate_preview_image(f, top_cm, bottom_cm)
  File "/app/preview.py", line 7, in generate_preview_image
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
AttributeError: '_io.BufferedReader' object has no attribute 'file'
```

此时 `f` 是一个 \_io.BufferedReader，没有 `.file` 属性，而你在 `generate_preview_image` 里写的是 `source.file.read()`。最简单也是最干净的做法是：

1. **不要在路由里 open() 再传文件对象**，而是直接把字符串路径传给 `generate_preview_image`；
2. **让 `generate_preview_image` 同时兼容“UploadFile”、“文件路径”** 和\*\*“任意文件流”\*\* 三种情况。

---

## 具体修改步骤

### 1. `preview.py`：更新 `generate_preview_image`

把原来的实现删掉，替换为下面这个：

```python
import fitz
from uuid import uuid4
import os
from fastapi import UploadFile

def generate_preview_image(source, top_cm, bottom_cm):
    """
    source: UploadFile | 文件路径(str) | bytes 流(二进制)
    """
    os.makedirs("outputs", exist_ok=True)

    # 1) 根据类型打开 PDF
    if isinstance(source, str):
        # 文件路径
        pdf = fitz.open(source)
    elif isinstance(source, UploadFile):
        # FastAPI 上传文件
        pdf = fitz.open(stream=source.file.read(), filetype="pdf")
    else:
        # 假设是 open(..., "rb") 或者 bytes
        # 如果是 BufferedReader，则 .read() 也能用
        data = source.read() if hasattr(source, "read") else source
        pdf = fitz.open(stream=data, filetype="pdf")

    # 2) 典型做法：预览第一页
    page = pdf.load_page(0)

    # 3) 裁剪坐标
    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    # 4) 渲染并保存
    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_path = f"outputs/{uuid4().hex}_preview.png"
    pix.save(preview_path)

    return preview_path
```

> 这样，无论你传入的是路径、`UploadFile` 还是已经 `open()` 的文件流，它都能正确处理。

---

### 2. `app.py`：调整 `/preview/` 调用

把这一段：

```python
if ext in ("doc", "docx"):
    pdf_path = convert_doc_to_pdf(file)
    with open(pdf_path, "rb") as f:
        preview_path = generate_preview_image(f, top_cm, bottom_cm)
else:
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
```

改为 **直接** 传路径或 `UploadFile`：

```python
if ext in ("doc", "docx"):
    # 转出来的 PDF 是路径
    pdf_path = convert_doc_to_pdf(file)
    preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
else:
    # 直接传 UploadFile
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
```

---

### 3. 重建并测试

```bash
docker build -t pdfstruc:v3.5 .
docker run -p 8000:8000 pdfstruc:v3.5
```

* 对 **.doc/.docx** 点击“预览剪裁”，后台会先转 PDF（路径），再生成预览图；
* 对 **.pdf** 文件，直接用上传流生成预览。

这样就彻底避免了 `_io.BufferedReader` 没有 `.file` 的问题，也让预览功能在所有格式上一致可用。

你不需要把整个 `convert_doc.py` 重写，只要在它里对上传文件名做一次 “清洗”，把空格、`&`、`/` 等字符替换掉，就能让 LibreOffice CLI 正常工作，也方便后续路径处理。下面是改动示例。

---

### 原 `convert_doc.py`

```python
def convert_doc_to_pdf(uploaded_file) -> str:
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, uploaded_file.filename)
    ...
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", "pdf",
        "--outdir", tmp_dir,
        input_path
    ], check=True)
    output_pdf = os.path.join(tmp_dir,
                              os.path.splitext(uploaded_file.filename)[0] + ".pdf")
    return output_pdf
```

---

### 修改后（带文件名清洗）

```python
import os
import re
import subprocess
import tempfile

def convert_doc_to_pdf(uploaded_file) -> str:
    """
    把上传的 .doc/.docx 文件保存到临时目录，先给它一个“安全”不含空格/特殊字符的名字，
    再用 LibreOffice 转 PDF，返回转换后的 PDF 路径。
    """
    # 1) 清洗文件名（去掉空格、&、/，替换为下划线）
    raw = os.path.splitext(uploaded_file.filename)[0]
    safe_stem = re.sub(r'[ \t/&\\\\]+', '_', raw)
    ext = os.path.splitext(uploaded_file.filename)[1]  # 包含“.”的后缀

    # 2) 准备临时目录和文件路径
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, safe_stem + ext)

    # 3) 写入上传内容
    with open(input_path, "wb") as f:
        f.write(uploaded_file.file.read())

    # 4) 调用 LibreOffice CLI 转 PDF
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", "pdf",
        "--outdir", tmp_dir,
        input_path
    ], check=True)

    # 5) 输出 PDF 文件路径（同样用 safe_stem）
    output_pdf = os.path.join(tmp_dir, safe_stem + ".pdf")
    if not os.path.exists(output_pdf):
        raise RuntimeError(f"File at path {output_pdf} does not exist.")
    return output_pdf
```

**改动要点**：

1. **清洗 `uploaded_file.filename`**，生成 `safe_stem`，去除空格和 `&` 等特殊字符；
2. 保存和转换时使用 `safe_stem + ext`，保证 LibreOffice 能正确处理文件；
3. 输出 PDF 也用同样的 `safe_stem`，后续取预览或提取都不会再遇到路径解析问题。

完成这一改动，重建镜像后所有带空格或特殊字符的 Word 文档都能正常转换、预览和提取了。

在你贴的日志里，真正的错误是：你生成的 `csv_path` 里含有 **空格** 和 **`&`**，导致后续文件查找不到：

```
outputs/FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.csv
```

但 `os.path.exists` 自然找不到这种名字（同时浏览器又 URL 编码得不靠谱），所以报 `File at path ... does not exist`。

---

### 核心思路

* **把原始文件名做一次 “清洗”**（sanitize），把空格、`&`、`/` 等不安全字符替换成下划线或减号；
* 生成的文件名再拼接到 `outputs/` 下，就一定能读写到了。

---

## 1. 修改 `process.py`

在文件开头 `import` 区域，确保有：

```python
import os
import re
import fitz
import csv
from uuid import uuid4
```

然后把你的 `process_pdf_and_extract` 里的这一段：

```python
    # 原来的剪裁 + 提取逻辑不变
    base = filename.rsplit(".", 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{base}.csv"
```

**替换为**：

```python
    # —— 清洗文件名：去掉空格、&、/ 等，并用下划线代替 ——  
    raw = filename.rsplit(".", 1)[0]
    safe = re.sub(r'[ \t/&\\\\]+', '_', raw)  # 空格、制表符、/ 和 & 全部替换
    # 确保 outputs 目录存在
    os.makedirs("outputs", exist_ok=True)
    csv_path = os.path.join("outputs", f"{uuid4().hex}_{safe}.csv")
```

这样，无论上传文件叫啥，你最终在 `outputs/` 里看到的就都是类似：

```
outputs/5f8c9ab2_FusionOS_23.1.3安装BF3驱动_Nvqual测试指导书V1.0-zhangfeng_20250412.csv
```

---

## 2. 对 `/download/` 接口的 URL 编码（前端已做，但后端也可以更健壮）

当前你的前端是：

```js
csvLink.href = `/download/?path=${encodeURIComponent(res.path)}`;
```

后端可以继续保留原先逻辑，FastAPI 会自动 URL 解码。只要 `res.path`（也就是 `csv_path` ）里没有空格和特殊字符，就不会再解析错误。

---

## 3. （可选）日志打印调试

如果你想在后台确认文件确实存在，可以临时在 `app.py` 的 `download` 里加：

```python
@app.get("/download/")
async def download(path: str):
    print("Download requested for:", path, "exists?", os.path.exists(path))
    return FileResponse(path, filename=os.path.basename(path))
```

重启后看控制台，会告诉你到底哪个路径不存在。

---

完成以上 **文件名清洗** 改动，重新构建并重启服务：

```bash
docker build -t pdfstruc:v3 .
docker run -p 8000:8000 pdfstruc:v3
```

之后再试：

1. 上传 `FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.docx`；
2. 从前端下载 CSV 链接，应该能成功拿到 `outputs/<uuid>_FusionOS_23.1.3安装BF3驱动_Nvqual测试指导书V1.0-zhangfeng_20250412.csv`。

这样就彻底解决 “找不到文件” 的问题了。

要让预览也支持 Word 文档，最好把 `generate_preview_image` 做两方面改造：

1. **让它能接收 PDF 文件路径**（而不是只接收 `UploadFile` 流）；
2. 在 `/preview/` 路由里，对 `.doc/.docx` 先转换，然后再把路径交给它。

下面是精准的改动步骤。

---

## 1. 修改 `preview.py`

把原来的

```python
import fitz
from uuid import uuid4
import os

def generate_preview_image(file, top_cm, bottom_cm):
    os.makedirs("outputs", exist_ok=True)
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
    page = pdf.load_page(2)
    ...
```

替换为：

```python
import fitz
from uuid import uuid4
import os

def generate_preview_image(source, top_cm, bottom_cm):
    """
    source: 要么是 UploadFile，要么是 PDF 文件路径字符串
    """
    os.makedirs("outputs", exist_ok=True)

    # 1) 打开 PDF
    if isinstance(source, str):
        pdf = fitz.open(source)
    else:
        pdf = fitz.open(stream=source.file.read(), filetype="pdf")

    # 2) 取第 1 页（或你要的页数）
    page = pdf.load_page(0)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_path = f"outputs/{uuid4().hex}_preview.png"
    pix.save(preview_path)
    return preview_path
```

> **要点：**
>
> * 传入字符串时直接 `fitz.open(path)`；
> * 传入 `UploadFile` 时保持原逻辑。

---

## 2. 修改 `app.py` 的 `/preview/` 路由

在文件顶部加入：

```python
from convert_doc import convert_doc_to_pdf
```

然后把 `/preview/` 改为：

```python
@app.post("/preview/")
async def preview(
    file: UploadFile = File(...),
    top_cm: float = Form(...),
    bottom_cm: float = Form(...)
):
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext in ("doc", "docx"):
        # 先转换成 PDF，得到临时路径
        pdf_path = convert_doc_to_pdf(file)
        # 直接用路径调用预览
        preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
    else:
        # PDF 直接走流
        preview_path = generate_preview_image(file, top_cm, bottom_cm)

    return {"preview_path": preview_path}
```

> **注意：** `convert_doc_to_pdf` 需要返回文件路径（字符串），不是 `UploadFile`。

---

### 重启测试

1. 重新构建镜像：

   ```bash
   docker build -t pdfstruc:v3 .
   ```
2. 启动容器并打开页面。
3. 试上传一个 `.docx` 或 `.doc`，点“预览剪裁”，应该在右侧显示生成的 PNG。

这样就能保证 **PDF** 和 **Word** 都能生成预览了。

```
RuntimeError: File at path outputs/FusionOS 23.1.3安装BF3驱动 does not exist.
convert /tmp/tmpjzyi5xil/FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.docx -> /tmp/tmpjzyi5xil/FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.pdf using filter : writer_pdf_Export
INFO:     192.168.65.1:52855 - "POST /process_batch/ HTTP/1.1" 200 OK
INFO:     192.168.65.1:52855 - "GET /download/?path=outputs/FusionOS%2023.1.3%E5%AE%89%E8%A3%85BF3%E9%A9%B1%E5%8A%A8&Nvqual%E6%B5%8B%E8%AF%95%E6%8C%87%E5%AF%BC%E4%B9%A6V1.0-zhangfeng_20250412.csv HTTP/1.1" 500 Internal Server Error
```
是的，预览也需要加上对 Word 文档的转换，思路和批量处理保持一致：先把 `.doc/.docx` 转成临时 PDF，再传给 `generate_preview_image`。下面给出最小化的改动，只改 `app.py` 的 `/preview/` 路由，和（可选）微调 `preview.py` 以接受文件路径：

---

### 1. 在 `app.py` 的头部引入转换函数

```python
from convert_doc import convert_doc_to_pdf
```

### 2. 修改 `/preview/` 接口

把原来的

```python
@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
    return {"preview_path": preview_path}
```

替换为

```python
@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    # 如果是 Word，先转 PDF
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext in ("doc", "docx"):
        # convert_doc_to_pdf 会保存临时 PDF 并返回路径
        pdf_path = convert_doc_to_pdf(file)
        # 打开转换后的文件作为二进制流
        with open(pdf_path, "rb") as f:
            preview_path = generate_preview_image(f, top_cm, bottom_cm)
    else:
        preview_path = generate_preview_image(file, top_cm, bottom_cm)

    return {"preview_path": preview_path}
```

这样：

* **PDF** 文件直接走原逻辑；
* **Word** 文件先用 LibreOffice 转为 PDF，再生成预览图。

---

### 3. （可选）微调 `preview.py` 接口签名

如果你希望 `generate_preview_image` 接受一个文件路径而不是 `UploadFile`，也可以把它改成：

```python
def generate_preview_image(file_or_path, top_cm, bottom_cm):
    os.makedirs("outputs", exist_ok=True)
    # 支持传入路径或 UploadFile
    if isinstance(file_or_path, str):
        pdf = fitz.open(file_or_path)
    else:
        pdf = fitz.open(stream=file_or_path.read(), filetype="pdf")
    ...
```

但其实不改也没问题——我们在上面已经把 Word 的流换成了文件流。

---

完成以上改动后，前端“预览”按钮就能同时预览 PDF 和 Word 文件（转成 PDF 后的片段）了。

下面给出最小化的改动方案，只更新或新增几个文件、几段代码，不用全部重写。

---

## 1. 安装 LibreOffice 与中文字体（修改 `Dockerfile`）

在你的 `Dockerfile` 中，找到安装依赖的地方，替换为下面内容：

```dockerfile
FROM python:3.10-slim

# 开启 UTF-8 环境，安装 LibreOffice 及字体
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt-get update && \
    apt-get install -y libreoffice fonts-noto-cjk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **说明**：
>
> * `libreoffice` 用于 Word→PDF 转换；
> * `fonts-noto-cjk` 解决中文渲染和提取乱码；
> * 保留原有 Python 依赖安装。

---

## 2. 新增 Word→PDF 转换模块 `convert_doc.py`

在项目根或 `app/` 目录下新建 `convert_doc.py`，内容如下：

```python
import subprocess
import os
import tempfile

def convert_doc_to_pdf(uploaded_file) -> str:
    """
    接收 UploadFile，保存到临时文件，再调用 LibreOffice 转 PDF，
    返回生成的 PDF 路径。
    """
    # 保存上传的 Word 文件到临时目录
    suffix = os.path.splitext(uploaded_file.filename)[1].lower()
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, uploaded_file.filename)
    with open(input_path, "wb") as f:
        f.write(uploaded_file.file.read())

    # 调用 libreoffice CLI 转 PDF
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", "pdf",
        "--outdir", tmp_dir,
        input_path
    ], check=True)

    # 返回 PDF 路径
    output_pdf = os.path.join(tmp_dir, os.path.splitext(uploaded_file.filename)[0] + ".pdf")
    if not os.path.exists(output_pdf):
        raise RuntimeError(f"Failed to convert {uploaded_file.filename} to PDF")
    return output_pdf
```

---

## 3. 修改 `process.py`：接入转换逻辑

在文件开头 `import` 区域下方添加：

```python
from convert_doc import convert_doc_to_pdf
```

然后把原来的 `process_pdf_and_extract(file, ...)` 函数改成以下形式，只在开头多处理 Word 文档，后续不变：

```python
def process_pdf_and_extract(file, top_cm, bottom_cm):
    # —— 新增：如果是 .doc/.docx，先转换为 PDF ——  
    filename = file.filename
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in ("doc", "docx"):
        pdf_path = convert_doc_to_pdf(file)
        # 打开转换后的 PDF
        pdf = fitz.open(pdf_path)
    else:
        # 直接打开上传的 PDF 流
        pdf = fitz.open(stream=file.file.read(), filetype="pdf")

    # 原来的剪裁 + 提取逻辑不变
    base = filename.rsplit(".", 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{base}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)
        for b in sorted(blocks, key=lambda b: (b[1], b[0])):
            text = b[4].strip()
            if not text: continue
            m = heading_pattern.match(text)
            if m:
                current_heading = f"{m.group(1)} {m.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    # UTF-8 BOM 写入，防止乱码
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for h, c in content_dict.items():
            writer.writerow([h, c.strip()])

    return csv_path
```

> **说明**：
>
> * `.doc/.docx` 上传后调用 `convert_doc_to_pdf` 得到 PDF 文件路径；
> * 直接读取流的部分保留。

---

## 4. 修改 `app.py`：处理多文件时也支持 Word

在 `from process import ...` 之下加上引入转换模块（可选）：

```python
from convert_doc import convert_doc_to_pdf
```

然后把 `/process_batch/` 接口里的循环改为：

```python
@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        # 直接调用原有函数即可，process_pdf_and_extract 已处理 Word
        csv_path = process_pdf_and_extract(file, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    # 其余不变……
```

预览接口 `/preview/` 保持处理 PDF 流即可；如果想也支持 Word 预览，可以同样转换后再调用 `generate_preview_image`。

---

## 5. 更新 `requirements.txt`

在末尾补充（若尚未添加）：

```txt
# LibreOffice CLI 已由系统安装，这里只需 Python 库
# 无需额外 Python 包
```

无需额外 pip 库改动，只要 `convert_doc.py` 不依赖新包。

---

## 6. 重建并测试

```bash
docker build -t pdfstruc_v3.4 .
docker run -p 8000:8000 pdfstruc_v3.4
```

* 在前端上传 `.docx` 或 `.doc`：会后台自动转 PDF → 剪裁 → 提取 → 返回 CSV。
* 原有上传 PDF 流程未经更改。

---

这样，你只需新增一个模块 `convert_doc.py`、改动 `process.py` 的开头，以及调整 `Dockerfile` 安装 LibreOffice，即可 **无缝集成 Word 转 PDF**，保留所有现有的裁剪预览和 CSV 提取功能。
