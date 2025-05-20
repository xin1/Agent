好的，下面是一个**完整的部署流程**，可以让你将支持 `.pdf`, `.docx`, `.doc` 文件的结构化提取工具（含裁剪预览 + 转 CSV + 下载）部署到 **Docker 容器**中。

---

## 🧱 1. 项目结构

假设你的项目目录如下：

```
pdfstruc/
├── app.py
├── process.py
├── convert_doc.py
├── preview.py
├── zip_util.py
├── requirements.txt
├── Dockerfile
├── static/
│   └── index.html
├── outputs/
└── start.sh
```

---

## 📄 2. `convert_doc.py`（Word转PDF）

```python
# convert_doc.py
import os
import subprocess
from uuid import uuid4

def convert_to_pdf(upload_file, save_dir="converted_pdfs"):
    os.makedirs(save_dir, exist_ok=True)
    filename = upload_file.filename
    file_ext = filename.lower().split('.')[-1]

    unique_name = f"{uuid4().hex}_{filename}"
    input_path = os.path.join(save_dir, unique_name)

    with open(input_path, "wb") as f:
        f.write(upload_file.file.read())

    if file_ext == "pdf":
        return input_path  # 已是 PDF
    elif file_ext in ["doc", "docx"]:
        output_pdf = input_path.rsplit('.', 1)[0] + ".pdf"
        try:
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "pdf", "--outdir", save_dir, input_path
            ], check=True)
            return output_pdf
        except Exception as e:
            raise RuntimeError(f"转换失败: {e}")
    else:
        raise ValueError("不支持的文件类型")
```

---

## 🧠 3. `process.py`（PDF结构化提取）

你已有，关键函数名为 `process_pdf_and_extract(pdf_file, top_cm, bottom_cm)`。

---

## 🖼 4. `preview.py`（生成裁剪预览）

此模块接收 PDF 文件、裁剪上下边界，生成裁剪后图像供用户预览。

---

## 📦 5. `app.py`（FastAPI 主接口）

修改后支持 PDF、Word 自动转换：

```python
# app.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from convert_doc import convert_to_pdf
from process import process_pdf_and_extract
from preview import generate_preview_image
from zip_util import zip_csvs
from uuid import uuid4
from fastapi import HTTPException

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    try:
        pdf_path = convert_to_pdf(file)
        preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
        return {"preview_path": preview_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败：{str(e)}")

@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        try:
            pdf_path = convert_to_pdf(file)
            with open(pdf_path, "rb") as pdf_file:
                class DummyUpload:
                    def __init__(self, filename, file):
                        self.filename = filename
                        self.file = file
                dummy = DummyUpload(os.path.basename(pdf_path), pdf_file)
                csv_path = process_pdf_and_extract(dummy, top_cm, bottom_cm)
                csv_paths.append(csv_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"处理文件出错: {str(e)}")

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}

@app.get("/download/")
async def download(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="文件未找到")
    return FileResponse(path, filename=os.path.basename(path))
```

---

## 📜 6. `requirements.txt`

```txt
fastapi
uvicorn
python-multipart
PyMuPDF
aiofiles
```

---

## 🐳 7. Dockerfile

```Dockerfile
# 使用轻量 Python 镜像
FROM python:3.10-slim

# 安装 LibreOffice
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-noto-cjk \
    poppler-utils \
    && apt-get clean

# 设置工作目录
WORKDIR /app

# 拷贝代码
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要目录
RUN mkdir -p outputs converted_pdfs

# 暴露端口
EXPOSE 8000

# 启动脚本
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ▶️ 8. 启动命令（本地）

在项目目录下运行：

```bash
docker build -t pdfstruc .
docker run -d -p 8000:8000 --name pdfstruc-app pdfstruc
```

访问：[http://localhost:8000](http://localhost:8000)

---

## ✅ 9. 前端支持

你前端 `<input type="file">` 标签需要支持 Word：

```html
<input type="file" id="file" name="file" accept=".pdf,.doc,.docx" multiple>
```

---

## ✅ 10. 常见问题排查

| 问题          | 原因                   | 解决方案                                              |
| ----------- | -------------------- | ------------------------------------------------- |
| 文件处理失败      | LibreOffice 未安装或转换失败 | Dockerfile 已集成                                    |
| 预览路径返回 null | 裁剪出错                 | 检查预览图逻辑是否使用正确裁剪区域                                 |
| 下载失败        | 下载路径未encode或文件不存在    | 使用 `encodeURIComponent(path)` 并检查 `/download/` 实现 |

---

如果你需要我将这套完整项目打包为 GitHub 项目模版或加上前端示例代码，也可以继续告诉我。需要吗？

非常好的问题，确实需要 **返回 PDF 路径**，这样主流程才能继续处理转化后的文件。

在上面的 `convert_doc_to_pdf` 函数中，**已经有 `return output_path`**，意思是：

* 你传入一个 `.docx` 路径
* 它转换为 `.pdf`，保存到 `uploads/xxxx.pdf`
* 然后返回这个路径供主流程使用

如果你希望更明确地看到完整流程如何整合，我现在帮你梳理下：

---

## ✅ 一套完整支持 `.pdf` 和 `.docx` 的流程整合

### 🧱 `convert_docx.py`

```python
import os
import uuid
from docx2pdf import convert

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_docx_to_pdf(file):
    # 保存临时 docx 文件
    suffix = os.path.splitext(file.filename)[-1].lower()
    if suffix != ".docx":
        raise ValueError("只支持 .docx 文件，请手动将 .doc 转换为 .docx")

    temp_docx_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.docx")
    with open(temp_docx_path, "wb") as f:
        f.write(file.file.read())

    temp_pdf_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.pdf")
    convert(temp_docx_path, temp_pdf_path)

    # 清理 docx
    os.remove(temp_docx_path)
    return temp_pdf_path
```

---

### 🧠 修改 `process.py` 支持 PDF 或 Word 文件

```python
from convert_docx import convert_docx_to_pdf
import os, re, csv, fitz
from uuid import uuid4

def process_file_and_extract(file, top_cm, bottom_cm):
    filename = file.filename
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".pdf":
        pdf_path = os.path.join("uploads", f"{uuid4().hex}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(file.file.read())
    elif ext == ".docx":
        pdf_path = convert_docx_to_pdf(file)
    else:
        raise ValueError("仅支持 .pdf 和 .docx 文件")

    pdf = fitz.open(pdf_path)
    filename_base = os.path.splitext(filename)[0]
    csv_path = f"outputs/{uuid4().hex}_{filename_base}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)
        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

        for block in sorted_blocks:
            text = block[4].strip()
            if not text:
                continue
            match = heading_pattern.match(text)
            if match:
                current_heading = f"{match.group(1)} {match.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for heading, content in content_dict.items():
            writer.writerow([heading, content.strip()])

    return csv_path
```

---

### 🚀 更新 `app.py`

```python
@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        try:
            csv_path = process_file_and_extract(file, top_cm, bottom_cm)
            csv_paths.append(csv_path)
        except Exception as e:
            return {"error": str(e)}

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}
```

---

### ✅ 最后记得更新前端 `accept` 属性：

```html
<input type="file" name="files" multiple accept=".pdf,.docx" />
```

---

如果你需要我打包完整结构或修复运行问题，请告诉我你当前的项目结构或发我你已有的文件目录清单，我可以一次性替你处理完整。是否继续？

以下是完整整合的支持 `.doc`, `.docx`, `.pdf` 文件的结构化提取处理流程，包含：

1. 支持上传 `.doc/.docx/.pdf` 的前端页面
2. 后端 `app.py`，统一处理所有格式
3. `process.py`，处理 PDF 提取结构
4. `convert_doc.py`，Word 转 PDF 模块

---

### ✅ 目录结构建议

```
project/
├── app.py
├── convert_doc.py
├── process.py
├── preview.py
├── zip_util.py
├── static/
│   └── index.html
├── outputs/
└── uploads/
```

---

### ✅ convert\_doc.py（新增模块：Word 转 PDF）

```python
import os
import uuid
from docx2pdf import convert

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_doc_to_pdf(input_path, suffix):
    if suffix not in [".docx"]:
        raise ValueError("仅支持 .docx 文件，.doc 文件请先手动另存为 .docx")

    # 输出路径
    output_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.pdf")

    # 临时拷贝文件并转换（因为 docx2pdf 只支持路径）
    temp_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.docx")
    os.rename(input_path, temp_path)

    try:
        convert(temp_path, output_path)
        return output_path
    except Exception as e:
        print("❌ 转换失败:", e)
        raise
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

```

---

### ✅ process.py（处理 PDF 文件）

保持不变：

```python
# ...省略原代码
def process_pdf_and_extract(file, top_cm, bottom_cm):
    # file 可以是 UploadFile 或 文件路径（str）
    if isinstance(file, str):
        pdf = fitz.open(file)
        filename = os.path.splitext(os.path.basename(file))[0]
    else:
        pdf = fitz.open(stream=file.file.read(), filetype="pdf")
        filename = file.filename.rsplit('.', 1)[0]

    # ...保持原逻辑
```

---

### ✅ app.py（支持 doc/docx/pdf 自动处理）

```python
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import shutil
from process import process_pdf_and_extract
from convert_doc import convert_doc_to_pdf
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

def save_upload_file(upload_file: UploadFile):
    temp_path = os.path.join("uploads", upload_file.filename)
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    return temp_path

def convert_if_needed(upload_file: UploadFile):
    suffix = os.path.splitext(upload_file.filename)[1].lower()
    if suffix in [".doc", ".docx"]:
        saved_path = save_upload_file(upload_file)
        return convert_doc_to_pdf(saved_path, suffix)
    elif suffix == ".pdf":
        return upload_file
    else:
        raise ValueError("Unsupported file type")

@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    pdf_path_or_file = convert_if_needed(file)
    preview_path = generate_preview_image(pdf_path_or_file, top_cm, bottom_cm)
    return {"preview_path": preview_path}

@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        pdf_path_or_file = convert_if_needed(file)
        csv_path = process_pdf_and_extract(pdf_path_or_file, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}

@app.get("/download/")
async def download(path: str):
    return FileResponse(path, filename=os.path.basename(path))
```

---

### ✅ static/index.html（更新文件选择器）

```html
<input id="fileInput" type="file" name="files" multiple accept=".pdf,.doc,.docx">
```

---

### 📌 注意事项

1. ✅ `comtypes` 仅支持 Windows，如需跨平台需用 LibreOffice 替代；
2. ✅ 确保机器安装了 Microsoft Word；
3. ✅ `uploads/` 用于临时保存上传的 Word 文件和转换后的 PDF；
4. ✅ 如果你部署在 Docker 中，请说明，我会帮你切换为 LibreOffice 转换方案。

---

是否需要我打包生成一份完整代码 zip，或进一步帮你部署成 Docker 项目？


非常好，保持职责单一是个好习惯。我们可以新建一个模块，比如：

```
convert_doc.py
```

专门负责将 `.doc`、`.docx` 文件转换为 `.pdf`，再由你的主处理逻辑统一处理 PDF。

---

## ✅ convert\_doc.py 示例代码

```python
import os
import tempfile
from pathlib import Path
from docx2pdf import convert
from uuid import uuid4
import shutil

os.makedirs("temp_uploads", exist_ok=True)

def save_upload_file(upload_file) -> str:
    """
    将 UploadFile 保存为临时本地文件，返回文件路径
    """
    temp_filename = f"{uuid4().hex}_{upload_file.filename}"
    temp_path = os.path.join("temp_uploads", temp_filename)
    with open(temp_path, "wb") as f:
        f.write(upload_file.file.read())
    return temp_path


def convert_word_to_pdf(doc_path: str) -> str:
    """
    将 Word 文件（.doc/.docx）转换为 PDF，返回 PDF 路径
    """
    output_dir = tempfile.mkdtemp()
    convert(doc_path, output_dir)
    
    # 找到转换后的 PDF 文件
    for f in Path(output_dir).glob("*.pdf"):
        pdf_temp_path = os.path.join("temp_uploads", f"{uuid4().hex}_{f.name}")
        shutil.move(str(f), pdf_temp_path)
        return pdf_temp_path

    raise RuntimeError("转换 Word 到 PDF 失败")
```

---

## ✅ 如何在 process.py 中使用

在 `process.py` 顶部引入：

```python
from convert_doc import save_upload_file, convert_word_to_pdf
```

然后在 `process_pdf_and_extract()` 中这样用：

```python
def process_pdf_and_extract(file, top_cm, bottom_cm):
    filename = file.filename
    suffix = filename.lower().split('.')[-1]

    # 保存文件
    local_path = save_upload_file(file)

    # 如果是 Word 文件，先转成 PDF
    if suffix in ["doc", "docx"]:
        try:
            local_path = convert_word_to_pdf(local_path)
        except Exception as e:
            raise RuntimeError(f"Word 转换失败: {str(e)}")

    # 打开 PDF 并处理
    pdf = fitz.open(local_path)
    ...
```

---

## ✅ 总结

你现在有了：

* `convert_doc.py`：负责文档保存与 Word 转 PDF
* `process.py`：负责 PDF 剪裁与内容结构提取

结构更清晰、职责更明确。是否需要我一并生成 `convert_doc.py` 文件？或者还想兼容 Linux 的转换方法？


以下是完整的支持 `.pdf`、`.docx` 和 `.doc` 文件的流程及相关代码模块，包括：

* `app.py`：主 FastAPI 接口
* `convert_doc.py`：将 Word 文档（doc/docx）转为 PDF
* `process.py`：结构化处理 PDF 内容并生成 CSV
* `preview.py`：生成 PDF 页面裁剪预览

---

### ✅ 1. `convert_doc.py`（新增：Word 转 PDF）

```python
import os
import uuid
from pathlib import Path

def convert_to_pdf(uploaded_file) -> str:
    from tempfile import NamedTemporaryFile
    from docx import Document
    import subprocess

    suffix = uploaded_file.filename.rsplit('.', 1)[-1].lower()
    tmp_dir = "temp_docs"
    os.makedirs(tmp_dir, exist_ok=True)

    with NamedTemporaryFile(delete=False, dir=tmp_dir, suffix=f".{suffix}") as temp_file:
        temp_file.write(uploaded_file.file.read())
        temp_file_path = temp_file.name

    if suffix == "docx":
        output_path = temp_file_path.replace(".docx", ".pdf")
        try:
            import docx2pdf
            docx2pdf.convert(temp_file_path, output_path)
        except Exception as e:
            raise RuntimeError(f"docx 转换失败: {e}")
    elif suffix == "doc":
        output_path = temp_file_path.replace(".doc", ".pdf")
        # 用 LibreOffice 转换 doc -> pdf
        result = subprocess.run([
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", tmp_dir, temp_file_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError("LibreOffice 转换 doc 失败：" + result.stderr.decode())
    else:
        raise ValueError("不支持的文件类型")

    return output_path
```

> ⚠️ Linux 上需安装 `libreoffice`，Windows 上推荐用 `docx2pdf`。确保 `.docx` 安装了 `docx2pdf`，`.doc` 则使用 LibreOffice。

---

### ✅ 2. `process.py`

```python
import os
import fitz  # PyMuPDF
import csv
import re
from uuid import uuid4

os.makedirs("outputs", exist_ok=True)

def process_pdf_and_extract(file_path, top_cm, bottom_cm):
    pdf = fitz.open(file_path)
    filename = os.path.basename(file_path).rsplit('.', 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{filename}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)

        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

        for block in sorted_blocks:
            text = block[4].strip()
            if not text:
                continue
            match = heading_pattern.match(text)
            if match:
                current_heading = f"{match.group(1)} {match.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for heading, content in content_dict.items():
            writer.writerow([heading, content.strip()])

    return csv_path
```

---

### ✅ 3. `preview.py`

```python
import fitz  # PyMuPDF
import uuid
from convert_doc import convert_to_pdf

def generate_preview_image(file, top_cm, bottom_cm):
    suffix = file.filename.rsplit('.', 1)[-1].lower()
    if suffix in ['doc', 'docx']:
        file_path = convert_to_pdf(file)
    else:
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.file.read())
            file_path = tmp.name

    pdf = fitz.open(file_path)
    page = pdf.load_page(0)
    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(clip=clip)
    preview_path = f"outputs/{uuid.uuid4().hex}_preview.png"
    pix.save(preview_path)

    return preview_path
```

---

### ✅ 4. `app.py`

```python
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from preview import generate_preview_image
from convert_doc import convert_to_pdf
from process import process_pdf_and_extract
from zip_util import zip_csvs
import tempfile

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
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext in ['pdf']:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.file.read())
                path = tmp.name
        elif ext in ['doc', 'docx']:
            path = convert_to_pdf(file)
        else:
            continue
        csv_path = process_pdf_and_extract(path, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}

@app.get("/download/")
async def download(path: str):
    return FileResponse(path, filename=os.path.basename(path))
```

---

### ✅ 补充说明：

1. 安装依赖（部分 Linux 可选）：

```bash
pip install python-docx docx2pdf pymupdf
sudo apt install libreoffice  # 处理 .doc 转换
```

2. 支持文件扩展：
   前端 `<input type="file">` 允许添加 `accept=".pdf,.doc,.docx"` 支持多格式选择。

---

如需我一起更新 `zip_util.py` 或 `index.html` 前端部分，也可以继续告诉我。
